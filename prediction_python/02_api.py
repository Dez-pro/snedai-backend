"""
=============================================================================
AirData - API Python de prediction journaliere
Inspirée du projet airdata d'origine, adaptee au dataset journalier valide
=============================================================================
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, List

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from prediction_utils import (
    DATASET_PATH,
    MODELS_DIR,
    MODELS_METADATA_PATH,
    TARGETS,
    TARGET_KEYS,
    TARGETS_BY_KEY,
    add_days,
    get_coverage,
    load_history_dataframe,
    load_observed_reference_dataframe,
    normalize_site_name,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AIRDATA PYTHON API] %(levelname)s %(message)s",
)
logger = logging.getLogger("airdata_python_api")

MODELS: Dict[str, object] = {}
SCALERS: Dict[str, object] = {}
METADATA: Dict[str, object] = {}
SITE_ALIASES: Dict[str, str] = {}
SITE_METADATA: Dict[str, dict] = {}
HISTORY_MAP: Dict[str, Dict[str, dict]] = {}
OBSERVED_REFERENCE_MAP: Dict[str, Dict[str, dict]] = {}
FORECAST_MAP: Dict[str, Dict[str, dict]] = {}
SITE_SEQUENCE_MAP: Dict[str, List[dict]] = {}
FEATURE_COLUMNS: List[str] = []


class PredictRequest(BaseModel):
    site: str = Field(
        ...,
        description="MISSION ZI, MISSION ANOUMABO, ZI ou ANOUMABO",
        examples=["MISSION ZI"],
    )
    date: str = Field(
        ...,
        description="Date de prediction au format AAAA-MM-JJ",
        examples=["2026-04-12"],
    )


class SeriesRequest(BaseModel):
    site: str = Field(
        ...,
        description="MISSION ZI, MISSION ANOUMABO, ZI ou ANOUMABO",
        examples=["MISSION ZI"],
    )
    startDate: str = Field(
        ...,
        description="Date de debut au format AAAA-MM-JJ",
        examples=["2026-04-10"],
    )
    endDate: str = Field(
        ...,
        description="Date de fin au format AAAA-MM-JJ",
        examples=["2026-04-15"],
    )


app = FastAPI(
    title="AirData Python - Prediction journaliere environnementale",
    description=(
        "API Python proche du projet airdata d'origine, adaptee au dataset "
        "journalier valide et aux regles de couverture du projet."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def validate_date(date_str: str) -> str:
    try:
        return pd.Timestamp(date_str).strftime("%Y-%m-%d")
    except Exception as error:  # pragma: no cover - validation simple
        raise HTTPException(
            status_code=400,
            detail=f"Date invalide : '{date_str}'. Format attendu : AAAA-MM-JJ",
        ) from error


def get_site_metadata_map(history_df: pd.DataFrame) -> Dict[str, dict]:
    metadata = {}

    for site_name, site_df in history_df.groupby("site"):
        latest_row = site_df.iloc[-1]
        metadata[site_name] = {
            "site": site_name,
            "site_id": latest_row["site_id"],
            "zone_id": latest_row["zone_id"],
            "zone": latest_row["zone"],
            "capteur_id": latest_row["capteur_id"],
            "altitude_m": float(latest_row["altitude_m"]),
            "longitude": float(latest_row["longitude"]),
            "latitude": float(latest_row["latitude"]),
            "site_code": int(latest_row["site_code"]),
        }

    return metadata


def build_aliases(site_metadata_map: Dict[str, dict]) -> Dict[str, str]:
    aliases = {}

    for site_name in site_metadata_map:
        normalized = normalize_site_name(site_name)
        aliases[normalized] = site_name
        aliases[normalized.replace("MISSION ", "")] = site_name

    return aliases


def build_record_map(dataframe: pd.DataFrame, source: str) -> Dict[str, Dict[str, dict]]:
    record_map: Dict[str, Dict[str, dict]] = {}

    for _, row in dataframe.iterrows():
        site_name = row["site"]
        iso_date = row["date"].strftime("%Y-%m-%d")
        record_map.setdefault(site_name, {})
        record_map[site_name][iso_date] = {
            "source": source,
            "date": iso_date,
            "values": {target_key: float(row[target_key]) for target_key in TARGET_KEYS},
        }

    return record_map


def build_site_sequence(history_df: pd.DataFrame, site_name: str) -> List[dict]:
    site_df = history_df[history_df["site"] == site_name].sort_values("date")
    sequence = []

    for _, row in site_df.iterrows():
        sequence.append(
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "values": {target_key: float(row[target_key]) for target_key in TARGET_KEYS},
            }
        )

    return sequence


def build_feature_row(records: List[dict], site_code: int, target_date: str) -> pd.DataFrame:
    if len(records) < 7:
        raise HTTPException(
            status_code=500,
            detail="Historique insuffisant pour construire les features de prediction.",
        )

    date_value = pd.Timestamp(target_date)
    row = {
        "site_code": site_code,
        "month": int(date_value.month),
        "day_of_week": int(date_value.weekday()),
        "is_weekend": int(date_value.weekday() >= 5),
        "day_of_year": int(date_value.day_of_year),
    }

    for target_key in TARGET_KEYS:
        values = [record["values"][target_key] for record in records[-7:]]
        row[f"{target_key}_lag1"] = float(values[-1])
        row[f"{target_key}_roll3"] = float(sum(values[-3:]) / 3)
        row[f"{target_key}_roll7"] = float(sum(values) / 7)

    return pd.DataFrame([row], columns=FEATURE_COLUMNS)


def predict_next_day(records: List[dict], site_code: int, target_date: str) -> dict:
    feature_frame = build_feature_row(records, site_code, target_date)
    predictions = {}

    for target in TARGETS:
        target_key = target["key"]
        scaler = SCALERS[target_key]
        model = MODELS[target_key]
        target_info = METADATA["targets"][target_key]

        features_scaled = scaler.transform(feature_frame)
        value = float(model.predict(features_scaled)[0])
        value = max(target_info["min_target"], min(target_info["max_target"], value))
        predictions[target_key] = round(value, 3)

    return predictions


def initialize_forecast_state(history_df: pd.DataFrame) -> tuple[Dict[str, Dict[str, dict]], Dict[str, List[dict]]]:
    forecast_cache: Dict[str, Dict[str, dict]] = {}
    sequence_map: Dict[str, List[dict]] = {}

    for site_name in SITE_METADATA:
        forecast_cache[site_name] = {}
        sequence_map[site_name] = build_site_sequence(history_df, site_name)

    return forecast_cache, sequence_map


def ensure_forecast_available(site_name: str, iso_date: str) -> None:
    coverage = METADATA["coverage"]

    if iso_date < coverage["forecast_start"]:
        return

    site_forecasts = FORECAST_MAP.setdefault(site_name, {})
    if iso_date in site_forecasts:
        return

    site_sequence = SITE_SEQUENCE_MAP.get(site_name)
    if not site_sequence:
        raise HTTPException(
            status_code=500,
            detail=f"Sequence de donnees introuvable pour le site {site_name}.",
        )

    site_meta = SITE_METADATA[site_name]
    next_date = add_days(site_sequence[-1]["date"], 1)

    while next_date <= iso_date and next_date <= coverage["forecast_end"]:
        predictions = predict_next_day(site_sequence, site_meta["site_code"], next_date)
        forecast_record = {
            "source": "forecast",
            "date": next_date,
            "values": predictions,
        }
        site_forecasts[next_date] = forecast_record
        site_sequence.append(forecast_record)
        next_date = add_days(next_date, 1)


def format_prediction_payload(site_name: str, record: dict) -> dict:
    return {
        "site": {
            "site": site_name,
            "site_id": SITE_METADATA[site_name]["site_id"],
            "zone_id": SITE_METADATA[site_name]["zone_id"],
            "zone": SITE_METADATA[site_name]["zone"],
            "capteur_id": SITE_METADATA[site_name]["capteur_id"],
            "altitude_m": SITE_METADATA[site_name]["altitude_m"],
            "longitude": SITE_METADATA[site_name]["longitude"],
            "latitude": SITE_METADATA[site_name]["latitude"],
        },
        "date": record["date"],
        "mode": "forecast" if record["source"] == "forecast" else "historical",
        "source": record["source"],
        "coverage": METADATA["coverage"],
        "data_version": Path(METADATA["dataset"]["file"]).stem,
        "predictions": {
            target_key: {
                "label": TARGETS_BY_KEY[target_key]["name"],
                "unit": TARGETS_BY_KEY[target_key]["unit"],
                "value": record["values"][target_key],
            }
            for target_key in TARGET_KEYS
        },
    }


def get_record_for_date(site_name: str, iso_date: str) -> dict:
    coverage = METADATA["coverage"]

    if iso_date < coverage["historical_start"] or iso_date > coverage["forecast_end"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"La date '{iso_date}' n'est pas couverte.",
                "coverage": coverage,
            },
        )

    if iso_date <= coverage["historical_end"]:
        observed_record = OBSERVED_REFERENCE_MAP.get(site_name, {}).get(iso_date)
        if observed_record:
            return observed_record

        historical_record = HISTORY_MAP.get(site_name, {}).get(iso_date)
        if historical_record:
            return historical_record

        raise HTTPException(
            status_code=404,
            detail=f"Aucune donnee historique disponible pour {site_name} a la date {iso_date}.",
        )

    ensure_forecast_available(site_name, iso_date)

    forecast_record = FORECAST_MAP.get(site_name, {}).get(iso_date)
    if not forecast_record:
        raise HTTPException(
            status_code=404,
            detail=f"Aucune prevision disponible pour {site_name} a la date {iso_date}.",
        )

    return forecast_record


@app.on_event("startup")
def startup_load_models() -> None:
    global METADATA, FEATURE_COLUMNS, SITE_METADATA, SITE_ALIASES
    global HISTORY_MAP, OBSERVED_REFERENCE_MAP, FORECAST_MAP, SITE_SEQUENCE_MAP

    if not MODELS_METADATA_PATH.exists():
        raise RuntimeError(
            "Le fichier models_metadata.json est introuvable. "
            "Lance d'abord: python 01_train_models.py"
        )

    with MODELS_METADATA_PATH.open("r", encoding="utf-8") as file:
        METADATA = json.load(file)

    FEATURE_COLUMNS = METADATA["feature_columns"]

    for target in TARGETS:
        target_key = target["key"]
        model_info = METADATA["targets"][target_key]
        MODELS[target_key] = joblib.load(MODELS_DIR / model_info["model_file"])
        SCALERS[target_key] = joblib.load(MODELS_DIR / model_info["scaler_file"])

    history_df = load_history_dataframe()
    observed_reference_df = load_observed_reference_dataframe()

    SITE_METADATA = get_site_metadata_map(history_df)
    SITE_ALIASES = build_aliases(SITE_METADATA)

    HISTORY_MAP = build_record_map(history_df, "synthetic_history")
    OBSERVED_REFERENCE_MAP = build_record_map(
        observed_reference_df,
        "observed_reference",
    )
    FORECAST_MAP, SITE_SEQUENCE_MAP = initialize_forecast_state(history_df)

    logger.info("Dataset charge : %s", DATASET_PATH)
    logger.info("Modeles charges : %s", len(MODELS))
    logger.info("Sites disponibles : %s", list(SITE_METADATA.keys()))
    logger.info("Couverture : %s", METADATA["coverage"])
    logger.info("Generation des previsions : mode paresseux")


@app.get("/")
def root() -> dict:
    return {
        "success": True,
        "message": "API Python de prediction environnementale operationnelle.",
        "routes": {
            "health": "/health",
            "meta": "/meta",
            "predict": "POST /predict",
        },
    }


@app.get("/health")
def health() -> dict:
    return {
        "success": True,
        "status": "ok",
        "models_loaded": len(MODELS),
    }


@app.get("/meta")
def meta() -> dict:
    return {
        "success": True,
        "dataset": METADATA["dataset"],
        "coverage": METADATA["coverage"],
        "sites": list(SITE_METADATA.keys()),
        "targets": {
            target_key: {
                "name": target_info["name"],
                "unit": target_info["unit"],
                "model_file": target_info["model_file"],
                "metrics": target_info["metrics"],
            }
            for target_key, target_info in METADATA["targets"].items()
        },
    }


@app.post("/predict")
def predict(request: PredictRequest) -> dict:
    normalized_site = normalize_site_name(request.site)
    site_name = SITE_ALIASES.get(normalized_site)

    if not site_name:
        raise HTTPException(
            status_code=400,
            detail=f"Site inconnu : '{request.site}'. Choix possibles : {list(SITE_METADATA.keys())}",
        )

    iso_date = validate_date(request.date)
    record = get_record_for_date(site_name, iso_date)

    return {
        "success": True,
        **format_prediction_payload(site_name, record),
    }


@app.post("/series")
def predict_series(request: SeriesRequest) -> dict:
    normalized_site = normalize_site_name(request.site)
    site_name = SITE_ALIASES.get(normalized_site)

    if not site_name:
        raise HTTPException(
            status_code=400,
            detail=f"Site inconnu : '{request.site}'. Choix possibles : {list(SITE_METADATA.keys())}",
        )

    start_date = validate_date(request.startDate)
    end_date = validate_date(request.endDate)

    if end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail="La date de fin doit etre superieure ou egale a la date de debut.",
        )

    items = []
    current_date = start_date

    while current_date <= end_date:
        record = get_record_for_date(site_name, current_date)
        items.append(format_prediction_payload(site_name, record))
        current_date = add_days(current_date, 1)

    return {
        "success": True,
        "site": {
            "site": site_name,
            "site_id": SITE_METADATA[site_name]["site_id"],
            "zone_id": SITE_METADATA[site_name]["zone_id"],
            "zone": SITE_METADATA[site_name]["zone"],
            "capteur_id": SITE_METADATA[site_name]["capteur_id"],
            "altitude_m": SITE_METADATA[site_name]["altitude_m"],
            "longitude": SITE_METADATA[site_name]["longitude"],
            "latitude": SITE_METADATA[site_name]["latitude"],
        },
        "coverage": METADATA["coverage"],
        "count": len(items),
        "items": items,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PREDICTION_PYTHON_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
