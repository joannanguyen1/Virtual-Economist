import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getAuthApiBase } from "../lib/api";

import "../styles/watchlist.css";

type WatchlistItem = {
  symbol: string;
  displayName: string;
  price: number;
  change: number;
  percentChange: number;
};
const WatchlistCard: React.FC = () => {

  const navigate = useNavigate();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [symbolInput, setSymbolInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const AUTH_API = getAuthApiBase();

  const token = localStorage.getItem("token");

  const normalizedSymbols = useMemo(
    () => new Set(items.map((item) => item.symbol.toUpperCase())),
    [items],
  );

  useEffect(() => {
    const loadWatchlist = async () => {
      try {
        const response = await fetch(`${AUTH_API}/api/watchlist`, {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          throw new Error("Failed to load watchlist");
        }

        const data = await response.json();
        setItems(data);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    void loadWatchlist();
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log("handleAdd fired");

    const symbol = symbolInput.trim().toUpperCase();

    if (symbol === "" || normalizedSymbols.has(symbol)) {
      return;
    }

    try {
      setSubmitting(true);

      const response = await fetch(`${AUTH_API}/api/watchlist`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ symbol }),
      });
      console.log("add status:", response.status);
      const data = await response.json();
      console.log("add response:", data);

      if (!response.ok) {
        setError(data.error || "Failed to add symbol"); 
        return;
      }

      if (!response.ok) {
        throw new Error(data.error || "Failed to add symbol");
      }

      const newItem = await data;
      setItems((prev) => [...prev, newItem]);
      setSymbolInput("");
    } catch (error) {
      console.error(error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemove = async (
    e: React.MouseEvent<HTMLButtonElement>,
    symbol: string,
  ) => {
    e.stopPropagation();

    try {
      const response = await fetch(`${AUTH_API}/api/watchlist/${symbol}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to remove symbol");
      }

      setItems((prev) => prev.filter((item) => item.symbol !== symbol));
    } catch (error) {
      console.error(error);
    }
  };

  const formatPrice = (price: number) => `$${price.toFixed(2)}`;

  const formatChange = (value: number) => {
    const prefix = value > 0 ? "+" : "";
    return `${prefix}${value.toFixed(2)}`;
  };

  const formatPercent = (value: number) => {
    const prefix = value > 0 ? "+" : "";
    return `${prefix}${value.toFixed(2)}%`;
  };

  return (
    <section className="watchlist-card">
      <div className="watchlist-header">
        <div>
          <p className="watchlist-eyebrow">My watchlist</p>
          <h2>Track the market names you care about</h2>
        </div>

        <form className="watchlist-form" onSubmit={handleAdd}>
          <input
            type="text"
            value={symbolInput}
            onChange={(e) => setSymbolInput(e.target.value)}
            placeholder="Add symbol"
            maxLength={10}
            aria-label="Add symbol"
          />
          <button type="submit">
            {submitting ? "Adding..." : "Add"}
          </button>
        </form>
        {error && <p className="watchlist-error">{error}</p>}
      </div>

      {loading ? (
        <div className="watchlist-empty">
          <p>Loading watchlist...</p>
        </div>
      ) : items.length === 0 ? (
        <div className="watchlist-empty">
          <h3>No symbols yet</h3>
          <p>Add a stock symbol to start building your watchlist.</p>
        </div>
      ) : (
        <div className="watchlist-table">
          <div className="watchlist-table-head">
            <span>Symbol</span>
            <span>Price</span>
            <span>Change</span>
            <span></span>
          </div>

          {items.map((item) => (
            <div
              key={item.symbol}
              className="watchlist-row"
              onClick={() =>
                navigate(`/assistant?mode=market&symbol=${item.symbol}`)
              }
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  navigate(`/assistant?mode=market&symbol=${item.symbol}`);
                }
              }}
              role="button"
              tabIndex={0}
            >
              <div className="watchlist-symbol-group">
                <span className="watchlist-symbol">{item.symbol}</span>
                <span className="watchlist-name">{item.displayName}</span>
              </div>

              <span className="watchlist-price">
                {formatPrice(item.price)}
              </span>

              <span
                className={[
                  "watchlist-change",
                  item.change > 0 ? "positive" : "",
                  item.change < 0 ? "negative" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                {formatChange(item.change)} ({formatPercent(item.percentChange)})
              </span>

              <button
                type="button"
                className="watchlist-remove"
                onClick={(e) => handleRemove(e, item.symbol)}
                aria-label={`Remove ${item.symbol}`}
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
};

export default WatchlistCard;