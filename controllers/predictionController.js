import {
  PredictionError,
  getPredictionMeta,
  getPredictionForDate,
  getPredictionSeries,
} from "../services/predictionService.js";

const handlePredictionError = (error, res) => {
  if (error instanceof PredictionError) {
    return res.status(error.statusCode).json({
      success: false,
      message: error.message,
      details: error.details,
    });
  }

  console.error(error);
  return res.status(500).json({
    success: false,
    message: "Erreur serveur.",
  });
};

const getPredictionMetadata = async (req, res) => {
  try {
    const payload = await getPredictionMeta();
    return res.json(payload);
  } catch (error) {
    return handlePredictionError(error, res);
  }
};

const predictEnvironmentalData = async (req, res) => {
  try {
    const { site, date } = req.body;
    const payload = await getPredictionForDate({ site, date });
    return res.json(payload);
  } catch (error) {
    return handlePredictionError(error, res);
  }
};

const predictEnvironmentalSeries = async (req, res) => {
  try {
    const { site, startDate, endDate } = req.body;
    const payload = await getPredictionSeries({ site, startDate, endDate });
    return res.json(payload);
  } catch (error) {
    return handlePredictionError(error, res);
  }
};

export {
  getPredictionMetadata,
  predictEnvironmentalData,
  predictEnvironmentalSeries,
};
