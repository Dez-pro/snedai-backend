import express from 'express';
import {
  loginUser,
  registerUser,
  adminLogin,
  forgetPassword,
  resetPassword,
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

// Power BI embed config sécurisée
userRouter.get('/powerbi/embed-config', getEmbedConfig);

// Exemple de route protégée
userRouter.get('/me', authMiddleware, (req, res) => {
  res.json({ success: true, userId: req.user.id });
});

export default userRouter;