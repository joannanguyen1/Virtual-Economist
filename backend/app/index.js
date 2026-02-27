import express from "express";
import cors from "cors";
import authRoutes from "./server.js";
import dotenv from "dotenv";

dotenv.config();

const app = express();

app.use(cors());
app.use(express.json());

app.use("/api", authRoutes);

app.listen(800, () => {
  console.log("Backend running on port 800");
});

