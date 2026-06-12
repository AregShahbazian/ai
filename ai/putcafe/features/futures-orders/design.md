# Futures order protocol — Design

**ID:** `pc-futures-orders` · refs [`prd.md`](prd.md) ·
**Branch:** `feature/futures-orders`

## Architecture decision

The existing `pivot_strategy.simulate` is already a faithful futures matching
engine — isolated margin, per-position liquidation, resting stop/limit fills,
gap-aware OHLC matching, deterministic intra-candle path, fee model. So we
**extract that engine** instead of inventing one, and reshape the two algos to
drive it through an **order-action interface**. Single source of truth stays in
**Python (bot-backend)**, stateless + deterministic; the **positions-backend
becomes a futures-session store** that persists the computed snapshot. Spot is
removed. Because the sim is deterministic, the persisted snapshot *is* the
durable truth and replay/headless/reload all reveal it by cursor — exactly the
model the `pivot` algo already uses, now extended to every algo.

```
bot-backend (Python)                positions-backend (TS)        frontend
  futures.py  ← matching engine       futures_sessions table        engine.ts (one path)
  algos/pivot.py  emits actions   ⇄   create/list/get/delete    ⇄   OverviewWidget / ChartView
  algos/dca.py    emits actions       (stores snapshot JSONB)        (orders ledger, per-side panel)
  /api/bot/futures/run → snapshot
```

## 1. Futures engine (`bot/app/futures.py`)

Hedge-mode, isolated margin. State the engine owns across the candle walk:

- `positions: {long: Pos|None, short: Pos|None}` — each `Pos` = `{qty, entry,
  margin, leverage, notional, liqPrice, feePaid, entryTime}`. (Today's algos use
  one side at a time; the engine is genuinely dual-side.)
- `orders: list[Order]` — the ledger (full lifecycle), unchanged shape from the
  current `pc-overview-widgets` ledger plus `positionSide` and `reduceOnly`.
- `balance` (free), `equity`, `events`, `wins/losses`, `bust`.

**Order model** (superset of today): `{id, role, type, side, positionSide,
reduceOnly, price, qty, pct, status, createdAt, filledAt, fillPrice,
cancelledAt, tradeIdx}`. Types: `market | limit | stop_market | stop_limit`.
`role` is presentational (`entry|tp|sl|exit|liq`). A **ladder entry** is just
several `limit` orders — no special case.

**Per-candle loop:**
1. Apply the algo's order **actions** (`place | cancel | amend`) for this candle
   — placing resting orders, cancelling/amending live ones.
2. **Match** resting + market orders against the candle along the deterministic
   OHLC path (`_path`: green O→L→H→C, red O→H→L→C). An order fills only when the
   candle range crosses its price (no lookahead); market fills immediately at
   open. Reduce-only orders only close their side.
3. **Conflict rule** (documented, pessimistic): within one candle the path order
   decides which of competing levels (SL vs TP vs liq vs opposite entry) fills
   first; ties resolve adverse-to-strategy. This is the current pivot rule,
   generalised.
4. **Liquidation:** when a side's adverse excursion reaches its `liqPrice`,
   force-close it at liq (market), loss capped at that side's margin.
5. Record fills as **trades** and **events**; update balances/equity.

Fee/slippage model unchanged (taker `0.001`, slippage `0.0005`; resting limits
fill at price-or-better, no slippage). Reused helpers: `_path`, `_bracket`,
`fill`, `fee_of`, liq math — moved verbatim so numbers don't shift.

## 2. Algo interface (`bot/app/algos/`)

```python
class Algo(Protocol):
    def decide(self, ctx: StepContext) -> list[Action]: ...
```

`StepContext` gives the algo: the new candle, confirmed pivots so far, both
position sides, open orders, balance — everything the PRD requires for a step.
`Action` = `place(order_spec) | cancel(order_id) | amend(order_id, patch)`.

- **`pivot.py`** — ports today's logic 1:1 onto actions: while flat, *place*
  stop-market entry orders at the gated high/low pivots (the "armed stops");
  on fill, *place* the reduce-only TP (limit) + SL (stop_market) bracket;
  the opposite resting entry stop, when hit in-position, becomes a
  close-and-reverse (reduce-only close + new opposite entry). Same levels,
  same re-arm gate, same alternation — results must match the current sim.
- **`dca.py`** — every `frequencySec`, *place* a `market` buy (long add) of
  `quoteAmount` notional, leverage 1, no bracket. Accumulates a long; never
  brackets, effectively never liquidates at ×1.

This makes both algos genuinely order-driven (PRD §4) over one engine.

## 3. Bot API (`bot/app/main.py`)

- `POST /api/bot/futures/run` `{candles, seedCandles, algo, params, pivots}` →
  full snapshot `{positions, orders, trades, events, equity, realizedPnl, wins,
  losses, leverage, bust, pivots}`. Replaces `/simulate`, `/sessions/*/seed`,
  `/step`, `/run` (the DCA per-candle path is gone).
- `/analyze` stays (live-chart pivots, indicator-style).

The frontend runs this once per session for **all** algos; replay reveals by
cursor; live-tuning re-runs it (as pivot does today).

## 4. Persistence (positions-backend, TS)

Replace the spot schema with futures sessions (one migration, drop spot path):

```sql
CREATE TABLE futures_sessions (
  id uuid PK, created_at, market, interval, start_time, end_time,
  mode, algo, params jsonb, starting_balance, fees_enabled, leverage,
  status,                       -- active|finished
  snapshot jsonb                -- the engine result (positions/orders/trades/events/equity/bust)
);
```

Endpoints (futures namespace): `POST /api/positions/sessions` (create from a
run — stores config + snapshot), `GET …/sessions`, `GET …/sessions/:id`,
`POST …/sessions/:id/finish`, `DELETE …` (one / all-except). Spot `orders`,
`state`, `base_qty/avg_entry/quote_balance` columns and the buy-only order
endpoint are **removed**. The snapshot is deterministic-reproducible, so storing
it is enough to survive reload and list in Sessions.

## 5. Frontend

- **`api/backend.ts`** — collapse to futures types: `FuturesParams {quoteAmount
  (margin), leverage, tpSlRatio, slCapPct, frequencySec}`, `FuturesSnapshot
  {positions, orders, trades, events, equity, …}`, `Order` gains
  `positionSide/reduceOnly/type`. `bot.run(...)`, `positions.*` futures CRUD.
- **`backtest/engine.ts`** — one path: `start()` fetches candles + seed history,
  calls `bot.run`, persists the session, sets `upTo=1` (replay) or end
  (headless); `stepOnce` is cursor-advance + significance from events;
  `setParams/setPivotOptions` re-run. The DCA per-candle positions branch,
  `seed/step/run` retry logic, and `reseed` are deleted.
- **`OverviewWidget.tsx`** — Positions tab shows **both sides** when present
  (qty, entry, margin, leverage, uPnL, **liq price**); Orders tab unchanged but
  now spans all types/sides with the Open|Closed filter; Sessions tab lists
  futures sessions. DCA shows a single long with no SL/TP (—).
- **`ChartView.tsx`** — order lines already render the ledger; extend labels
  with side/type (e.g. `Buy stop`, `TP +1.79%`, `Liq`), and draw per-side
  position entry lines. No new primitive needed.

## 6. Determinism & correctness gate

The pivot port **must reproduce** the current `simulate` output on the two saved
BTCUSDT 1h files (trades, exit reasons, pnl, liq, orders) within float
tolerance — verified by a script diffing old vs new over real HTTP before the
frontend is wired. DCA verified to accumulate a long with periodic market fills.
Replay/headless/reload parity asserted (same snapshot, revealed by cursor).

## Non-goals (unchanged from PRD)

No real connectivity, no cross-margin/one-way/funding, no partial fills, no user
order-placement UI. Hedge-mode dual-side is *supported* by the engine though the
shipped algos each use one side at a time.
