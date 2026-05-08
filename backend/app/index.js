import express from "express";
import cors from "cors";
import authRoutes from "./server.js";
import dotenv from "dotenv";
import watchlistRouter from "./api/routes/watchlist.js";

dotenv.config();

const app = express();
const PORT = Number(process.env.AUTH_PORT) || 800;

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

const server = app.listen(PORT, "0.0.0.0", () => {
  const addr = server.address();
  console.log(`[auth] listening on ${addr.address}:${addr.port}`);
});

// Surface the actual reason for any premature shutdown.
server.on("error", (err) => {
  console.error("[auth] http server error:", err);
});
server.on("close", () => {
  console.error("[auth] http server closed");
});

process.on("beforeExit", (code) => {
  console.error(`[auth] beforeExit code=${code} — event loop drained`);
});
process.on("exit", (code) => {
  console.error(`[auth] exit code=${code}`);
});
process.on("uncaughtException", (err) => {
  console.error("[auth] uncaughtException:", err);
});
process.on("unhandledRejection", (reason) => {
  console.error("[auth] unhandledRejection:", reason);
});
for (const sig of ["SIGTERM", "SIGINT", "SIGHUP", "SIGPIPE"]) {
  process.on(sig, () => {
    console.error(`[auth] received ${sig} — shutting down`);
    server.close(() => process.exit(0));
  });
}
