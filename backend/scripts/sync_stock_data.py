from __future__ import annotations

import argparse

from dotenv import load_dotenv

from backend.app.services.stock_sync import DEFAULT_STARTER_TICKERS, sync_stock_data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Populate stock_data from live Finnhub APIs.")
    parser.add_argument(
        "--tickers",
        help="Comma-separated ticker list. Defaults to a starter universe if omitted.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Truncate stock_data before inserting refreshed rows.",
    )
    parser.add_argument(
        "--with-embeddings",
        action="store_true",
        help="Generate Titan embeddings for each stock snapshot.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=1.0,
        help="Delay between symbols to reduce Finnhub rate-limit risk.",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    tickers = (
        [ticker.strip() for ticker in args.tickers.split(",")]
        if args.tickers
        else DEFAULT_STARTER_TICKERS
    )
    written = sync_stock_data(
        tickers,
        with_embeddings=args.with_embeddings,
        truncate=args.truncate,
        delay_seconds=args.delay_seconds,
    )
    print(f"Wrote {written} stock snapshot rows.")


if __name__ == "__main__":
    main()
