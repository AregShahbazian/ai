# Design: Header Buttons — SuperChart Migration

## Approach: Buttons in ChartController, state management in React component

Buttons are created imperatively via `ChartController.createToolbarButtons()` (already exists for Share button). A new React component `HeaderButtons` handles state-driven updates (enable/disable, highlight) via effects — same split as TV's approach where `Header` renders null and only manages button lifecycle.

## Button creation

Extend `ChartController.createToolbarButtons()` to create all 5 buttons after the existing Share button. Each button uses `this._superchart.createButton()`:

```javascript
createToolbarButtons({mainChart, onAlert, onBuy, onSell, onReplay, onSettings}) {
  // Existing share button...

  this._alertButton = this._superchart.createButton({
    align: "right",
    icon: '<i class="fa-solid fa-bell"></i>',
    text: i18n.t("...header.alert"),
    tooltip: i18n.t("...header.setPriceAlert"),
    onClick: onAlert,
  })

  if (mainChart) {
    this._buyButton = this._superchart.createButton({
      align: "right",
      icon: '<i class="fa-solid fa-arrow-up"></i>',
      text: i18n.t("...header.buy"),
      tooltip: i18n.t("...header.buy"),
      onClick: onBuy,
    })

    this._sellButton = this._superchart.createButton({
      align: "right",
      icon: '<i class="fa-solid fa-arrow-down"></i>',
      text: i18n.t("...header.sell"),
      tooltip: i18n.t("...header.sell"),
      onClick: onSell,
    })
  }

  this._replayButton = this._superchart.createButton({
    align: "right",
    icon: '<i class="fa-solid fa-backward"></i>',
    text: i18n.t("...header.replay"),
    tooltip: i18n.t("...header.pickReplayStart"),
    onClick: onReplay,
  })

  this._settingsButton = this._superchart.createButton({
    align: "right",
    icon: '<i class="fa-solid fa-gear"></i>',
    text: i18n.t("...header.settings"),
    tooltip: i18n.t("...header.chartSettings"),
    onClick: onSettings,
  })
}
```

### Why callbacks are passed in, not wired internally

The button actions need React context values (`currentMarket`, `replayController`, `exchangeApiKey`, `questionController`) and Redux `dispatch`. The controller has `dispatch` and `getState` but not React contexts. Rather than pulling all contexts into the controller, pass action callbacks from the React component. This matches how the existing Share button works — its `onClick` calls `this.shareScreenshot()` which only needs controller-internal state.

### Buy/Sell conditional creation

Buy and Sell only exist on `mainChart`. Rather than creating and hiding them, just skip creation when `!mainChart`. This is a mount-time constant (a chart doesn't switch between main/secondary), so no reactivity needed.

### Grid bot: no buttons

Grid bot charts don't call `createToolbarButtons()` for header buttons. The existing Share button creation can be split: `createShareButton()` (called by all charts) and `createHeaderButtons(...)` (called only by trading terminal charts, not grid bot).

## Styling

SC's `superchart-toolbar-btn` class provides base styling (flex row, centered, hover color change, right border separator). Custom styling per button via the returned HTMLElement:

```javascript
// Bottom border colors
this._alertButton.style.borderBottom = "2px solid #007FFF"
this._buyButton.style.borderBottom = "2px solid #06BF7B"
this._sellButton.style.borderBottom = "2px solid #F04747"
this._settingsButton.style.borderBottom = "2px solid rgba(20,26,33,0.4)"
// Replay: no border
```

SC buttons already inherit theme text color via `var(--superchart-text-color)` and have hover states via `var(--superchart-primary-color)`. No custom hover CSS needed unless we want different hover colors per button.

## State management: `HeaderButtons` React component

New file: `super-chart/header-buttons.js`. Renders null, manages button DOM state via effects. Mounted inside `SuperChartWidgetWithProvider` alongside other overlay components.

```javascript
const HeaderButtons = () => {
  const {readyToDraw, chartController} = useSuperChart()
  const {currentMarket} = useContext(MarketTabContext)
  const {exchangeApiKey} = useContext(MarketTabDataContext)
  const {onToggle: toggleSettingsModal} = useContext(GridItemSettingsContext)
  const dispatch = useDispatch()
  const screen = useContext(ScreenContext)
  const screen = useContext(ScreenContext)
  const isMobile = screen === SCREENS.MOBILE

  // Create buttons once when chart is ready (skip on mobile — ActionButtons handles it)
  useEffect(() => {
    if (!readyToDraw || !chartController || isMobile) return
    chartController.createHeaderButtons({
      mainChart: true, // or from props/context
      onAlert: () => dispatch(conditionalCallback(
        () => dispatch(newAlert(currentMarket.coinraySymbol, {price: currentMarket?.getMarket().lastPrice})),
        i18n.t("actions.preview.userActions.createAlerts"),
        {features: {feature: "trading"}},
      )),
      onBuy: () => dispatch(conditionalCallback(
        () => dispatch(startOrder({orderSide: OrderSide.BUY}, true)),
        i18n.t("actions.preview.userActions.createOrders"),
        {features: {feature: "trading"}, device: {mustBeActive: !exchangeApiKey?.paperTrading}},
      )),
      onSell: () => dispatch(conditionalCallback(
        () => dispatch(startOrder({orderSide: OrderSide.SELL}, true)),
        i18n.t("actions.preview.userActions.createOrders"),
        {features: {feature: "trading"}, device: {mustBeActive: !exchangeApiKey?.paperTrading}},
      )),
      onReplay: () => {}, // Phase 5: wire to SC's own ReplayContext
      onSettings: () => toggleSettingsModal("CenterView"),
    })
  }, [readyToDraw])

  // Phase 5: enable/disable effect (reads replayMode + backtest from SC ReplayContext)
  // Phase 5: replay highlight effect (reads selectingStartTime from SC ReplayContext)

  return null
}
```

## Controller helper methods

```javascript
// Enable/disable Alert, Buy, Sell buttons
setHeaderButtonsEnabled(enabled) {
  for (const btn of [this._alertButton, this._buyButton, this._sellButton]) {
    if (!btn) continue
    btn.style.opacity = enabled ? "1" : "0.2"
    btn.style.pointerEvents = enabled ? "auto" : "none"
  }
}

// Highlight replay button
setReplayButtonHighlight(active) {
  if (!this._replayButton) return
  this._replayButton.style.color = active ? "#2563EB" : ""
}
```

FA icons inherit `color` from their parent, so setting `color` on the button changes both text and icon — no CSS filter hack needed.

## i18n

Same pattern as existing Share button. In `createHeaderButtons`, store span references and register a `languageChanged` listener that updates all button labels and tooltips. Unsubscribe in `dispose()`.

## Mobile

On mobile, desktop buttons are NOT created (skip `createHeaderButtons` when `screen === SCREENS.MOBILE`). The existing `ActionButtons` component is mounted in the SC widget tree with the same render condition.

In `super-chart.js`, add `TradingViewControls`-equivalent rendering below the chart container:

```jsx
const SuperChartControls = () => {
  const screen = useContext(ScreenContext)
  const {readyToDraw} = useSuperChart()
  // Phase 5: read replayMode from SC ReplayContext
  const replayMode = undefined

  const showActionButtons = !replayMode && mainChart && screen === SCREENS.MOBILE

  if (!showActionButtons) return null

  return <TradeFormContextProvider>
    <div tw="flex flex-row space-x-2 p-2 overflow-auto" className="no-scrollbar">
      <ActionButtons/>
    </div>
  </TradeFormContextProvider>
}
```

## File changes

| File | Change |
|------|--------|
| `super-chart/chart-controller.js` | Split `createToolbarButtons` into `createShareButton` + `createHeaderButtons`. Add `setHeaderButtonsEnabled`, `setReplayButtonHighlight`. Store button refs. Cleanup in `dispose()`. |
| **New:** `super-chart/header-buttons.js` | React component (renders null). Creates buttons on mount, manages enable/disable/highlight via effects. |
| `super-chart/super-chart.js` | Mount `<HeaderButtons/>` and `<SuperChartControls/>` in `SuperChartWidgetWithProvider`. |

## What works now vs later

| Feature | Status | Notes |
|---------|--------|-------|
| Alert button + action | Full | — |
| Buy/Sell buttons + actions | Full | — |
| Settings button + action | Full | — |
| Replay button | Created, no-op | Phase 5: wire to SC's own ReplayContext |
| Enable/disable (replay/backtest) | Methods ready, not wired | Phase 5: reads from SC ReplayContext |
| Replay highlight | Method ready, not wired | Phase 5: reads `selectingStartTime` from SC ReplayContext |
| Quiz visibility (hide alert/replay) | Not implemented | Phase 7 — `QuizContext` not yet in SC tree |
| Period-bar hide (quiz play) | Ready, not wired | Phase 5/7 — call `sc.setPeriodBarVisible(false)` when entering quiz play mode |
| SC built-in button hide (Indicators, Timezone, Settings, Screenshot, Full Screen) | Full | Global CSS in `chart-controller.js._applyTemporaryHacks` targeting `.superchart-period-bar [data-button="<id>"]` |
| Mobile ActionButtons | Mounted | Reused as-is |
| i18n updates | Full | — |
| Bottom border styling | Full | — |
