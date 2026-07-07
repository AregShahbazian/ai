# MCP chart tools → SuperChart parity — Design

PRD: `prd.md` (id `mcp-sc-bridge`). Verified against SC `f51001b` / coinray-chart
`2b25f9f` (deps docs are stale on overlay display-naming only; the `SuperchartApi`
surface is unchanged — see the SC-API investigation in the run notes).

## Architecture — provider-agnostic chart handle

Today `tools/charts.js` calls TV APIs directly through two registry helpers
(`withActiveChart` → `tvWidget.activeChart()`, `withTvWidget` → `tvWidget`). We
interpose a **uniform handle** so the tools never touch a provider API directly.

```
tools/charts.js ─┐
tools/context.js ┼─► chart-bridge/chart-handle.js
                 │      listCharts()        → union of TV + SC charts
                 │      resolveHandle(id)   → { provider, ...uniform methods }
                 │         ├─ tvHandle(tvState)      (TV path — unchanged calls)
                 │         └─ scHandle(controller)   (SC path — new)
                 │
                 ├─ widget-registry.js   (TV store, registration UNCHANGED)
                 └─ ChartRegistry        (SC store, the branch's canonical one)
```

**Decision (PRD R1):** no second registry for SC. `chart-handle.js` *reads*
`ChartRegistry` directly and unions it with the existing TV `widget-registry`.
SC widgets keep registering themselves via `ChartRegistry.register` exactly as
they do now (`super-chart.js:120`, `trading-terminal-chart.js:66`).

### Uniform handle interface

Both `tvHandle` and `scHandle` expose the same methods; tools call only these:

| Method | TV impl | SC impl |
|---|---|---|
| `meta` → `{id, coinraySymbol, resolution, ready, mainChart, provider}` | from tv state | from controller |
| `getResolution()` | `chart.resolution()` | `controller.getResolution()` |
| `setResolution(res)` | `chart.setResolution(res)` | `controller.setResolution(res)` |
| `listIndicators()` → `[{id,name,paneId?}]` | `chart.getAllStudies()` | `chart.getIndicators()` |
| `addIndicator(name, settings)` → `{studyId}` | `chart.createStudy(...)` | `chart.createIndicator(...)` |
| `removeIndicatorById(id)` | `chart.removeEntity(id)` | `chart.removeIndicator({name,paneId})` |
| `removeIndicatorsByName(name)` → `[ids]` | loop `getAllStudies` | `chart.removeIndicator({name})` |
| `listAvailableIndicators(name?)` | `tvWidget.getStudiesList/Inputs` | hardcoded catalog |
| `listDrawings()` → `[canonical]` | `getAllShapes` + `fromTradingView` | `getOverlays` + `fromSuperchart` |
| `addDrawing(canonical)` → `id` | `createMultipointShape` | `controller.createUserOverlay(...)` |
| `removeDrawing(id)` | `chart.removeEntity(id)` | `controller.removeUserOverlay(id)` |
| `clearDrawings()` | `chart.removeAllShapes()` | loop user overlays → remove |
| `screenshot()` → `url` | `captureScreenshot(widget)` + `.png` | `header.captureScreenshotForNote` |
| `isReady()` | `tvState.ready` | `!!controller.getChart()` |

`resolveHandle(id)` throws `chart_panel_not_open` when the id resolves to no
live/ready chart in either registry — identical error contract to today.

### `listCharts()` union shape

Returns the array `tabSummary()` (in `tools/context.js`) and `pickChartId()`
already consume — so R1 falls out with no change to the matching logic:

```js
{ id, coinraySymbol, resolution, ready, mainChart }   // + provider (internal)
```

- **TV entries** — unchanged, from `widget-registry.listCharts()`.
- **SC entries** — one per `ChartRegistry` controller:
  - `id` = `controller.id` (the `marketTabId || "main"` the TT chart registers).
  - `coinraySymbol` = `controller.currentMarket?.coinraySymbol` (public getter).
  - `resolution` = `controller.getResolution()` (new method, below).
  - `ready` = `!!controller.getChart()`.
  - `mainChart` = `controller.id === activeTradingTab.id` — parity-equivalent to
    TV's `mainChart` flag without needing a per-widget boolean (PRD R9: TV parity,
    one entry per grid chart widget, no per-pane).

`context.js`'s `tabSummary` matches a mounted chart to a trading tab by
`coinraySymbol`; since SC controllers now surface `coinraySymbol`, SC tabs report
`rendered: true` with a real `chartId`. **R1 done via the union alone.**

## SC drawing adapter — `chart-bridge/superchart-adapter.js`

Canonical drawing schema (`mcp/drawings/schema.js`, unchanged) ↔ SC overlays.
Mirrors the TV adapter's role. Key SC facts (from the SC-API investigation):

- Points: SC `Point = {timestamp(ms), value}` (TV used epoch **seconds**).
  `toScPoint({time,price}) → {timestamp: Date.parse(time), value: price}`;
  reverse `→ {time: new Date(ts).toISOString(), price: value}`.
- Create: `sc.createOverlay(overlayCreate & {properties?, save?})` → stable
  `overlay_<ms>_<n>` id (round-trips to `removeOverlay(id)`). Persisted by
  default (matches TV shapes surviving reload). Wrapped by
  `controller.createUserOverlay()`.
- Remove: `sc.removeOverlay(id)` (single only — no bulk; clear loops).

### kind → SC overlay name

| canonical | SC overlay `name` | pts |
|---|---|---|
| `line` mode `horizontal` | `horizontalStraightLine` | 1 |
| `line` mode `vertical` | `verticalStraightLine` | 1 |
| `line` mode `trend` | `segment` | 2 |
| `line` mode `ray` | `rayLine` | 2 |
| `rectangle` | `rect` | 2 |
| `fib_retracement` | **`fibonacciSegment`** (naming trap — *not* `fibonacciLine`, which is the "Fibonacci Channel") | 2 |
| `label` | `text` | 1 |
| `arrow` | `arrow` | 1 |

### Style mapping

- **Pro overlays** (`segment`, `rect`, `fibonacciSegment`) read style from an
  internal properties Map, not `styles` (per SC integration context doc). Pass
  `properties: {lineColor, lineWidth, lineStyle}` (lineStyle string:
  `solid|dashed`, `dotted→dashed`).
- **Standard overlays** (`horizontalStraightLine`, `verticalStraightLine`,
  `rayLine`, `text`, `arrow`): pass `styles: {line:{color,size,style}}` /
  `styles:{text:{color,size}}`.
- Rectangle fill → `properties`/`styles` polygon color + opacity (best-effort).
- `fromSuperchart(overlay)` reads `overlay.styles`/`overlay.extendData` back to
  the canonical `{style,fill,label}` (best-effort; symmetric with the above).

### User-drawing classification (list / clear scoping)

`getOverlays()` returns BOTH user drawings and app-managed overlays (orders,
alerts, bid/ask, bases, break-even, pnl — created via `controller._createOverlay`
with names like `priceLevelLine`, `timeLine`, `styledSegment`, `tradeLine`,
`fontAwesomeMarker`, `priceLevelLine`). To match TV's `getAllShapes` (user
shapes only), we **whitelist** the user-drawable catalog:

```
USER_DRAWING_OVERLAY_NAMES = { horizontalStraightLine, horizontalRayLine,
  horizontalSegment, verticalStraightLine, verticalRayLine, verticalSegment,
  straightLine, rayLine, segment, parallelStraightLine, priceChannelLine,
  fibonacciLine, fibonacciCircle, fibonacciSegment, fibonacciSpiral,
  fibonacciSpeedResistanceFan, fibonacciExtension, arrow, circle, rect,
  triangle, parallelogram, brush, threeWaves, fiveWaves, eightWaves, anyWaves,
  abcd, xabcd, gannBox, text, note, callout, comment, measure }
```

`listDrawings`/`clearDrawings` operate only on overlays whose `name` is in this
set — app overlays (distinct names) are never listed or wiped. Overlays whose
`name` isn't a canonical kind still list with `kind = name` (parity with TV's
`KIND_FROM_SHAPE` fallthrough).

> **Known rough edges (documented, best-effort in v1):** `arrow` direction and
> rectangle fill fidelity depend on SC overlay internals; `fromSuperchart` style
> read-back may under-report for Pro overlays. These are style-fidelity only —
> create/list/remove/round-trip all work. Recorded for a follow-up polish pass;
> no SC source change requested yet.

## Indicators (R5 full parity) — `superchart-adapter.js`

- **list** — `chart.getIndicators().map(i => ({id:i.id, name:i.name, paneId:i.paneId}))`.
- **add** — `chart.createIndicator(name, false, undefined)`; then look up the
  created indicator by name to return its `{studyId:id}`. `settings.inputs` →
  `IndicatorCreate.calcParams` (array) when provided.
- **removeById** — find in `getIndicators()` by id → `chart.removeIndicator({name,paneId})`.
- **removeByName** — `chart.removeIndicator({name})` (all panes).
- **available catalog** — SC does not re-export `getSupportedIndicators`
  (engine-internal per SC re-export policy). Hardcode the klinecharts built-in
  set: `MA, EMA, SMA, BBI, VOL, MACD, BOLL, KDJ, RSI, BIAS, BRAR, CCI, DMI, CR,
  PSY, DMA, TRIX, OBV, VR, WR, MTM, EMV, SAR, ROC, PVT, AO`. `listAvailableIndicators(name)`
  returns `{name, calcParams}` from a freshly-introspected/default template
  (best-effort). **Full parity for the operational tools (list/add/remove);**
  the *catalog* is a static list — logged as an SC feature request
  (getSupportedIndicators export) rather than worked around further.

## Screenshot (R6)

`scHandle.screenshot()` promisifies the controller's existing note path:

```js
new Promise((resolve) => controller.header.captureScreenshotForNote(resolve))
```

`captureScreenshotForNote` already uploads (`uploadScreenshot`) and resolves the
hosted image URL via `fetchScreenshotImageUrl` — returns the final URL directly
(no `.png` suffix; that suffix is TV-only). Returns `false` on failure → tool
throws `upstream_error` (same as TV).

## readyToDraw (R8)

**Gap:** TV dispatches redux `setChartReadyToDraw` (`use-trading-view.js:408,518`,
gated on `mainChart`) → `state.replay.chartReadyToDraw` → the intro-modal
Start/Resume buttons (`onboarding-smart-trading-intro-modal.js:86,246,263`
`disabled={!chartReady}`). SC's `_setReadyToDraw` only sets **local** React state
(`super-chart/context.js:29`) — the redux flag stays false, buttons stuck.

**Fix (mirror TV, main chart only):**
- `ChartController` gains `_isMainChart` (from a new `controllerOptions.isMainChart`,
  default `false`).
- In the existing `superchart.onApiReady` handler (chart-controller.js:74) — after
  `_setReadyToDraw(true)` — also `if (this._isMainChart) this.dispatch(setChartReadyToDraw(true))`.
- In `dispose()` — `if (this._isMainChart) this.dispatch(setChartReadyToDraw(false))`.
- `useMarketTabChart` accepts `isMainChart` and forwards it into
  `controllerOptions`; `TradingTerminalChart` passes `isMainChart: true`. Grid /
  charts-page charts omit it (stay `false`) — so only the main trading chart
  drives the single global flag, exactly like TV's `mainChart` gate (R9 parity).

Dispatch happens *inside* the controller (`this.dispatch`) — compliant with the
"no external dispatch/getState" rule.

## open_market / tab auto-switch (R7)

`activateMarketTab` (TradingTabsController) is already provider-agnostic — the SC
`CandleChart` mounts on tab activation. Only the post-activate timeframe set is
TV-coded today (`tv.tvWidget.activeChart().setResolution`). Rewrite to:
`activateMarketTab` → `waitForChart` (unified) → `resolveHandle(id).setResolution(tf)`.
After it resolves, the chart is discoverable via the unified `listCharts()` (R7
acceptance).

## ChartController additions (desktop code — SC lib untouched)

All new methods are thin wrappers keeping SC/klinecharts calls inside the
controller boundary (per the integration context doc's "controller owns all SC
API calls"):

```js
getResolution()              → periodToResolution(this._superchart.getPeriod())
setResolution(res)           → this._superchart.setPeriod(toPeriod(res))
createUserOverlay(create)    → this._superchart.createOverlay(create)   // persisted
removeUserOverlay(id)        → this._superchart.removeOverlay(id)
listUserOverlays()           → this.getChart()?.getOverlays() ?? []
```

Indicator ops in the adapter use the public `controller.getChart()`.
`_isMainChart` + readyToDraw dispatch as in R8.

## Files

**New**
- `src/mcp/chart-bridge/superchart-adapter.js` — `toSuperchart`/`fromSuperchart`,
  `USER_DRAWING_OVERLAY_NAMES`, `AVAILABLE_INDICATORS`, indicator helpers.
- `src/mcp/chart-bridge/chart-handle.js` — `listCharts()`, `resolveHandle(id)`,
  `tvHandle`, `scHandle`.

**Edit**
- `src/mcp/chart-bridge/widget-registry.js` — expose TV-only `listTvCharts()` /
  `getTvChart()` (rename internal), keep `withActiveChart`/`withTvWidget` for the
  TV handle. Registration path untouched.
- `src/mcp/tools/charts.js` — tools call `resolveHandle`/handle methods; `pickChartId`/
  `waitForChart`/`resolveProvidedChartId` use unified `listCharts`/`getHandle`.
- `src/mcp/tools/context.js` — import `listCharts` from `chart-handle`; tweak
  chart-id wording (drop "TradingView widget id").
- `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`
  — new methods + `_isMainChart` + `setChartReadyToDraw` dispatch.
- `.../super-chart/charts/market-tab-chart.js` — accept + forward `isMainChart`.
- `.../super-chart/charts/trading-terminal-chart.js` — pass `isMainChart: true`.

## Requirement → design-section map

- **R1 discovery/resolution** → `chart-handle.js` union `listCharts()` + `resolveHandle`; `context.js` unchanged matching.
- **R2 provider dispatch** → `resolveHandle` returns provider-tagged handle; single id resolves its provider via which registry holds it.
- **R3 timeframe** → handle `get/setResolution`; `ChartController.get/setResolution`.
- **R4 drawings** → `superchart-adapter.js` (`to/fromSuperchart`, whitelist), handle `list/add/remove/clearDrawings`, `createUserOverlay/removeUserOverlay`, stable overlay-id round-trip.
- **R5 indicators (full parity)** → adapter indicator helpers + hardcoded catalog; handle `list/add/removeById/removeByName/listAvailable`.
- **R6 screenshot** → `scHandle.screenshot()` → `header.captureScreenshotForNote`.
- **R7 open_market/auto-switch** → provider-agnostic `activateMarketTab` + unified `waitForChart` + `handle.setResolution`.
- **R8 readyToDraw** → controller `_isMainChart` + `setChartReadyToDraw` dispatch; `isMainChart` threaded through TT chart.
- **R9 multi-chart TV parity** → union yields one entry per grid chart widget; `mainChart` derived from active-tab id; no per-pane surface added.
- **Non-req: no second registry** → `chart-handle` reads `ChartRegistry`; no SC registration added.
- **Non-req: TV byte-compatible** → `tvHandle` wraps the exact existing calls; TV registration/screenshot modules untouched.
- **Non-req: no SC source change** → all additions are desktop-side; catalog + bulk-remove done client-side; gaps logged as SC feature requests.
