# Review: sc-on-ready

PRD: `./prd.md`
Design: `./design.md`
Tasks: `./tasks.md`

## Round 1: initial implementation (2026-04-17)

### Implemented

- `context.js` — dropped `notifyReady` `useCallback` wrapper; exposes the raw
  `setReadyToDraw` setter directly as `_setReadyToDraw` on the context value,
  matching the existing `_setVisibleRange` shape. `useCallback` import
  removed (no longer used).
- `chart-controller.js` — constructor accepts `setReadyToDraw`, stores as
  `this._setReadyToDraw`. Added `this._disposed = false`. Subscription
  `this._unsubReady = superchart.onReady(...)` placed **after** sub-controller
  instantiation so that a (hypothetical) synchronous fire finds `this.replay`
  populated. Callback: `_setReadyToDraw(true)` → `_applyTemporaryHacks()` →
  (main chart only) `syncChartColors()` + `replay.init()`, guarded by
  `_disposed`. `dispose()` flips `_disposed = true` and calls `_unsubReady()`
  at the top, before all existing unsubs / sub-controller disposes.
- `replay-controller.js` — `init()` collapsed to two lines
  (`_replayEngine = sc.replay; _wireCallbacks()`). `_pollForEngine` method,
  `_pollInterval` field, setInterval, 20-attempt cap, and
  `"[SC] Replay engine did not become available"` warning — all deleted.
  `clearInterval(this._pollInterval)` removed from `destroy()`.
- `super-chart.js` — destructures `_setReadyToDraw` from `useSuperChart()`;
  passes `setReadyToDraw: _setReadyToDraw` into `ChartController`. Entire rAF
  poll + `cancelAnimationFrame` cleanup deleted.
- `grid-bot-super-chart.js` — same as main widget.
- Task 6 (`?.` tightening) merged into Task 2 — went straight to strict
  `this._setReadyToDraw(true)` since the migration happened atomically.

### Verification

1. Grep `_notifyReady` — 0 matches (verified).
2. Grep `_pollForEngine` / `_pollInterval` — 0 matches (verified).
3. Grep `"Replay engine did not become"` — 0 matches (verified).
4. Grep `requestAnimationFrame` / `cancelAnimationFrame` / `rafId` /
   `checkReady` in super-chart tree — 0 matches (verified).
5. Grep new symbols `_setReadyToDraw` / `_unsubReady` / `_disposed` present
   in expected files only (verified).
6. Main chart boot — candles render, overlays draw (orders/alerts/bases/
   trades/bid-ask), chart colors correct on first paint.
7. Dark/light theme toggled before mount — colors correct on first paint in
   both.
8. Replay: start from chart context-menu immediately after mount — engine
   wires instantly, no perceptible delay vs. previous poll-based behavior.
9. Replay flow: start, step, step-back, play/pause, stop, mode switch
   (default ↔ smart).
10. Fast mount/unmount — no console errors, no post-dispose mutations,
    no orphan onReady fires hitting a torn-down controller (guarded by
    `_unsubReady()` + `_disposed` flag).
11. Trading-Terminal context tests (per `ai/workflow.md`):
    - Change TradingTab with replay active
    - Change coinraySymbol with replay active
    - Change resolution with replay active
    - Change exchangeApiKeyId with overlays drawn
12. Grid-bot chart: bot-settings page + backtest modal over settings
    (two simultaneous instances) — both paint + draw their overlays.
13. TV chart (CenterView) fully functional — symbol sync, period sync, VR
    persist/restore, overlays.
