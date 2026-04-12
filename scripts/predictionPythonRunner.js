import fs from "fs";
import path from "path";
import { spawn } from "child_process";

const ROOT_DIR = process.cwd();
const PREDICTION_DIR = path.join(ROOT_DIR, "prediction_python");
const WINDOWS_VENV_PYTHON = path.join(PREDICTION_DIR, ".venv", "Scripts", "python.exe");
const UNIX_VENV_PYTHON = path.join(PREDICTION_DIR, ".venv", "bin", "python");

const mode = process.argv[2];
const modeToScript = {
  api: path.join(PREDICTION_DIR, "02_api.py"),
  train: path.join(PREDICTION_DIR, "01_train_models.py"),
};

function resolvePythonExecutable() {
  const envExecutable = process.env.PREDICTION_PYTHON_EXECUTABLE?.trim();
  if (envExecutable) {
    return envExecutable;
  }

  if (fs.existsSync(WINDOWS_VENV_PYTHON)) {
    return WINDOWS_VENV_PYTHON;
  }

  if (fs.existsSync(UNIX_VENV_PYTHON)) {
    return UNIX_VENV_PYTHON;
  }

  return process.platform === "win32" ? "python" : "python3";
}

if (!modeToScript[mode]) {
  console.error("Usage: node scripts/predictionPythonRunner.js <api|train>");
  process.exit(1);
}

const pythonExecutable = resolvePythonExecutable();
const pythonScript = modeToScript[mode];

const child = spawn(pythonExecutable, [pythonScript], {
  cwd: ROOT_DIR,
  env: {
    ...process.env,
    PYTHONUNBUFFERED: "1",
  },
  stdio: "inherit",
  windowsHide: true,
});

child.on("error", (error) => {
  console.error(`Impossible de lancer Python (${pythonExecutable}) : ${error.message}`);
  process.exit(1);
});

child.on("exit", (code) => {
  process.exit(code ?? 0);
});
