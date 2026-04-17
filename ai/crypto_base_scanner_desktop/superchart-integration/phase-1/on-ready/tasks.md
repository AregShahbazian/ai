# Tasks: Replace chart-ready polling with SC `onReady`

PRD: `./prd.md` (id: `sc-on-ready`)
Design: `./design.md`

Ordering matters — the controller must accept the new `setReadyToDraw` prop
before the widgets start passing it in, otherwise webpack will render a broken
intermediate state.

---

## Task 1 — Context: rename `_notifyReady` → `_setReadyToDraw`

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/context.js`

**Changes:**

1. Rename the `useCallback` wrapper `notifyReady` → `_setReadyToDraw`.
   Change its body from `() => setReadyToDraw(true)` to `(v) => setReadyToDraw(v)`
   so it accepts a boolean.
2. Rename the context key `_notifyReady: notifyReady` → `_setReadyToDraw`.
3. Update the `useMemo` dep array: `notifyReady` → `_setReadyToDraw`.

**Verify:** file compiles. No other file imports `_notifyReady` by name outside
of the two chart widgets (which we update in Task 4 / Task 5).

---

## Task 2 — ChartController: accept `setReadyToDraw`, subscribe to `onReady`, add `_disposed` + `_unsubReady`

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`

**Changes:**

1. Add `setReadyToDraw` to the constructor's destructured options alongside
   `setVisibleRange`. Store as `this._setReadyToDraw = setReadyToDraw`.
2. Add `this._disposed = false` alongside the other field initializations in
   the constructor body (near `this._currentMarket = null`).
3. After the existing `this._unsubVR = superchart.onVisibleRangeChange(...)`
   line, add:
   ```js
   this._unsubReady = superchart.onReady(() => {
     if (this._disposed) return
     this._setReadyToDraw?.(true)
     this._applyTemporaryHacks()
     if (this.isMainChart) {
       this.syncChartColors()
       this.replay.init()
     }
   })
   ```
   The `?.` on `_setReadyToDraw` guards widget-side misconfiguration during
   the intermediate commit between Task 2 and Tasks 4/5.
4. In `dispose()`, add as the FIRST two lines:
   ```js
   this._disposed = true
   this._unsubReady()
   ```

**Verify:**
- Lint clean.
- Instantiating a `ChartController` without passing `setReadyToDraw` does not
  throw (the optional-chaining guard holds until the widgets are updated).
- Grep for `_notifyReady` — it should still exist in the two widget files
  (about to be fixed in Tasks 4 + 5) and nowhere else.

---

## Task 3 — ReplayController: collapse `init()`, delete `_pollForEngine`

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js`

**Changes:**

1. Replace the `init()` body with:
   ```js
   init() {
     this._replayEngine = this._chartController._superchart.replay
     this._wireCallbacks()
   }
   ```
2. Delete the entire `_pollForEngine()` method (and its preceding
   `// TEMP: poll ...` + `// Capped at 20 attempts ...` comments).
3. Delete the `_pollInterval = null` class field declaration (around line 22).
4. In `destroy()`, delete the `clearInterval(this._pollInterval)` line.

**Verify:**
- Lint clean.
- Grep for `_pollInterval` — zero matches in the file.
- Grep for `_pollForEngine` — zero matches in the file.
- Grep for `"Replay engine did not become available"` — zero matches anywhere
  (the warning is gone).

---

## Task 4 — super-chart.js: pass setter, wire onReady via controller, drop rAF

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/super-chart.js`

**Changes:**

1. In the `useSuperChart()` destructure (line 54): replace `_notifyReady` with
   `_setReadyToDraw`.
2. In the `new ChartController(...)` options object (line 84), add
   `setReadyToDraw: _setReadyToDraw` alongside `setVisibleRange`.
3. Delete the entire rAF block, currently lines 89–101:
   ```js
   // TEMP: poll until chart mounts. Replace with SC onReady callback when implemented.
   let rafId
   const checkReady = () => { ... }
   rafId = requestAnimationFrame(checkReady)
   ```
4. In the effect cleanup (starting line 103), delete the
   `cancelAnimationFrame(rafId)` line.

**Verify:**
- Lint clean.
- Grep this file for `_notifyReady`, `rafId`, `checkReady`,
  `requestAnimationFrame`, `cancelAnimationFrame` — all zero matches.
- Runtime: load Trading Terminal, confirm chart + overlays + colors appear
  on first paint (same as before the change).

---

## Task 5 — grid-bot-super-chart.js: pass setter, wire onReady via controller, drop rAF

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/grid-bot-super-chart.js`

**Changes:**

1. In the `useSuperChart()` destructure (line 24): replace `_notifyReady` with
   `_setReadyToDraw`.
2. In the `new ChartController(...)` options object (line 46), add
   `setReadyToDraw: _setReadyToDraw` alongside `setVisibleRange`.
3. Delete the entire rAF block, currently lines 50–59:
   ```js
   let rafId
   const checkReady = () => { ... }
   rafId = requestAnimationFrame(checkReady)
   ```
4. In the effect cleanup (starting line 61), delete the
   `cancelAnimationFrame(rafId)` line.

**Verify:**
- Lint clean.
- Grep this file for `_notifyReady`, `rafId`, `checkReady`,
  `requestAnimationFrame`, `cancelAnimationFrame` — all zero matches.
- Runtime: open grid-bot settings / backtest modal with a grid-bot chart,
  confirm the chart paints and its overlays (prices, orders, trades) appear.

---

## Task 6 — Remove the optional-chain safety net (tighten `_setReadyToDraw` call)

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`

**Changes:**

Once both widgets (Tasks 4 + 5) pass `setReadyToDraw` unconditionally, drop
the `?.` introduced in Task 2:

```js
this._setReadyToDraw(true)
```

This is a small correctness-by-strictness step — if a future call site forgets
to inject the setter, we want the error loud rather than silent.

**Verify:** lint clean. Chart boots. Grid-bot chart boots.

---

## Post-implementation — write `review.md`

After all six tasks land, create/append `review.md` in this folder with a
numbered verification checklist covering:

1. Main chart boot: candles render, overlays draw, colors correct on first
   paint.
2. Dark/light theme toggle before mount — colors correct on first paint in
   both themes.
3. Replay start immediately after mount — no delay, no `"[SC] Replay engine
   did not become available"` warning (impossible; line is deleted).
4. Replay flow end-to-end: start, step, step-back, play, pause, stop, switch
   modes (default ↔ smart) — all behave as before.
5. Fast mount/unmount — no console errors, no orphaned callbacks
   (grep runtime console for warnings).
6. Trading Terminal context tests (per `ai/workflow.md`):
   - Change TradingTab with replay active
   - Change coinraySymbol with replay active
   - Change resolution with replay active
   - Change exchangeApiKeyId with overlays drawn
7. Grid-bot chart: mount in bot-settings page, mount in backtest modal over
   settings simultaneously — both paint and draw overlays.
8. TV chart (CenterView) still fully functional (symbol sync, period sync, VR
   persist/restore, overlays).
9. Grep codebase for zero remaining matches of `_notifyReady`, `_pollForEngine`,
   `_pollInterval`, `requestAnimationFrame.*chart`, and the two `TEMP: poll`
   comments.

## Apply Steps (chat reply after implementation)

- No SuperChart rebuild needed — `onReady` is already in the linked build.
- HMR should pick up all four file changes. If anything stays stale, restart
  `yarn start-web` (or `yarn start` for electron).
