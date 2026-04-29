# Tasks: /charts Page — SuperChart Integration

## Step 1: Header-buttons controller — flag split

### Task 1.1: Add `showReplay` / `showSettings` flags

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/controllers/header-buttons-controller.js`

Split the Replay and Settings button creation out of the existing
`if (mainChart)` block. Default the new flags from `mainChart` so TT
and CS call sites are untouched.

```diff
-  createHeaderButtons({mainChart, onAlert, onBuy, onSell, onReplay, onSettings, onToggleChart}) {
+  createHeaderButtons({mainChart, showReplay = mainChart, showSettings = mainChart, onAlert, onBuy, onSell, onReplay, onSettings, onToggleChart}) {
     const H = "containers.trade.market.marketGrid.centerView.tradingView.header"
     const t = (key) => i18n.t(`${H}.${key}`)

     this._alertButton = this._createToolbarButton({
       icon: "bell", text: t("alert"), tooltip: t("setPriceAlert"),
       borderColor: "#007FFF", onClick: onAlert,
     })

     if (mainChart) {
       this._buyButton = this._createToolbarButton({
         icon: "arrow-up", text: t("buy"), tooltip: t("buy"),
         borderColor: "#06BF7B", onClick: onBuy,
       })
       this._sellButton = this._createToolbarButton({
         icon: "arrow-down", text: t("sell"), tooltip: t("sell"),
         borderColor: "#F04747", onClick: onSell,
       })
-      this._replayButton = this._createToolbarButton({
-        icon: "backward", text: t("replay"), tooltip: t("pickReplayStart"),
-        onClick: onReplay,
-      })
-      this._settingsButton = this._createToolbarButton({
-        icon: "gear", text: t("settings"), tooltip: t("chartSettings"),
-        borderColor: "rgba(20,26,33,0.4)", onClick: onSettings,
-      })
     }
+
+    if (showReplay) {
+      this._replayButton = this._createToolbarButton({
+        icon: "backward", text: t("replay"), tooltip: t("pickReplayStart"),
+        onClick: onReplay,
+      })
+    }
+
+    if (showSettings) {
+      this._settingsButton = this._createToolbarButton({
+        icon: "gear", text: t("settings"), tooltip: t("chartSettings"),
+        borderColor: "rgba(20,26,33,0.4)", onClick: onSettings,
+      })
+    }
```

`_toolbarButtons` filtering, `setHeaderButtonsEnabled`,
`setReplayButtonHighlight`, `dispose()` already handle null button
refs — no other changes needed.

### Task 1.2: Forward flags through `<HeaderButtons/>`

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/header-buttons.js`

```diff
-const HeaderButtons = ({mainChart, gridBotChart}) => {
+const HeaderButtons = ({mainChart, gridBotChart, showReplay, showSettings}) => {
   ...
       chartController.headerButtons?.createHeaderButtons({
         mainChart,
+        showReplay,
+        showSettings,
         onAlert: ...,
         onBuy: ...,
         onSell: ...,
         onReplay: ...,
         onSettings: ...,
       })
```

Both new props are `undefined` → fall through to `mainChart` defaults
in `createHeaderButtons`.

**Verify (Step 1):**

1. Open the Trading Terminal — header still shows Alert + Buy + Sell +
   Replay + Settings (5 buttons). No change vs before.
2. Open a Customer Service market or position page — header still
   shows Alert only. No change.
3. Open a grid-bot page — chart still shows whatever buttons it had
   before (no header buttons via `createHeaderButtons` because of
   `if (!gridBotChart)` early-exit in `header-buttons.js`).
4. No console errors anywhere.

---

## Step 2: `LastInteractedChartContext` + `ReplayHotkeys` `chartId` prop

### Task 2.1: Create the context module

**File:** `src/containers/charts/last-interacted-chart-context.js` (new)

```js
import React, {createContext, useContext, useMemo, useState} from "react"

const NOOP = () => {}

const LastInteractedChartContext = createContext({
  lastInteractedChartTabId: null,
  setLastInteractedChartTabId: NOOP,
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

The default `setLastInteractedChartTabId: NOOP` lets producers (chart
widget, header buttons) call the setter unconditionally — outside the
provider it's an inert no-op.

### Task 2.2: Add optional `chartId` prop to `<ReplayHotkeys/>`

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/replay/replay-hotkeys.js`

Switch from `useSuperChart()` (which throws when no provider) to a raw
`useContext(SuperChartContext)` so the page-level mount works without
a `SuperChartContextProvider` ancestor. When `chartId` is passed,
resolve the controller via `ChartRegistry`; when absent, behave as
today.

```diff
-import {useSuperChart} from "../context"
+import {SuperChartContext} from "../context"
+import ChartRegistry from "~/models/chart-registry"
 ...
-const ReplayHotkeys = () => {
-  const {chartController} = useSuperChart()
-  const {currentMarket} = useContext(MarketTabContext)
-  const chartId = chartController?.id || "main"
+const ReplayHotkeys = ({chartId: chartIdProp}) => {
+  const usingProp = chartIdProp !== undefined
+  const ctx = useContext(SuperChartContext)
+  const tabContext = useContext(MarketTabContext)
+  const chartController = usingProp
+    ? ChartRegistry.get(chartIdProp)
+    : ctx?.chartController
+  const chartId = usingProp ? chartIdProp : (chartController?.id || "main")
+  const currentMarket = usingProp
+    ? chartController?._currentMarket
+    : tabContext?.currentMarket
   const replayMode = useSelector(selectReplayMode(chartId))
   ...
   const replay = chartController?.replay
   ...
+  // Page-level mount with no chart yet interacted → no controller to bind to.
+  if (usingProp && !chartController) return null
   ...
```

`SuperChartContext` is currently a non-exported `createContext(null)`
in `super-chart/context.js`. Export it for this consumer:

```diff
 // super-chart/context.js
-const SuperChartContext = createContext(null)
+export const SuperChartContext = createContext(null)
```

(`useSuperChart()` continues to be the recommended hook for per-chart
consumers — only `ReplayHotkeys` needs the raw context for its
optional-prop branch.)

**Verify (Step 2):**

1. Open the Trading Terminal — replay hotkeys (play/pause / step /
   step-back / stop) work as before during a default replay session.
   `<ReplayHotkeys/>` (no prop) still resolves the controller via
   `useSuperChart()`-equivalent path.
2. No console errors.

---

## Step 3: `ChartsPageChartWidget` skeleton + grid-item swap

### Task 3.1: Create the widget

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/charts/charts-page-chart.js` (new)

Pattern mirrors `trading-terminal-chart.js` with /charts adaptations.
Skip `<ReplayHotkeys/>` mount (it'll be page-level — Step 4); skip
`<TradingHotkeys/>`, mobile `<ActionButtons/>` /
`<PickReplayStartButton/>`, fullscreen-on-landscape; pass
`tabsController: ChartTabsController` to `MarketTabSyncController`;
pass `showTradingOptions: false` to `ContextMenuController`; render
`<HeaderButtons mainChart={false} showReplay showSettings/>`.

```js
import React, {useContext, useEffect, useRef} from "react"
import {useSelector} from "react-redux"
import "twin.macro"

import {MarketTabContext} from "~/containers/market-tabs/context"
import WidgetContext from "../../../grid-layout/widget-context"
import CoinrayDatafeed from "../datafeeds/coinray-datafeed"
import {toPeriod, toSymbolInfo} from "../chart-helpers"
import {ChartTabsController} from "~/models/market-tabs/chart-tabs-controller"
import {HeaderButtonsController} from "../controllers/header-buttons-controller"
import {MarketTabSyncController} from "../controllers/market-tab-sync-controller"
import {ReplayController} from "../controllers/replay-controller"
import {ContextMenuController} from "../controllers/context-menu-controller"
import {PositionsController} from "../controllers/positions-controller"
import {TradeFormController} from "../controllers/trade-form-controller"
import {SuperChartContextProvider, useVisibleRange} from "../context"
import {useChartLifecycle} from "./super-chart"
import BidAsk from "../overlays/bid-ask"
import BreakEven from "../overlays/break-even"
import Trades from "../overlays/trades"
import PnlHandle from "../overlays/pnl-handle"
import Bases from "../overlays/bases"
import PriceAlerts from "../overlays/alerts/price-alerts/price-alerts"
import EditPriceAlert from "../overlays/alerts/price-alerts/edit-price-alert"
import TriggeredPriceAlerts from "../overlays/alerts/price-alerts/triggered-price-alerts"
import TimeAlerts from "../overlays/alerts/time-alerts/time-alerts"
import EditTimeAlert from "../overlays/alerts/time-alerts/edit-time-alert"
import TriggeredTimeAlerts from "../overlays/alerts/time-alerts/triggered-time-alerts"
import TrendlineAlerts from "../overlays/alerts/trendline-alerts/trendline-alerts"
import EditTrendlineAlert from "../overlays/alerts/trendline-alerts/edit-trendline-alert"
import TriggeredTrendlineAlerts from "../overlays/alerts/trendline-alerts/triggered-trendline-alerts"
import TaScannerAlerts from "../overlays/alerts/ta-scanner-alerts/ta-scanner-alerts"
import Orders from "../overlays/orders/orders"
import storeGlobal from "~/util/store-global"
import Screenshot from "../screenshot"
import ChartRegistry from "~/models/chart-registry"
import HeaderButtons from "../header-buttons"
import OverlayContextMenu from "../overlays/overlay-context-menu"
import ChartContextMenu from "../chart-context-menu"
import ReplayTimelines from "../overlays/replay-timelines"
import {ReplayContextProvider} from "../replay/replay-context"
import {ReplayControls} from "../replay/replay-controls"
import {selectReplayMode} from "~/models/replay/selectors"
import {REPLAY_MODE} from "~/models/replay/constants"
import ErrorBoundary from "~/components/error-boundary"
import {TradeFormContextProvider} from "~/components/design-system/v2/trade/context"
import {useLastInteractedChart} from "~/containers/charts/last-interacted-chart-context"
import {css} from "twin.macro"

const ChartsPageChart = () => {
  const {id: marketTabId, currentMarket, resolution} = useContext(MarketTabContext)
  const miscRememberVisibleRange = useSelector(state => state.chartSettings.miscRememberVisibleRange)
  const visibleRange = useVisibleRange()
  const {containerWidth, containerHeight} = useContext(WidgetContext)
  const replayMode = useSelector(selectReplayMode(marketTabId))
  const persistTimeoutRef = useRef()
  const {setLastInteractedChartTabId} = useLastInteractedChart()

  const coinraySymbol = currentMarket?.coinraySymbol

  const {containerRef, controllerRef} = useChartLifecycle({
    chartId: marketTabId,
    buildDatafeed: () => new CoinrayDatafeed(),
    superchartOptions: {
      symbol: toSymbolInfo(coinraySymbol),
      period: toPeriod(resolution || "60"),
    },
    setup: ({superchart, controller}) => {
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
      storeGlobal({chartController: controller, ChartRegistry})

      const unsubReplayInit = superchart.onReady(() => controller.replay?.init())
      return () => {
        clearTimeout(persistTimeoutRef.current)
        unsubReplayInit?.()
      }
    },
    useResizeObserver: false,
  })

  // Push currentMarket so PositionsController et al. resolve labels.
  useEffect(() => {
    controllerRef.current?.setCurrentMarket(currentMarket)
  }, [currentMarket])

  // Sync symbol changes (skip initial mount).
  const mountedRef = useRef(false)
  useEffect(() => {
    if (!mountedRef.current) return
    controllerRef.current?.marketTabSync?.syncSymbolToChart(coinraySymbol, resolution)
  }, [coinraySymbol])

  // Sync resolution changes (skip initial mount).
  useEffect(() => {
    if (!mountedRef.current) return
    controllerRef.current?.marketTabSync?.syncResolutionToChart(resolution)
  }, [resolution])

  useEffect(() => {
    mountedRef.current = true
  }, [])

  // Resize driven by WidgetContext + replayMode.
  useEffect(() => {
    controllerRef.current?.resize()
  }, [containerWidth, containerHeight, replayMode])

  // Visible-range persist (per ChartTab).
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

  const handlePointerDown = () => {
    setLastInteractedChartTabId(marketTabId)
  }

  return <div ref={containerRef}
              tw="flex-1 min-h-0"
              onPointerDown={handlePointerDown}/>
}

const SuperChartControls = () => {
  const {id: marketTabId} = useContext(MarketTabContext)
  const replayMode = useSelector(selectReplayMode(marketTabId))

  if (!replayMode) return null

  return <TradeFormContextProvider>
    <div tw="flex flex-row space-x-2 p-2 overflow-auto"
         css={css`box-shadow: inset 0 1px 0 0 var(--border-primary);`}
         className="no-scrollbar">
      <ErrorBoundary>
        <ReplayControls/>
      </ErrorBoundary>
    </div>
  </TradeFormContextProvider>
}

const ChartsPageOverlays = () => {
  const {id: marketTabId} = useContext(MarketTabContext)
  const replayMode = useSelector(selectReplayMode(marketTabId))

  return <>
    {/* Always mounted */}
    <Trades/>
    <Bases/>
    <BreakEven/>
    <PnlHandle/>
    <Screenshot/>
    <ChartContextMenu/>

    {/* Live-only */}
    {!replayMode && <TaScannerAlerts/>}

    {/* Hidden during DEFAULT replay (mounted in live and SMART) */}
    {replayMode !== REPLAY_MODE.DEFAULT && <>
      <BidAsk/>
      <PriceAlerts/>
      <EditPriceAlert/>
      <TriggeredPriceAlerts/>
      <TimeAlerts/>
      <EditTimeAlert/>
      <TriggeredTimeAlerts/>
      <TrendlineAlerts/>
      <EditTrendlineAlert/>
      <TriggeredTrendlineAlerts/>
      <Orders/>
      <OverlayContextMenu/>
    </>}

    {/* Replay-only */}
    {replayMode && <ReplayTimelines/>}
  </>
}

const ChartsPageChartWidget = () => {
  const {id: marketTabId} = useContext(MarketTabContext)

  return <SuperChartContextProvider chartId={marketTabId}>
    <ReplayContextProvider>
      <div tw="flex flex-col flex-1 h-full">
        <ChartsPageChart/>
        <SuperChartControls/>
      </div>
      <HeaderButtons mainChart={false} showReplay showSettings/>
      <ChartsPageOverlays/>
    </ReplayContextProvider>
  </SuperChartContextProvider>
}

export default ChartsPageChartWidget
```

### Task 3.2: Swap `CandleChart` for `ChartsPageChartWidget`

**File:** `src/containers/trade/trading-terminal/grid-layout/flex-grid/charts-grid-item.js`

```diff
-import {useCallback, useContext} from "react"
+import {useContext} from "react"
 import {logProfile} from "~/actions/profiler"
 import WidgetContext from "../widget-context"
 import {withSizeProps} from "~/util/with-size-props"
-import CandleChart from "../../widgets/candle-chart"
+import ChartsPageChartWidget from "../../widgets/super-chart/charts/charts-page-chart"
 ...
-import {ChartTabsController} from "~/models/market-tabs/chart-tabs-controller"

 const ChartsGridContent = ({node}) => {
-  const {id: marketTabId, currentMarket, coinraySymbol} = useContext(MarketTabContext)
-
-  const handleTVSymbolChanged = useCallback((coinraySymbol) => {
-    ChartTabsController.get().getTabById(marketTabId).setCoinraySymbol(coinraySymbol)
-  }, [marketTabId])
-
-  const handleTVIntervalChanged = useCallback(async (interval) => {
-    await ChartTabsController.get().getTabById(marketTabId).setResolution(interval)
-  }, [marketTabId])
-
-  const handleTVVisibleRangeChanged = useCallback((visibleRange) => {
-    ChartTabsController.get()
-      .getTabById(marketTabId).setVisibleRange(visibleRange)
-      .catch(console.error)
-  }, [marketTabId])
+  const {currentMarket, coinraySymbol} = useContext(MarketTabContext)

   if (currentMarket?.coinraySymbol !== coinraySymbol) return <ActivityIndicatorCentered/>

   return <div css={[
     tw`flex-1 flex flex-col overflow-hidden h-full bg-widget-background`,
     node.getParent().getType() === "border" && tw`border-0 rounded-none`,
   ]}>
     <MarketHeaderBar withMarketStats/>
-    <CandleChart toggleable={false}
-                 handleTVSymbolChanged={handleTVSymbolChanged}
-                 handleTVIntervalChanged={handleTVIntervalChanged}
-                 handleTVVisibleRangeChanged={handleTVVisibleRangeChanged}/>
+    <ChartsPageChartWidget/>
   </div>
 }
```

The grid item already wraps in `<MarketTabContextProvider
marketTabId={node.getId()}>` and `<WidgetContext.Provider>`. The new
widget reads both. No other call-site changes.

**Verify (Step 3):**

1. Navigate to `/charts`. Default layout loads with one chart-tab —
   chart renders, candles load.
2. Add a second chart-tab via the chart-tabs top bar — second chart
   renders alongside the first; both show live candles for their own
   symbols.
3. Change resolution from chart 1's period bar — only chart 1 redraws;
   `ChartTab.resolution` updates in Redux DevTools; chart 2 unaffected.
4. Change symbol from chart 1's period-bar symbol search — chart 1
   reloads; `ChartTab.coinraySymbol` updates; chart 2 unaffected.
5. Pan chart 1, switch chart layouts, switch back — chart 1's visible
   range restored.
6. Header buttons show **Alert + Replay + Settings** on each chart;
   no Buy/Sell.
7. Right-click chart background → menu shows Alert + Start Replay
   items, no Buy/Sell.
8. Settings button opens the chart-settings modal; preview chart
   renders alongside live grid charts; Save → all live charts pick up
   new colors.
9. Start a default replay on chart 1 — engine plays, replay timelines
   render on chart 1 only. Chart 2 keeps live candles.
10. While chart 1 replays, start a smart replay (backtest) on chart
    2 — both run independently.
11. Stop chart 1's session — chart 2's session continues; only
    chart 1's `state.replay.sessions[chart1Id]` is cleared.
12. **Replay hotkeys do NOT work yet** — that's Step 4. Header
    buttons + context menu cover replay start/stop in this step.

---

## Step 4: Page-level `<ReplayHotkeys/>` + producer wiring

### Task 4.1: Wrap `/charts` in the provider, mount page-level hotkeys

**File:** `src/containers/charts.js`

```diff
+import {LastInteractedChartProvider, useLastInteractedChart} from "./charts/last-interacted-chart-context"
+import ReplayHotkeys from "./trade/trading-terminal/widgets/super-chart/replay/replay-hotkeys"
 ...

+const ChartsReplayHotkeys = () => {
+  const {lastInteractedChartTabId} = useLastInteractedChart()
+  return <ReplayHotkeys chartId={lastInteractedChartTabId}/>
+}
+
 const Charts = () => {
   ...
   return <div tw={"flex flex-col h-full flex-1 overflow-hidden bg-widget-background text-text-primary"}>
     <GridItemSettingsProvider>
+      <LastInteractedChartProvider>
         <MarketHeaderBar global withLayoutControls withChartSettings/>
         <MarketSelectPopup .../>
         {chartsCustomLayoutsLoading
           ? <ActivityIndicatorCentered .../>
           : <div tw="...">...</div>}
         <ChartsHotkeys/>
+        <ChartsReplayHotkeys/>
+      </LastInteractedChartProvider>
     </GridItemSettingsProvider>
   </div>
 }
```

`ChartsReplayHotkeys` is a small wrapper so the
`useLastInteractedChart` hook fires inside the provider. It always
passes the live `lastInteractedChartTabId` (initially `null`).

### Task 4.2: Bump on Replay header button click

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/header-buttons.js`

Read the bump setter from `useLastInteractedChart` (no-op default
outside the provider — TT/CS unaffected). Call it inside the
`onReplay` closure before the picker call:

```diff
+import {useLastInteractedChart} from "~/containers/charts/last-interacted-chart-context"
 ...
 const HeaderButtons = ({mainChart, gridBotChart, showReplay, showSettings}) => {
   ...
+  const {setLastInteractedChartTabId} = useLastInteractedChart()
   ...
       chartController.headerButtons?.createHeaderButtons({
         mainChart, showReplay, showSettings,
         onAlert: ...,
         onBuy: ...,
         onSell: ...,
-        onReplay: () => chartController?.replay?.handleSelectReplayStartTimeClick(screen === SCREENS.MOBILE),
+        onReplay: () => {
+          setLastInteractedChartTabId(chartController?.id)
+          chartController?.replay?.handleSelectReplayStartTimeClick(screen === SCREENS.MOBILE)
+        },
         onSettings: ...,
       })
```

The pointerdown listener in `ChartsPageChartWidget` (Task 3.1) already
covers canvas-click bumping; this task adds the Replay-button bump.

**Verify (Step 4):**

1. Open `/charts` with two chart-tabs visible.
2. Click chart 1's canvas → press the replay play/pause hotkey
   (default `shift+space`, check user's bindings) — chart 1's replay
   engine receives the call (no-op if no session active; visible
   effect once a session is started).
3. Start a default replay on chart 2 via its Replay header button →
   click chart 2's canvas to pick a start time → engine starts.
4. Press play/pause hotkey → chart 2's engine responds. Chart 1
   ignored.
5. Click chart 1's canvas → press play/pause → chart 1's engine
   responds.
6. Click chart 2's Replay header button → without clicking the canvas,
   press a replay hotkey → chart 2's controller responds (verifies the
   button-click bump from Task 4.2).
7. Fresh page load (refresh) — before any chart interaction, press a
   replay hotkey → no-op, no console errors.
8. While in a chart-1 replay session, press step / step-back / stop
   hotkeys → chart 1's session responds.

---

## Step 5: `CandleChart` cleanup

### Task 5.1: Drop `toggleable` prop and TV branch

**File:** `src/containers/trade/trading-terminal/widgets/candle-chart.js`

```diff
-import React from "react"
 import "twin.macro"
-import {DefaultTradingWidget} from "./center-view/tradingview"
 import TradingTerminalChartWithProvider from "./super-chart/charts/trading-terminal-chart"

-const CandleChart = ({toggleable = true, ...tvProps}) => {
+const CandleChart = () => {
   return <div tw="flex flex-col flex-1 h-full">
-    {toggleable
-      ? <TradingTerminalChartWithProvider key="sc"/>
-      : <DefaultTradingWidget {...tvProps}/>}
+    <TradingTerminalChartWithProvider key="sc"/>
   </div>
 }

 export default CandleChart
```

**Verify (Step 5):**

1. Trading Terminal still renders the SC chart correctly.
2. `/charts` still works (now uses `ChartsPageChartWidget` directly,
   not `CandleChart`).
3. Run `grep -n "toggleable" src/containers/trade/trading-terminal/widgets/candle-chart.js`
   — no hits.
4. Run `grep -n "DefaultTradingWidget" src/containers/trade/trading-terminal/widgets/candle-chart.js`
   — no hits. (`DefaultTradingWidget` is still imported by quizzes /
   training / market-explorer / customer-service-layouts — out of scope.)
5. No console errors / no React warnings.

---

## Step 6: Cross-page parity check

No code changes — verification only. See `review.md` for the full
verification checklist.

---

## Step 7: TV cleanup (out of scope — Phase 10f)

`DefaultTradingWidget` and the broader TV chart entry stay in tree
because quizzes / training / market-explorer / customer-service-layouts
admin still consume them. Removal happens in Phase 10f.
