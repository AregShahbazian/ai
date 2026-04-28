# Tasks: Customer Service Charts — SuperChart Integration

## Step 1: Library tweak — gate Replay & Settings under `mainChart`

### Task 1.1: Move Replay & Settings creation under the `mainChart` block

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/controllers/header-buttons-controller.js`

In `createHeaderButtons({mainChart, onAlert, onBuy, onSell, onReplay,
onSettings, onToggleChart})`, move both `_replayButton` and
`_settingsButton` creation **into** the existing `if (mainChart) {...}`
block alongside Buy/Sell.

```diff
   if (mainChart) {
     this._buyButton = this._createToolbarButton({
       icon: "arrow-up", text: t("buy"), tooltip: t("buy"),
       borderColor: "#06BF7B", onClick: onBuy,
     })
     this._sellButton = this._createToolbarButton({
       icon: "arrow-down", text: t("sell"), tooltip: t("sell"),
       borderColor: "#F04747", onClick: onSell,
     })
+    this._replayButton = this._createToolbarButton({
+      icon: "backward", text: t("replay"), tooltip: t("pickReplayStart"),
+      onClick: onReplay,
+    })
+    this._settingsButton = this._createToolbarButton({
+      icon: "gear", text: t("settings"), tooltip: t("chartSettings"),
+      borderColor: "rgba(20,26,33,0.4)", onClick: onSettings,
+    })
   }
-
-  this._replayButton = this._createToolbarButton({
-    icon: "backward", text: t("replay"), tooltip: t("pickReplayStart"),
-    onClick: onReplay,
-  })
-
-  this._settingsButton = this._createToolbarButton({
-    icon: "gear", text: t("settings"), tooltip: t("chartSettings"),
-    borderColor: "rgba(20,26,33,0.4)", onClick: onSettings,
-  })
```

`_toolbarButtons` filtering, `setHeaderButtonsEnabled`, and
`setReplayButtonHighlight` already handle null button refs — no
other changes needed.

**Verify (Step 1):**

1. Open the Trading Terminal — header still shows Alert + Buy + Sell +
   Replay + Settings (5 buttons).
2. Open a grid bot page — chart still shows whatever buttons it had
   (Share screenshot button via `HeaderController`, no trading buttons).
   No Replay or Settings button — same as before.
3. No console errors.

---

## Step 2: `CustomerServiceSuperChartWidget` skeleton + market page swap

### Task 2.1: Create the widget

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/customer-service-super-chart.js` (new)

Pattern matches `grid-bot-super-chart.js`, with synth contexts and the
read-only overlay set.

```js
import React, {useContext, useEffect, useMemo, useRef} from "react"
import PropTypes from "prop-types"
import {useStore} from "react-redux"
import {ThemeContext} from "styled-components"
import UUID from "uuid-random"
import "twin.macro"
import {createDataLoader, Superchart} from "superchart"
import "superchart/styles"

import {createCurrentMarket} from "~/actions/coinray"
import {EMPTY_MARKET_TRADING_INFO} from "~/actions/trading"
import {MarketTabContext, MarketTabDataContext} from "~/containers/market-tabs/context"
import CoinrayDatafeed from "./coinray-datafeed"
import {SUPPORTED_PERIODS, toPeriod, toSuperchartTheme, toSymbolInfo} from "./chart-helpers"
import {ChartController} from "./chart-controller"
import {HeaderButtonsController} from "./controllers/header-buttons-controller"
import {PositionsController} from "./controllers/positions-controller"
import {SuperChartContextProvider, useSuperChart} from "./context"
import ChartRegistry from "~/models/chart-registry"

import HeaderButtons from "./header-buttons"
import Screenshot from "./screenshot"
import BidAsk from "./overlays/bid-ask"
import BreakEven from "./overlays/break-even"
import Bases from "./overlays/bases"
import Trades from "./overlays/trades"
import PnlHandle from "./overlays/pnl-handle"
import Orders from "./overlays/orders/orders"
import PriceAlerts from "./overlays/alerts/price-alerts/price-alerts"
import EditPriceAlert from "./overlays/alerts/price-alerts/edit-price-alert"
import TriggeredPriceAlerts from "./overlays/alerts/price-alerts/triggered-price-alerts"
import TimeAlerts from "./overlays/alerts/time-alerts/time-alerts"
import EditTimeAlert from "./overlays/alerts/time-alerts/edit-time-alert"
import TriggeredTimeAlerts from "./overlays/alerts/time-alerts/triggered-time-alerts"
import TrendlineAlerts from "./overlays/alerts/trendline-alerts/trendline-alerts"
import EditTrendlineAlert from "./overlays/alerts/trendline-alerts/edit-trendline-alert"
import TriggeredTrendlineAlerts from "./overlays/alerts/trendline-alerts/triggered-trendline-alerts"
import TaScannerAlerts from "./overlays/alerts/ta-scanner-alerts/ta-scanner-alerts"

const CS_RESOLUTION = "60"

const CustomerServiceSuperChart = ({coinraySymbol, chartId}) => {
  const containerRef = useRef(null)
  const {_setReadyToDraw, _setVisibleRange} = useSuperChart()
  const {currentMarket} = useContext(MarketTabContext)
  const store = useStore()
  const theme = useContext(ThemeContext)
  const controllerRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current || !coinraySymbol) return

    const datafeed = new CoinrayDatafeed()
    const dataLoader = createDataLoader(datafeed)

    const superchart = new Superchart({
      container: containerRef.current,
      symbol: toSymbolInfo(coinraySymbol),
      period: toPeriod(CS_RESOLUTION),
      dataLoader,
      theme: toSuperchartTheme(theme?._name),
      periods: SUPPORTED_PERIODS,
      debug: false,
    })

    const controller = new ChartController(superchart, datafeed, {
      id: chartId,
      dispatch: store.dispatch,
      getState: store.getState,
      setVisibleRange: _setVisibleRange,
      setReadyToDraw: _setReadyToDraw,
      // Lock customer-facing trading interactions off regardless of
      // staff chart settings. Read-only display flags pass through.
      // Alert flags untouched — staff alert flow keeps working.
      getChartSettings: () => ({
        ...store.getState().chartSettings,
        openOrdersEnableEditing: false,
        openOrdersEnableCanceling: false,
        positionsEnableCanceling: false,
      }),
    })
    controller.headerButtons = new HeaderButtonsController(controller)
    controller.positions = new PositionsController(controller)

    controllerRef.current = controller
    ChartRegistry.register(chartId, controller)

    // Disable the symbol-search trigger in the period bar — CS pages
    // bind the symbol to the URL, so letting the staff change it from
    // the chart UI would desync chart and route. Period picker stays
    // enabled. Scoped to this chart's container so other instances
    // (TT) are unaffected.
    const unsubReady = superchart.onReady(() => {
      const symbolBtn = containerRef.current?.querySelector("[data-button=\"symbolSearch\"]")
      if (symbolBtn) {
        symbolBtn.style.pointerEvents = "none"
        symbolBtn.style.opacity = "0.5"
        symbolBtn.style.cursor = "default"
      }
    })

    return () => {
      unsubReady?.()
      ChartRegistry.unregister(chartId)
      controller.dispose()
    }
  }, [])

  // Push currentMarket into the controller so PositionsController et al.
  // resolve baseCurrency/precisions when composing handle labels
  // (e.g. open TP draws "104 XNO", not just "104").
  useEffect(() => {
    controllerRef.current?.setCurrentMarket(currentMarket)
  }, [currentMarket])

  // Sync symbol changes
  useEffect(() => {
    if (!controllerRef.current || !coinraySymbol) return
    controllerRef.current._superchart.setSymbol(toSymbolInfo(coinraySymbol))
  }, [coinraySymbol])

  // Sync theme changes
  useEffect(() => {
    controllerRef.current?.syncThemeToChart(theme?._name)
  }, [theme?._name])

  // Sync chart color changes (also re-applies after theme toggle)
  const chartColors = useStore().getState().chartSettings.chartColors
  useEffect(() => {
    controllerRef.current?.syncChartColors()
  }, [chartColors, theme?._name])

  // Resize via ResizeObserver
  useEffect(() => {
    if (!containerRef.current) return
    const ro = new ResizeObserver(() => controllerRef.current?.resize())
    ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, [])

  return <div ref={containerRef} tw="flex-1 h-full min-h-0"/>
}

CustomerServiceSuperChart.propTypes = {
  coinraySymbol: PropTypes.string.isRequired,
  chartId: PropTypes.string.isRequired,
}

const CustomerServiceSuperChartWidget = ({coinraySymbol, marketTradingInfo}) => {
  const chartId = useMemo(() => `cs-${UUID().split("-")[0]}`, [])

  const csMarketTab = useMemo(() => ({
    id: undefined,
    coinraySymbol,
    currentMarket: createCurrentMarket(coinraySymbol),
    exchangeCode: undefined,
    resolution: CS_RESOLUTION,
  }), [coinraySymbol])

  const csMarketTabData = useMemo(() => ({
    marketTradingInfo: marketTradingInfo || EMPTY_MARKET_TRADING_INFO,
  }), [marketTradingInfo])

  return (
    <SuperChartContextProvider chartId={chartId}>
      <MarketTabContext.Provider value={csMarketTab}>
        <MarketTabDataContext.Provider value={csMarketTabData}>
          <CustomerServiceSuperChart coinraySymbol={coinraySymbol} chartId={chartId}/>
          <HeaderButtons mainChart={false}/>
          <Screenshot/>
          <BidAsk/>
          <BreakEven/>
          <Bases/>
          <Trades/>
          <PnlHandle/>
          <Orders/>
          <PriceAlerts/>
          <EditPriceAlert/>
          <TriggeredPriceAlerts/>
          <TimeAlerts/>
          <EditTimeAlert/>
          <TriggeredTimeAlerts/>
          <TrendlineAlerts/>
          <EditTrendlineAlert/>
          <TriggeredTrendlineAlerts/>
          <TaScannerAlerts/>
        </MarketTabDataContext.Provider>
      </MarketTabContext.Provider>
    </SuperChartContextProvider>
  )
}

CustomerServiceSuperChartWidget.propTypes = {
  coinraySymbol: PropTypes.string.isRequired,
  marketTradingInfo: PropTypes.object,
}

export default CustomerServiceSuperChartWidget
```

Notes for the implementer:

- `setSymbol` is the page-level call site for symbol changes since
  there's no `MarketTabSyncController.syncSymbolToChart`. Calling it on
  every effect run is safe (SC dedups same-symbol calls); the
  `if (!coinraySymbol) return` guard prevents the initial run from
  redundantly setting what the constructor already set.
- `chartColors` is read via the store ref pattern from
  `grid-bot-super-chart.js`. If `useSelector` is preferred for parity
  with `super-chart.js`, swap accordingly — the effect deps stay the
  same.

### Task 2.2: Swap the chart on `account/market.js`

**File:** `src/containers/customer-service/account/market.js`

Replace the import and the JSX:

```diff
-import {DefaultTradingWidget} from "../../trade/trading-terminal/widgets/center-view/tradingview"
+import CustomerServiceSuperChartWidget from "../../trade/trading-terminal/widgets/super-chart/customer-service-super-chart"
```

```diff
-<DefaultTradingWidget coinraySymbol={coinraySymbol}
-                      marketTradingInfo={marketTradingInfo}
-                      mainChart={false}/>
+<CustomerServiceSuperChartWidget coinraySymbol={coinraySymbol}
+                                 marketTradingInfo={marketTradingInfo}/>
```

**Verify (Step 2):**

1. Sign in as a user with CS access. Navigate to a CS market page:
   `/customer-service/accounts/<id>/markets/<coinraySymbol>/<exchangeApiKeyId>`.
2. SC chart renders with live candles for the customer's market.
3. Period bar shows Alert + Settings buttons (right side). No Buy /
   Sell / Replay buttons.
4. Bid/ask, bases, trades, alerts, TA-scanner alerts, orders all draw
   per the staff session + customer `marketTradingInfo` exactly as on
   the TV chart they replace.
5. Click the Alert button → `alertsForm` Redux state goes to "creating"
   → an editable price-alert line appears on the chart → click the
   body to submit / drag to move price → alert is saved against the
   staff session.
6. Click the Settings button → no-op (existing TV behaviour: no
   `GridItemSettingsProvider` above the chart).
7. Right-click the chart background → no context menu opens.
8. Right-click an alert/order line → no context menu opens.
9. Switch theme — chart re-styles; chart settings toggled in TT (alert
   line visibility, base visibility, etc.) reflect immediately.
10. No console errors during mount, symbol change, or alert creation.

---

## Step 3: Position page swap

### Task 3.1: Swap the chart on `account/position.js`

**File:** `src/containers/customer-service/account/position.js`

Replace the import and the JSX (same swap as the market page):

```diff
-import {DefaultTradingWidget} from "../../trade/trading-terminal/widgets/center-view/tradingview"
+import CustomerServiceSuperChartWidget from "../../trade/trading-terminal/widgets/super-chart/customer-service-super-chart"
```

```diff
-<DefaultTradingWidget coinraySymbol={coinraySymbol}
-                      marketTradingInfo={marketTradingInfo}
-                      mainChart={false}/>
+<CustomerServiceSuperChartWidget coinraySymbol={coinraySymbol}
+                                 marketTradingInfo={marketTradingInfo}/>
```

The position page already wraps its subtree in `<WithPosition
position={position} marketTradingInfo={marketTradingInfo}
market={market}>`, which provides `CurrentPositionContext` with the
customer's parsed position. The SC overlays (`BreakEven`, `PnlHandle`)
read the position from there directly — no extra wiring needed at this
call site.

**Verify (Step 3):**

1. Navigate to a CS position page: `/customer-service/positions/<id>`.
2. Chart renders with live candles for the customer's market.
3. `BreakEven` line draws at the customer's position break-even price
   (when `chartSettings.miscShowBreakEvenPoint` is on).
4. `PnlHandle` draws the live PnL marker tied to the customer's
   position.
5. All other overlays render exactly as on the market page.
6. Header: Alert + Settings buttons; no Buy / Sell / Replay.
7. No console errors.

---

## Step 4: Cross-page parity check

No code changes — verification only. See `review.md` for the full
verification checklist.

---

## Step 5: TV cleanup (out of scope — Phase 10f)

`DefaultTradingWidget`, `tradingview.js`, and the broader TV chart
entry stay in tree because the /charts page (Phase 9a) and quizzes
(Phase 9d) still consume them. Removal happens in Phase 10f. This PRD
changes only the two CS pages and one library file.
