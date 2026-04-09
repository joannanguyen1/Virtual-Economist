# Demo Runbook

## 5-minute pre-demo checklist

1. Open the app home page in a fresh browser tab.
2. Verify the APIs are healthy:
   - `curl http://127.0.0.1:8000/health`
   - `curl http://127.0.0.1:800/health`
3. Log in with a verified test account.
4. Confirm saved chats load in the sidebar.
5. Test one housing prompt and one market prompt before presenting.

## Best demo prompts

### Housing / city

- `Compare median home values in Philadelphia, Austin, and Miami.`
- `What is the weather forecast in Austin, Texas this week?`
- `What is the housing inventory in Austin, Texas?`
- `Compare Austin and Philadelphia on home value and weather.`

### Market / stocks

- `What is Apple current stock price?`
- `Which technology companies have strong buy ratings?`
- `Show me Apple price history over the last 90 trading days.`
- `What is the Sharpe ratio of NVIDIA over the past year?`

## Safer phrasing during the demo

- Prefer company names or tickers users recognize: Apple, Microsoft, Nvidia, Tesla.
- Prefer major U.S. cities with known coverage: Austin, Philadelphia, Miami, Denver.
- Ask for one metric first, then compare.

## Live demo storyline

1. Start with one assistant workspace that handles both housing and markets.
2. Show a housing comparison question.
3. Show a live stock quote question.
4. Show a deeper quant question using `stock_ohlcv`.
5. Log in and reopen a saved chat to demonstrate persistence.

## Recovery commands

### FastAPI agent backend

```bash
cd /opt/virtual-economist
uv --project backend run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

### Auth backend

```bash
cd /opt/virtual-economist/backend
npm start
```

### Frontend local fallback

```bash
cd /opt/virtual-economist/frontend
npm start
```

## EC2 note

Your current instance is a `t2.micro`. It can run the demo, but it is tight on
CPU and memory. For a more stable public demo, a `t3.small` or larger instance
would be safer.
