import fs from "fs";
import path from "path";
import { spawnSync } from "child_process";

const ROOT_DIR = process.cwd();
const PREDICTION_DIR = path.join(ROOT_DIR, "prediction_python");
const REQUIREMENTS_FILE = path.join(PREDICTION_DIR, "requirements.txt");
const MODELS_METADATA_FILE = path.join(PREDICTION_DIR, "models", "models_metadata.json");
const WINDOWS_VENV_PYTHON = path.join(PREDICTION_DIR, ".venv", "Scripts", "python.exe");
const UNIX_VENV_PYTHON = path.join(PREDICTION_DIR, ".venv", "bin", "python");

function shouldRunSetup() {
  return process.env.RENDER === "true" || process.env.AUTO_SETUP_PREDICTION_PYTHON === "true";
}

function log(message) {
  console.log(`[prediction-setup] ${message}`);
}

function fail(message) {
  console.error(`[prediction-setup] ${message}`);
  process.exit(1);
}

function runCommand(command, args, description) {
  log(description);
  const result = spawnSync(command, args, {
    cwd: ROOT_DIR,
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1",
    },
    stdio: "inherit",
    windowsHide: true,
  });

  if (result.error) {
    fail(`${description} a echoue: ${result.error.message}`);
  }

  if (result.status !== 0) {
    fail(`${description} a echoue avec le code ${result.status}.`);
  }
}

function getSystemPythonExecutable() {
  const envExecutable = process.env.PREDICTION_PYTHON_EXECUTABLE?.trim();
  if (envExecutable) {
    return envExecutable;
  }

  return process.platform === "win32" ? "python" : "python3";
}

function getVenvPythonExecutable() {
  if (fs.existsSync(WINDOWS_VENV_PYTHON)) {
    return WINDOWS_VENV_PYTHON;
  }

  if (fs.existsSync(UNIX_VENV_PYTHON)) {
    return UNIX_VENV_PYTHON;
  }

  return null;
}

function ensurePredictionFilesExist() {
  if (!fs.existsSync(PREDICTION_DIR)) {
    fail(`Dossier prediction introuvable: ${PREDICTION_DIR}`);
  }

  if (!fs.existsSync(REQUIREMENTS_FILE)) {
    fail(`Fichier requirements introuvable: ${REQUIREMENTS_FILE}`);
  }
}

function main() {
  if (!shouldRunSetup()) {
    log("setup Python ignore hors Render.");
    return;
  }

  ensurePredictionFilesExist();

  const systemPython = getSystemPythonExecutable();
  const venvPython = getVenvPythonExecutable();

  if (!venvPython) {
    runCommand(systemPython, ["-m", "venv", path.join("prediction_python", ".venv")], "creation du venv Python");
  }

  const resolvedVenvPython = getVenvPythonExecutable();
  if (!resolvedVenvPython) {
    fail("Impossible de resoudre le binaire Python du venv.");
  }

  runCommand(resolvedVenvPython, ["-m", "pip", "install", "--upgrade", "pip"], "mise a jour de pip");
  runCommand(resolvedVenvPython, ["-m", "pip", "install", "-r", path.join("prediction_python", "requirements.txt")], "installation des dependances Python");

  if (!fs.existsSync(MODELS_METADATA_FILE)) {
    runCommand(resolvedVenvPython, [path.join("prediction_python", "01_train_models.py")], "entrainement des modeles Python");
  } else {
    log("artefacts Python deja presents, entrainement saute.");
  }
}

main();
