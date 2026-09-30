# Project plan: ICT Silver Bullet forex bot

**Goal:** find out, with honest backtesting, whether an ICT Silver Bullet strategy on EURUSD, GBPUSD, USDJPY, NZDUSD and USDCHF has an edge after costs. If it does, automate it on a MetaTrader 5 broker.

**Documents:**
- [research.md](research.md): what ICT sources say, with links
- [strategy.md](strategy.md): the exact rules and parameters (single source of truth)
- this file: phases, deliverables and status

---

## Phases

| # | Phase | Deliverable | Status |
|---|---|---|---|
| 0 | Decisions | Owner's answers on pairs, windows, entry models, exits, stops, timeframes, bias, trailing, data, costs, execution | ✅ Done |
| 1 | Research & spec | `docs/research.md`, `docs/strategy.md` | ✅ Done |
| 2 | Pine Script | `pine/silver_bullet.pine`: a TradingView **strategy** with every variant as an input, chart drawings and alerts | ✅ Done (not compiled here; the owner pastes it into TradingView) |
| 3 | Historical data | `scripts/download_dukascopy.py` plus 5 years of 1-minute bid/ask data for the 5 pairs in `data/dukascopy/` (local, git-ignored) | ✅ Done (see the data check in [README](../README.md)) |
| 4 | Python backtester | `silver_bullet/` package implementing `strategy.md`: data loading and resampling, liquidity levels, setup detection for all models, an event-driven engine with 1-minute exit replay, bid/ask fills, costs, and reports | ⏭ Next |
| 5 | Evaluation | Run the 84-variant grid × 5 pairs; train 2021-10 → 2024-09, test 2024-10 → 2026-09; breakdowns by pair, window, year and direction; choose 1–3 variants | Planned |
| 6 | Forward test | Pine alerts and/or the Python signal engine on live data; paper-trade on an MT5 **demo** account for 4–8 weeks and compare with the backtest | Planned |
| 7 | Automation | MT5 execution adapter (Python `MetaTrader5` package, Windows): position sizing at `RISK_PCT`, limit orders, partial exits, stop management, the weekend close, restart-safe state, logging, Telegram alerts, a kill switch | Planned |
| 8 | Go live | Small size first, with monitoring and a weekly comparison against the backtest | Planned |

## Phase 4 design (Python backtester)

```
silver_bullet/
  config.py      all parameters from strategy.md (dataclass), variant grid
  data.py        load data/dukascopy/*.csv.gz → UTC → NY time; resample 1m → 3m/5m/15m/1h (bid+ask OHLC)
  levels.py      liquidity levels (PDH/PDL, sessions, 15m fractals), taken-level tracking
  bias.py        daily_dol, h1_structure, premium_discount (only completed higher-TF candles)
  setups.py      FVG detection in windows, sweeps, impulse leg, models 1–3, stop/targets, skip rule
  engine.py      event loop: pending orders → fills → partial/stop/trail/weekend exits,
                 replaying 1m candles inside each TF candle for ordering
  report.py      per-trade CSV, summary per variant/pair/window/year, train vs test
  cli.py         python -m silver_bullet.cli --pairs ... --variants ... --start ... --end ...
tests/           unit tests per module + a no-look-ahead test (future data must not change past trades)
```

**Key principles:**
- Only **completed** candles are used for decisions.
- Higher-timeframe levels become visible only after their candle closes.
- Test for look-ahead explicitly.
- Keep backtest and live logic in the **same** code path (the engine emits signals; the MT5 adapter executes them).

## Phase 7 notes (automation)

- **Broker platform:** MetaTrader 5 through the official `MetaTrader5` Python package (Windows only; the terminal must be running and logged in).
- **Legal:** Indian residents are generally not permitted to trade forex with overseas brokers (RBI/FEMA; the RBI publishes an alert list). The legal route in India is exchange-traded currency derivatives (NSE/BSE: EURUSD, GBPUSD, USDJPY cross-currency futures; NZDUSD and USDCHF are not listed). **The owner should confirm the broker's legal status before live trading.**
- **Risk controls to build:** max daily loss, max open trades per pair, news-time blackout (optional), stale-data guard, heartbeat alerts.

## Open items needing the owner

| Item | When needed |
|---|---|
| MT5 broker and account type (demo first) | Phase 6–7 |
| Risk per trade (default 1%) and daily loss limit | Phase 7 |
| Whether to add a news filter (e.g. skip windows around high-impact USD releases) | Phase 5, if results show news-driven losses |
