import mongoose from "mongoose";

const connectDB = async () => {
  try {
    const uri = process.env.MONGO_URI;
    if (!uri) {
      throw new Error("MONGO_URI manquant dans les variables d'environnement.");
    }

    await mongoose.connect(uri);

    console.log("✅ MongoDB connecté !");
  } catch (error) {
    console.error("❌ Erreur connexion MongoDB:", error.message);
    process.exit(1);
  }
};

export default connectDB;
