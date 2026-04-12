import fetch from "node-fetch";
import fs from "fs";
import path from "path";
import { spawn } from "child_process";

const DEFAULT_PYTHON_API_URL = process.env.PREDICTION_PYTHON_API_URL || "http://127.0.0.1:8000";
const REQUEST_TIMEOUT_MS = Number(process.env.PREDICTION_PYTHON_TIMEOUT_MS || 15000);
const STARTUP_TIMEOUT_MS = Number(process.env.PREDICTION_PYTHON_STARTUP_TIMEOUT_MS || 120000);
const HEALTH_CHECK_INTERVAL_MS = 1500;
const AUTO_START_PYTHON_ENGINE = process.env.PREDICTION_PYTHON_AUTO_START !== "false";
const PYTHON_VENV_EXECUTABLE = path.join(
  process.cwd(),
  "prediction_python",
  ".venv",
  "Scripts",
  "python.exe"
);
const PYTHON_API_ENTRYPOINT = path.join(process.cwd(), "prediction_python", "02_api.py");

let pythonProcess = null;
let pythonStartupPromise = null;
let pythonStartupError = null;

class PredictionError extends Error {
  constructor(message, statusCode = 400, details = null) {
    super(message);
    this.name = "PredictionError";
    this.statusCode = statusCode;
    this.details = details;
  }
}

function buildUrl(pathname) {
  return `${DEFAULT_PYTHON_API_URL.replace(/\/+$/, "")}${pathname}`;
}

function sleep(delayMs) {
  return new Promise((resolve) => {
    setTimeout(resolve, delayMs);
  });
}

async function pingPythonApi() {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 3000);

  try {
    const response = await fetch(buildUrl("/health"), {
      method: "GET",
      signal: controller.signal,
    });

    return response.ok;
  } catch (error) {
    return false;
  } finally {
    clearTimeout(timeoutId);
  }
}

function getPythonLaunchCommand() {
  if (fs.existsSync(PYTHON_VENV_EXECUTABLE)) {
    return {
      command: PYTHON_VENV_EXECUTABLE,
      args: [PYTHON_API_ENTRYPOINT],
    };
  }

  return {
    command: "python",
    args: [PYTHON_API_ENTRYPOINT],
  };
}

async function waitForPythonApiReady(timeoutMs = STARTUP_TIMEOUT_MS) {
  const startedAt = Date.now();

  while (Date.now() - startedAt < timeoutMs) {
    if (pythonStartupError) {
      break;
    }

    if (await pingPythonApi()) {
      return true;
    }

    if (pythonProcess && pythonProcess.exitCode !== null) {
      break;
    }

    await sleep(HEALTH_CHECK_INTERVAL_MS);
  }

  return false;
}

async function ensurePythonApiAvailable() {
  if (await pingPythonApi()) {
    return;
  }

  if (!AUTO_START_PYTHON_ENGINE) {
    throw new PredictionError(
      "Le moteur Python de prediction est indisponible.",
      503,
      {
        python_api_url: DEFAULT_PYTHON_API_URL,
        hint: "Lancez l'API Python avec: npm run prediction:api",
      }
    );
  }

  if (pythonStartupPromise) {
    return pythonStartupPromise;
  }

  pythonStartupPromise = (async () => {
    const { command, args } = getPythonLaunchCommand();
    pythonStartupError = null;

    if (!fs.existsSync(PYTHON_API_ENTRYPOINT)) {
      throw new PredictionError(
        "Le fichier d'entree de l'API Python est introuvable.",
        500,
        { python_entrypoint: PYTHON_API_ENTRYPOINT }
      );
    }

    if (pythonProcess && pythonProcess.exitCode === null) {
      const ready = await waitForPythonApiReady();
      if (ready) {
        return;
      }
    } else {
      pythonProcess = spawn(command, args, {
        cwd: process.cwd(),
        env: { ...process.env },
        stdio: "ignore",
        windowsHide: true,
      });

      pythonProcess.on("error", (error) => {
        pythonStartupError = error;
        pythonProcess = null;
      });

      pythonProcess.on("exit", () => {
        pythonProcess = null;
      });
    }

    const ready = await waitForPythonApiReady();
    if (!ready) {
      throw new PredictionError(
        "Le moteur Python de prediction ne demarre pas correctement.",
        503,
        {
          python_api_url: DEFAULT_PYTHON_API_URL,
          python_command: command,
          startup_error: pythonStartupError?.message || null,
        }
      );
    }
  })();

  try {
    await pythonStartupPromise;
  } finally {
    pythonStartupPromise = null;
  }
}

async function parseJsonResponse(response) {
  try {
    return await response.json();
  } catch (error) {
    return null;
  }
}

function normalizeRemoteError(statusCode, payload) {
  const detail = payload?.detail;

  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    return new PredictionError(
      detail.message || "Erreur retournee par le moteur Python de prediction.",
      statusCode,
      detail
    );
  }

  if (typeof detail === "string" && detail.trim()) {
    return new PredictionError(detail, statusCode);
  }

  if (typeof payload?.message === "string" && payload.message.trim()) {
    return new PredictionError(payload.message, statusCode, payload.details ?? null);
  }

  return new PredictionError(
    "Le moteur Python de prediction a retourne une erreur.",
    statusCode
  );
}

async function requestPythonApi(pathname, options = {}) {
  try {
    await ensurePythonApiAvailable();

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      const response = await fetch(buildUrl(pathname), {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        },
        signal: controller.signal,
      });

      const payload = await parseJsonResponse(response);

      if (!response.ok) {
        throw normalizeRemoteError(response.status, payload);
      }

      return payload;
    } finally {
      clearTimeout(timeoutId);
    }
  } catch (error) {
    if (error instanceof PredictionError) {
      throw error;
    }

    if (error?.name === "AbortError") {
      throw new PredictionError(
        "Le moteur Python de prediction a mis trop de temps a repondre.",
        504,
        {
          python_api_url: DEFAULT_PYTHON_API_URL,
          timeout_ms: REQUEST_TIMEOUT_MS,
        }
      );
    }

    throw new PredictionError(
      "Le moteur Python de prediction est indisponible.",
      503,
      {
        python_api_url: DEFAULT_PYTHON_API_URL,
        hint: "Lancez l'API Python avec: prediction_python\\.venv\\Scripts\\python.exe prediction_python\\02_api.py",
      }
    );
  }
}

async function getPredictionMeta() {
  return requestPythonApi("/meta", { method: "GET" });
}

async function getPredictionForDate({ site, date }) {
  return requestPythonApi("/predict", {
    method: "POST",
    body: JSON.stringify({ site, date }),
  });
}

async function getPredictionSeries({ site, startDate, endDate }) {
  return requestPythonApi("/series", {
    method: "POST",
    body: JSON.stringify({ site, startDate, endDate }),
  });
}

async function warmPredictionEngine() {
  await ensurePythonApiAvailable();
}

export {
  PredictionError,
  getPredictionMeta,
  getPredictionForDate,
  getPredictionSeries,
  warmPredictionEngine,
};
