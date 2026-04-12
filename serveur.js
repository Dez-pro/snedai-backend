import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import connectDB from "./config/Db.js";
import userRouter from "./routes/userRoutes.js";
import predictionRouter from "./routes/predictionRoutes.js";
import { warmPredictionEngine } from "./services/predictionService.js";

dotenv.config();

connectDB();

const app = express();
const port = process.env.PORT || 4000;
const host = process.env.HOST || "0.0.0.0";
const localUrl = `http://localhost:${port}`;

app.use(express.json());
app.use(cors());

app.get("/", (req, res) => {
  res.json({
    success: true,
    name: "AirData Backend",
    message: "Backend operationnel",
    docs: {
      health: "/health",
      users: "/api/user",
      prediction: "/api/prediction",
    },
  });
});

app.get("/health", (req, res) => {
  res.json({
    success: true,
    status: "ok",
    port,
  });
});

app.use("/api/user", userRouter);
app.use("/user", userRouter);
app.use("/api/prediction", predictionRouter);

app.listen(port, host, () => {
  console.log("");
  console.log("Backend AirData demarre");
  console.log(`Local   : ${localUrl}`);
  console.log(`Health  : ${localUrl}/health`);
  console.log(`Users   : ${localUrl}/api/user`);
  console.log(`Predict : ${localUrl}/api/prediction`);
  console.log("");

  warmPredictionEngine()
    .then(() => {
      console.log("Prediction Python : moteur pret");
    })
    .catch((error) => {
      console.error("Prediction Python :", error.message);
    });
});
