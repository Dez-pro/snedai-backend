import express from 'express';
import {
  loginUser,
  registerUser,
  adminLogin,
  forgetPassword,
  resetPassword,
  getCurrentUser,
  updateUserRole,
} from "./../controllers/userController.js";
import { getEmbedConfig } from "../controllers/powerbiController.js";
import authMiddleware from "../middleware/authMiddleware.js";

const userRouter = express.Router();

// Auth routes
userRouter.post('/register', registerUser);
userRouter.post('/login', loginUser);
userRouter.post('/admin', adminLogin);

// Mot de passe oublié / réinitialisation
userRouter.post('/forgetpassword', forgetPassword);
userRouter.post('/resetpassword/:token', resetPassword);

// Profil et rôle utilisateur
userRouter.get('/me', authMiddleware, getCurrentUser);
userRouter.post('/update-role', authMiddleware, updateUserRole);

// Power BI embed config sécurisée
userRouter.get('/powerbi/embed-config', authMiddleware, getEmbedConfig);

export default userRouter;
