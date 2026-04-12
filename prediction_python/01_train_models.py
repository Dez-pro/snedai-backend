"""
=============================================================================
AirData - Backend Python de prediction journaliere
Entrainement de 11 modeles XGBoost (un par variable environnementale)
=============================================================================
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from prediction_utils import (
    DATASET_PATH,
    MODELS_DIR,
    MODELS_METADATA_PATH,
    TARGETS,
    TARGET_KEYS,
    build_chronological_splits,
    build_site_metadata,
    build_training_dataframe,
    get_coverage,
    load_history_dataframe,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [PREDICTION PYTHON] - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

XGB_PARAMS = {
    "n_estimators": 260,
    "max_depth": 5,
    "learning_rate": 0.05,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "objective": "reg:squarederror",
    "n_jobs": -1,
    "random_state": 42,
    "eval_metric": "rmse",
    "early_stopping_rounds": 20,
}


def train_all_models() -> None:
    logger.info("=" * 70)
    logger.info("AIRDATA PYTHON - ENTRAINEMENT DES MODELES JOURNALIERS")
    logger.info("=" * 70)

    history_df = load_history_dataframe()
    training_df, feature_columns = build_training_dataframe(history_df)
    train_df, validation_df, test_df = build_chronological_splits(training_df)
    coverage = get_coverage(history_df)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    metadata = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": {
            "file": DATASET_PATH.name,
            "path": str(DATASET_PATH),
            "training_rows": int(len(training_df)),
        },
        "coverage": coverage,
        "feature_columns": feature_columns,
        "sites": build_site_metadata(history_df),
        "targets": {},
    }

    logger.info("Dataset: %s", DATASET_PATH)
    logger.info("Historique: %s lignes", len(history_df))
    logger.info("Training frame: %s lignes", len(training_df))
    logger.info(
        "Split chronologique -> train: %s | validation: %s | test: %s",
        len(train_df),
        len(validation_df),
        len(test_df),
    )

    for index, target in enumerate(TARGETS, start=1):
        target_key = target["key"]
        target_column = f"target_{target_key}_j1"
        scaler_path = MODELS_DIR / target["model_file"].replace(".joblib", "_scaler.joblib")
        model_path = MODELS_DIR / target["model_file"]

        logger.info("-" * 70)
        logger.info("[%s/%s] Entrainement -> %s", index, len(TARGETS), target["name"])

        X_train = train_df[feature_columns]
        y_train = train_df[target_column]

        X_validation = validation_df[feature_columns]
        y_validation = validation_df[target_column]

        X_test = test_df[feature_columns]
        y_test = test_df[target_column]

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_validation_scaled = scaler.transform(X_validation)
        X_test_scaled = scaler.transform(X_test)

        model = XGBRegressor(**XGB_PARAMS)
        model.fit(
            X_train_scaled,
            y_train,
            eval_set=[(X_validation_scaled, y_validation)],
            verbose=False,
        )

        predictions = model.predict(X_test_scaled)

        mae = mean_absolute_error(y_test, predictions)
        rmse = np.sqrt(mean_squared_error(y_test, predictions))
        r2 = r2_score(y_test, predictions)

        joblib.dump(model, model_path)
        joblib.dump(scaler, scaler_path)

        metadata["targets"][target_key] = {
            "name": target["name"],
            "unit": target["unit"],
            "source_column": target["source_column"],
            "target_column": target_column,
            "model_file": model_path.name,
            "scaler_file": scaler_path.name,
            "train_rows": int(len(train_df)),
            "validation_rows": int(len(validation_df)),
            "test_rows": int(len(test_df)),
            "min_target": float(np.min(y_train)),
            "max_target": float(np.max(y_train)),
            "mean_target": float(np.mean(y_train)),
            "metrics": {
                "mae": round(float(mae), 4),
                "rmse": round(float(rmse), 4),
                "r2": round(float(r2), 4),
            },
        }

        logger.info("MAE  : %.4f %s", mae, target["unit"])
        logger.info("RMSE : %.4f %s", rmse, target["unit"])
        logger.info("R2   : %.4f", r2)
        logger.info("Model : %s", model_path.name)
        logger.info("Scaler: %s", scaler_path.name)

    with MODELS_METADATA_PATH.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)

    logger.info("-" * 70)
    logger.info("Fichier metadata sauvegarde -> %s", MODELS_METADATA_PATH.name)
    logger.info("Entrainement termine.")


if __name__ == "__main__":
    train_all_models()
