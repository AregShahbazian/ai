# Futures order protocol — Review

## Round 0: implementation verification (2026-06-13)

Branch `feature/futures-orders` (worktree
`~/git/worktrees/putcafe/futures-orders`), tag `[pc-futures-orders]`.

**Backend (bot):** `app/futures.py` (new engine), `app/algos/{__init__,pivot,dca}.py`
(new), `app/main.py` (rewritten — `/api/bot/futures/run` + `/analyze` only);
deleted `app/pivot_strategy.py`, `app/dca.py`.
**Backend (positions):** `src/db.ts` + `src/index.ts` — `futures_sessions` store
(config + snapshot JSONB); spot order/state endpoints and columns gone.
**Frontend:** `api/backend.ts` (futures types), `backtest/engine.ts` (one path),
`components/{OverviewWidget,BacktestPanel}.tsx`, `chart/ChartView.tsx`,
`util/orders.ts`, `debug/bridge.ts`.

### Design recap

The old `pivot_strategy.simulate` was already a futures matching engine, so it
was **extracted** into `FuturesEngine` (hedge-mode, isolated margin, resting
orders, OHLC no-lookahead matching, per-side liquidation, events) and the two
algos reshaped to drive it via the order protocol (`place/cancel/amend` +
`open/close/add`). Single source of truth stays in Python, stateless +
deterministic; positions-backend persists the snapshot. Spot is removed — every
session is futures; DCA is a leverage-1 accumulating long, pivot is the ported
breakout. Frontend collapsed to one run-once + reveal-by-cursor path for all
algos.

### Verification

1. ✅ **Pivot parity gate (the crux).** New engine vs the former
   `simulate`, diffed over both saved BTCUSDT 1h files across 5
   ratio/SL/leverage combos (incl. ×1, ×10, ×25, SL 0.02–8): trades, exit
   reasons, prices, qty, pnl, liq, **and the full order ledger** match
   byte-for-byte (`PARITY PASS`). The cutover does not change pivot results.
   (claude-verified)
2. ✅ **DCA accumulation.** 116-candle run, 6h cadence → 20 market buys
   averaging into one long (margin Σ = balance, liq far away, open trade);
   fund-exhaustion correctly skips buys once free balance < buy size.
   (claude-verified)
3. ✅ **Bot API** `POST /api/bot/futures/run` over HTTP for pivot + DCA returns
   `{positions, orders, trades, events, equity, …}`; both algos exercised.
   (claude-verified)
4. ✅ **Positions persistence** against a real Postgres: create-with-snapshot,
   list (meta only), get (snapshot rides along), finish, delete — all green.
   (claude-verified)
5. ✅ `tsc -b` + `vite build` clean; positions `tsc` clean; all Python compiles.
   (claude-verified)
6. Overview widget: Positions tab renders each open side (hedge-mode ready)
   with leverage + liq; Orders tab spans all types/sides with Open|Closed; DCA
   shows a long with — SL/TP. — awaits manual check on preview.
7. Chart: per-side entry lines + bracket/stop order lines + liq (>×1). — manual.
8. Replay/headless/reload parity (same snapshot revealed by cursor; step-back
   render-only). — manual.

### Notes / deferred

- **Live-tuning** (TP/SL ratio, leverage, pivot options mid-replay) re-runs the
  in-memory snapshot but does **not** rewrite the persisted session's stored
  snapshot — the persisted row is the initial run. Acceptable; a PATCH endpoint
  could sync it later.
- **Hedge-mode dual-side** is fully supported by the engine; the two shipped
  algos each use one side at a time (per PRD non-goal).
- Old spot `sessions`/`trades` tables are left in the DB (dead data, no code
  path) rather than dropped — non-destructive cutover.
- Order types `stop_limit` + ladder entries are supported by the engine/types
  but unused by the current algos (ladder = several `limit` orders, no special
  case).
- `positions/yarn.lock` left untracked to match the existing convention
  (Dockerfile treats it as optional; none was tracked before).
