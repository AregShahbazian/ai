---
id: pc-pivot-trading
---

# Pivot trading — breakout strategy on swing highs/lows

Builds on [`../pivot-detection/prd.md`](../pivot-detection/prd.md) (`pc-pivots`).
Origin: [`../../discussions/2026-06-12-pivot-trading-strategy.md`](../../discussions/2026-06-12-pivot-trading-strategy.md).
Context: [`../../discussions/2026-06-12-futures-order-protocol.md`](../../discussions/2026-06-12-futures-order-protocol.md).

A new bot algo, **`pivot`**, that takes directional positions off detected
pivots. **Simulated in the backtest** — the spot, buy-only positions-backend
can't model shorts, resting orders, or brackets (that's the deferred
`pc-futures-orders`).

## Requirements

### 1. Entry — stop-market breakout

- When **flat**, arm a buy-stop at the last confirmed **high** pivot and a
  sell-stop at the last confirmed **low** pivot (the recent
  resistance/support).
- A candle breaching a level in that direction fills a **stop-market** entry:
  up-breakout → **long**, down-breakout → **short**.
- **One netted position at a time** — never two. The position may be closed
  (full), or closed-and-reversed into the opposite side, but never stacked.

### 2. Bracket — TP/SL set at entry

- On entry, compute and set a **take-profit** and **stop-loss**:
  - `SL%` = price distance from entry to the **opposite** pivot, **capped** at a
    configurable **SL cap %** (fallback to the cap when no opposite pivot exists).
  - `TP%` = `SL% × ratio`, with a configurable **TP/SL ratio** (e.g. 2 ⇒ 4% SL
    gives 8% TP).
- A candle touching TP or SL closes the position (single **full** close).

### 3. Close + reverse — structure break

- While long, price breaking below the **current** last low pivot (opposite
  structure break) **closes the long and opens a short** in the same candle;
  mirror for a short breaking the last high pivot.
- This is distinct from the SL: the latest opposite pivot can drift above the
  bracket stop, signalling a trend flip rather than a stop-out.

### 4. Re-arm rule

- After a **TP or SL** exit (which leaves us flat), do **not** re-enter until a
  **fresh pivot** confirms (a pivot whose `confirmedAt` is after the exit).
  Prevents whipsaw re-entries while price still sits beyond the breached pivot.
- A close-and-reverse is not a flat exit and needs no re-arm.

### 5. Configuration

- Algorithm selector gains **Pivot** alongside DCA.
- Params: **TP/SL ratio**, **SL cap %**, **position size** (notional USDT), and
  the pivot **lookback** (reuses the existing pivot lookback control).
- Runs in **replay** (watch entries/exits form, paused on each trade) and
  **headless** (jump to the final result). Live-tunable params re-run the sim
  mid-replay, like the pivot options.

### 6. Visualization

- Entry/exit **markers** on the chart (long/short entries, TP/SL/reverse exits),
  clipped to the replay cursor.
- Bracket **price lines** (entry, SL, TP) for the position open at the cursor.
- Results: realized PnL, ROI, win rate, trade count, open-position state.

## Non-requirements

- No real resting/stop orders, hedge-mode model, leverage, margin, or
  liquidation — all deferred to `pc-futures-orders`.
- No persistence of pivot sims to the positions-backend (no Sessions-list entry,
  no reload) while simulated-only.
- No partial TP, scaling, or pyramiding (single full close).
- No "smart" TP/SL beyond capped opposite-pivot distance (pivot time-distance /
  recency weighting is a future refinement).
- No equity-curve subchart (numbers only for now).
