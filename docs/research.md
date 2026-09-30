# Research notes: ICT Silver Bullet

A summary of what public ICT material says, and which parts the strategy spec ([strategy.md](strategy.md)) adopts. Where sources disagree, the spec turns the choice into a parameter so the backtest can decide.

## Time windows (New York local time, daylight-saving aware)

| Window | NY time | IST (US summer / US winter) | Notes |
|---|---|---|---|
| London Open SB | 03:00–04:00 | 12:30–13:30 / 13:30–14:30 | Best for EUR, GBP, CHF pairs |
| NY AM SB | 10:00–11:00 | 19:30–20:30 / 20:30–21:30 | ICT's most-cited window |
| NY PM SB | 14:00–15:00 | 23:30–00:30 / 00:30–01:30 | Thinner forex liquidity (London closed) |

- The FVG must **form inside** the window. The same FVG formed outside the window is not a Silver Bullet. [fxopen], [grandalgo], [innercircletrader]
- "The Silver Bullet is a scalp, not a swing": trades are usually closed or trailed within the same session. [innercircletrader] *The owner chose no time exit (close only at target/stop, plus a weekend close), so this is not adopted.*

## Setup

1. **Mark liquidity before the window** on the 15-minute chart: previous day/session highs and lows, established 15m swing extremes, equal highs/lows. [innercircletrader]
2. **Price sweeps a liquidity pool** (or runs through it toward the next one). [innercircletrader]
3. **Displacement / market structure shift (MSS)** on 1–5 minute charts. The move that sweeps and reverses must close decisively and leave an FVG behind. Some sources require the MSS; simpler versions only require "the first FVG in the window". [innercircletrader], [fxopen], [forexalgo-trader]
4. **Entry on the FVG retrace.** Enter when price taps the FVG; don't chase the displacement. Direction follows the FVG (bullish FVG → buy). [forexalgo-trader], [innercircletrader]

## Entry price inside the FVG

- The FVG **edge** (first touch) or its **consequent encroachment (CE)**, the 50% midpoint. Both are used in ICT teaching. → parameter `ENTRY_LEVEL`.
- **OTE (optimal trade entry):** the 62%–79% Fibonacci retracement of the impulse leg, with **70.5%** as the "sweet spot". Longs: draw swing low → swing high; shorts: swing high → swing low. Use the most recent valid impulse leg. [ictkillzone OTE], [innercircletrader fib]
- The Silver Bullet and OTE describe the same behaviour measured differently. The SB uses the FVG as the entry zone and OTE uses the 62–79% retracement. [ictkillzone OTE] → **Entry model 1** requires the FVG entry to lie inside OTE.

## Stop-loss

- Beyond the **first candle of the FVG** (the candle before the displacement candle), plus a small buffer. [forexalgo-trader], [innercircletrader]
- Alternative: beyond the swing that was swept (the start of the leg). → parameter `STOP_MODE`.

## Targets and Fibonacci projections

- **Forex objective:** at least **15 pips** (indices: 5–15 handles); a clean setup often gives 20–30 pips. [luxalgo], [innercircletrader]
- **Target = next liquidity pool** (draw on liquidity). One source asks for at least 1:3 risk:reward. [innercircletrader] *The owner chose ≥ 2R; `MIN_RR` is a parameter.*
- **ICT Fibonacci set:** retracements 0.5 (equilibrium), 0.62, 0.705, 0.79. **Standard-deviation projections:** −0.27, −0.62, −1.0, −2.0, −2.5, −4.0. Projections serve as profit targets after an OTE entry; −1.0 is one full leg length beyond the swing. [innercircletrader fib], [tradingfinder], [backtrex]
- The spec projects from the **impulse (displacement) leg** used for the OTE: −1.0 = leg extreme + 1 × leg range; −2.0 / −2.5 similarly.

## Timeframes

- Execution on 1m, 3m or 5m; 3m is often cited. Liquidity is marked on 15m. [luxalgo], [innercircletrader] *Owner chose 3m and 5m.*

## Claims to treat with caution

- Published win rates (e.g. "55–65% with 1:3 RR") come from educators, not audited backtests. The backtest must establish our own numbers.

## Data sources checked

| Source | Result |
|---|---|
| **Dukascopy datafeed** | Free 1-minute **bid and ask** candles per day, years of history. **Chosen.** Plain HTTP works from the owner's network (HTTPS timed out). About 12 s per file, so the download runs in parallel. |
| TradingView (free plan) | About 5,000 bars: ~17 days of 5m / ~10 days of 3m. Fine for visual checks, too short for backtesting. |
| HistData.com | Free 1-minute data but bid-only, with manual monthly downloads. Not used. |

## Sources

- [fxopen] https://fxopen.com/blog/en/what-is-the-ict-silver-bullet-strategy-and-how-does-it-work/
- [grandalgo] https://grandalgo.com/blog/ict-silver-bullet-strategy
- [innercircletrader] https://innercircletrader.net/tutorials/ict-silver-bullet-strategy/
- [innercircletrader fib] https://innercircletrader.net/tutorials/ict-fibonacci-levels/
- [ictkillzone OTE] https://www.ictkillzone.com/ict-ote
- [luxalgo] https://www.luxalgo.com/library/indicator/ict-silver-bullet/
- [forexalgo-trader] https://forexalgo-trader.com/resources/295-ict-silver-bullet-strategy
- [tradingfinder] https://tradingfinder.com/education/forex/ict-standard-deviation-projections/
- [backtrex] https://backtrex.com/en/blog/ict-standard-deviation-projection-price-targets
