# ICT Silver Bullet: forex strategy & bot

A research-first project to test the **ICT Silver Bullet** strategy on **EURUSD, GBPUSD, USDJPY, NZDUSD and USDCHF**. It runs on 3- and 5-minute charts in the three New York Silver Bullet windows (03:00, 10:00, 14:00 NY). If backtests show an edge after costs, the plan is to automate it on a MetaTrader 5 broker.

## Status

| Phase | State |
|---|---|
| Decisions, research, strategy spec | ✅ Done: [docs/strategy.md](docs/strategy.md), [docs/research.md](docs/research.md) |
| Pine Script strategy (TradingView) | ✅ Done: [pine/silver_bullet.pine](pine/silver_bullet.pine) |
| Historical data (Dukascopy 1m bid/ask, 5 years) | ✅ Downloader done: [scripts/download_dukascopy.py](scripts/download_dukascopy.py) |
| Python backtester | ⏭ Next: see [docs/plan.md](docs/plan.md) |
| Evaluation, forward test, MT5 automation | Planned |

## The strategy in one paragraph

Inside a Silver Bullet window, look for a **fair value gap** on the 3m or 5m chart and enter with a **limit order** in the gap. The three entry models:

1. **SB + OTE:** needs a liquidity sweep before the move, and the entry must sit in the 62–79% Fibonacci retracement of the impulse leg.
2. **SB classic:** needs a liquidity sweep before the move.
3. **SB + bias:** no sweep needed; the trade must follow a higher-timeframe bias.

The stop goes beyond the first FVG candle, or beyond the start of the leg. Exits:
- **Target:** the nearest untaken liquidity level. The trade is skipped unless that level is ≥ 15 pips and ≥ 2R away.
- **Standard-deviation projections:** if the −1.0 projection of the leg comes first, take 50% there, move the stop to breakeven, and exit the rest at the liquidity level or the −2.0 projection, whichever is closer.
- **Weekend:** anything still open closes on Friday at 16:45 NY.

All variants (model, stop, timeframe, bias, stop management) are parameters, so the backtest can pick the best. Full rules: [docs/strategy.md](docs/strategy.md).

## Using the Pine Script

1. TradingView → open a 3m or 5m chart of a pair (e.g. `OANDA:EURUSD`).
2. Pine Editor → paste [pine/silver_bullet.pine](pine/silver_bullet.pine) → **Add to chart**.
3. Choose the variant in the settings.

The **free plan** loads only about 5,000 bars (roughly 10–17 days), so the Strategy Tester results cover a short period and ignore the spread. Use the script for **visual checks and alerts**; the real backtest is the Python one (phase 4). For alerts: *Create Alert → Condition: ICT Silver Bullet → "alert() function calls only"*.

## Getting the data

```bash
python scripts/download_dukascopy.py --start 2021-10-01 --end 2026-09-30   # resumable, ~2 h
python scripts/download_dukascopy.py --build                               # rebuild CSVs from the cache
```

Output: `data/dukascopy/<PAIR>_1m_<YEAR>.csv.gz`, UTC 1-minute candles with bid **and** ask OHLC. The `data/` folder is git-ignored.

## Layout

```
docs/        research.md · strategy.md (rules) · plan.md (phases)
pine/        silver_bullet.pine
scripts/     download_dukascopy.py
data/        downloaded market data (local only)
```

## Legal note

Residents of India are generally not permitted to trade forex with overseas brokers (RBI/FEMA). Exchange-traded currency futures on NSE/BSE (EURUSD, GBPUSD, USDJPY) are the regulated route. Check your broker's status before trading live.
