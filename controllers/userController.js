import validator from "validator";
import bcrypt from "bcrypt";
import jwt from "jsonwebtoken";
import crypto from "crypto";
import dotenv from "dotenv";
import userModel from "../models/userModel.js";

dotenv.config(); // ⚠️ Toujours configurer dotenv en premier

// --- Création token JWT ---
const createToken = (id) => {
  return jwt.sign({ id }, process.env.JWT_SECRET, { expiresIn: "30d" });
};

// --- Login utilisateur ---
const loginUser = async (req, res) => {
  try {
    const { email, password } = req.body;

    const user = await userModel.findOne({ email });
    if (!user) return res.json({ success: false, message: "Cet utilisateur n'existe pas." });

    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) return res.json({ success: false, message: "Mot de passe incorrect." });

    const token = createToken(user._id);

    res.json({
      success: true,
      token,
      user: { id: user._id, name: user.name, email: user.email, role: user.role },
    });
  } catch (error) {
    console.error(error);
    res.json({ success: false, message: "Erreur serveur." });
  }
};

// --- Inscription utilisateur ---
const registerUser = async (req, res) => {
  try {
    const { name, email, password, city, role } = req.body;

    if (await userModel.findOne({ email })) {
      return res.json({ success: false, message: "L'utilisateur est déjà inscrit !" });
    }

    if (!validator.isEmail(email)) return res.json({ success: false, message: "Adresse email invalide !" });
    if (password.length < 8) return res.json({ success: false, message: "Mot de passe trop court (8 caractères min)." });
    if (!city || !city.trim()) return res.json({ success: false, message: "Veuillez renseigner votre ville." });

    const salt = await bcrypt.genSalt(10);
    const hashedPassword = await bcrypt.hash(password, salt);

    const newUser = new userModel({ 
      name, 
      email, 
      password: hashedPassword, 
      city: city.trim(), 
      role: role || "citoyen" 
    });

    const user = await newUser.save();
    const token = createToken(user._id);

    res.json({
      success: true,
      token,
      user: { id: user._id, name: user.name, email: user.email, role: user.role },
    });
  } catch (error) {
    console.error(error);
    res.json({ success: false, message: "Erreur serveur." });
  }
};

// --- Admin Login ---
const adminLogin = async (req, res) => {
  try {
    const { email, password } = req.body;

    if (email === process.env.ADMIN_EMAIL && password === process.env.ADMIN_PASSWORD) {
      const token = jwt.sign({ email, role: "admin" }, process.env.JWT_SECRET, { expiresIn: "30d" });
      return res.json({ success: true, token, role: "admin" });
    }

    res.json({ success: false, message: "Identifiants administrateur invalides." });
  } catch (error) {
    console.error(error);
    res.json({ success: false, message: "Erreur serveur." });
  }
};

// --- Mot de passe oublié ---
const forgetPassword = async (req, res) => {
  try {
    const { email } = req.body;
    const user = await userModel.findOne({ email });
    if (!user) return res.json({ success: false, message: "Utilisateur non trouvé." });

    const resetToken = crypto.randomBytes(32).toString("hex");
    const resetTokenExpires = Date.now() + 10 * 60 * 1000; // 10 minutes

    user.resetPasswordToken = resetToken;
    user.resetPasswordExpires = resetTokenExpires;
    await user.save();

    // On renvoie seulement le token au frontend
    res.json({ success: true, token: resetToken, message: "Token généré." });
  } catch (error) {
    console.error(error);
    res.json({ success: false, message: "Erreur serveur." });
  }
};

// --- Réinitialisation mot de passe ---
const resetPassword = async (req, res) => {
  try {
    const { password } = req.body;
    const { token } = req.params;

    const user = await userModel.findOne({
      resetPasswordToken: token,
      resetPasswordExpires: { $gt: Date.now() },
    });

    if (!user) return res.json({ success: false, message: "Token invalide ou expiré." });
    const salt = await bcrypt.genSalt(10);
    user.password = await bcrypt.hash(password, salt);

    user.resetPasswordToken = undefined;
    user.resetPasswordExpires = undefined;

    await user.save();

    res.json({ success: true, message: "Mot de passe réinitialisé avec succès." });
  } catch (error) {
    console.error(error);
    res.json({ success: false, message: "Erreur serveur." });
  }
};

export { loginUser, registerUser, adminLogin, forgetPassword, resetPassword };