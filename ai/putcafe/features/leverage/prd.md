---
id: pc-leverage
---

# Leverage — futures-style margin, leverage picker, liquidation in the pivot backtest

Builds on [`../pivot-trading/prd.md`](../pivot-trading/prd.md) (`pc-pivot-trading`).
Context: [`../futures-orders/prd.md`](../futures-orders/prd.md) (`pc-futures-orders`) —
this PRD is the minimal margin/leverage slice of that model, applied to the
existing **backtest-simulated `pivot` algo only**; the full hedge-mode order
protocol stays deferred.

## Requirements

### 1. Leverage parameter + picker

- New `leverage` param on the pivot strategy (`PivotParams` end-to-end:
  frontend panel → `bot.simulate` → `StrategyParams`). Integer ×1–×125,
  default **×1** (today's behavior unchanged at ×1).
- UI: a futures-style **picker** in the Backtest panel's strategy section
  (next to Quote amount) — slider or stepped buttons over common values
  (1, 2, 3, 5, 10, 20, 25, 50, 75, 100, 125).
- **Live-tunable** like the other pivot params (change re-runs the sim) and
  **saved/loaded in presets**; old presets without it load as ×1.

### 2. Margin model (isolated, per position)

- `quoteAmount` becomes the **isolated margin** allocated to each position;
  **notional = quoteAmount × leverage**; `qty = notional / entry`.
- Fees and slippage apply to the **notional** (so fee impact scales with
  leverage), same taker/slippage constants as today.
- PnL math is unchanged (`qty × Δprice`) — leverage amplifies it via qty.

### 3. Liquidation

- Each position carries a **liquidation price**: the adverse move where loss
  (incl. close fee estimate) exhausts its isolated margin — simplified
  `entry × (1 ∓ 1/leverage)` adjusted for fees; no maintenance-margin tier
  table. At ×1 it's effectively unreachable (longs: price → ~0).
- A candle crossing liq force-closes at the liq price, `exitReason: "liq"`,
  realized loss = full margin. The position's loss can never exceed its
  margin (equity never goes more negative than that per trade).
- Intra-candle ordering: liq competes with SL/reverse on the adverse extreme
  via the existing OHLC path heuristic, **pessimistic** — if both SL and liq
  are within the candle, the one closer to entry on the adverse side fills
  first (normally SL; liq only when SL lies beyond it).
- If the bracket's computed SL is beyond the liq price, liq is the effective
  stop — deterministic, no error.

### 4. Bankruptcy guard

- A new entry (incl. reverse-opens) requires `equity ≥ quoteAmount` margin;
  otherwise the sim stops trading for the rest of the range (session is
  bust). Reverse that can't fund the new side just closes.

### 5. Results & visualization

- Liquidations render distinctly (marker/label and trade-list reason) and
  count as losses in the win/loss tally.
- Session summary shows leverage used; trade rows expose notional/margin so
  numbers reconcile.

## Non-requirements

- No funding rates, no cross margin, no maintenance-margin tiers.
- No partial liquidation; full close only.
- DCA/spot path (positions-backend) unchanged — spot stays ×1.
- No resting-order protocol changes (`pc-futures-orders`).
