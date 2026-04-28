# Multi-Chart Unblock — Design

## Scope

Six small surgical changes:

1. Patch `ai/deps/SUPERCHART_API.md` + `SUPERCHART_USAGE.md` to current
   SC hashes.
2. Delete the TT main ↔ settings-preview unmount workaround
   (`previewShown` plumbing across three files).
3. Delete the grid-bot settings kill-switch (`SHOW_SETTINGS_CHART`).
4. Add `controller.id` on `ChartController` and route replay's
   `_chartId` + `replay-context.js` through it (Q3 resolution).
5. Convert four `getActive()` callers to explicit-`chartId` lookups
   plumbed through `MarketTabContext` (TT) or `BotFormContext`
   (grid-bot).
6. Strip dead surface from `chart-registry.js`
   (`getActive`/`setActive`/`getAll`/`activeId`).

Order matters only for (4) and (5): `controller.id` must exist before
`replay-context.js` is rewired and before `actions/replay.js` callers
are converted.

No new abstractions, no new contexts, no new hooks — `BotFormContext`
gets one new field (`chartId`), nothing else.

## Architecture decisions

### `controller.id` as the single source of truth

`ChartController` gains a public `id` field, set at construction by
the mount site and never mutated. This is the same value the mount
site passes to `ChartRegistry.register(id, controller)`, so registry
key and controller-internal id always agree.

```js
// chart-controller.js — constructor
this.id = id          // new field, never mutated
```

Mount-site change pattern (`super-chart.js`, `grid-bot-super-chart.js`,
`preview-super-chart.js`):

```js
const controller = new ChartController(superchart, datafeed, {
  id: chartId,        // new
  dispatch: store.dispatch,
  // ...
})
ChartRegistry.register(chartId, controller)
```

Why a public field, not a method/getter:

- `chartId` is a constructor invariant — never changes, never depends
  on derived state.
- Read sites (`replay-controller.js`, `replay-context.js`) want a
  stable string, not a function call.
- `marketTabSync._marketTabId` mutates on tab switch; that mutation
  must NOT migrate the controller's identity (replay's pinned
  `_sessionChartId` already exists for tab switches mid-session, and
  is unrelated).

For the TT main chart, `controller.id` is `marketTabId || "main"` at
construction. It does NOT update when the TT tab changes — the
controller is reused across tabs and Redux sessions are keyed by tab,
so the controller's identity stays as whatever tab id it was
constructed with. This matches the "TT main chart is reused across
tabs" model documented in R6.8 of the PRD. Today's
`marketTabSync.setMarketTabId(...)` flow already calls
`ChartRegistry.unregister(prevId); ChartRegistry.register(newId,
controller)` on tab switches (`super-chart.js:153-154`), so
`controller.id` must be re-assigned in lockstep with that re-register
so reads stay in sync with the registry key. Single line change.

### Replay's `_chartId` reads from `controller.id`

`ReplayController._chartId` getter
(`replay-controller.js:94-96`) currently reads
`this._chartController?.marketTabSync?._marketTabId || "main"`. This
falls back to `"main"` on charts without a `marketTabSync`
sub-controller (grid-bot, preview), causing collision with the TT
main chart's session key.

New getter:

```js
get _chartId() {
  return this._sessionChartId || this._chartController?.id || "main"
}
```

`_sessionChartId` (the pin) keeps its meaning: it freezes the chart
identity at session start so a TT tab switch mid-session doesn't
migrate the session. `controller.id` replaces the marketTabSync
read.

### `replay-context.js` reads from `useSuperChart().chartController.id`

Today (`replay-context.js:13`):

```js
const {id: marketTabId} = useContext(MarketTabContext)
const chartId = marketTabId || "main"
```

After:

```js
const {chartController} = useSuperChart()
const chartId = chartController?.id || "main"
```

`ReplayContext` is consumed only inside the SC widget subtree (where
`useSuperChart()` is available), so the change is local. The
`MarketTabContext` import goes away. This also de-couples the replay
chart-tree hook from TT, matching the Q3 page-agnostic intent.

### Inputs resolve `chartId` via `MarketTabContext` or `BotFormContext`

Both inputs already share the same `getActive()` shape
(`price-field.js:89`, `date-picker-input.js:29`). They become:

```js
const marketTabId = useContext(MarketTabContext)?.id
const botChartId = useContext(BotFormContext)?.chartId
const chartId = marketTabId || botChartId
const ctrl = chartId ? ChartRegistry.get(chartId) : null
if (!ctrl) return  // defensive null-guard, never a UI state (R4.4)
```

Both contexts have safe defaults (default `MarketTabContext` provides
no `id`; default `BotFormContext` will provide no `chartId`), so
reading without a provider doesn't throw. `useContext` is safe to call
unconditionally at the top of the hook, in any order.

The chart-pick button stays unconditionally rendered. The
`if (!ctrl) return` is the only branch — it covers transient races
during fast remounts (registry write order), nothing else.

### `BotFormContext` extension

`src/components/design-system/v2/trade/bots/context.js` default value
gains `chartId`:

```js
const BotFormContext = React.createContext({
  submitBotForm: (state) => () => null,
  chartId: null,
})
```

Each `<BotFormContext.Provider value={...}>` site adds `chartId` to
its `value` object. There are three providers:

- `grid-bot-settings.js` — settings page; the page generates one
  `grid-bot-<uuid>` and uses it for both its `GridBotSuperChartWidget`
  and its `BotFormContext.Provider`.
- `backtest-content.js` — backtest modal desktop; same pattern,
  separate UUID.
- `backtest-content-mobile-form.js` — backtest modal mobile; same.

`grid-bot-overview.js` doesn't use `BotFormContext` (the overview is
read-only and has no input forms), so it doesn't need to plumb
`chartId`.

The `chartId` is generated at the page/modal level rather than read
back from the rendered `GridBotSuperChartWidget`, because the chart
mount and the form siblings live in the same container — the page
owns both. `GridBotSuperChartWidget` keeps generating its own
internal UUID today; we move that generation up to the page so the
form can also see it.

### `takeScreenshot(chartId, callback)` with caller-provided id

```js
// screenshot.js
export const takeScreenshot = async (chartId, callback) => {
  const controller = chartId ? ChartRegistry.get(chartId) : null
  if (!controller?.header) {
    callback(false)
    return
  }
  await controller.header.captureScreenshotForNote(callback)
}
```

`notes-form.js:50` is the sole caller today and lives inside TT
widgets. It already has `MarketTabContext` available — adapter:

```js
// notes-form.js
const marketTabId = this.props.marketTabId  // wired via connect/HOC
takeScreenshot(marketTabId, (url) => { ... })
```

`notes-form` is a class component using the legacy connect pattern.
The `marketTabId` is available in the React tree via `MarketTabContext`
— wire it through with a thin functional wrapper or pass via
`mapStateToProps` from the active tab. Cleanest is a small wrapper
component that reads context and forwards as a prop. Decided in
implementation.

### `actions/replay.js` accepts `chartId`

`getSmartReplayController` has no callers in the repo — it is just
an exported helper. Convert to take `chartId`:

```js
export function getSmartReplayController(chartId) {
  return chartId ? ChartRegistry.get(chartId)?.replay?.smart || null : null
}
```

`replaySafeCallback` is called from three TT widget files
(`list-items.js`, `my-orders/order-row.js`, `my-orders/my-orders-header.js`).
All three are inside `MarketTabContext`. The thunk shape is awkward
because `replaySafeCallback(callback)` returns a thunk that does the
guard check at dispatch time. The `chartId` must be captured in the
closure at the call site — caller supplies it:

```js
// actions/replay.js
export const replaySafeCallback = (callback, chartId) => {
  return () => {
    const scReplay = chartId ? ChartRegistry.get(chartId)?.replay : null
    if (scReplay) return scReplay.replaySafeCallback(callback)
    return (...args) => callback(...args)
  }
}
```

Call sites add a `chartId` argument — read from `MarketTabContext`:

```js
const {id: marketTabId} = useContext(MarketTabContext)
// ...
onClick={dispatch(replaySafeCallback(handler, marketTabId))}
```

### `chart-registry.js` slimming

After the four callers above are converted, delete:

- `getActive()` method
- `setActive(id)` method
- `getAll()` method
- `let activeId = null` and the `activeId = id` line in `register`
- The whole `activeId` fallback block in `unregister`

Remaining surface: `register`, `unregister`, `get`, `subscribe`. The
listener signaling stays the same (`emit()` on register/unregister)
because `useActiveSmartReplay` and `super-chart/context.js` rely on
it.

## Data flow

### Settings preview unmount removal

```
Before:                            After:
TT widget renders                  TT widget renders
  └─ CandleChart                     └─ CandleChart
       reads previewShown                 unconditionally renders
       conditional render                 SuperChartWidgetWithProvider
       └─ SuperChartWidget         └─ SuperChartWidget
                                       (always mounted — coexists
                                        with PreviewSuperChartWidget
                                        when settings modal is open)
```

`GridItemSettingsContext` reverts to `{component, isOpen, onToggle}`.
`TradingviewSettings` no longer publishes `showPreview` — the
`useEffect` that called `setPreviewShown` is removed. The preview
gates only on local `showPreview`.

### Grid-bot kill-switch removal

```
Before:                            After:
GridBotSettings renders            GridBotSettings renders
  └─ SHOW_SETTINGS_CHART = true      └─ market &&
       && market &&                       <GridBotSuperChartWidget .../>
       <GridBotSuperChartWidget .../>
```

Constant + comment + `&&` guard removed. Behavior unchanged.

### Replay session keying

```
Before:
ReplayController._chartId
  → controller.marketTabSync?._marketTabId || "main"
  → grid-bot/preview fall back to "main" → collision with TT main

After:
ReplayController._chartId
  → controller.id || "main"
  → every chart has a stable, unique id
  → no collision possible
```

`replay-context.js` follows the same pattern via
`useSuperChart().chartController.id`.

### Inputs picker resolution

```
TT form (inside MarketTabContext):
  PriceField onClick → useContext(MarketTabContext)?.id
                     → ChartRegistry.get(marketTabId)
                     → ctrl.interaction.start(...)

Grid-bot form (inside BotFormContext):
  PriceField onClick → useContext(BotFormContext)?.chartId
                     → ChartRegistry.get(chartId)
                     → ctrl.interaction.start(...)
```

### Notes screenshot resolution

```
Before:
notes-form takeScreenshot button
  → takeScreenshot(callback)
  → ChartRegistry.getActive()  // last registered, ambiguous

After:
notes-form takeScreenshot button
  → takeScreenshot(marketTabId, callback)
  → ChartRegistry.get(marketTabId)  // exact chart
```

## File changes — summary table

| File | Change |
|---|---|
| `ai/deps/SUPERCHART_API.md` | Update hashes + add per-instance/shortName/onRightClick/pageX/touch right-click notes |
| `ai/deps/SUPERCHART_USAGE.md` | Update hashes; reference per-instance multi-chart pattern |
| `src/containers/trade/trading-terminal/grid-layout/grid-item-settings.js` | Strip `previewShown`/`setPreviewShown` from default + state + memo + close-clearing effect |
| `src/containers/trade/trading-terminal/widgets/center-view/tradingview/settings.js` | Drop `previewShown` context read + publish effect; gate preview on `showPreview` only; delete WORKAROUND comment |
| `src/containers/trade/trading-terminal/widgets/candle-chart.js` | Drop `GridItemSettingsContext` import + `previewActive` gate; delete TEMPORARY comment |
| `src/containers/bots/grid-bot/grid-bot-settings.js` | Delete `SHOW_SETTINGS_CHART` + comment + guard; lift chartId UUID to page; pass to `BotFormContext.Provider` value |
| `src/components/design-system/v2/trade/bots/context.js` | Add `chartId: null` to default `BotFormContext` value |
| `src/containers/bots/grid-bot/backtest/backtest-content.js` | Lift chartId UUID to page; pass to provider |
| `src/containers/bots/grid-bot/backtest/backtest-content-mobile-form.js` | Same |
| `src/containers/trade/trading-terminal/widgets/super-chart/grid-bot-super-chart.js` | Accept `chartId` prop instead of generating UUID internally |
| `src/containers/trade/trading-terminal/widgets/super-chart/preview-super-chart.js` | No change — preview's UUID is page-internal; not exposed to forms |
| `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js` | Add `id` field via constructor option `{id}` |
| `src/containers/trade/trading-terminal/widgets/super-chart/super-chart.js` | Pass `id: marketTabId \|\| "main"` to `ChartController`; update `controller.id` in lockstep with the registry re-register on tab switch |
| `src/containers/trade/trading-terminal/widgets/super-chart/grid-bot-super-chart.js` | Pass `id: chartId` to `ChartController` |
| `src/containers/trade/trading-terminal/widgets/super-chart/preview-super-chart.js` | Pass `id: chartId` to `ChartController` |
| `src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js` | Replace `_chartId` getter to read `_sessionChartId \|\| _chartController?.id \|\| "main"` |
| `src/containers/trade/trading-terminal/widgets/super-chart/replay/replay-context.js` | Drop `MarketTabContext` import; resolve `chartId` from `useSuperChart().chartController?.id` |
| `src/containers/trade/trading-terminal/widgets/super-chart/screenshot.js` | `takeScreenshot(chartId, callback)` |
| `src/containers/trade/trading-terminal/widgets/notes-form.js` | Pass `marketTabId` to `takeScreenshot` (wrapper or HOC reads `MarketTabContext`) |
| `src/components/design-system/v2/trade/inputs/price-field.js` | Read chartId from `MarketTabContext` or `BotFormContext`; resolve via `ChartRegistry.get` |
| `src/components/design-system/v2/trade/inputs/date-picker-input.js` | Same |
| `src/actions/replay.js` | `getSmartReplayController(chartId)`; `replaySafeCallback(callback, chartId)` |
| `src/components/design-system/v2/list-items.js` | Pass `marketTabId` from `MarketTabContext` to `replaySafeCallback` |
| `src/containers/trade/trading-terminal/widgets/my-orders/order-row.js` | Same |
| `src/containers/trade/trading-terminal/widgets/my-orders/my-orders-header.js` | Same |
| `src/models/chart-registry.js` | Delete `getActive`, `setActive`, `getAll`, `activeId` |

## Open items for implementation

- **`notes-form` `marketTabId` plumbing.** Class component with
  legacy connect; pick the smallest of: (a) thin functional wrapper
  that reads `MarketTabContext` and passes `marketTabId` as a prop,
  (b) `static contextType = MarketTabContext` if no other context is
  consumed, (c) HOC. Implementer chooses; whichever results in
  fewest lines.
- **`replaySafeCallback` argument order.** Adding `chartId` as a
  second positional arg (`replaySafeCallback(callback, chartId)`)
  matches the existing thunk shape but is easy to forget. Optional:
  swap to `replaySafeCallback({callback, chartId})` object form.
  Defer to implementer; prefer positional + lint via grep before
  shipping.
- **`grid-bot-super-chart.js` UUID lift.** The widget currently
  `useMemo(() => `grid-bot-${UUID()}`, [])` internally. After the
  lift, the page generates the UUID and passes it as a prop;
  the widget falls back to its own UUID only when no prop is
  passed (defensive — keeps `grid-bot-overview.js` working without
  changes since overview doesn't have a form).
