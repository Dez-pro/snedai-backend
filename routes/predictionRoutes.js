import express from "express";
import {
  getPredictionMetadata,
  predictEnvironmentalData,
  predictEnvironmentalSeries,
} from "../controllers/predictionController.js";

const predictionRouter = express.Router();

predictionRouter.get("/meta", getPredictionMetadata);
predictionRouter.post("/predict", predictEnvironmentalData);
predictionRouter.post("/series", predictEnvironmentalSeries);

export default predictionRouter;
