# Prediction Python

Module Python de prediction journaliere, proche du projet `airdata` d'origine.

## Fichiers

- `01_train_models.py` : entraine un modele par variable environnementale et sauvegarde les `.joblib`
- `02_api.py` : expose une API FastAPI avec `GET /meta`, `POST /predict`, `POST /series`
- `prediction_utils.py` : fonctions communes de chargement et de preparation des donnees
- `models/` : dossier des modeles Python sauvegardes

## Dataset utilise

Le module lit le dataset local du backend :

- `../data/dataset_prediction_fin_2026.xlsx`

## Variables predites

- Temperature
- Humidite
- Pression
- SO2
- CO
- NO2
- PM1.0
- PM2.5
- PM10
- H2S
- CO2

## Lancer l'entrainement

Depuis la racine du backend :

```bash
npm run prediction:train
```

Ou directement en Python :

```bash
cd prediction_python
.venv\\Scripts\\python.exe -m pip install -r requirements.txt
.venv\\Scripts\\python.exe 01_train_models.py
```

## Lancer l'API

Depuis la racine du backend :

```bash
npm run prediction:api
```

Ou directement en Python :

```bash
cd prediction_python
.venv\\Scripts\\python.exe 02_api.py
```

- `POST /predict` attend :

- `site`
- `date` au format `AAAA-MM-JJ`

- `POST /series` attend :

- `site`
- `startDate`
- `endDate`

## Regles de couverture

- `2024-01-01` a `2026-04-11` : donnees couvertes
- `2026-04-12` a `2026-12-31` : previsions calculees
- hors plage : date non couverte
