#!/usr/bin/env bash
set -e

echo "[render-build] npm install"
npm install

echo "[render-build] create python venv"
python3 -m venv prediction_python/.venv

echo "[render-build] install python deps"
prediction_python/.venv/bin/python -m pip install --upgrade pip
prediction_python/.venv/bin/python -m pip install -r prediction_python/requirements.txt

if [ ! -f prediction_python/models/models_metadata.json ]; then
  echo "[render-build] train prediction models"
  prediction_python/.venv/bin/python prediction_python/01_train_models.py
fi
