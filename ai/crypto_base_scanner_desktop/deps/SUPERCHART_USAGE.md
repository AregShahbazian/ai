# Superchart Usage Patterns

> Source: `$SUPERCHART_DIR` (example app + source, branch: main)
> Superchart git hash: `f51001b2d48690e8c34695b188f08eb8903b4430`
> coinray-chart (`packages/coinray-chart`, branch: main) git hash: `2b25f9fb8a65ffe338e571b1fd1580e328244e7f`
> Do NOT explore source — use this doc instead.

## Package rename (SC `474f052`)

Upstream package was renamed `superchart` → `@coinrayio/superchart` and
bumped to `0.1.0`. The app's `package.json` still pins
`"superchart": "link:../Superchart"`, so the symlink keeps imports
working under the old name. **Keep using `from "superchart"` in this
repo** until the dep entry is renamed; do not switch import strings
ad-hoc or they'll break the linked-package resolution.

## Two editions: community vs enterprise (SC `24e6fb8`)

SC now ships two npm packages from one source tree:
`@coinrayio/superchart` (community, `dist-community/`) and
`@coinrayio/superchart-enterprise` (enterprise, `dist-enterprise/`).
The root `package.json` `main`/`module`/`types`/`exports` point at
`dist-enterprise/`, so consuming the repo by symlink/git URL always
yields the enterprise edition. The Altrady symlink resolves to
enterprise — the `brand` option is available and respected at runtime.

Edition can be read at runtime:

```javascript
import { Superchart, edition, EDITION } from "superchart"
Superchart.edition() // "enterprise" in this repo
edition()             // "enterprise"
EDITION               // "enterprise"
```

In community, `brand` is `Omit`-stripped from `SuperchartOptions`'s
type and ignored at runtime (the Altrady badge is locked in). In
enterprise it's a real option — see "Branding / Watermark" below.

## Library version & welcome banner (SC `17dc259`, updated in `24e6fb8`)

- `Superchart.version()` — TV-style static method, returns `"0.1.0"`.
- `import { version, VERSION } from "superchart"` — function or constant
  form, same value.
- First chart instance per page logs a dashed-border welcome banner to
  the console with the bundled version. Subsequent instances on the
  same page are silent. Survives HMR. Not `NODE_ENV`-gated, so it shows
  in production too. Cannot be suppressed from the host side.
- In the enterprise build (what the app uses), the banner appends
  " Enterprise" to the message ("Welcome to Superchart Enterprise v…").

## Branding / Watermark (SC `24e6fb8`)

Every `Superchart` instance auto-renders a watermark badge in the
chart's bottom-left corner. There is no off-by-default mode. To control
it (enterprise only):

```javascript
// Hide entirely
new Superchart({ ..., brand: false })

// Override with custom mark
new Superchart({
  ...,
  brand: {
    logo: "<svg>...</svg>" || <MyLogo />,  // SVG string, URL/data-URI, or ReactNode
    name: "My App",                        // text next to logo
    url:  "https://my.app/chart",          // makes badge clickable; omit for visual-only
  },
})

// Omit `brand` → default Altrady badge (logo + "Superchart" + altrady.com/superchart)
```

Visual styling is overridable via CSS custom properties on the host
container (`--superchart-brand-color`, `--superchart-brand-background`,
etc.) — no need to touch the component. If the app ever wants to fully
suppress the watermark, set `brand: false` on the constructor (works
today via the enterprise symlink).

## Dependencies

`superchart` exposes its own public API — do NOT install or import from
`klinecharts` directly. As of SC `0bb516b`, klinecharts is bundled into
`dist/superchart.{es,cjs}.js` (moved to devDependencies; removed from
`rollupOptions.external`). All types, registration functions
(`registerOverlay` / `registerFigure` / `registerIndicator`), and constants
needed for custom overlays/indicators are re-exported from `superchart`.
Importing from klinecharts would resolve to a different engine instance
than the one SC registered overlays/figures against, causing silent
failures.

Also fixed in `0bb516b` (no API surface change):
- `applyChartTemplate` no longer cross-contaminates layout when multiple
  `useChartState` instances are active, and no longer marks itself dirty
  mid-apply.
- `sc.dispose()` no longer triggers an autosave storm during teardown.

## Multi-instance

Two or more `Superchart` instances on one page coexist as of SC `276e661`.
Each instance owns its own `ChartStore`. Required disciplines:

- One `Datafeed` per `Superchart` — never share. Each instance constructs
  its own `new CoinrayDatafeed()` and `createDataLoader(datafeed)`.
- Distinct container DOM elements — never reuse a `useRef<HTMLDivElement>`
  across two constructors.
- Dispose order on unmount: `superchart.dispose()` then `datafeed.dispose()`.
- Pass distinct `storageKey`s if both instances render the same `ticker`
  AND a `storageAdapter` is wired. SC's default `storageKey` is
  `symbol.ticker` and would collide.
- Pass `SymbolInfo.shortName` for human-friendly legend (template
  `{shortName||ticker} · {period}`, coinray-chart `2d463e69`).

Reference: `$SUPERCHART_DIR/.storybook/api-stories/MultiChart.stories.tsx`.

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

// Remove via SC API (preferred — routes through persistence pipeline; canvas/storage/modal stay in sync)
chart.removeOverlay(overlayId)       // overlay id returned by createOverlay
chart.removeIndicator("RSI")         // indicator type-name; no-op if not active

// Query/modify via klinecharts (escape hatch — bypasses SC lifecycle; no autosave, no modal sync)
chart.getChart().getOverlays({ paneId: "candle_pane" })
chart.getChart().removeOverlay({ id: overlayId })
chart.getChart().overrideOverlay({ id: overlayId, lock: true })
```

## Storage/Persistence

### Bundled adapters (new in 8c245a1)

```javascript
import { LocalStorageAdapter, HttpStorageAdapter } from 'superchart'

// localStorage-backed (dev / small data)
const storageAdapter = new LocalStorageAdapter({ prefix: 'altrady:' })

// HTTP-backed (production)
const storageAdapter = new HttpStorageAdapter({
  baseUrl: '/api/chart-state',
  headers: () => ({ Authorization: `Bearer ${getToken()}` }),
})
```

### Custom adapter (minimal, last-write-wins)

```javascript
const storageAdapter = {
  async load(key) { return await db.chartStates.get(key) || null },
  async save(key, state) {
    await db.chartStates.put({ key, ...state })
    return { revision: Date.now() }   // return StorageWriteResult
  },
  async delete(key) { await db.chartStates.delete(key) },
}
```

### Custom adapter (with optimistic concurrency)

Implement `expectedRevision` to prevent clobbering concurrent saves:

```javascript
async save(key, state, expectedRevision) {
  const existing = await db.get(key)
  if (expectedRevision !== undefined && existing?.revision !== expectedRevision) {
    throw new StorageConflictError(existing.state, existing.revision)
  }
  const revision = (existing?.revision ?? 0) + 1
  await db.put({ key, state, revision })
  return { revision }
}
```

SC catches `StorageConflictError` internally, merges states, and retries up to 3 times. After 3 failures it calls `onStorageError` and re-throws.

> **Symbol/period autosave race fixed in SC `6e9266b`.** Pre-`6e9266b`,
> `useChartState` was instantiated at ~8 sites inside SC (period bar,
> popups, templates, etc.). Each call attached its own
> symbol/period autosave subscriber, so a single symbol or period
> change would fan out to 8 concurrent `enqueueMutation` calls on the
> same storage key, blow past `SAVE_RETRY_LIMIT`, and surface a
> spurious `StorageConflictError` through `onStorageError`. SC now
> gates that subscriber behind a `mirrorSymbolPeriod` flag and only
> the top-level `SuperchartComponent` sets it. No host change needed
> — if you added a workaround to silence `StorageConflictError` in
> `onStorageError` on symbol/period switches, it can be removed.

### Wiring to Superchart

```javascript
new Superchart({
  ...,
  storageAdapter,
  storageKey: `${coinraySymbol}_${resolution}`,  // default: symbol.ticker
  onStorageError: (err) => dispatch(showErrorToast(err.message)),
  autoSaveDelay: 500,   // collapse rapid drawing edits into one save per 500ms
})
```

State is auto-saved on indicator/overlay/preference changes. Disable auto-save with `disabledFeatures: ['auto_save_state']` and call `sc.saveState()` explicitly.

### Imperative API

```javascript
await sc.saveState()                          // force-save now
await sc.loadState()                          // re-fetch and re-apply from adapter
await sc.clearState()                         // delete remote record; chart unchanged
const entries = await sc.listSavedStates()    // list all saved keys
```

All four are no-ops when no `storageAdapter` is configured.

### Study / Drawing templates

Shown in indicator settings modal and overlay floating settings when the adapter implements the optional template methods:

```javascript
const storageAdapter = {
  // ... core methods ...

  // Study templates (all 4 required to enable UI)
  async listStudyTemplates(indicatorName) { return [] },
  async loadStudyTemplate(name) { return null },
  async saveStudyTemplate(name, template) { /* persist */ },
  async deleteStudyTemplate(name) { /* delete */ },

  // Drawing templates (all 4 required to enable UI)
  async listDrawingTemplates(toolName) { return [] },
  async loadDrawingTemplate(toolName, name) { return null },
  async saveDrawingTemplate(toolName, name, template) { /* persist */ },
  async deleteDrawingTemplate(toolName, name) { /* delete */ },
}
```

To include the bundled system presets in your list responses, merge `SYSTEM_STUDY_TEMPLATES` / `SYSTEM_DRAWING_TEMPLATES` into the returned arrays. Hide these features with `disabledFeatures: ['study_templates', 'drawing_templates']`.

### Chart templates — named full-chart layouts (new in 69a41cf)

A "chart template" is a snapshot of a complete chart (indicators + overlays + styles
+ pane layout + preferences + symbol + period) saved under a name. Applying a
template is a **full chart swap** — TV "Chart Layout" semantics, distinct from the
per-overlay/per-indicator study and drawing templates above. The active template is
tracked in `ChartState.activeChartTemplate`; with `auto_save_state` enabled, edits
re-save the active template (`ea1dd96`).

Enabled when: `chart_templates` feature flag is `true` AND the adapter implements
`list/load/save/deleteChartTemplate` (rename/duplicate are optional and fall back to
load+save+delete).

```javascript
const storageAdapter = {
  // ... core methods + study + drawing template methods ...

  async listChartTemplates() { return [] },                    // → ChartTemplateMeta[]
  async loadChartTemplate(name) { return null },               // → ChartTemplate | null
  async saveChartTemplate(name, template) { /* persist */ },
  async deleteChartTemplate(name) { /* delete */ },
  // Optional (SC falls back to load+save (+delete) if missing):
  async renameChartTemplate(oldName, newName) { /* atomic rename */ },
  async duplicateChartTemplate(name, newName) { /* atomic duplicate */ },
}
```

Imperative usage:

```javascript
await sc.saveChartTemplate("Scalp")                  // snapshot current chart
await sc.listChartTemplates()                        // → ChartTemplateMeta[]
await sc.applyChartTemplate("Scalp")                 // restore — swaps symbol+period too
await sc.renameChartTemplate("Scalp", "Day-trade")
await sc.duplicateChartTemplate("Scalp", "Scalp 2")
await sc.deleteChartTemplate("Scalp")
```

**Altrady note:** Keep `chart_templates` and `multi_chart_browser` disabled until the
backend adapter implements the six chart-template methods. Until then leave them in
`disabledFeatures`.

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

## setVisibleRange / resetView (async — 12e80de)

Both methods are now async. Always await them and handle `SetVisibleRangeError`.

```javascript
import { isSetVisibleRangeError } from 'superchart'

// Scroll/zoom to a specific time range (unix seconds)
try {
  await sc.setVisibleRange({ from: question.solutionStart / 1000, to: question.solutionEnd / 1000 })
} catch (e) {
  if (isSetVisibleRangeError(e)) {
    if (e.code === 'no_data_at_time') showToast('No data at this time')
    if (e.code === 'aborted') { /* chart unmounted — ignore */ }
  }
}

// Reset to default zoom (live view, default bar space)
await sc.resetView()
```

Both calls are safe before the chart is ready — they wait for the API-ready signal internally (the same one `onApiReady` exposes). Both are also safe during an init load — they queue and drain when the load completes (latest call wins).

`setVisibleRange` fetches missing history backward if `range.from` is before the loaded data buffer. This requires `dataLoader.getRange` to be present (it is, via `createDataLoader`).

## Replay Engine Usage

The replay engine is merged into Superchart's main branches and is a first-class feature.
Full upstream reference: `$SUPERCHART_DIR/docs/replay.md`.

### Accessing the engine

`sc.replay` returns `ReplayEngine | null`. It is `null` until the internal klinecharts
chart mounts (same timing as `getChart()`). Use `onApiReady` to gate access:

```javascript
// Wait for chart to be ready, then access replay
sc.onApiReady(() => {
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

## Feature Flags

Control which SC UI features are available at construction time:

```javascript
new Superchart({
  ...,
  enabledFeatures:  ['crosshair_magnet'],
  disabledFeatures: ['study_templates', 'drawing_templates', 'chart_templates',
                     'multi_chart_browser', 'auto_save_state',
                     'settings_button', 'timezone_button'],
})
```

New flags in 69a41cf (`9adf04f`):

- `settings_button` (default `true`) — hides the gear/settings button in the period bar
- `timezone_button` (default `true`) — hides the timezone selector button in the period bar

Both default ON; disable to reclaim toolbar space when the host app exposes its own settings/timezone UI.

`disabledFeatures` wins when a flag appears in both lists. Toggle at runtime:

```javascript
sc.setFeatureEnabled('crosshair_magnet', true)
sc.isFeatureEnabled('drawing_bar')  // → boolean
```

React components inside SC re-render automatically via `useFeature` when a flag changes. See `SUPERCHART_API.md → FeatureFlag` for all flags and defaults.

**Altrady note:** Disable `study_templates`, `drawing_templates`, `chart_templates`, and `multi_chart_browser` until those features are wired to the Altrady backend. Disable `auto_save_state` if manual save control is required (then call `sc.saveState()` explicitly).

## Transient Overlays (`save: false`)

Overlays created with `save: false` render on the chart but are never written to the `StorageAdapter` and are not restored on reload:

```javascript
sc.createOverlay({
  name: 'timeLine',
  points: [{ timestamp: replayCurrentTime, value: 0 }],
  save: false,   // transient — not persisted
})
```

All Altrady app-driven overlays (order lines, price lines, trade lines via the fluent factories) never save by design — they bypass SC's overlay lifecycle. Any new `createOverlay` calls for replay markers, measurement tools, or other app-managed transient overlays should pass `{ save: false }`.

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



## BREAKING: DatafeedConfiguration Fields Renamed to snake_case (ce4c809)

`DatafeedConfiguration` aligns all fields to snake_case to match the TradingView Datafeed contract:

| Old (camelCase) | New (snake_case) |
|---|---|
| `supportedResolutions` | `supported_resolutions` |
| `symbolsTypes` | `symbols_types` |

**Action required:** Update every `Datafeed.onReady` callback that constructs `DatafeedConfiguration`:

```javascript
// Before (broken after ce4c809)
setTimeout(() => callback({ supportedResolutions: SUPPORTED_RESOLUTIONS, symbolsTypes: [{name: "Crypto", value: "crypto"}] }), 0)

// After
setTimeout(() => callback({ supported_resolutions: SUPPORTED_RESOLUTIONS, symbols_types: [{name: "Crypto", value: "crypto"}] }), 0)
```

In Altrady, update `coinray-datafeed.js` lines 36-38 — both field names appear there.
The other fields (`exchanges`, `supports_marks`, `supports_timescale_marks`) were already snake_case and are unchanged.

## User-Drawn Overlay Context Menu (2954fe0 / 8ea9d2c / 548ca06 / 6d68fbb)

SC exposes three new `SuperchartApi` methods and one new constructor option for building
a host-rendered right-click context menu on user-drawn overlays.

### Constructor option

```javascript
new Superchart({
  onUserOverlayRightClick: (event) => {
    // event is OverlayEvent<unknown>
    // event.overlay.id  — the right-clicked overlay id
    // event.overlay.name — overlay type (e.g. "segment")
    // event.pageX / event.pageY — page coords for anchoring the popover
    openOverlayContextMenu(event)
  },
})
```

When `onUserOverlayRightClick` is supplied, SC suppresses its built-in right-click popup
and calls this callback instead. Per-overlay `onRightClick` handlers (wired at `createOverlay`
time) take precedence over this global callback.

### Instance methods

```javascript
// Open SC's native overlay settings dialog (same as built-in "Settings" menu entry)
sc.openOverlaySettings(overlayId)

// Snapshot the overlay's current styling as a DrawingTemplate
const extracted = sc.getDrawingTemplate(overlayId)
// extracted: { toolName: "segment", template: { name: "", toolName: "segment", properties: {...} } }
// Fill template.name before persisting:
if (extracted) {
  const name = "My Trend Style"
  await storageAdapter.saveDrawingTemplate(extracted.toolName, name, { ...extracted.template, name })
}

// Apply a stored DrawingTemplate to an existing overlay
const tpl = await storageAdapter.loadDrawingTemplate("segment", "My Trend Style")
if (tpl) sc.applyDrawingTemplate(overlayId, tpl)

// Lock / unlock an overlay (routes through modifyOverlay pipeline; autosave fires)
sc.setOverlayLocked(overlayId, true)
sc.setOverlayLocked(overlayId, false)
```

**Altrady controller note:** Wire `onUserOverlayRightClick` in the `Superchart` constructor.
The callback should call a controller method to show the Altrady context menu — do NOT embed
rendering logic in the callback (controller owns all visual decisions). `openOverlaySettings`,
`getDrawingTemplate`, `applyDrawingTemplate`, and `setOverlayLocked` are called from context
menu action handlers in the controller.


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
    Use `sc.onApiReady(callback)` to run code once `getChart()` is guaranteed non-null.
    If the chart is already mounted, the callback fires immediately. Use
    `sc.onDataLoaded(callback)` instead when the code needs concrete bar data.

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
    klinecharts instance isn't available synchronously. Use `sc.onApiReady()` instead
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
    `DatafeedConfiguration` (exchanges, symbols_types) captured by `Datafeed.onReady`
    is now exposed via `dataLoader.getConfiguration()`. SC uses it internally to
    populate the exchange filter tabs in the built-in symbol-search modal. If
    application code needs those filter lists (e.g. a custom picker), read them
    from `getConfiguration()` after `onReady` has fired — returns `null` before.

19. **`setVisibleRange` and `resetView` are now async** (12e80de): Both return
    `Promise<void>`. Fire-and-forget calls that previously worked silently will now
    swallow errors. Always `await` them inside an async function or attach `.catch()`.
    On component unmount, a queued call rejects with `code: 'aborted'` — that is safe
    to ignore. Wrap with `isSetVisibleRangeError` to distinguish it from real errors.

20. **`setVisibleRange` may trigger a network fetch**: If `range.from` is before the
    loaded data buffer, SC calls `dataLoader.getRange` to fetch missing history. The
    call is therefore not instant even when the chart is already ready. Do not assume
    the chart has scrolled to the target range synchronously after `await` — the
    promise resolves only after the fetch completes and the range is applied.

21. **`onReady` was split into `onApiReady` + `onDataLoaded`** (69a41cf): The single
    pre-69a41cf `onReady` option and method no longer exist. Use `onApiReady` for
    "chart instance exists" (toolbar/subscription wiring) and `onDataLoaded` for
    "bars are loaded" (overlays at concrete timestamps, screenshots). Both forms
    fire immediately if the milestone is already past and the method form returns
    an unsubscribe function. Migrate prior `sc.onReady(...)` calls to `sc.onApiReady(...)`
    unless the callback actually needs bar data — in which case prefer `onDataLoaded`.

22. **`removeOverlay` / `removeIndicator` should go through the SC API**: Use
    `sc.removeOverlay(id)` and `sc.removeIndicator(name)` rather than reaching into
    `sc.getChart().removeOverlay(...)`. The SC methods route through the persistence
    pipeline so canvas, storage, and the open settings modal stay in sync. The
    klinecharts-level call still works but bypasses autosave and the modal.

23. **Chart templates dirty the active template on edits**: When the user applies a
    chart template, `ChartState.activeChartTemplate` is set. With `auto_save_state` on,
    subsequent symbol/period/overlay/indicator changes re-save the template — not just
    the chart state. If the host UI tracks "dirty template" state, treat any chart edit
    while `activeChartTemplate` is set as a template-write event.

24. **`DatafeedConfiguration` fields are now snake_case** (ce4c809): `supportedResolutions` is now `supported_resolutions`; `symbolsTypes` is now `symbols_types`. Any `Datafeed.onReady` callback that passes the old camelCase keys will silently send `undefined` to SC (the symbol-search modal will have no exchange tabs or type filters). Update to the new names. See "BREAKING: DatafeedConfiguration Fields Renamed" section above.

25. **`onUserOverlayRightClick` suppresses the built-in popup** (2954fe0): Providing this constructor option fully disables SC's native right-click context menu for user-drawn overlays. The consumer becomes responsible for all context-menu entries. Call `sc.openOverlaySettings(id)` to re-expose the Settings dialog, `sc.setOverlayLocked(id, true/false)` for lock/unlock, and `sc.getDrawingTemplate(id)` / `sc.applyDrawingTemplate(id, tpl)` for template operations. Per-overlay `onRightClick` handlers (from `createOverlay`) still win over this global option.

26. **`resolveSymbol` now overrides construction-time precision** (f51001b2): The data
    loader syncs `pricescale`→`pricePrecision` and the new `volume_precision`→`volumePrecision`
    from the `LibrarySymbolInfo` back into the chart's `SymbolInfo` on first resolve. Whatever
    precision was passed to `new Superchart()` is overwritten once `resolveSymbol` returns — set
    `volume_precision`/`pricescale` in the datafeed if you want to control the y-axis precision.

27. **`Datafeed.searchSymbols` gained an optional `options` arg** (2b25f9fb): signature is now
    `searchSymbols(userInput, exchange, symbolType, onResult, options?: { offset?, limit? })`. The
    symbol-search modal passes `offset` for infinite scroll. Backward-compatible — datafeeds that
    ignore `options` still work, but paginate on `offset`/`limit` to support the modal's scroll.
