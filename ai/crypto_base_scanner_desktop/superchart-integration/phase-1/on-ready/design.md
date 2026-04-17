# Design: Replace chart-ready polling with SC `onReady`

PRD: `./prd.md` (id: `sc-on-ready`)

## Summary

Replace two `requestAnimationFrame` polls (main + grid-bot chart widgets) and
one `setInterval` poll (`ReplayController._pollForEngine`) with a single
subscription to `superchart.onReady(...)`. Collapse the three-concept ready
flow (`readyToDraw` / `notifyReady` / `checkReady`) to one React-visible
state (`readyToDraw`) plus its private setter (`_setReadyToDraw`).

## Resolved Open Questions (from PRD)

### R4 — how the context surfaces `readyToDraw` state

**Decision:** Rename the context's `_notifyReady` callback to `_setReadyToDraw`.
Shape is unchanged — it's still a stable callback that flips `readyToDraw` to
`true`. Only the name changes, to communicate "this is the React state setter"
rather than "this is the I-am-ready signal". The signal concept is gone
(`onReady` is the signal now); what remains is a trivial state setter that
the `ChartController` calls exactly once.

Rejected: lifting state into the widget and passing it into the provider.
`readyToDraw` must be in context so overlay components can read it via
`useSuperChart()` without prop-drilling. Provider-owned state is the minimal
shape.

### R6 — constructor option vs. instance method for `onReady`

**Decision:** Use the instance method `superchart.onReady(cb)`, subscribed
inside the `ChartController` constructor, with the returned unsubscribe stored
as `this._unsubReady` and called in `dispose()`.

Rationale:
- Consistent with the existing pattern for `onSymbolChange`, `onPeriodChange`,
  and `onVisibleRangeChange` — all subscribed in the controller constructor
  with their unsubs kept on `this._unsubXxx` and invoked in `dispose()`
  (`chart-controller.js:74–78, 372–374`).
- The callback closes over `this` (the controller) directly — no ref lookup,
  no chicken-and-egg with the `new Superchart()` → `new ChartController()`
  sequencing in the widget.
- The returned unsubscribe gives explicit protection against a post-dispose
  `onReady` fire (rare, but cheap to guard against).
- Since SC fires the callback synchronously if the chart is already ready
  (per `SUPERCHART_API.md` line 107), subscribing "after" the constructor is
  safe — no possibility of missing the event.

Rejected: constructor option. It's simpler on the call site but diverges from
how every other SC callback is wired, and makes the controller non-owner of
its own subscription lifecycle.

## Architecture

### Ownership split

- **`super-chart.js` / `grid-bot-super-chart.js`** — create `Superchart`, create
  `ChartController`, pass the context's `_setReadyToDraw` into the controller.
  Do NOT subscribe to `onReady` from the widget. No rAF. No local ready logic.
- **`ChartController`** — subscribes to `superchart.onReady(...)` in its
  constructor. Inside the callback, runs all post-mount work (flip
  `readyToDraw`, apply temp CSS hacks, sync colors, init replay).
- **`SuperChartContextProvider`** — owns `readyToDraw` React state. Exposes
  `readyToDraw` (value) and `_setReadyToDraw` (setter) on the context object.

### Flow

```
React mount
  │
  └──> useEffect in super-chart.js / grid-bot-super-chart.js
         │
         ├──> new Superchart({ container, symbol, period, ... })
         │
         ├──> new ChartController(superchart, datafeed, {
         │      dispatch, getState, marketTabId,
         │      setVisibleRange: _setVisibleRange,
         │      setReadyToDraw: _setReadyToDraw,     // NEW injected setter
         │      isMainChart | isGridBotChart,
         │    })
         │       │
         │       └──> constructor subscribes:
         │              this._unsubReady = superchart.onReady(() => {
         │                if (this._disposed) return
         │                this._setReadyToDraw(true)
         │                this._applyTemporaryHacks()
         │                if (this.isMainChart) {
         │                  this.syncChartColors()
         │                  this.replay.init()
         │                }
         │              })
         │
         └──> (return cleanup — no rAF to cancel)

[SC internal async mount completes]
  │
  └──> onReady callback fires (once)
         │
         ├──> _setReadyToDraw(true)       → React re-renders context consumers
         ├──> _applyTemporaryHacks()      → periodBar class tweak
         ├──> syncChartColors()           → chart.setStyles + background DOM
         └──> replay.init()               → this._replayEngine = sc.replay;
                                            this._wireCallbacks()
```

### Why branching on `isMainChart` inside the callback

The grid-bot chart widget currently runs only `_applyTemporaryHacks()` after
ready (no color sync, no replay wiring). To preserve exact current behavior,
the controller callback guards `syncChartColors()` and `replay.init()` behind
`this.isMainChart`.

An alternative shape — factor out a public `onChartReady()` method and have
each widget call the specific post-ready methods it needs — was considered
and rejected: it pushes the ordering + branching decision to the call site
and duplicates it across two widgets. Keeping it in the controller means the
sequencing is defined once.

## API Changes

### `ChartController` constructor

**Before:**

```js
constructor(superchart, datafeed, {
  dispatch, getState, marketTabId, setVisibleRange,
  isMainChart = false, isGridBotChart = false,
} = {}) { ... }
```

**After:**

```js
constructor(superchart, datafeed, {
  dispatch, getState, marketTabId,
  setVisibleRange, setReadyToDraw,                    // setReadyToDraw NEW
  isMainChart = false, isGridBotChart = false,
} = {}) { ... }
```

Stored as `this._setReadyToDraw`, mirroring `this._setVisibleRange`.

### `ChartController` private fields

- **Add:** `this._unsubReady = superchart.onReady(() => { ... })`
- **Add:** `this._disposed = false`, flipped to `true` at the top of
  `dispose()` before any teardown runs. Guards the `onReady` callback body in
  case it fires after dispose.
- **Delete:** nothing else — existing fields stay.

### `ChartController.dispose()`

Add two lines:

```js
dispose() {
  this._disposed = true       // NEW — set before teardown
  this._unsubReady()           // NEW — release the onReady sub
  this._unsubSymbol()
  this._unsubPeriod()
  this._unsubVR()
  // ... rest unchanged
}
```

### `ReplayController.init()`

**Before:**

```js
init() {
  this._pollForEngine()
}

_pollForEngine() {
  const sc = this._chartController._superchart
  if (!sc) return
  if (sc.replay) {
    this._replayEngine = sc.replay
    this._wireCallbacks()
    return
  }
  let attempts = 0
  const MAX_ATTEMPTS = 20
  this._pollInterval = setInterval(() => {
    attempts++
    if (sc.replay) {
      clearInterval(this._pollInterval); this._pollInterval = null
      this._replayEngine = sc.replay
      this._wireCallbacks()
    } else if (attempts >= MAX_ATTEMPTS) {
      clearInterval(this._pollInterval); this._pollInterval = null
      console.warn("[SC] Replay engine did not become available after", MAX_ATTEMPTS, "attempts")
    }
  }, 50)
}
```

**After:**

```js
init() {
  this._replayEngine = this._chartController._superchart.replay
  this._wireCallbacks()
}
```

Deletions:
- `_pollForEngine()` — entire method
- `_pollInterval` field (class property, line 22)
- `clearInterval(this._pollInterval)` line in `destroy()` (line 935)

`init()` is called synchronously from inside the `onReady` callback in
`ChartController`, so `sc.replay` is guaranteed non-null
(per `SUPERCHART_API.md` / explorer verification). No null check needed.

### `SuperChartContextProvider` (context.js)

Rename the callback and its usages:

**Before:**

```js
const [readyToDraw, setReadyToDraw] = useState(false)
...
const notifyReady = useCallback(() => setReadyToDraw(true), [])

const value = useMemo(() => ({
  readyToDraw,
  chartColors,
  _setVisibleRange: setVisibleRange,
  get chartController() { return ChartRegistry.get(chartId) },
  _notifyReady: notifyReady,
}), [readyToDraw, chartColors, chartId, notifyReady])
```

**After:**

```js
const [readyToDraw, setReadyToDraw] = useState(false)
...
const _setReadyToDraw = useCallback((v) => setReadyToDraw(v), [])

const value = useMemo(() => ({
  readyToDraw,
  chartColors,
  _setVisibleRange: setVisibleRange,
  get chartController() { return ChartRegistry.get(chartId) },
  _setReadyToDraw,
}), [readyToDraw, chartColors, chartId, _setReadyToDraw])
```

(Signature accepts a boolean rather than being fixed to `true`. Controller
will only ever call `_setReadyToDraw(true)` in this PR, but the shape leaves
room for future resets, e.g. on symbol change, without another API churn.)

### Chart widgets (`super-chart.js`, `grid-bot-super-chart.js`)

In both widgets:

1. Destructure `_setReadyToDraw` from `useSuperChart()` (instead of
   `_notifyReady`).
2. Pass it into the `ChartController` constructor:
   ```js
   new ChartController(superchart, datafeed, {
     dispatch, getState, marketTabId,
     setVisibleRange: _setVisibleRange,
     setReadyToDraw: _setReadyToDraw,      // NEW
     isMainChart: true,                    // or isGridBotChart: true
   })
   ```
3. Delete the entire rAF block (`let rafId`, `checkReady`, `requestAnimationFrame`).
4. Delete `cancelAnimationFrame(rafId)` from the effect cleanup.

## Data Flow

```
React render
  → SuperChartContextProvider
      readyToDraw = false
      _setReadyToDraw = stable callback

React mount → useEffect → create Superchart + ChartController

ChartController.constructor
  ↳ superchart.onReady(() => {
      if (_disposed) return
      _setReadyToDraw(true)              ──▶ provider state flips
      _applyTemporaryHacks()
      if (isMainChart) {
        syncChartColors()
        replay.init()                    ──▶ replay engine wired
      }
    })

[SC async mount completes] → onReady callback fires once

React re-renders context consumers with readyToDraw=true
  ↳ useDrawOverlayEffect gate opens
  ↳ overlays (orders/alerts/bases/trades/etc.) run their draw effects
  ↳ HeaderButtons effects run
  ↳ PickReplayStartButton enables

React unmount → useEffect cleanup
  ↳ ChartRegistry.unregister(...)
  ↳ controller.dispose()
      _disposed = true
      _unsubReady()                      ──▶ drops any pending callback
      _unsubSymbol() / _unsubPeriod() / _unsubVR()
      sub-controllers dispose
      superchart.dispose()
      datafeed.dispose()
```

## Dispose / Race Safety

Two defenses, both cheap:

1. **`_unsubReady()` in `dispose()`** — primary defense. Releases the SC
   subscription so SC won't fire the callback after the controller is torn
   down.
2. **`_disposed` flag guard inside the callback** — defense in depth. Covers
   a hypothetical case where `onReady` is mid-invocation when `dispose()`
   runs, or where SC fires the callback synchronously during subscription
   while a React concurrent render is mid-commit. No known path today
   triggers this, but the guard is one `if (this._disposed) return` line.

No other subscribers of `readyToDraw` need changes — they continue to gate
on `readyToDraw` via `useSuperChart()`, and they receive the updated state
through the normal React render path.

## Non-goals

Unchanged from PRD. Explicit callouts:

- No SC library changes — `onReady` is already shipped in the linked build.
- No overlay file changes — `useDrawOverlayEffect`, `useOverlayDeps`, and all
  `overlays/*.js` files untouched.
- No replay-engine behavior changes (step logic, held-step interval, error
  handling, auto-exit on symbol change). Only the engine *discovery* path
  changes.
- Held-step `setInterval` (`replay-controller.js:642`) is unrelated and
  stays.
- TV integration untouched.

## Testing Pointers (for the review doc)

From the PRD:

- Main chart boot (overlays + colors present on first paint).
- Replay engine immediate availability (start replay right after mount; no
  `"Replay engine did not become available"` warning possible — the line is
  deleted).
- Fast mount/unmount / rapid tab switch (no orphan callbacks, no
  post-dispose mutations).
- Theme toggle at boot (colors correct on both dark and light first paint).
- Grid-bot chart (paints + overlays draw).
- Symbol/period change round-trip (echo-guard behavior intact).
- TV chart regression check.

## Open Questions

None after R4 and R6 are resolved above.
