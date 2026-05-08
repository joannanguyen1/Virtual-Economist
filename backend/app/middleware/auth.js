import jwt from "jsonwebtoken";

import pool from "../../database/db.js";

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

export function requireRole(...allowedRoles) {
  const allowed = new Set(allowedRoles);

  return async function requireRoleMiddleware(req, res, next) {
    try {
      const userId = req.user?.id;
      if (!userId) {
        return res.status(401).json({ error: "Authentication required" });
      }

      const result = await pool.query("SELECT role FROM users WHERE id = $1", [userId]);
      if (result.rows.length === 0) {
        return res.status(401).json({ error: "User no longer exists" });
      }

      const role = result.rows[0].role;
      req.user.role = role;

      if (!allowed.has(role)) {
        return res.status(403).json({
          error: `This action requires one of the following roles: ${Array.from(allowed).sort().join(", ")}`,
        });
      }

      return next();
    } catch (error) {
      console.error("Role auth error:", error);
      return res.status(500).json({ error: "Server error" });
    }
  };
}
