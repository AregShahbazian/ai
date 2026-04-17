# Tasks: Price Alerts — SuperChart Integration

## Task 1: Add chart-controller methods

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`

**Changes:**
- Add `createPriceAlert(price, {color, quantityText, showLine, onModify, onCancel})` method
  - `isBodyVisible: false`, `align: "right"`, `editable: false`
  - Explicit color properties for body, quantity, cancel button, y-axis label (see design)
  - `lineStyle: "dashed"` when `showLine` is true
  - Register under `"alerts"` group with alert ID as key
- Add `createEditingPriceAlert(price, {color, bodyText, quantityText, onModify, onMoveEnd, onCancel})` method
  - `editable: true`, body visible with white background
  - Register under `"editAlert"` group with key `"price"`
- Add `createSavingPriceAlert(price, {color, showLine})` method
  - `editable: false`, body text = i18n "Saving", `isQuantityVisible: false`, `isCancelButtonVisible: false`
  - Register under `"editAlert"` group with key `"price"`

**Verify:** Methods exist, no syntax errors.

## Task 2: Create `price-alerts.js` overlay component

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/overlays/price-alerts.js` (new)

**Changes:**
- Renders all submitted price alerts (pending + triggered)
- Filter `marketTradingInfo.alerts` by `alertType === "price"`, exclude `alertsFormId`
- Build quantity text: truncated note (max 20 chars), uppercase, with recurring indicator
- Show "DELETING..." for alerts in `deletingAlertIds`
- Triggered alerts use `chartColors.closedAlert`, no onModify/onCancel
- Uses `useSuperChart()`, `useSymbolChangeCleanup`, `util.useImmutableCallback`
- Data from `MarketTabDataContext.marketTradingInfo`, `useSelector` for chartSettings and alertsForm state

**Verify:**
1. Open chart with pending price alerts — handles appear at correct prices
2. Quantity shows truncated note, uppercase
3. Click modify → opens edit mode
4. Click cancel → deletes alert
5. Toggle `alertsShowClosed` — triggered alerts appear/disappear with darker blue
6. Switch symbols — handles clear and redraw

## Task 3: Create `edit-price-alert.js` overlay component

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/overlays/edit-price-alert.js` (new)

**Changes:**
- Renders the currently-editing price alert (one at a time)
- When `isSubmitting`: show saving state (non-editable, "Saving" text)
- When editing: show draggable handle with "Alert me when" body text and price quantity
- `onModify` → `dispatch(submitAlertsForm())`
- `onMoveEnd` → update alert price via `dispatch(editAlert({...alert, price: newPrice}))`
- `onCancel` → `dispatch(resetAlertForm())` (exits edit mode, does NOT delete)
- Gated on `alertsForm.isEditing && alert.alertType === "price"`

**Verify:**
1. Edit a price alert → draggable handle appears with "Alert me when"
2. Drag handle → price updates in alert form
3. Click confirm (modify) → alert submits
4. Click cancel → exits edit mode, alert is NOT deleted
5. During save → "Saving" text appears, handle is not draggable

## Task 4: Wire into `super-chart.js`

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/super-chart.js`

**Changes:**
- Import `PriceAlerts` from `./overlays/price-alerts`
- Import `EditPriceAlert` from `./overlays/edit-price-alert`
- Render `<PriceAlerts/>` and `<EditPriceAlert/>` alongside existing overlays

**Verify:**
1. Both TV and SC charts show price alerts
2. No duplicate alerts (editing alert is filtered from submitted list)
3. All overlay lifecycle works: symbol change cleanup, readyToDraw gating
