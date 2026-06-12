---
id: pc-futures-orders
---

# Futures order protocol — hedge-mode isolated simulation with full order types

Builds on [`../../mvp/prd.md`](../../mvp/prd.md). Origin:
[`../../discussions/2026-06-12-futures-order-protocol.md`](../../discussions/2026-06-12-futures-order-protocol.md).
The margin / leverage / liquidation slice already shipped for the pivot sim in
[`../leverage/prd.md`](../leverage/prd.md) (`pc-leverage`); this feature is the
remaining order-protocol + matching engine and the full backend cutover.

## Scope decisions

- **Futures-only, full cutover.** The positions-backend becomes a **futures**
  backend (hedge-mode, isolated margin) — **spot is dropped entirely**, no spot
  path remains. The migration's interim state is unconstrained, but
  **post-migration every algo runs on futures**.
- **All algos work on the new engine.** Both **DCA** and **pivot** emit order
  actions through the protocol and keep working after the cutover.
- **Pivot migrates fully.** The pivot strategy moves off today's stateless
  bot-side sim onto this real persisted order/matching engine and must stay
  working (same backtest semantics, now order-driven).
- **Sessions persist.** Futures sessions — positions per side, orders, balances,
  events — persist in the DB (as DCA sessions do today), surviving reload; not
  stateless.

## Requirements

### 1. Futures position model (positions-backend)

- All simulations are **hedge-mode futures with isolated margin**: a session
  can hold a **long and a short position simultaneously**, each with its own
  quantity, average entry, allocated (isolated) margin, and leverage.
- Opening/extending adds to a side; **reduce-only** actions shrink/close a
  side and realize PnL; they never flip or open the opposite side.
- Unrealized PnL per side and liquidation per side (a side whose loss exhausts
  its isolated margin is liquidated without touching the other side or the
  free balance).
- Fees/slippage stay session-togglable as today; maker vs taker fee applies by
  how an order fills.

### 2. Order types and lifecycle

- The bot can place, cancel, and amend orders; orders address a
  `positionSide` (long|short) and may be `reduceOnly`.
- Supported types:
  - **Market** — fills immediately at the current candle.
  - **Limit** — rests until price crosses it; **ladder entry** = multiple
    limit orders at different prices.
  - **Stop-market / stop-limit** — trigger at a stop price, then fill as
    market / rest as limit.
  - **Take-profit** and **stoploss** — reduce-only exits attached to a
    position side, at minimum expressible as the above order types.
- Resting orders **persist across candles** and are visible to the bot and
  the frontend until filled or cancelled.
- Every fill, trigger, cancel, and liquidation is reported back to the
  frontend as an event in the step/run flow.

### 3. Fill simulation honesty

- Resting orders are matched against each candle's OHLC — an order fills only
  when the candle's range actually crosses its price; **no lookahead**.
- Conflicting crossings within one candle (e.g. TP and SL both touched)
  resolve by a fixed, documented, deterministic rule — pessimistic for the
  strategy in ambiguous cases.
- Identical inputs produce identical results in replay and headless modes.

### 4. Bot decision interface

- Per step, the bot receives enough state to decide: both position sides,
  open orders, balances/margin — and returns a list of **order actions**
  (place/cancel/amend) instead of today's instant-fill decisions.
- The interface must support, in one step, combinations like: close or extend
  an existing side, and open the same or opposite side via market, limit, or
  ladder entry with TP and stoploss attached.
- Both **replay** (per-candle stepping, pause-on-significant-event) and
  **headless** (server-side run) support the full model with identical
  semantics.

### 5. Visualization (frontend)

- Working orders render on the chart (e.g. price lines) with type/side
  distinguishable; fills render as trade markers as today.
- Position state per side (qty, avg entry, margin, uPnL, liq price) visible in
  the session panel; events respect replay-cursor honesty (shown only once
  reached, also when stepping back).

## Non-requirements

- No real exchange connectivity — simulation only.
- No cross margin, no one-way mode, no funding-rate simulation (may come
  later).
- No partial fills — orders fill in full when crossed.
- No order placement UI for the user — orders originate from the bot only.

## Migration

- **DCA and pivot both port onto the order protocol** as part of this work (see
  Scope decisions) — they're not deferred. A trivial test algo may be used to
  bring the engine up first, but the feature isn't done until both real algos
  run on it and the spot path is removed.
- The current stateless `/api/bot/simulate` pivot sim is replaced by
  persisted, order-driven futures sessions; existing replay/headless semantics
  and the overview-widget order ledger must continue to work against the real
  engine.
