import jwt from "jsonwebtoken";

const JWT_SECRET = process.env.JWT_SECRET;

export function requireAuth(req, res, next) {
  try {
    const authHeader = req.headers.authorization;
    console.log("auth header:", authHeader);

    if (!authHeader || !authHeader.startsWith("Bearer ")) {
      return res.status(401).json({ error: "Authentication required" });
    }

    const token = authHeader.replace("Bearer ", "").trim();

    const payload = jwt.verify(token, JWT_SECRET);

    req.user = {
      id: payload.id,
      email: payload.email,
    };

    next();
  } catch (error) {
    console.error("JWT auth error:", error);
    return res.status(401).json({ error: "Invalid or expired token" });
  }
}