# Console bridge — design

PRD: [`prd.md`](prd.md) (`pc-console-bridge`).

## Shape

One new module dir, `frontend/src/debug/`, owning everything; React components
only **register handles** into it. No backend changes.

```
src/debug/bridge.ts    # core: registry, event log, waiters, window.pc assembly
```

### Registry + handles

The bridge is a module-level singleton. Components contribute capability
handles whose getters read **refs at call time** (always-current, registered
once per mount):

- **`AppHandle`** (from `App.tsx`): `getUi()` (market, interval, config,
  pivotOptions, range, preset names), `startSession(overrides)`,
  `stopSession()`, `loadPreset(name)`, `loadSession(id)`.
  `startSession` builds the `SessionConfig` itself from merged
  current-state + overrides (avoids stale-closure state), pre-syncs
  `prevKeyRef` on market/interval overrides (same trick as `loadPreset`), and
  updates the visible UI state — bridge and UI never diverge.
- **`ChartHandle`** (from `ChartView.tsx`): `visibleRange()`, `markers()`
  (captured in a ref at `setMarkers` time), `pivotShapes()` (the primitive's
  public `pivots`), `priceLines()` (mapped from `IPriceLine.options()`),
  `rangeHighlight()`, `renderedCandles()` (count + first/last from
  `candlesRef`).
- **engine**: passed in directly at install — playback + snapshot access.

### Snapshot tap → events → waiters

App constructs the engine with `s => { bridgeSnapshot(s); setSnap(s) }`. The
bridge keeps the latest snapshot, notifies subscribers, and derives **events**
by diffing consecutive snapshots: `status` transitions, `trade`
(dca: `trades.length` growth; pivot algo: cursor passing a sim
entry/exit time), `pivots` count change, `error`, plus `call` events for every
bridge invocation. Ring buffer of 500 with monotonic `seq`.

Waiters subscribe to snapshot changes (not just events): predicate + timeout
(default 30 s) → promise; timeout rejects `{ code: "timeout" }`. `playTo(t)`
subscribes, keeps re-issuing `engine.play()` if a significant-event pause
lands before `t`, pauses on arrival; resolves early if `finished`.

### Awaitable actions

Each action triggers the same path the UI uses, then awaits the engine
reflecting it: `session.start` → status `ready` (replay) / `finished`
(headless), rejecting if the engine lands on `idle` + `error`;
`play`/`pause`/`stop`/`restart`/`loadSession` analogous; `stepForward` awaits
the engine call; `setSpeed`/`setAutoResume`/`stepBack` resolve immediately
with a snapshot summary. All returns are JSON-safe summaries, never live
objects. Time args normalized sec/ms (`>1e12 → /1000`).

### verify()

- Backend session (dca / loaded): `positions.getSession` → field-by-field diff
  against the frontend mirror (trade count, quoteBalance, baseQty, avgEntry,
  feesPaid, status; float epsilon 1e-9 relative).
- Pivot sim (no backend session): internal invariants — wins + losses =
  closed-trade count; equity ≈ startingBalance + realizedPnl; per-trade
  bracket sanity (SL/TP on the correct side of entry per side).
- → `{ ok, kind: "backend" | "sim", mismatches: [{ field, frontend, backend }] }`.

### window.pc

`install()` (called from App) assembles the namespace; `pc.ready` resolves
once both handles are registered. `pc` is also callable —
`pc(time?)` keeps the old ad-hoc dump behavior (alias `pc.dump`). `pc.help()`
returns + pretty-prints the command table. `pc.version = 1`.

## Playwright proof

`@playwright/test` devDep; `playwright.config.ts` (webServer `yarn dev`,
`reuseExistingServer`, baseURL `http://localhost:5173`); `e2e/bridge.spec.ts`
driving: `pc.ready` → headless pivot run on a **fixed 2024 BTCUSDT 1h range**
(immutable klines ⇒ deterministic) → `verify().ok` → replay + `playTo` first
entry → `chart.markers()` ⊇ that entry, `priceLines()` = entry/SL/TP →
`session.stop()`. Network-dependent (Binance + VPS backend) — documented in
the spec header. Script: `yarn e2e`.

## Risks

- lightweight-charts plugin has no marker read-back → capture-at-set ref.
- `playTo` across autoResume=false pauses → re-play loop guarded by the
  target check (no infinite loop: `finished` resolves).
- Bulk `state.candles()` unbounded → require `{ from?, to?, last? }`, default
  `last: 50`.
