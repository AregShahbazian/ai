# Superchart Usage Patterns

> Source: `$SUPERCHART_DIR` (example app + source, branch: main)
> Superchart git hash: `89a1c9263ca9073ea6019cc9a2a02112ddfe7d1b`
> coinray-chart (`packages/coinray-chart`, branch: main) git hash: `011e1975dd6f40227d9f3d5d93a65e7aa9be0937`
> Do NOT explore source — use this doc instead.

## Initialization Pattern

Imperative construction in `useRef` + `useEffect` with empty deps. NOT a React component.

```javascript
import { Superchart, createDataLoader } from "superchart"
import "superchart/styles"

const chartRef = useRef(null)
const containerRef = useRef(null)

useEffect(() => {
  // 1. Create datafeed adapter (implements Datafeed interface)
  const datafeed = new CoinrayDatafeed(/* ... */)

  // 2. Bridge to klinecharts DataLoader
  const dataLoader = createDataLoader(datafeed)

  // 3. Construct Superchart (synchronous store update, async React render)
  chartRef.current = new Superchart({
    container: containerRef.current,        // DOM element
    symbol: toSymbolInfo(coinraySymbol),
    period: toPeriod(resolution || "60"),
    dataLoader,
    theme: "dark",
    periods: SUPPORTED_PERIODS,
  })

  return () => {
    chartRef.current?.dispose()
    chartRef.current = null
  }
}, [])
```

The constructor synchronously sets internal store values, then renders a React
component via `createRoot`. The internal `_api` populates asynchronously via
`onApiReady`. Methods called before `_api` is ready safely fall back to store
getters/setters.

## Datafeed Wiring

`createDataLoader(datafeed)` wraps the TradingView-compatible `Datafeed` interface:

1. Caches symbol resolution (`symbolCache` Map)
2. Tracks active subscriptions (`activeSubscriptions` Map)
3. Aligns time ranges via `adjustFromTo()`
4. Converts `Bar` ↔ `KLineData` format
5. Generates subscriber UIDs: `"${ticker}_${resolution}"`
6. Requests `DEFAULT_COUNT_BACK = 500` bars per page

**Data flow:**
```
klinecharts DataLoader.getBars()
  → Datafeed.resolveSymbol() [cached after first call]
  → Datafeed.getBars()
  → CoinrayCache.fetchCandles()
  → bars → callback
```

**`setOnBarsLoaded` hook:** Register a callback for indicator/script backfill:
```javascript
dataLoader.setOnBarsLoaded((fromMs) => {
  // Trigger historical data load for backend indicators
  indicatorProvider.backfillFrom(fromMs)
})
```

## Symbol/Period Change

From parent → chart (works):
```javascript
useEffect(() => {
  chartRef.current?.setSymbol(toSymbolInfo(coinraySymbol))
}, [coinraySymbol])

useEffect(() => {
  chartRef.current?.setPeriod(toPeriod(resolution))
}, [resolution])
```

Internally, `setSymbol`/`setPeriod` trigger:
1. Unsubscribe old datafeed subscription
2. Resolve new symbol (if symbol changed)
3. Call `getBars()` for new symbol/period
4. Call `subscribeBars()` for real-time updates

From chart → parent (event callbacks):
```javascript
// Option A: constructor callbacks
const chart = new Superchart({
  ...,
  onSymbolChange: (symbol) => dispatch(setSymbol(symbol)),
  onPeriodChange: (period) => dispatch(setPeriod(period)),
  onVisibleRangeChange: (range) => console.log(range.from, range.to), // unix seconds
  onCrosshairMoved: ({ point }) => setHover(point.time, point.price),
  onSelect:         ({ point }) => openAlertDialog(point),
  onRightSelect:    ({ point }) => openContextMenu(point),
  onDoubleSelect:   ({ point }) => zoomToPoint(point),
})

// Option B: subscribe later (returns unsubscribe function)
const unsub = chart.onSymbolChange((symbol) => { ... })
unsub() // stop listening
```

Both approaches can be combined. All callbacks fire for UI-initiated and
API-initiated changes. Initial constructor values do NOT trigger callbacks.

## Chart Pointer Events

Four pointer events are available in addition to symbol/period/range:

| Event | Constructor option | Subscribe method | Payload |
|-------|--------------------|------------------|---------|
| Crosshair move | `onCrosshairMoved` | `chart.onCrosshairMoved(cb)` | `PriceTimeResult` |
| Click | `onSelect` | `chart.onSelect(cb)` | `PriceTimeResult` |
| Right-click | `onRightSelect` | `chart.onRightSelect(cb)` | `PriceTimeResult` |
| Double-click | `onDoubleSelect` | `chart.onDoubleSelect(cb)` | `PriceTimeResult` |

All subscribe methods return an unsubscribe function. `PriceTimeResult` carries both
canvas pixel coordinates and the chart-space `{ time, price }` under the pointer.
`coordinate.pageX`/`pageY` (page-relative pixels) are populated for `onSelect` /
`onRightSelect` / `onDoubleSelect` — use them to position floating context menus
at the click without manual offset arithmetic. They are always 0 for
`onCrosshairMoved` (no native event origin).

**Overlay consumption:** `onSelect` / `onRightSelect` / `onDoubleSelect` only fire when the
click lands on the MAIN candle pane AND no overlay consumed the event. If an overlay
(e.g. an order line, drawing tool) handled the click, the callback is skipped. Use this
to let drawings take priority over chart-level click handlers.

**Single-click deferral:** `onSelect` is intentionally delayed ~250 ms so that a
following double-click cancels it — see gotcha #13.

## Overlay/Drawing Management

```javascript
// Create an overlay
const overlayId = chart.createOverlay({
  name: "straightLine",
  points: [{ timestamp, value }, { timestamp, value }],
  properties: { lineColor: "#ff0000", lineWidth: 2 }
}, paneId)

// Create order lines (pass options object, not positional args)
const orderLine = createOrderLine(chart.getChart(), {
  price: 42000,
  text: "Buy Limit",
  lineColor: "#00ff00",
  bodyBackgroundColor: "#1a1a2e",
  editable: true,
})
  .onCancel({ orderId }, (params) => cancelOrder(params.orderId))

// Remove
orderLine.remove()

// Toggle drawing mode
chart.setOverlayMode(mode)

// Query/modify via klinecharts
chart.getChart().getOverlays({ paneId: "candle_pane" })
chart.getChart().removeOverlay({ id: overlayId })
chart.getChart().overrideOverlay({ id: overlayId, lock: true })
```

## Storage/Persistence

```javascript
const storageAdapter = {
  async save(key, state) { await db.chartStates.put({ key, ...state }) },
  async load(key) { return await db.chartStates.get(key) || null },
  async delete(key) { await db.chartStates.delete(key) },
}

new Superchart({
  ...,
  storageAdapter,
  storageKey: `${coinraySymbol}_${resolution}`,
})
```

State is auto-saved on indicator/overlay/preference changes.

## Toolbar Customization

Add custom buttons/dropdowns to the period bar:

```javascript
// Simple button (right side by default)
const btn = chart.createButton({
  text: 'Alert',
  tooltip: 'Set price alert',
  onClick: () => openAlertDialog(),
})

// Button with SVG icon on the left side
chart.createButton({
  align: 'left',
  icon: '<svg viewBox="0 0 20 20" width="16" height="16">...</svg>',
  onClick: () => activateDrawingMode(),
})

// Dropdown menu
chart.createDropdown({
  text: 'Chart Type',
  items: [
    { text: 'Candlestick', onClick: () => setType('candle') },
    { type: 'separator' },
    { text: 'Line', onClick: () => setType('line') },
  ],
})
```

Returned elements are plain `HTMLElement`s — set `innerHTML`, add classes, etc.
If called before React mounts, calls are queued and replayed on `onApiReady`.

### Hiding the period bar

```javascript
// Hide the whole bar at construction
const sc = new Superchart({ ..., periodBarVisible: false })

// Or toggle at runtime
sc.setPeriodBarVisible(false)

// Hide individual built-in buttons via CSS targeting the data-button attribute:
//   [data-button="screenshot"]  { display: none; }
//   [data-button="fullscreen"]  { display: none; }
// Full list in SUPERCHART_API.md → "Period Bar Button IDs".
```

## Overlay Default Style Templates

New overlays inherit the user's last-used style per overlay type (TradingView behavior).
When `modifyOverlayProperties()` is called, the new properties are saved as the default
template for that overlay type. Defaults are persisted in `ChartState.overlayDefaults`.

## Overlay Timeframe Visibility

Overlays can be shown/hidden per timeframe. Configured via the overlay settings modal
(Visibility tab) or programmatically via `setOverlayTimeframeVisibility(id, visibility)`.
Rules are checked on period change: `period.span >= rule.from && period.span <= rule.to`
within each category. Persisted in `SavedOverlay.timeframeVisibility`.

## Overlay Extend Left/Right

Line-based overlays (`segment`, `fibonacciSegment`, `fibonacciExtension`) can extend
to viewport edges via `extendData: { extendLeft: true, extendRight: false }`.

## Debug Logging

Pass `debug: false` in constructor options to silence non-essential `console.log` calls.
Default is `true`. All internal logs go through the `log()` utility which checks this flag.

## Replay Engine Usage

The replay engine is merged into Superchart's main branches and is a first-class feature.
Full upstream reference: `$SUPERCHART_DIR/docs/replay.md`.

### Accessing the engine

`sc.replay` returns `ReplayEngine | null`. It is `null` until the internal klinecharts
chart mounts (same timing as `getChart()`). Use `onReady` to gate access:

```javascript
// Wait for chart to be ready, then access replay
sc.onReady(() => {
  wireReplay(sc.replay)
})
```

### Starting a session

`setCurrentTime` is async — `await` it (or listen to `onReplayStatusChange`) before
calling `play` / `step`:

```javascript
// Start replay at 24h ago, optional end cap 1h ago
await sc.replay.setCurrentTime(Date.now() - 24 * 3600_000, Date.now() - 3600_000)
sc.replay.play(20)  // 20 candles/sec
```

### Status subscription

```javascript
const unsub = sc.replay.onReplayStatusChange((status) => {
  // 'idle' | 'loading' | 'ready' | 'playing' | 'paused' | 'finished'
  dispatch(setReplayStatus(status))
})
// cleanup: unsub()
```

### Step subscription

```javascript
sc.replay.onReplayStep((candle, direction) => {
  // direction: 'forward' | 'back'
  dispatch(setReplayCurrentTime(sc.replay.getReplayCurrentTime()))
  dispatch(setReplayPrice(candle.close))
})
```

### Error handling

```javascript
sc.replay.onReplayError((error) => {
  const messages = {
    unsupported_resolution: "Resolution not supported for replay.",
    no_data_at_time: "No data at this time.",
    resolution_change_failed: "Period change failed; reverted.",
    partial_construction_failed: "Could not build partial candle.",
  }
  showToast(messages[error.type] ?? "Replay error")
  // For resolution_change_failed, also sync external period state:
  if (error.type === "resolution_change_failed") {
    const ep = sc.getChart()?.getPeriod()
    if (ep) dispatch(setPeriod(ep))
  }
})
```

### Exiting replay

```javascript
await sc.replay.setCurrentTime(null)  // clears state, resumes live mode
// Or just change symbol — sc.setSymbol() exits replay automatically
```

### Controller pattern note

In Altrady, a `ReplayController` owns all replay state. Wire `onReplayStatusChange`,
`onReplayStep`, and `onReplayError` in the controller (not in a component). Dispatch
Redux actions to propagate status / currentTime to the UI. Unsubscribe all three in
the controller's `dispose()`. Colors and labels for any replay-related visuals are
built in the controller from `chartColors`, per Altrady overlay conventions.

### Datafeed requirement for replay

`Datafeed.getBars` must honour `from` when `countBack === 0` — the replay engine's
`getRange` always calls with `countBack: 0`. If your existing implementation derives
`from` from `countBack`, add a branch for the `countBack === 0` path.

Add optional `getFirstCandleTime` to enable start-time validation:

```javascript
getFirstCandleTime(symbolName, resolution, callback) {
  // return Unix ms timestamp of earliest available candle, or null
  CoinrayCache.getFirstCandleTime(symbolName, resolution)
    .then(ts => callback(ts))
    .catch(() => callback(null))
}
```

### What to disable in Altrady during replay

- Live price ticker (freeze or hide — chart shows historical data)
- Order placement forms (price shown is historical)
- Alert triggers based on chart price
- Provide a visible "Exit Replay" / "Go Live" button that calls `sc.replay.setCurrentTime(null)`

## Cleanup Pattern

```javascript
return () => {
  chartRef.current?.dispose()       // Disposes all: providers, React root, klinecharts, store
  chartRef.current = null
  datafeedRef.current?.dispose?.()  // Unsubscribes all candle subscriptions
  datafeedRef.current = null
}
```

`dispose()` does: clean up event subscriptions, clear all listeners, dispose
indicatorProvider, dispose scriptProvider, unmount internal React root, call
klinecharts `dispose()`, remove CSS classes, reset store. `destroy()` is an alias.

## Non-Obvious Gotchas

1. **Two React roots**: Superchart creates its own React root internally. It does
   NOT share React context with the host app. Communication goes through the
   `Superchart` class API only.

2. **React.StrictMode**: Double-mount effects in the host app will create/destroy/
   recreate the Superchart instance. Ensure refs are properly cleaned up.

3. **`_api` is null initially**: Safe — methods fall back to store getters/setters
   which are populated synchronously by the constructor.

4. **`onReady` must fire async**: `Datafeed.onReady()` must call its callback via
   `setTimeout(() => callback(config), 0)`. This is required by the TradingView
   convention and expected by `createDataLoader`.

5. **Bar.time is ms, PeriodParams.from/to is seconds**: The `Datafeed.getBars()`
   callback must return `Bar` objects with `time` in milliseconds. But
   `PeriodParams.from/to` arrive in seconds.

6. **Locale crash**: `setLocale()` with anything other than `en-US` or `zh-CN`
   crashes klinecharts canvas tooltip. Only 2 locales are registered with no fallback.

7. **`resolutionToPeriod`/`periodToResolution` NOT exported**: They exist in
   superchart source but are not re-exported from the main entry point.
   The desktop app implements its own versions in `helpers.js`.

8. **Queued requests in createDataLoader**: `getBars()` can be called before
   `resolveSymbol()` completes. The loader chains resolution as a promise, so
   bar requests queue behind symbol resolution automatically.

9. **Constructor renders async but setters work sync**: The constructor updates
   the internal signal store synchronously. React rendering is async. Calling
   `setSymbol()`/`setPeriod()` immediately after construction is safe.

10. **getChart() may return null**: Before the internal klinecharts instance is
    mounted, `getChart()` returns null. Gate overlay operations behind a null check.
    Use `sc.onReady(callback)` to run code once `getChart()` is guaranteed non-null.
    If the chart is already ready, the callback fires immediately.

11. **createButton/createDropdown before mount**: If called before React mounts,
    the calls are queued internally and replayed when `onApiReady` fires. The
    returned HTMLElement is a placeholder — it won't be the actual toolbar element.

12. **onVisibleRangeChange timestamps**: The `VisibleTimeRange.from`/`.to` are
    unix seconds (not ms). They are derived from the klinecharts data list
    timestamps divided by 1000.

13. **`onSelect` is deferred 250 ms**: Single clicks are held for ~250 ms before
    `onSelect` fires so that a following double-click can cancel the pending call
    and invoke `onDoubleSelect` instead. Do not chain a synchronous UI response
    directly off `onSelect` if users might double-click — prefer `onDoubleSelect`
    for actions that should pre-empt the single-click path. `onRightSelect` and
    `onCrosshairMoved` are NOT deferred.

14. **Pointer events require an uncaptured click**: `onSelect` / `onRightSelect` /
    `onDoubleSelect` only fire when the click was NOT consumed by an overlay
    (drawings, order lines, trade markers, etc.). Interactive overlays take
    priority. If you need chart-level clicks to always fire, set `ignoreEvent: true`
    (via `extendData`) on the overlays that should pass-through.

15. **`sc.replay` is null until chart mounts**: Same timing as `getChart()` — the
    klinecharts instance isn't available synchronously. Use `sc.onReady()` instead
    of polling with `setInterval`. The internal error→period-sync listener is
    registered automatically on first non-null read of `sc.replay` (idempotent).

16. **`getBars` with `countBack: 0` required for replay**: `createDataLoader`'s
    `getRange` method (used exclusively by the replay engine) calls `getBars` with
    `countBack: 0`. If your `getBars` derives `from` from `countBack` instead of
    reading `from` directly, replay buffer fetches return wrong data. Only the
    `countBack === 0` path needs the fix; normal `countBack > 0` loading is
    unaffected.

17. **`pageX`/`pageY` in `PriceTimeResult`**: `coordinate.pageX`/`pageY` carry
    page-relative pixels only for `onSelect` / `onRightSelect` / `onDoubleSelect`
    (pulled from the originating DOM event). They are always `0` for
    `onCrosshairMoved`. Use them to position a floating context menu at the exact
    click location without manual offset math.

18. **`SuperchartDataLoader.getConfiguration()` for symbol-search UIs**: The
    `DatafeedConfiguration` (exchanges, symbolsTypes) captured by `Datafeed.onReady`
    is now exposed via `dataLoader.getConfiguration()`. SC uses it internally to
    populate the exchange filter tabs in the built-in symbol-search modal. If
    application code needs those filter lists (e.g. a custom picker), read them
    from `getConfiguration()` after `onReady` has fired — returns `null` before.
