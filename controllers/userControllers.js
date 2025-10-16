import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";
import User from "../models/User.js"; // ton modèle corrigé

// Générer un JWT
const generateToken = (id) => {
  return jwt.sign({ id }, process.env.JWT_SECRET, { expiresIn: "7d" });
};

// Inscription
export const registerUser = async (req, res) => {
  try {
    const { name, email, password, city, role } = req.body;

    // Vérif des champs obligatoires
    if (!name || !email || !password || !city || !role) {
      return res.status(400).json({ success: false, message: "Tous les champs sont requis." });
    }

    // Vérif du rôle
    const validRoles = ["citoyen", "chercheur", "décideur", "autorité"];
    if (!validRoles.includes(role)) {
      return res.status(400).json({ success: false, message: "Rôle invalide." });
    }

    // Vérif si email déjà utilisé
    const userExists = await User.findOne({ email });
    if (userExists) {
      return res.status(400).json({ success: false, message: "Cet email est déjà utilisé." });
    }

    // Hash du mot de passe
    const hashedPassword = await bcrypt.hash(password, 10);

    // Création de l'utilisateur
    const user = await User.create({
      name,
      email,
      password: hashedPassword,
      city,
      role,
    });

    // Réponse
    res.status(201).json({
      success: true,
      message: "Inscription effectuée avec succès",
      token: generateToken(user._id),
      user: {
        id: user._id,
        name: user.name,
        email: user.email,
        role: user.role,
        city: user.city,
      },
    });
  } catch (error) {
    console.error("Erreur inscription:", error);
    res.status(500).json({ success: false, message: "Erreur serveur lors de l'inscription." });
  }
};