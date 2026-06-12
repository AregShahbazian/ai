---
id: pc-console-bridge
---

# Console bridge — scriptable debug/control API on `window.pc`

Origin: the ad-hoc `pc()` dump hooked into `App.tsx` (uncommitted, now carried
on `feature/console-bridge`). This feature grows it into a structured,
**awaitable** console API covering the whole app, so a human in DevTools — or
Playwright via `page.evaluate` — can drive sessions, control playback, inspect
frontend/chart/backend state, and diff them. The foundation for scripted e2e
scenarios.

## Requirements

### 1. Bridge surface & lifecycle

- One namespace, **`window.pc`**, present in all builds (debug app, no secrets).
- **Every method returns a Promise resolving to plain JSON-serializable data**
  (structure-cloneable), so `page.evaluate` returns results directly. Failures
  reject with structured `{ code, message }` errors — never silent.
- `pc.ready` — promise resolving once the app is mounted and the bridge wired
  (the Playwright boot gate). `pc.version` — bumped on breaking bridge changes.
  `pc.help()` — lists every command with a one-line doc.
- All time arguments accept unix **seconds or milliseconds** (auto-normalized,
  like the current `pc(time)`).
- Subsumes the ad-hoc dump as `pc.dump(time?)`, same behavior.

### 2. Session control — awaitable

- `pc.session.start({ start, end, mode?, algo?, ...params? })` — unspecified
  fields default from current UI state. Resolves when the session reaches
  `ready` (replay) or `finished` (headless), returning a snapshot summary.
- `pc.session.stop()`, `pc.session.loadPreset(name)`, `pc.session.loadSession(id)`.
- Bridge actions drive the **same code paths as the UI** and update visible UI
  state (range, config, panel) — bridge and UI must never diverge.

### 3. Playback control — awaitable

- `pc.play()`, `pc.pause()`, `pc.stepForward()`, `pc.stepBack()`,
  `pc.restart()`, `pc.setSpeed(n)`, `pc.setAutoResume(b)` — mirror
  PlaybackControls; each resolves once the engine reflects the action.
- **Waiters**, all with a `timeoutMs` (structured timeout rejection):
  `pc.waitFor.status(s)`, `pc.waitFor.time(t)`, `pc.waitFor.trade({ fromSeq? })`,
  `pc.waitFor.finished()`.
- `pc.playTo(time)` — play and auto-pause when the cursor reaches that candle.

### 4. Frontend state inspection

- `pc.state.snapshot()` — engine snapshot **summary** (status, mode, upTo,
  counts, balances — not candle arrays).
- Bulk data behind explicit accessors: `pc.state.candles({ from?, to?, last? })`,
  `pc.state.trades()`, `pc.state.pivots()`, `pc.state.sim()`,
  `pc.state.config()`, `pc.state.pivotOptions()`, `pc.state.candleAt(time)`.

### 5. Chart/render inspection — what's actually drawn

- `pc.chart.visibleRange()`, `pc.chart.markers()` (trade arrows as rendered),
  `pc.chart.pivotShapes()` (triangle primitives), `pc.chart.priceLines()`
  (entry/SL/TP), `pc.chart.rangeHighlight()`, `pc.chart.renderedCandles()`
  (count + first/last time).
- Purpose: assert render ↔ engine-state agreement (e.g. markers clipped to the
  replay cursor), not just app state.

### 6. Backend access & cross-check

- Read-only passthrough of the existing api client: `pc.backend.sessions()`,
  `pc.backend.session(id)`.
- `pc.verify(sessionId?)` — built-in frontend↔backend diff for the active (or
  given) session: trade count/sums, balances, fees, avg entry, status →
  `{ ok, mismatches: [{ field, frontend, backend }] }`.
- For pivot sims (no backend session) `verify()` runs internal invariants
  instead: equity = startingBalance + realizedPnl − fees; wins + losses =
  closed trades; bracket prices consistent with entries.

### 7. Event log

- Bounded ring buffer (~500) of structured events with monotonic `seq`: engine
  status transitions, trades, pivot confirmations, errors, bridge calls (candle
  ticks coalesced). `pc.events.since(seq?)`, `pc.events.clear()`. Waiters (§3)
  are built on it.

### 8. Playwright proof

- One committed example spec driving a full scenario **through the bridge
  only**: start replay on a fixed range → `playTo` a known candle → assert
  `pc.chart.markers()` against `pc.state.trades()` → run headless →
  `pc.verify()` clean. Doubles as living documentation.

## Non-requirements

- **No backend changes** — existing endpoints, read-only passthrough.
- **No mutations beyond UI-equivalent actions** — no injecting trades, editing
  engine internals, or skipping sim logic.
- No e2e suite/CI wiring — the single example spec only.
- No remote-control transport (WebSocket/CDP server); page console only.
- No debug UI panel; no screenshot/visual-regression tooling.
- Not a stable public API — internal; `pc.version` bump on break is enough.
