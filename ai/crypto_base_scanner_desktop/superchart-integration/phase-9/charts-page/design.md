# Design: /charts Page — SuperChart Integration

## Key Design Decisions

### 1. Fifth SC widget variant — `ChartsPageChartWidget`

Mirrors `TradingTerminalChart` more closely than CS does, because /charts
*does* run a real `MarketTabContext` per cell (provided by
`MarketTabContextProvider`, keyed by the flex-layout node id == chart-tab
id). The widget is essentially TT minus a few features:

| Aspect | TT | /charts |
|---|---|---|
| Tabs controller | `TradingTabsController` | `ChartTabsController` |
| `mainChart` | `true` | `false` |
| `showReplay` | `true` | `true` |
| `showSettings` | `true` | `true` |
| `showTradingOptions` (ctx menu) | `true` | `false` |
| Edit-overlays (`EditOrders`/`EntryConditions`/`EntryExpirations`) | mounted | not mounted |
| `<TradingHotkeys/>` | mounted | not mounted |
| `<ReplayHotkeys/>` | per cell | **page-level**, accepts `chartId` prop |
| Mobile `<ActionButtons/>` + `<PickReplayStartButton/>` | mounted | not mounted |
| Fullscreen-on-landscape mobile | yes | no |
| Visible-range persist target | `TradingTabsController` | `ChartTabsController` |

Registry key: each cell uses `marketTabId` directly (= `node.getId()`,
which equals the chart-tab id). No `"main"` fallback applies on /charts;
flex-layout enforces id uniqueness.

### 2. `MarketTabSyncController` reuse

The controller already accepts a `tabsController` injection
(`market-tab-sync-controller.js:41`). TT passes `TradingTabsController`;
CS doesn't attach this controller; /charts passes `ChartTabsController`.
The chart-driven symbol/period sync, the visible-range echo guard, and
`syncSymbolToChart` / `syncResolutionToChart` work unchanged for both
tab types.

The implication: chart UI changes (period bar symbol search, period
picker) round-trip back into the active `ChartTab` via
`ChartTabsController.get().getTabById(marketTabId).setCoinraySymbol(...)` /
`setResolution(...)`. Same logic powers TT.

### 3. Header buttons — flag split

`controllers/header-buttons-controller.js` after the CS PRD has:

```js
if (mainChart) { Buy; Sell; Replay; Settings }
```

This collapses three audiences (TT / CS / /charts) into a binary that
can't express /charts. Replace with three independent flags:

```diff
-createHeaderButtons({mainChart, onAlert, onBuy, onSell, onReplay, onSettings, onToggleChart}) {
+createHeaderButtons({mainChart, showReplay, showSettings, onAlert, onBuy, onSell, onReplay, onSettings, onToggleChart}) {
   ...
   if (mainChart) {
     this._buyButton = ...
     this._sellButton = ...
-    this._replayButton = ...
-    this._settingsButton = ...
   }
+  if (showReplay) {
+    this._replayButton = this._createToolbarButton({
+      icon: "backward", text: t("replay"), tooltip: t("pickReplayStart"),
+      onClick: onReplay,
+    })
+  }
+  if (showSettings) {
+    this._settingsButton = this._createToolbarButton({
+      icon: "gear", text: t("settings"), tooltip: t("chartSettings"),
+      borderColor: "rgba(20,26,33,0.4)", onClick: onSettings,
+    })
+  }
```

Caller matrix:

| Caller | `mainChart` | `showReplay` | `showSettings` | Result |
|---|---|---|---|---|
| TT (`trading-terminal-chart.js`) | `true` | `true` | `true` | Alert + Buy + Sell + Replay + Settings |
| CS (`customer-service-chart.js`) | `false` | (omitted → `false`) | (omitted) | Alert only |
| /charts (`charts-page-chart.js`) | `false` | `true` | `true` | Alert + Replay + Settings |
| Grid-bot (`grid-bot-chart.js`) | n/a | n/a | n/a | `<HeaderButtons gridBotChart/>` skips `createHeaderButtons` entirely |

`HeaderButtons` (`super-chart/header-buttons.js`) receives the new
props and forwards them to `createHeaderButtons`. The existing
`onReplay` / `onSettings` handlers remain wired unconditionally — only
the controller-side guards change.

`setHeaderButtonsEnabled` and `setReplayButtonHighlight` already
null-check their refs (`if (!btn) continue`, `if (!this._replayButton)
return`) so they remain safe with any subset of buttons.

### 4. Last-interacted chart tracking — React context, not Redux

The state has zero cross-page reach: producers and consumers all live
inside the /charts subtree. A small React context wrapping the page is
the right shape — no Redux slice, no controller field, no
`useReducer`.

```js
// containers/charts/last-interacted-chart-context.js (new)
const LastInteractedChartContext = createContext({
  lastInteractedChartTabId: null,
  setLastInteractedChartTabId: () => {},  // no-op default
})

export const LastInteractedChartProvider = ({children}) => {
  const [lastInteractedChartTabId, setLastInteractedChartTabId] = useState(null)
  const value = useMemo(
    () => ({lastInteractedChartTabId, setLastInteractedChartTabId}),
    [lastInteractedChartTabId],
  )
  return <LastInteractedChartContext.Provider value={value}>
    {children}
  </LastInteractedChartContext.Provider>
}

export const useLastInteractedChart = () => useContext(LastInteractedChartContext)
```

The default `setLastInteractedChartTabId: () => {}` is the key to keeping
producers (chart-widget pointerdown listeners, Replay-button onClick)
free of conditional wiring — they call it unconditionally; outside the
provider it's inert. This means:

- `ChartsPageChartWidget` always calls
  `setLastInteractedChartTabId(thisTabId)` on `pointerdown` — works on
  /charts (real setter), no-op on TT (TT doesn't mount this widget
  anyway, but the principle holds for any future host).
- `HeaderButtons` always calls `setLastInteractedChartTabId(chartController.id)`
  inside its `onReplay` closure — works on /charts, no-op on TT/CS.

#### Producers

1. **Chart-canvas pointerdown** — `ChartsPageChartWidget`'s container
   `<div ref={containerRef}>` gets an `onPointerDown` handler that
   calls the setter with this cell's `marketTabId`. Pointer events
   capture mouse, touch, and pen — broader than `onClick`, and fires
   on the down stroke (matching "intent to interact").

2. **Replay header button click** — `HeaderButtons.useEffect` already
   builds the `onReplay` closure for `createHeaderButtons`. Add
   `setLastInteractedChartTabId(chartController.id)` as the first line
   of that closure (before the existing
   `chartController?.replay?.handleSelectReplayStartTimeClick(...)`).
   Reads the setter from `useLastInteractedChart()`. No-op outside the
   provider.

   Why bump here too: when the user clicks Replay on chart A without
   first having clicked the canvas, the picker arms on A, but
   `lastInteractedChartTabId` would still point at the last
   pointerdown chart (could be B or null). Bumping at button click
   keeps "intent" aligned with the picker target.

3. **(Not bumped: Alert and Settings buttons)** — Alert opens a form;
   Settings opens a page-level modal. Neither is tied to a
   chart-specific hotkey. Keep the bump set minimal.

#### Consumer

`<ReplayHotkeys/>` mounted **once** at the page level inside
`containers/charts.js`:

```jsx
const ReplayHotkeysFromContext = () => {
  const {lastInteractedChartTabId} = useLastInteractedChart()
  return <ReplayHotkeys chartId={lastInteractedChartTabId}/>
}
// ...
<LastInteractedChartProvider>
  ...page tree...
  <ReplayHotkeysFromContext/>
  <ChartsHotkeys/>
</LastInteractedChartProvider>
```

A small wrapper component is needed because `useLastInteractedChart`
must be called inside the provider, and `<ReplayHotkeys/>`'s
`chartId` prop wants the live value.

### 5. `ReplayHotkeys` — optional `chartId` prop

`super-chart/replay/replay-hotkeys.js` today reads everything from
context:

```js
const {chartController} = useSuperChart()
const {currentMarket} = useContext(MarketTabContext)
const chartId = chartController?.id || "main"
const replayMode = useSelector(selectReplayMode(chartId))
const replay = chartController?.replay
```

It's mounted inside the per-chart `SuperChartContextProvider` +
`MarketTabContext`, so all those reads are scoped to the right chart.

For the page-level mount on /charts, none of those contexts are
accessible — the hotkeys component sits **outside** any chart's
provider. So we add an optional `chartId` prop that switches the
resolution path:

```js
const ReplayHotkeys = ({chartId: chartIdProp}) => {
  // Two paths:
  // - Per-chart mount (TT): read everything from contexts. chartIdProp is undefined.
  // - Page-level mount (/charts): chartIdProp is the last-interacted tab id.
  //   Resolve controller via ChartRegistry; resolve currentMarket from controller.
  const ctx = useContext(SuperChartContext)            // null on page-level mount
  const tabContext = useContext(MarketTabContext)      // null on page-level mount
  const usingProp = chartIdProp !== undefined

  const chartController = usingProp
    ? ChartRegistry.get(chartIdProp)
    : ctx?.chartController
  const chartId = usingProp
    ? chartIdProp
    : (chartController?.id || "main")
  const currentMarket = usingProp
    ? chartController?._currentMarket
    : tabContext?.currentMarket
  // ...
  // Bind nothing if chartIdProp is set but ChartRegistry has no controller yet
  // (fresh /charts load before any chart canvas was clicked).
  if (usingProp && !chartController) return null
  // ...rest unchanged
}
```

Notes:

- `useContext(SuperChartContext)` returns `null` outside any provider —
  but `useSuperChart()` throws (`if (!ctx) throw new Error(...)`). So
  the page-level mount cannot call `useSuperChart()`. Switching to a
  raw `useContext(SuperChartContext)` keeps the no-throw fallback
  available for the page-level path.
- `chartController._currentMarket` is set by the
  `setCurrentMarket(currentMarket)` effect in the chart widget — which
  runs unconditionally (TT, CS, /charts all do this). So reading
  `currentMarket` from the controller is the right page-level fallback.
- `replayMode` selector keys by `chartId` — works for both paths.
- `chartSettings` and `tradingHotkeysMap` selectors are global Redux —
  no path change.
- `dispatch` from `useDispatch` — unchanged.

The TT mount stays `<ReplayHotkeys/>` (no prop) — exact same behaviour.
CS doesn't mount this component at all.

### 6. Sub-controller attach

Same set as TT — the widget is mostly TT minus `mainChart`-specific
chrome:

```js
controller.marketTabSync = new MarketTabSyncController(controller, {
  marketTabId,
  tabsController: ChartTabsController,
})
controller.headerButtons = new HeaderButtonsController(controller)
controller.contextMenu = new ContextMenuController(controller, {showTradingOptions: false})
controller.contextMenu.mount(superchart)
controller.positions = new PositionsController(controller)
controller.tradeForm = new TradeFormController(controller)
controller.replay = new ReplayController(controller)

const unsubReplayInit = superchart.onReady(() => controller.replay?.init())
return () => unsubReplayInit?.()
```

Why every controller is needed:

| Controller | Why on /charts |
|---|---|
| `MarketTabSyncController` | Round-trips chart-driven symbol/period changes back to the chart-tab. Visible-range restore on tab/symbol switch. |
| `HeaderButtonsController` | Alert + Replay + Settings buttons. |
| `ContextMenuController` | Alert + replay items in the chart-bg right-click menu. `showTradingOptions: false` hides Buy/Sell. |
| `PositionsController` | Required by `Orders`, `BreakEven`, `PnlHandle` overlays. |
| `TradeFormController` | `PositionsController`'s entry-condition / entry-expiration helpers reference `this.c.tradeForm?._tradeForm?.*` on optional chains. Edit-overlays aren't mounted, so the chains short-circuit, but TT mounts it for parity and to keep the dispose path identical. |
| `ReplayController` | Per-chart replay engine. Init via `onReady`, same as TT. |

`storeGlobal({chartController, ChartRegistry})` — TT mounts it for the
window-level dev affordance. /charts can mount it too; with N charts,
last-writer-wins on the global is harmless (multi-chart-unblock R6.7).

### 7. Overlay set

Children of `<SuperChartContextProvider>` for /charts:

```
Always mounted:
  Trades, Bases, BreakEven, PnlHandle,
  Screenshot, ChartContextMenu

Live-only (!replayMode):
  TaScannerAlerts

Hidden during DEFAULT replay (mounted in live and SMART):
  BidAsk
  PriceAlerts, EditPriceAlert, TriggeredPriceAlerts
  TimeAlerts,  EditTimeAlert,  TriggeredTimeAlerts
  TrendlineAlerts, EditTrendlineAlert, TriggeredTrendlineAlerts
  Orders
  OverlayContextMenu

Replay-only:
  ReplayTimelines
```

Same gating expressions as TT (`replayMode !== REPLAY_MODE.DEFAULT`,
`!replayMode`, `replayMode`). The `replayMode` is read via
`useSelector(selectReplayMode(marketTabId))` against the cell's tab id.

**Skipped vs TT:** `EditOrders`, `EditEntryConditions`,
`EditEntryExpirations`, `TradingHotkeys`, `ActionButtons`,
`PickReplayStartButton`. Plus the fullscreen-on-landscape mobile
treatment.

### 8. Replay UI — controls + timelines

`<ReplayContextProvider>` wraps each cell's subtree (`SuperChartContextProvider`
ancestor satisfied by `<SuperChartContextProvider chartId={marketTabId}/>`
in the widget root). It's a per-chart concept and the existing
implementation is multi-instance-safe (already verified by
multi-chart-unblock).

`<ReplayControls>` renders inside the cell when `replayMode` is
truthy. It reads `MarketTabContext.currentMarket` (per-cell) and
`WidgetContext.containerWidth` (provided by `withSizeProps` in
`charts-grid-item.js`) — both already available. Mobile-only mounts
(`PickReplayStartButton`, `ActionButtons`) are skipped.

### 9. Visible-range persist

```js
const persistTimeoutRef = useRef()
useEffect(() => {
  const {from, to, barSpace} = visibleRange
  if (!from || !to || !miscRememberVisibleRange) return
  clearTimeout(persistTimeoutRef.current)
  persistTimeoutRef.current = setTimeout(() => {
    ChartTabsController.get()
      .getTabById(marketTabId)
      .setVisibleRangeFromTo({from, to, barSpace})
      .catch(console.error)
  }, 500)
}, [visibleRange, miscRememberVisibleRange, marketTabId])
```

Same shape as TT, target swapped to `ChartTabsController`. `MarketTab`
already exposes `setVisibleRangeFromTo` (`market-tab.js:155`), inherited
by `ChartTab`.

Restoration on tab/symbol switch is handled by
`MarketTabSyncController.restoreVisibleRange` (already wired in the
base controller). No new code.

### 10. Lifecycle & registry

`useChartLifecycle` handles registry register/unregister and
controller dispose. The /charts widget is no different from TT or CS
in this regard. Closing a chart tab → `ChartTabsController.removeMarketTab` →
flex-layout deletes the node → `ChartsGridItem` unmounts →
`useChartLifecycle` cleanup runs → SC chart disposed, registry
unregisters.

The `marketTabId` mutation effect TT uses (rebinds the registry under
a new id when `MarketTabContext.id` changes) does **not** apply on
/charts: each chart cell owns a stable `marketTabId === node.getId()`
for its lifetime. If the user switches markets within a tab, the same
cell stays mounted; only `coinraySymbol` and `resolution` change.

### 11. Wire-up

`containers/charts.js`:

```jsx
<GridItemSettingsProvider>
  <LastInteractedChartProvider>
    <MarketHeaderBar global withLayoutControls withChartSettings/>
    <MarketSelectPopup .../>
    {chartsCustomLayoutsLoading
      ? <ActivityIndicatorCentered .../>
      : <div tw="...">
          <ScrollView>
            <CurrencyContextProvider>
              <FlexGrid gridComponent={ChartGridItem} layout={chartsCurrentLayout}/>
            </CurrencyContextProvider>
          </ScrollView>
        </div>}
    <ReplayHotkeysFromContext/>
    <ChartsHotkeys/>
  </LastInteractedChartProvider>
</GridItemSettingsProvider>
```

`grid-layout/flex-grid/charts-grid-item.js`:

```diff
-import CandleChart from "../../widgets/candle-chart"
+import ChartsPageChartWidget from "../../widgets/super-chart/charts/charts-page-chart"
 ...
-  const handleTVSymbolChanged = useCallback(...)
-  const handleTVIntervalChanged = useCallback(...)
-  const handleTVVisibleRangeChanged = useCallback(...)
 ...
-  <CandleChart toggleable={false}
-               handleTVSymbolChanged={handleTVSymbolChanged}
-               handleTVIntervalChanged={handleTVIntervalChanged}
-               handleTVVisibleRangeChanged={handleTVVisibleRangeChanged}/>
+  <ChartsPageChartWidget/>
```

`widgets/candle-chart.js`:

```diff
-import {DefaultTradingWidget} from "./center-view/tradingview"
 import TradingTerminalChartWithProvider from "./super-chart/charts/trading-terminal-chart"

-const CandleChart = ({toggleable = true, ...tvProps}) => {
-  return <div tw="flex flex-col flex-1 h-full">
-    {toggleable
-      ? <TradingTerminalChartWithProvider key="sc"/>
-      : <DefaultTradingWidget {...tvProps}/>}
-  </div>
-}
+const CandleChart = () => {
+  return <div tw="flex flex-col flex-1 h-full">
+    <TradingTerminalChartWithProvider key="sc"/>
+  </div>
+}
```

## Data Flow

```
containers/charts.js
  └── <LastInteractedChartProvider>
       ├── lastInteractedChartTabId (useState)
       │
       ├── <FlexGrid gridComponent={ChartGridItem}/>
       │    └── for each chart-tab node:
       │         <ChartsGridItem node={node}>
       │           └── <MarketTabContextProvider marketTabId={node.getId()}>
       │                └── <MarketTabContext.Provider> + <MarketTabDataContext.Provider> + <CurrentPositionContextProvider>
       │                     └── <ChartsGridContent>
       │                          └── <ChartsPageChartWidget>
       │                               ├── containerRef onPointerDown → setLastInteractedChartTabId(marketTabId)
       │                               ├── <SuperChartContextProvider chartId={marketTabId}>
       │                               │    └── <ReplayContextProvider>
       │                               │         ├── <ChartsPageChart/>  (chart container + lifecycle)
       │                               │         ├── <SuperChartControls/>  (ReplayControls during replay)
       │                               │         ├── <HeaderButtons mainChart={false} showReplay showSettings/>
       │                               │         │   └── onReplay closure: setLastInteractedChartTabId(chartController.id) → handleSelectReplayStartTimeClick
       │                               │         └── <SuperChartOverlays/>  (overlay set per §7)
       │
       ├── <ReplayHotkeysFromContext/>
       │    └── <ReplayHotkeys chartId={lastInteractedChartTabId}/>
       │         └── ChartRegistry.get(chartId) → controller.replay
       │
       └── <ChartsHotkeys/>
            └── operates on ChartTabsController (uses `selected` field)
```

## File Changes

### New files

| File | Purpose |
|---|---|
| `super-chart/charts/charts-page-chart.js` | `ChartsPageChartWidget` (default export) + inner `ChartsPageChart` |
| `containers/charts/last-interacted-chart-context.js` | `LastInteractedChartProvider`, `useLastInteractedChart` |

(The new context file lives in a new `containers/charts/` subfolder so
the page can be split into multiple files cleanly. Alternative — colocate
in `containers/charts.js`'s file. Keeping it separate simplifies imports
from `header-buttons.js` and the chart widget.)

### Modified files

| File | Changes |
|---|---|
| `super-chart/controllers/header-buttons-controller.js` | Add `showReplay` / `showSettings` flags; gate the matching buttons on them |
| `super-chart/header-buttons.js` | Accept `showReplay` / `showSettings` props; in `onReplay` closure, call `setLastInteractedChartTabId(chartController.id)` from `useLastInteractedChart()` (no-op default outside the provider) |
| `super-chart/charts/trading-terminal-chart.js` | Pass `showReplay showSettings` to `<HeaderButtons mainChart .../>` to retain the all-five-buttons behaviour |
| `super-chart/replay/replay-hotkeys.js` | Add optional `chartId` prop; resolve controller via `ChartRegistry` when provided |
| `containers/charts.js` | Wrap in `<LastInteractedChartProvider>`; mount page-level `<ReplayHotkeys chartId={...}/>` (via wrapper) |
| `containers/trade/trading-terminal/grid-layout/flex-grid/charts-grid-item.js` | Mount `<ChartsPageChartWidget/>` instead of `<CandleChart toggleable={false}/>`; drop the three TV callbacks |
| `containers/trade/trading-terminal/widgets/candle-chart.js` | Drop `toggleable` prop, drop TV branch, drop TV import; always render SC |

## Invariants / Constraints

- `<ReplayHotkeys/>` is mounted **exactly once** on /charts (page level).
  Per-cell mounts are forbidden — Mousetrap collision.
- `lastInteractedChartTabId` is `null` until the user interacts with a
  chart canvas or clicks a Replay header button. Until then, replay
  hotkeys are no-ops on /charts.
- `setLastInteractedChartTabId` outside the provider is a no-op. So
  `HeaderButtons.onReplay` and `ChartsPageChartWidget.onPointerDown`
  may call it unconditionally — the `LastInteractedChartProvider` is
  the one place that activates the bump.
- The `ChartTab.selected` field continues to drive **page-level
  commands** (`closeSelectedChart`, `changeSelectedChartMarket`,
  `toggleWatchlist`) via `MarketTabsSelectors.selectSelectedChartTab`.
  It is **not** used for chart-specific actions (replay hotkey
  routing); those use `lastInteractedChartTabId`.
- `<HeaderButtons mainChart={false} showReplay showSettings/>` after
  the controller flag-split produces exactly Alert + Replay + Settings.
- `EditOrders`, `EditEntryConditions`, `EditEntryExpirations` are not
  mounted. Order-line drag and order edit are structurally
  impossible on /charts (matches TV behaviour).
- `TradingHotkeys` is not mounted. Buy/Sell/closed-orders-show hotkeys
  do not bind on /charts.
- The mobile fullscreen-on-landscape treatment in
  `trading-terminal-chart.js` is not ported. /charts inherits the
  page's own layout.
- Visible-range persist target is `ChartTabsController` (via
  `setVisibleRangeFromTo`), not `TradingTabsController`.
- `marketTabSync` is the only sub-controller whose constructor
  signature differs between TT and /charts (the `tabsController`
  injection); all others are constructed identically.

## Open Questions

- **Bump on Alert / Settings buttons too?** Currently no — minimal set
  of bump points, only Replay button + canvas pointerdown. Revisit if
  users get confused by replay hotkeys not following an Alert-button
  click. Likely not an issue: clicking Alert opens a form (focus
  shifts away from chart), and the user's next chart interaction is
  almost always a canvas click.
- **`useContext(SuperChartContext)` vs `useSuperChart()`** in
  `replay-hotkeys.js`. The hook throws when ctx is null; the raw
  `useContext` returns null. Switching to raw `useContext` is the
  least invasive way to support the page-level mount. If we want to
  keep the hook-throws-on-misuse invariant for the per-chart path,
  branch the read on `chartIdProp !== undefined` before any context
  read.
- **TT regression — passing `showReplay showSettings`**: a strict
  reading of the flag-split would require TT to opt in. The
  alternative is a back-compat default
  `showReplay = mainChart, showSettings = mainChart` in
  `createHeaderButtons`. Defaulting from `mainChart` keeps TT and CS
  call sites untouched. /charts would still pass explicit
  `showReplay showSettings` since `mainChart=false`. **Recommended:
  default the new flags from `mainChart`** — cuts the TT/CS diff to
  zero and keeps the surface intentional.
