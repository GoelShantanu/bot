# ICT Silver Bullet: strategy specification

This is the **single source of truth** for the rules. The Pine script (`pine/silver_bullet.pine`) and the Python backtester (phase 4 of [plan.md](plan.md)) must both implement exactly this. Parameters in `CODE` style are configurable. Defaults reflect the owner's decisions of 2026-09-30.

The owner asked for **several variants to be built and compared by backtest** (entry model, stop, timeframe, bias, trailing). Those are marked **[variant]**.

---

## 1. Market, time and units

| Item | Rule |
|---|---|
| Pairs | EURUSD, GBPUSD, USDJPY, NZDUSD, USDCHF |
| Clock | **New York time** (`America/New_York`, daylight-saving aware). Raw data is UTC and is converted. |
| Forex day | 17:00 NY → 17:00 NY. "Today" is the forex day containing the current candle. |
| Pip | 0.0001; **0.01 for USDJPY** |
| Entry timeframe `TF` **[variant]** | **3m** or **5m**, built from 1-minute data. Candles are labelled by their **open** time. |
| Liquidity timeframe | 15m (for swing levels) |

## 2. Silver Bullet windows

| Key | NY time | Enabled |
|---|---|---|
| `LO` | 03:00–04:00 | yes |
| `AM` | 10:00–11:00 | yes |
| `PM` | 14:00–15:00 | yes |

A candle is **in a window** if its open time `t` satisfies `start ≤ t < end`.

## 3. Building blocks

### 3.1 Fair value gap (FVG)

Three consecutive `TF` candles c1, c2, c3 (c3 is the newest):

- **Bullish FVG:** `c1.high < c3.low`. Zone = [`c1.high`, `c3.low`].
- **Bearish FVG:** `c1.low > c3.high`. Zone = [`c3.high`, `c1.low`].
- **CE** (consequent encroachment) = zone midpoint.
- The FVG is **eligible** only if **c3 is in an enabled window** (so it forms inside the window).
- `MIN_FVG_PIPS` (default 0 = any size). A minimum gap size is a tuning option.

### 3.2 Liquidity levels

Liquidity levels are used both for **sweeps** (entry models 1–2) and for **targets**. At any moment the set is:

| Level | Definition | Available from |
|---|---|---|
| PDH / PDL | Previous forex day's high / low | Start of today |
| Asian high / low | High / low of 20:00–00:00 NY | 00:00 NY |
| London high / low | High / low of 02:00–05:00 NY | 05:00 NY |
| NY AM high / low | High / low of 07:00–10:00 NY | 10:00 NY |
| 15m swing highs / lows | 15m fractal pivots (`SWING_STRENGTH` = 2 candles each side), formed within the last `SWING_MAX_AGE_H` = 24 h | When the pivot is confirmed (2 candles after it) |

- **Buy-side** liquidity = the highs; **sell-side** = the lows.
- A level is **taken** once price trades beyond it (high > level for buy-side, low < level for sell-side). Taken levels are removed.
- Every level **expires** `LEVEL_MAX_AGE_H` = 24 h after it becomes available. For PDH/PDL and session levels this is exactly one forex day, until the next day's version replaces it.

### 3.3 Sweep

- A **sell-side sweep** happens on the candle whose low first trades below an untaken sell-side level. **Buy-side sweep:** mirror.
- A sweep **qualifies** for an FVG if it occurred on c3 or within the `SWEEP_LOOKBACK` = 12 `TF` candles before c3.
- Bullish setups need a qualifying **sell-side** sweep; bearish setups need a **buy-side** sweep.

### 3.4 Impulse leg (used for OTE, SD projections and the "leg origin" stop)

- **Bullish:** `legLow` = lowest low from the qualifying sweep candle through c3, covering at least c1–c3 (models 1–2). In model 3, it's the lowest low of the `LEG_LOOKBACK` = 12 candles ending at c3. `legHigh` = highest high from the `legLow` candle through c3.
- **Bearish:** mirror (`legHigh` from the sweep; `legLow` = lowest low after it).
- `legRange = legHigh − legLow`.
- **All levels are frozen when c3 closes.** They are not updated while the order waits.

### 3.5 Market structure shift (optional)

`REQUIRE_MSS` (default **false**). If true, a bullish setup additionally needs a candle between `legLow` and c3 that **closes above** the highest high of the `MSS_LOOKBACK` = 10 candles before the `legLow` candle. Bearish is the mirror.

### 3.6 Higher-timeframe bias (entry model 3 only) **[variant]** `BIAS_MODE`

| Mode | Bullish when | Bearish when |
|---|---|---|
| `daily_dol` | today's open < price < PDH | PDL < price < today's open |
| `h1_structure` | the last 1h **close** above the most recent confirmed 1h pivot high (2/2) came after the last close below the most recent 1h pivot low | mirror |
| `premium_discount` | price < (PDH + PDL) / 2 (discount) | price > midpoint (premium) |

Price = c3 close. With no bias there's no trade.

## 4. Entry models **[variant]** `ENTRY_MODEL`

| Model | Direction from | Needs sweep | Extra filter |
|---|---|---|---|
| **1. SB + OTE** | FVG direction | yes | Entry price must lie inside the **OTE zone**: retracement `r = (legHigh − entry) / legRange` (bullish) with `OTE_MIN` 0.62 ≤ r ≤ `OTE_MAX` 0.79. The midpoint 0.705 is plotted. |
| **2. SB classic** | FVG direction | yes | none |
| **3. SB + bias** | FVG direction, must match `BIAS_MODE` | no | none |

- **Entry price** `ENTRY_LEVEL`: `ce` (default) or `edge` (the FVG boundary price reaches first: zone top for bullish, bottom for bearish).
- `FIRST_FVG_ONLY` (default **false**, since the owner chose no trade limit). If true, only the first eligible FVG per window, pair and direction is used.

## 5. Stop-loss **[variant]** `STOP_MODE`

| Mode | Bullish stop | Bearish stop |
|---|---|---|
| `fvg_candle1` | `c1.low − STOP_BUFFER` | `c1.high + STOP_BUFFER` |
| `leg_origin` | `legLow − STOP_BUFFER` | `legHigh + STOP_BUFFER` |

- `STOP_BUFFER_PIPS` = 1.0.
- `risk = |entry − stop|`. The setup is skipped if `risk ≤ 0`.

## 6. Targets and exits

### 6.1 Levels (bullish shown; bearish is the mirror)

- `TP_liq` = the **nearest untaken buy-side liquidity level above the entry**.
- `SD1 = legHigh + SD_PARTIAL × legRange` (`SD_PARTIAL` = 1.0)
- `SD2 = legHigh + SD_FINAL × legRange` (`SD_FINAL` = 2.0; 2.5 as an option)

### 6.2 Skip rule (owner: "prefer skipping the trade")

- Skip the setup unless `TP_liq − entry ≥ MIN_TARGET_PIPS` (15) **and** `TP_liq − entry ≥ MIN_RR × risk` (`MIN_RR` = 2.0).
- Also skip if there is no buy-side level above entry.
- `TARGET_RULE`: `nearest_must_qualify` (default, as above) or `first_qualifying` (use the nearest level that meets both minimums).

### 6.3 Exit plan: whichever comes first

Targets lie on the same side of the entry, so the one closer to entry is always reached first:

- **If `TP_liq ≤ SD1`:** exit **100% at `TP_liq`**.
- **Otherwise:**
  1. Exit `PARTIAL_PCT` = **50% at `SD1`**, then move the stop to **breakeven** (entry price).
  2. Exit the remaining 50% at **`min(TP_liq, SD2)`**.

### 6.4 Stop management **[variant]** `TRAIL_MODE`

The move to breakeven after the partial always applies. On top of it:

| Mode | Rule |
|---|---|
| `partial_be` | Nothing more |
| `be_1r` | When price reaches entry + 1 × risk, move the stop to entry |
| `be_1r_swing` | As `be_1r`, then after breakeven, each newly confirmed `TF` fractal low (2/2) above the current stop moves the stop to that low − `STOP_BUFFER` |

Stops only move in the trade's favour.

### 6.5 No time exit, except the weekend

- A trade closes only at a target, the stop, or **Friday 16:45 NY**. At that time all open positions close at market and pending orders are cancelled.
- There's no limit on the number of trades; several can be open at once, even on the same pair.

## 7. Order handling

- A **limit order** at the entry price is placed when c3 closes.
- It is cancelled if any of these happens first:
  - **Expiry:** `ORDER_EXPIRY` = `window_end` (default), or `window_end_plus_60`.
  - **Target reached first:** price reaches the first target (`TP_liq` or `SD1`, whichever is closer) before filling.
  - **Invalidation:** a `TF` candle **closes** beyond the stop level.
- **Fills with bid/ask** (Python backtest):
  - A long entry fills when **ask** low ≤ entry. Long stops and targets trigger on the **bid** (bid low ≤ stop; bid high ≥ target).
  - Shorts are the mirror: they enter on the bid, and exits trigger on the ask.
  - If a candle opens beyond a stop or target (a gap), the fill is at the open.
- **Same-candle ambiguity:** if the stop and a target can both be hit within one `TF` candle, replay the **1-minute candles** inside it. If a single 1-minute candle still touches both, assume the **stop first**.
- A candle that fills the order can also stop it out: after the fill, it's checked with the same 1-minute replay.

## 8. Costs (Python backtest)

- **Spread:** actual, from the bid/ask data.
- **Commission:** `COMMISSION_PIPS_RT` = 0.7 pip round trip (about $7 per 100k lot on USD-quoted pairs).
- **Slippage on stops:** gap fills at the open (above). No extra slippage by default.

## 9. Results and sizing

- Results are measured in **R** (1R = initial risk), **pips**, and the currency value of fixed-risk sizing (`RISK_PCT` = 1% of equity, used later for MT5 automation).
- Per trade, record: pair, window, model and variant settings, direction, entry/stop/targets, fill time, exit reason (`stop`, `breakeven`, `trail`, `tp_liq`, `sd1`, `sd2`, `weekend`), R, pips, costs, MAE/MFE, and holding time.

## 10. Variant grid for the backtest

| Dimension | Values |
|---|---|
| `ENTRY_MODEL` | 1, 2, 3 |
| `STOP_MODE` | fvg_candle1, leg_origin |
| `TF` | 3m, 5m |
| `TRAIL_MODE` | partial_be, be_1r, be_1r_swing |
| `BIAS_MODE` (model 3 only) | daily_dol, h1_structure, premium_discount |

That's 24 variants each for models 1 and 2 and 36 for model 3, **84 in total**, each run on 5 pairs.

Secondary options for later: `ENTRY_LEVEL`, `REQUIRE_MSS`, `MIN_RR` 3.0, `SD_FINAL` 2.5, `FIRST_FVG_ONLY`, `MIN_FVG_PIPS`, `ORDER_EXPIRY`, `TARGET_RULE`.

**Evaluation method:**
- **Train:** 2021-10 → 2024-09. **Test:** 2024-10 → 2026-09, never used for choosing.
- A variant is only credible if it's positive after costs in the test period, on more than one pair, with enough trades (≥ 100 in train).
