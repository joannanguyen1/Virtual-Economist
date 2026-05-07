import express from "express";
import cors from "cors";
import authRoutes from "./server.js";
import dotenv from "dotenv";
import watchlistRouter from "./api/routes/watchlist.js";

dotenv.config();

const app = express();
const corsOrigins = (process.env.CORS_ORIGINS || "")
  .split(",")
  .map((value) => value.trim())
  .filter(Boolean);

app.use(
  cors({
    origin: corsOrigins.length > 0 ? corsOrigins : true,
    credentials: true,
  }),
);
app.use(express.json());

app.get("/health", (_req, res) => {
  res.json({ status: "ok" });
});

app.use("/api/watchlist", watchlistRouter);
app.use("/api", authRoutes);

app.listen(800, () => {
  console.log("Backend running on port 800");
});
