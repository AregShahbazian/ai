# Tasks: Header Buttons — SuperChart Migration

## T1 — Split `createToolbarButtons` in ChartController

**File:** `super-chart/chart-controller.js`

- Rename existing `createToolbarButtons()` to `createShareButton()`
- Create new `createHeaderButtons({mainChart, onAlert, onBuy, onSell, onReplay, onSettings})`
- In `createHeaderButtons`, create buttons via `this._superchart.createButton()`:
  - Alert: `fa-bell`, `align: "right"`
  - Buy (if `mainChart`): `fa-arrow-up`
  - Sell (if `mainChart`): `fa-arrow-down`
  - Replay: `fa-backward`
  - Settings: `fa-gear`
- Store refs: `this._alertButton`, `this._buyButton`, `this._sellButton`, `this._replayButton`, `this._settingsButton`
- Apply bottom border styling after creation:
  - Alert: `2px solid #007FFF`
  - Buy: `2px solid #06BF7B`
  - Sell: `2px solid #F04747`
  - Settings: `2px solid rgba(20,26,33,0.4)`
  - Replay: none
- Update the call site (the `checkReady` callback in `super-chart.js`) to call `createShareButton()` instead of `createToolbarButtons()`. `createHeaderButtons` will be called from the React component (T2).

## T2 — Create `HeaderButtons` React component

**New file:** `super-chart/header-buttons.js`

- Renders null
- Reads from contexts: `useSuperChart` (readyToDraw, chartController), `MarketTabContext` (currentMarket), `MarketTabDataContext` (exchangeApiKey), `GridItemSettingsContext` (onToggle), `ScreenContext`
- On `readyToDraw` (and not mobile): calls `chartController.createHeaderButtons(...)` with callbacks:
  - `onAlert`: `conditionalCallback` → `newAlert(coinraySymbol, {price: lastPrice})`, feature gate `"trading"`
  - `onBuy`: `conditionalCallback` → `startOrder({orderSide: BUY}, true)`, feature gate `"trading"`, device gate `mustBeActive: !exchangeApiKey?.paperTrading`
  - `onSell`: same as Buy with `SELL`
  - `onReplay`: no-op (`() => {}`) — Phase 5
  - `onSettings`: `toggleSettingsModal("CenterView")`
- Skip button creation on mobile (`screen === SCREENS.MOBILE`)

## T3 — Add `setHeaderButtonsEnabled` and `setReplayButtonHighlight` to ChartController

**File:** `super-chart/chart-controller.js`

```javascript
setHeaderButtonsEnabled(enabled) {
  for (const btn of [this._alertButton, this._buyButton, this._sellButton]) {
    if (!btn) continue
    btn.style.opacity = enabled ? "1" : "0.2"
    btn.style.pointerEvents = enabled ? "auto" : "none"
  }
}

setReplayButtonHighlight(active) {
  if (!this._replayButton) return
  this._replayButton.style.color = active ? "#2563EB" : ""
}
```

Not wired to effects yet — Phase 5 will call these from `HeaderButtons` when SC ReplayContext exists.

## T4 — i18n language change listener

**File:** `super-chart/chart-controller.js` (inside `createHeaderButtons`)

- After creating buttons, store span refs for each button's text span (`querySelectorAll("span")[1]`)
- Register `i18n.on("languageChanged", updateHeaderButtonLabels)` that updates all button text + tooltips
- Store unsubscribe fn, call in `dispose()`
- Extend the existing `_unsubLanguageChange` (from Share button) or add `_unsubHeaderLanguageChange`

## T5 — Cleanup in `dispose()`

**File:** `super-chart/chart-controller.js`

- Remove header button elements from DOM if they exist (`btn.remove()`)
- Unsubscribe i18n listener
- Null out refs (`this._alertButton = null`, etc.)
- Verify SC's `dispose()` doesn't already handle toolbar button cleanup — if it does, skip manual removal

## T6 — Mount `HeaderButtons` and `SuperChartControls` in widget tree

**File:** `super-chart/super-chart.js`

- Import and mount `<HeaderButtons/>` inside `SuperChartWidgetWithProvider`, alongside other overlay components
- Create `SuperChartControls` component:
  - Reads `ScreenContext`
  - Shows `ActionButtons` (imported from TV's `action-buttons.js`) when `mainChart && screen === SCREENS.MOBILE`
  - Wrapped in `TradeFormContextProvider`
  - Styled same as TV's `TradingViewControls`: `flex flex-row space-x-2 p-2 overflow-auto`, `box-shadow` dividers
- Render `SuperChartControls` after the chart container div (outside `SuperChartWidget`, inside the provider)

## T7 — Verify and test

- Alert button: creates price alert at current price (check toast/form opens)
- Buy button: opens buy order form (check conditional callback gates)
- Sell button: opens sell order form
- Settings button: opens CenterView settings modal
- Replay button: present, no-op on click
- Buttons don't appear on grid bot chart
- Buy/Sell don't appear on non-main charts
- Buttons have correct bottom border colors
- Language change updates button labels
- Mobile: desktop buttons not created, ActionButtons bar appears
- Chart unmount: no orphaned DOM elements or listeners
