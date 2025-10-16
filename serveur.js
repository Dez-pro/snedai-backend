import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import connectDB from "./config/Db.js";
import userRouter from "./routes/userRoutes.js";


// Charger les variables d'environnement AVANT tout
dotenv.config();

// Connexion MongoDB
connectDB();

// Initialisation de l'app
const app = express();
const port = process.env.PORT || 4000;

// Middlewares
app.use(express.json());
app.use(cors());

// Routes
app.use("/api/user", userRouter);
app.use('/user', userRouter); // Pour compat anciennes URLs


// Lancement serveur
app.listen(port, () =>
  console.log("✅ Le serveur a démarré sur le port : " + port)
);
