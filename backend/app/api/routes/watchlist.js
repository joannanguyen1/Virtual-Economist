import express from "express";
import pool from "../../../database/db.js";
import { requireAuth } from "../../middleware/auth.js";

const router = express.Router();

const FINNHUB_API_KEY = process.env.FINNHUB_API_KEY;

async function fetchQuote(symbol) {
  const quoteRes = await fetch(
    `https://finnhub.io/api/v1/quote?symbol=${encodeURIComponent(symbol)}&token=${FINNHUB_API_KEY}`,
  );

  if (!quoteRes.ok) {
    throw new Error(`Failed to fetch quote for ${symbol}`);
  }

  const quoteData = await quoteRes.json();
  if (!quoteData.c) {
    throw new Error(`Symbol "${symbol}" not found or has no data`);
  }
  const profileRes = await fetch(
    `https://finnhub.io/api/v1/stock/profile2?symbol=${encodeURIComponent(symbol)}&token=${FINNHUB_API_KEY}`,
  );

  let profileData = {};
  if (profileRes.ok) {
    profileData = await profileRes.json();
  }

  return {
    symbol,
    displayName: profileData.name || symbol,
    price: quoteData.c ?? 0,
    change: quoteData.d ?? 0,
    percentChange: quoteData.dp ?? 0,
  };
}

router.get("/", requireAuth, async (req, res) => {
    const userId = req.user.id;
  try {
    const result = await pool.query(
      `
      SELECT symbol, display_name, sort_order
      FROM watchlists
      WHERE user_id = $1
      ORDER BY sort_order ASC, created_at ASC
      `,
      [userId],
    );

    const items = await Promise.all(
      result.rows.map(async (row) => {
        const liveData = await fetchQuote(row.symbol);

        return {
          symbol: row.symbol,
          displayName: row.display_name || liveData.displayName,
          price: liveData.price,
          change: liveData.change,
          percentChange: liveData.percentChange,
        };
      }),
    );

    res.json(items);
  } catch (error) {
    console.error("Error fetching watchlist:", error);
    res.status(500).json({ error: "Failed to fetch watchlist" });
  }
});

router.post("/", requireAuth, async (req, res) => {
    console.log("POST /api/watchlist hit");
  console.log("headers auth:", req.headers.authorization);
  console.log("req.user:", req.user);
  console.log("body:", req.body);
  try {
    const userId = req.user.id;
    const symbol = req.body.symbol?.trim().toUpperCase();

    if (!symbol) {
      return res.status(400).json({ error: "Symbol is required" });
    }

    const quote = await fetchQuote(symbol);
    console.log(quote);
    const orderResult = await pool.query(
      `
      SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order
      FROM watchlists
      WHERE user_id = $1
      `,
      [userId],
    );

    const nextOrder = orderResult.rows[0].next_order;

    const insertResult = await pool.query(
      `
      INSERT INTO watchlists (user_id, symbol, display_name, sort_order)
      VALUES ($1, $2, $3, $4)
      ON CONFLICT (user_id, symbol)
      DO UPDATE SET updated_at = NOW()
      RETURNING symbol, display_name
      `,
      [userId, symbol, quote.displayName, nextOrder],
    );

    res.status(201).json({
      symbol: insertResult.rows[0].symbol,
      displayName: insertResult.rows[0].display_name,
      price: quote.price,
      change: quote.change,
      percentChange: quote.percentChange,
    });
  } catch (error) {
    console.error("Error adding watchlist item:", error);
    const isInvalidSymbol = error.message.includes("not found");
    res.status(isInvalidSymbol ? 400 : 500).json({ error: error.message });
  }
});

router.delete("/:symbol", requireAuth, async (req, res) => {
    const userId = req.user.id;
  try {
    const symbol = req.params.symbol?.trim().toUpperCase();

    await pool.query(
      `
      DELETE FROM watchlists
      WHERE user_id = $1 AND symbol = $2
      `,
      [userId, symbol],
    );

    res.json({ success: true });
  } catch (error) {
    console.error("Error deleting watchlist item:", error);
    res.status(500).json({ error: "Failed to delete watchlist item" });
  }
});

export default router;