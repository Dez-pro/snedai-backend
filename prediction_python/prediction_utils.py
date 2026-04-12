from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = ROOT_DIR.parent
DATASET_PATH = BACKEND_ROOT / "data" / "dataset_prediction_fin_2026.xlsx"
MODELS_DIR = ROOT_DIR / "models"
MODELS_METADATA_PATH = MODELS_DIR / "models_metadata.json"

HISTORY_SHEET = "06_Synthetic_History"
OBSERVED_REFERENCE_SHEET = "01_Observed_Reference"

TARGETS: List[Dict[str, str]] = [
    {
        "key": "temperature_c",
        "name": "Temperature",
        "unit": "deg C",
        "source_column": "Temperature ℃",
        "model_file": "model_temperature_c.joblib",
    },
    {
        "key": "humidity_pct",
        "name": "Humidite",
        "unit": "%",
        "source_column": "Humidity %",
        "model_file": "model_humidity_pct.joblib",
    },
    {
        "key": "pressure_hpa",
        "name": "Pression",
        "unit": "hPa",
        "source_column": "Pressure hPa",
        "model_file": "model_pressure_hpa.joblib",
    },
    {
        "key": "so2_ug_m3",
        "name": "SO2",
        "unit": "ug/m3",
        "source_column": "SO2 μg/m³",
        "model_file": "model_so2_ug_m3.joblib",
    },
    {
        "key": "co_mg_m3",
        "name": "CO",
        "unit": "mg/m3",
        "source_column": "CO mg/m³",
        "model_file": "model_co_mg_m3.joblib",
    },
    {
        "key": "no2_ug_m3",
        "name": "NO2",
        "unit": "ug/m3",
        "source_column": "NO2 μg/m³",
        "model_file": "model_no2_ug_m3.joblib",
    },
    {
        "key": "pm1_ug_m3",
        "name": "PM1.0",
        "unit": "ug/m3",
        "source_column": "PM1.0 μg/m³",
        "model_file": "model_pm1_ug_m3.joblib",
    },
    {
        "key": "pm25_ug_m3",
        "name": "PM2.5",
        "unit": "ug/m3",
        "source_column": "PM2.5 μg/m³",
        "model_file": "model_pm25_ug_m3.joblib",
    },
    {
        "key": "pm10_ug_m3",
        "name": "PM10",
        "unit": "ug/m3",
        "source_column": "PM10 μg/m³",
        "model_file": "model_pm10_ug_m3.joblib",
    },
    {
        "key": "h2s_ug_m3",
        "name": "H2S",
        "unit": "ug/m3",
        "source_column": "H2S μg/m³",
        "model_file": "model_h2s_ug_m3.joblib",
    },
    {
        "key": "co2_mg_m3",
        "name": "CO2",
        "unit": "mg/m3",
        "source_column": "CO2 mg/m³",
        "model_file": "model_co2_mg_m3.joblib",
    },
]

TARGET_KEYS = [target["key"] for target in TARGETS]
TARGETS_BY_KEY = {target["key"]: target for target in TARGETS}

RENAME_COLUMNS = {
    "DateReelle": "date",
    "SiteID": "site_id",
    "Site": "site",
    "ZoneID": "zone_id",
    "ZoneGeo": "zone",
    "CapteurID": "capteur_id",
    "Abs.Alt m": "altitude_m",
    "Longitude": "longitude",
    "Latitude": "latitude",
    "Temperature ℃": "temperature_c",
    "Humidity %": "humidity_pct",
    "Pressure hPa": "pressure_hpa",
    "SO2 μg/m³": "so2_ug_m3",
    "CO mg/m³": "co_mg_m3",
    "NO2 μg/m³": "no2_ug_m3",
    "PM1.0 μg/m³": "pm1_ug_m3",
    "PM2.5 μg/m³": "pm25_ug_m3",
    "PM10 μg/m³": "pm10_ug_m3",
    "H2S μg/m³": "h2s_ug_m3",
    "CO2 mg/m³": "co2_mg_m3",
}

STATIC_COLUMNS = [
    "date",
    "site_id",
    "site",
    "zone_id",
    "zone",
    "capteur_id",
    "altitude_m",
    "longitude",
    "latitude",
]

CALENDAR_COLUMNS = [
    "site_code",
    "month",
    "day_of_week",
    "is_weekend",
    "day_of_year",
]


def add_days(date_value: pd.Timestamp | str, days: int) -> str:
    timestamp = pd.Timestamp(date_value)
    return (timestamp + pd.Timedelta(days=days)).strftime("%Y-%m-%d")


def normalize_site_name(site: str) -> str:
    return str(site or "").strip().upper()


def load_history_dataframe() -> pd.DataFrame:
    dataframe = pd.read_excel(DATASET_PATH, sheet_name=HISTORY_SHEET)
    dataframe = dataframe.rename(columns=RENAME_COLUMNS)

    dataframe["date"] = pd.to_datetime(dataframe["date"])
    dataframe["site"] = dataframe["site"].map(normalize_site_name)
    dataframe = dataframe.sort_values(["site", "date"]).reset_index(drop=True)
    dataframe["site_code"] = dataframe["site"].astype("category").cat.codes

    if "month" not in dataframe.columns:
        dataframe["month"] = dataframe["date"].dt.month
    if "day_of_week" not in dataframe.columns:
        dataframe["day_of_week"] = dataframe["date"].dt.weekday
    if "is_weekend" not in dataframe.columns:
        dataframe["is_weekend"] = (dataframe["day_of_week"] >= 5).astype(int)
    if "day_of_year" not in dataframe.columns:
        dataframe["day_of_year"] = dataframe["date"].dt.dayofyear

    numeric_columns = [
        "altitude_m",
        "longitude",
        "latitude",
        *TARGET_KEYS,
        "month",
        "day_of_week",
        "is_weekend",
        "day_of_year",
    ]
    dataframe[numeric_columns] = dataframe[numeric_columns].apply(pd.to_numeric, errors="coerce")

    return dataframe


def load_observed_reference_dataframe() -> pd.DataFrame:
    dataframe = pd.read_excel(DATASET_PATH, sheet_name=OBSERVED_REFERENCE_SHEET)
    dataframe = dataframe.rename(columns=RENAME_COLUMNS)
    dataframe["date"] = pd.to_datetime(dataframe["date"])
    dataframe["site"] = dataframe["site"].map(normalize_site_name)
    dataframe = dataframe.sort_values(["site", "date"]).reset_index(drop=True)

    numeric_columns = [
        "altitude_m",
        "longitude",
        "latitude",
        *TARGET_KEYS,
    ]
    dataframe[numeric_columns] = dataframe[numeric_columns].apply(pd.to_numeric, errors="coerce")

    return dataframe


def build_training_dataframe(history_df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    dataframe = history_df.copy()

    for target_key in TARGET_KEYS:
        grouped = dataframe.groupby("site")[target_key]
        dataframe[f"{target_key}_lag1"] = grouped.shift(1)
        dataframe[f"{target_key}_roll3"] = grouped.transform(
            lambda series: series.shift(1).rolling(3).mean()
        )
        dataframe[f"{target_key}_roll7"] = grouped.transform(
            lambda series: series.shift(1).rolling(7).mean()
        )
        dataframe[f"target_{target_key}_j1"] = grouped.shift(-1)

    feature_columns = CALENDAR_COLUMNS.copy()
    for target_key in TARGET_KEYS:
        feature_columns.extend(
            [
                f"{target_key}_lag1",
                f"{target_key}_roll3",
                f"{target_key}_roll7",
            ]
        )

    target_columns = [f"target_{target_key}_j1" for target_key in TARGET_KEYS]
    training_df = dataframe.dropna(subset=feature_columns + target_columns).copy()
    training_df = training_df.sort_values(["date", "site"]).reset_index(drop=True)

    return training_df, feature_columns


def build_chronological_splits(training_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    unique_dates = sorted(training_df["date"].dt.normalize().unique())
    train_end = int(len(unique_dates) * 0.70)
    validation_end = int(len(unique_dates) * 0.85)

    train_dates = set(unique_dates[:train_end])
    validation_dates = set(unique_dates[train_end:validation_end])
    test_dates = set(unique_dates[validation_end:])

    train_df = training_df[training_df["date"].dt.normalize().isin(train_dates)].copy()
    validation_df = training_df[
        training_df["date"].dt.normalize().isin(validation_dates)
    ].copy()
    test_df = training_df[training_df["date"].dt.normalize().isin(test_dates)].copy()

    return train_df, validation_df, test_df


def build_site_metadata(history_df: pd.DataFrame) -> list[dict]:
    metadata = []

    for site_name, site_df in history_df.groupby("site"):
        latest_row = site_df.iloc[-1]
        metadata.append(
            {
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
        )

    return metadata


def get_coverage(history_df: pd.DataFrame, forecast_end: str = "2026-12-31") -> dict:
    historical_start = history_df["date"].min().strftime("%Y-%m-%d")
    historical_end = history_df["date"].max().strftime("%Y-%m-%d")

    return {
        "historical_start": historical_start,
        "historical_end": historical_end,
        "forecast_start": add_days(historical_end, 1),
        "forecast_end": forecast_end,
    }
