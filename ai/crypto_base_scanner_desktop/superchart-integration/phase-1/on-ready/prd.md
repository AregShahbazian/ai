---
id: sc-on-ready
---

# PRD: Replace chart-ready polling with SC `onReady` callback

## Goal

Replace every polling workaround that waits for the SuperChart chart instance /
replay engine to mount with the SuperChart library's new first-class `onReady`
callback, and collapse the three-concept ready flow
(`readyToDraw` / `notifyReady` / `checkReady`) down to just `readyToDraw`.

After this change:

- No `requestAnimationFrame` poll for `getChart() !== null`.
- No `setInterval` poll for `sc.replay`.
- No context-level `_notifyReady` wrapper callback.
- Overlay components keep consuming a single `readyToDraw` React state via
  `useSuperChart()` / `useOverlayDeps()` — the public surface does not change.

## Background

The SuperChart library now exposes a dedicated chart-ready signal (already
documented in `ai/deps/SUPERCHART_API.md` lines 71, 107 and
`ai/deps/SUPERCHART_USAGE.md` lines 253, 401–404, 427–430):

```ts
// Constructor option
new Superchart({ ..., onReady: () => void })

// Instance method — returns unsubscribe; fires synchronously if already ready
sc.onReady(callback: () => void): () => void
```

Guarantees when `onReady` fires (confirmed against SC source at
`$SUPERCHART_DIR/src/lib/components/Superchart.ts`):

- `sc.getChart()` returns a non-null `Chart`.
- `sc.replay` is non-null. (Its `onReplayStatusChange` is still `idle`/`loading`
  until the first buffer loads — unchanged from today.)
- `chart.setStyles(...)` and `chart.createOverlay(...)` are safe to call.

## Current State (what we're replacing)

### 1. rAF poll — main trading-terminal chart

`src/containers/trade/trading-terminal/widgets/super-chart/super-chart.js:89–101`

```js
// TEMP: poll until chart mounts. Replace with SC onReady callback when implemented.
let rafId
const checkReady = () => {
  if (superchart.getChart() !== null) {
    _notifyReady()
    controller._applyTemporaryHacks()
    controller.syncChartColors()
    controller.replay?.init()
  } else {
    rafId = requestAnimationFrame(checkReady)
  }
}
rafId = requestAnimationFrame(checkReady)
```

Cleanup calls `cancelAnimationFrame(rafId)` in the effect teardown.

### 2. rAF poll — grid-bot chart

`src/containers/trade/trading-terminal/widgets/super-chart/grid-bot-super-chart.js:50–65`

Same pattern, minus `syncChartColors()` and `replay?.init()`.

### 3. setInterval poll — replay engine

`src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js:223–254`

```js
init() {
  this._pollForEngine()
}

// TEMP: poll until sc.replay is available. Replace with SC onReady callback when implemented.
// Capped at 20 attempts (~1s) to avoid infinite polling if the engine never appears.
_pollForEngine() { ... setInterval(..., 50) ... }
```

This poll exists only because `replay.init()` is called from inside the
component's rAF-poll `checkReady` — which itself needed the chart to be mounted.
With `onReady`, the callback site already has the guarantee `sc.replay` is
non-null, so the poll is unnecessary.

The controller also holds a `_pollInterval` field and clears it in `destroy()`
(line 935). Both go away.

### 4. Context wrapper `_notifyReady`

`src/containers/trade/trading-terminal/widgets/super-chart/context.js:11, 15, 18, 24–25`

```js
const [readyToDraw, setReadyToDraw] = useState(false)
const notifyReady = useCallback(() => setReadyToDraw(true), [])
// exposed on context as _notifyReady
```

Consumers: both chart widgets destructure `_notifyReady` from `useSuperChart()`
and call it from inside the rAF poll. With `onReady`, the chart widget can pass
`setReadyToDraw` straight to the SC constructor — the wrapper exists only to
bridge the poll-in-component pattern.

## What stays vs. what goes

| Concept | Purpose | Keep / Remove |
|---|---|---|
| `readyToDraw` (React state in `SuperChartContextProvider`) | Lets overlay components / buttons gate their draw/enable logic via `useSuperChart()` / `useOverlayDeps()`. Required — there is no React-visible alternative. | **Keep** |
| `_notifyReady` (context-exposed setter wrapper) | Bridged the in-component rAF poll back into context state. | **Remove** |
| `checkReady` (local rAF loop in each chart widget) | Polled `getChart() !== null`. | **Remove** |
| `_pollForEngine` / `_pollInterval` in `ReplayController` | Polled `sc.replay`. | **Remove** |
| `ReplayController.init()` | Kicks off engine wiring. | **Keep**, but called synchronously from inside the `onReady` callback. No polling inside it — just `this._replayEngine = sc.replay; this._wireCallbacks()`. |

## Requirements

### R1 — Wire `onReady` in the main chart widget

In `super-chart.js`, pass an `onReady` callback to the `Superchart` constructor.
Inside the callback, run the four post-mount actions currently executed by the
rAF poll, in order:

1. `setReadyToDraw(true)` (the context's `readyToDraw` flips via the React state
   setter, not via a `_notifyReady` wrapper)
2. `controller._applyTemporaryHacks()`
3. `controller.syncChartColors()`
4. `controller.replay.init()`

Remove the rAF poll, `rafId`, and `cancelAnimationFrame` cleanup.

### R2 — Wire `onReady` in the grid-bot chart widget

In `grid-bot-super-chart.js`, same pattern as R1 but with only:

1. `setReadyToDraw(true)`
2. `controller._applyTemporaryHacks()`

Grid bot doesn't use replay or chart-colors sync. Remove the rAF poll and its
cleanup.

### R3 — Drop the polling inside `ReplayController.init()`

`ReplayController.init()` must assume `sc.replay` is non-null (which `onReady`
guarantees). Implementation collapses to roughly:

```js
init() {
  this._replayEngine = this._chartController._superchart.replay
  this._wireCallbacks()
}
```

Remove `_pollForEngine`, `_pollInterval`, the setInterval, the 20-attempt cap,
and the console warning. Remove the `clearInterval(this._pollInterval)` line in
`destroy()`.

### R4 — Simplify `SuperChartContextProvider`

Remove `_notifyReady` from the context value. Expose the `readyToDraw` state
setter via a different path so the chart widget can flip it from inside the
`Superchart` constructor callback. Two acceptable shapes (design choice —
deferred to the design doc):

- Option A: Keep a single context method with a clearer name (e.g.
  `_setReadyToDraw`), used only by `super-chart.js` / `grid-bot-super-chart.js`.
- Option B: Lift `readyToDraw` state into each chart widget and pass it in to
  `SuperChartContextProvider` as a prop/value.

Either way, `_notifyReady` as a wrapper callback is gone. The public surface
consumed by overlay components (`useSuperChart().readyToDraw`,
`useOverlayDeps().readyToDraw`) is unchanged.

### R5 — No timing regressions for overlays

Because `onReady` fires at exactly the same moment the current rAF poll would
fire (first frame where `getChart()` is non-null), overlay components must
continue to draw at the same time they do today. Verify that
`useDrawOverlayEffect`'s `readyToDraw` gate flips at the first render after
`onReady` fires and that no overlay renders before `chart.setStyles(...)` has
been applied by `syncChartColors()`.

### R6 — Dispose correctness

If the instance-form `sc.onReady(cb)` is used, the returned unsubscribe must be
called in the effect's cleanup to avoid a leak on fast mount/unmount. If the
constructor-form `new Superchart({ onReady })` is used, no explicit unsubscribe
is needed — SC handles it internally. Design doc picks one.

Specifically: there must be no path where a ChartController is disposed but an
`onReady` callback fires afterward and mutates a disposed controller. Guard in
the callback body or rely on unsubscribe — design doc picks one.

## Non-Requirements

- **SC library changes.** The `onReady` API is already shipped
  (Superchart hash `4fd789f71f9e88e4705f4f72b839ba12791fc64b`,
  coinray-chart hash `26a9ca3af3c3055b90c6019a37d206ba08cd45b2`).
- **Overlay component changes.** Overlays continue to consume `readyToDraw`
  through `useSuperChart()` / `useOverlayDeps()`. No overlay file is touched.
- **Replay engine behavior.** `onReplayStatusChange` subscription, auto-exit on
  symbol change, step re-entrancy guard, held-step detection — all unchanged.
  This PRD only replaces *how we learn the engine is ready*, not what we do
  after.
- **Held-step `setInterval` in `replay-controller.js`** (line 642). That
  interval implements continuous step-back playback and is unrelated to
  chart-ready signalling.
- **TradingView chart.** TV integration is untouched.
- **New `readyToDraw` semantics.** No new readiness levels (data-loaded,
  first-buffer-ready, etc.) — same boolean, same meaning, just a reliable
  source.

## Files In Scope

| File | Change |
|---|---|
| `src/containers/trade/trading-terminal/widgets/super-chart/super-chart.js` | Pass `onReady` to `Superchart` constructor; remove rAF poll + `cancelAnimationFrame` cleanup. |
| `src/containers/trade/trading-terminal/widgets/super-chart/grid-bot-super-chart.js` | Same as above, minus `syncChartColors` / `replay.init` steps. |
| `src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js` | Replace `_pollForEngine` with direct assignment in `init()`. Remove `_pollInterval` field, `setInterval`, 20-attempt cap, warning log, and the `clearInterval` line in `destroy()`. |
| `src/containers/trade/trading-terminal/widgets/super-chart/context.js` | Remove `_notifyReady` from context. Expose `readyToDraw` state setter via the shape chosen in the design doc. |

No new files. No changes to overlay components, `chart-controller.js` internals
(beyond the already-existing `_applyTemporaryHacks` / `syncChartColors` /
`replay.init` methods), hooks, or the SC library.

## Testing Steps

1. **Main chart ready path.** Open the Trading Terminal. Verify the chart
   renders candles, overlays (orders, alerts, bases, trades) appear, and the
   chart colors reflect the current theme on first paint. No regressions vs.
   the current rAF-poll behavior.
2. **Replay engine ready path.** Immediately after chart mount, trigger replay
   (chart context menu → "Start replay from here" or the random-replay
   shortcut). Replay starts without a delay or a "no engine" noop. Verify no
   `"[SC] Replay engine did not become available"` warning ever appears in the
   console (the code that emits it is removed).
3. **Fast mount/unmount.** Rapidly switch between trading tabs / close and
   reopen the chart widget. No console errors, no memory leak warnings, no
   orphan callbacks firing on a disposed controller.
4. **Theme toggle at boot.** Launch the app with dark theme, then with light
   theme. Chart colors apply on first paint in both cases (R5 — this was
   already working via the rAF poll; confirm no regression).
5. **Grid-bot chart.** Open a grid-bot settings / backtest modal that mounts
   the grid-bot chart. Chart paints, overlays draw, no rAF poll warnings.
6. **Symbol/period change after boot.** Change the symbol and resolution in
   both directions (chart UI ↔ MarketTab). Existing echo-guard behavior still
   works — this PRD does not touch that path.
7. **TV still works.** Trading View's CenterView widget continues to function
   identically.

## Apply Steps

1. No SuperChart rebuild needed — `onReady` is already in the linked build.
2. Webpack HMR should pick up changes to the four files. If HMR fails, restart
   `yarn start-web` (or `yarn start` for electron).
