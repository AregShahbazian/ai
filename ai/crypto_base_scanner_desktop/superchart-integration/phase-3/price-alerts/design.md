# Design: Price Alerts — SuperChart Integration

## Approach

Three files change:

1. **`chart-controller.js`** — add `createPriceAlert` and `createEditingPriceAlert` methods
2. **`overlays/price-alerts.js`** — new overlay component for submitted price alerts (display-only)
3. **`overlays/edit-price-alert.js`** — new overlay component for editing price alert (interactive)

Plus wiring in `super-chart.js`.

The TV implementation bundles all three alert types into `alerts.js` (submitted) and `edit-alerts.js` (editing), switching on `alertType`. For SC, each alert type gets its own overlay file. This keeps files focused and avoids the switch-on-type pattern.

## Chart Controller — `createPriceAlert`

### Submitted alert

```js
createPriceAlert(price, {color, quantityText, showLine, onModify, onCancel}) {
  const chart = this.getChart()
  if (!chart) return null
  const line = createOrderLine(chart, {
    price: this._toPrice(price),
    quantity: quantityText,
    align: "right",
    editable: false,
    lineColor: color,
    lineStyle: showLine ? "dashed" : undefined,
    isBodyVisible: false,
    quantityTextColor: "#FFFFFF",
    quantityBackgroundColor: color,
    quantityBorderColor: color,
    cancelButtonBackgroundColor: "#FFFFFF",
    cancelButtonBorderColor: color,
    cancelButtonIconColor: color,
    yAxisLabelTextColor: "#FFFFFF",
    yAxisLabelBackgroundColor: color,
    yAxisLabelBorderColor: color,
    isCancelButtonVisible: !!onCancel,
    onModify,
    onCancel,
  })
  if (line) this._register("alerts", `price-${Date.now()}`, line)
  return line
}
```

Key decisions:
- `isBodyVisible: false` hides the body entirely. SC supports `isBodyVisible`, `isQuantityVisible`, and `isCancelButtonVisible` props to control section visibility.
- `editable: false` — disables dragging on submitted alerts. No `onMove`/`onMoveEnd` passed.
- `lineStyle: "dashed"` when `showLine` is true. When false, line is hidden (match TV behavior via `setExtendLeft(false)`).
- Registry key uses alert ID (passed by component), not `Date.now()` — see actual task below.

### Editing alert (active)

```js
createEditingPriceAlert(price, {color, bodyText, quantityText, onModify, onMoveEnd, onCancel}) {
  const chart = this.getChart()
  if (!chart) return null
  const line = createOrderLine(chart, {
    price: this._toPrice(price),
    text: bodyText,
    quantity: quantityText,
    align: "right",
    editable: true,
    lineColor: color,
    bodyTextColor: color,
    bodyBackgroundColor: "#FFFFFF",
    bodyBorderColor: color,
    quantityTextColor: "#FFFFFF",
    quantityBackgroundColor: color,
    quantityBorderColor: color,
    cancelButtonBackgroundColor: "#FFFFFF",
    cancelButtonBorderColor: color,
    cancelButtonIconColor: color,
    yAxisLabelTextColor: "#FFFFFF",
    yAxisLabelBackgroundColor: color,
    yAxisLabelBorderColor: color,
    isCancelButtonVisible: true,
    onModify,
    onMoveEnd,
    onCancel,
  })
  if (line) this._register("editAlert", "price", line)
  return line
}
```

Key decisions:
- `editable: true` — draggable, with `onMoveEnd` for price updates
- Body is visible: white background, alert-color text + border
- Registered under `"editAlert"` group (only one editing alert at a time)
- No `onMove` — only `onMoveEnd` (SC equivalent of TV's `onMove` which fires at drag end)

### Saving state

```js
createSavingPriceAlert(price, {color, showLine}) {
  const chart = this.getChart()
  if (!chart) return null
  const savingText = i18n.t("containers.trade.market.marketGrid.centerView.tradingView.editAlerts.saving")
  const line = createOrderLine(chart, {
    price: this._toPrice(price),
    text: savingText,
    align: "right",
    editable: false,
    lineColor: color,
    lineStyle: showLine ? "dashed" : undefined,
    bodyTextColor: "#FFFFFF",
    bodyBackgroundColor: color,
    bodyBorderColor: color,
    isQuantityVisible: false,
    yAxisLabelTextColor: "#FFFFFF",
    yAxisLabelBackgroundColor: color,
    yAxisLabelBorderColor: color,
    isCancelButtonVisible: false,
  })
  if (line) this._register("editAlert", "price", line)
  return line
}
```

## Component — `price-alerts.js`

Renders all submitted price alerts (both pending and triggered). Follows the same pattern as the TV `Alerts` component but only handles `alertType === "price"`.

### Data flow

```
MarketTabDataContext.marketTradingInfo.alerts → filter(alertType === "price") → map → createPriceAlert()
MarketTabDataContext.marketTradingInfo.triggeredAlerts → filter(alertType === "price") → map → createPriceAlert()
```

### Structure

```js
const PriceAlerts = () => {
  const {readyToDraw, chartController, chartColors} = useSuperChart()
  const {marketTradingInfo} = useContext(MarketTabDataContext)
  const {currentMarket} = useContext(MarketTabContext)
  const chartSettings = useSelector(state => state.chartSettings)
  const alertsFormId = useSelector(state => state.alertsForm.alert.id)
  const deletingAlertIds = useSelector(state => state.alertsForm.deletingAlertIds)
  const dispatch = useDispatch()

  const clearAlerts = util.useImmutableCallback(() => {
    chartController?.clearOverlays("alerts")
  })
  useSymbolChangeCleanup(currentMarket, clearAlerts)

  useEffect(() => {
    clearAlerts()
    if (!readyToDraw) return
    if (!chartSettings.alertsShow) return

    const {alerts, triggeredAlerts} = marketTradingInfo
    const color = chartColors.alert

    // Pending price alerts
    alerts
      .filter(a => a.alertType === "price" && a.id !== alertsFormId)
      .forEach(alert => {
        const quantityText = buildQuantityText(alert, chartSettings, deletingAlertIds)
        chartController.createPriceAlert(+alert.price, {
          color,
          quantityText,
          showLine: chartSettings.alertsShowLine,
          onModify: chartSettings.alertsEnableEditing
            ? {params: {}, callback: () => dispatch(editAlert(alert))}
            : undefined,
          onCancel: chartSettings.alertsEnableEditing && chartSettings.alertsEnableCanceling
            ? {params: {}, callback: () => dispatch(deleteAlert(alert.id))}
            : undefined,
        })
      })

    // Triggered price alerts
    if (chartSettings.alertsShowClosed) {
      triggeredAlerts
        .filter(a => a.alertType === "price" && a.id !== alertsFormId)
        .forEach(alert => {
          chartController.createPriceAlert(+alert.price, {
            color: chartColors.closedAlert,
            quantityText: buildQuantityText(alert, chartSettings, deletingAlertIds),
            showLine: chartSettings.alertsShowLine,
          })
        })
    }
  }, [readyToDraw, marketTradingInfo, chartSettings, chartColors, deletingAlertIds, alertsFormId])

  return null
}
```

### `buildQuantityText` helper (local to file)

```js
function buildQuantityText(alert, chartSettings, deletingAlertIds) {
  if (deletingAlertIds.includes(alert.id)) return "DELETING..."
  if (!chartSettings.alertsShowNote) return ""
  const {note, recurring, status} = alert
  const base = util.truncateString(note || "Alert", 20)
  const indicator = !recurring ? "" : status === AlertStatus.PENDING ? " \u2759\u2759" : " \u25b6"
  return `${base}${indicator}`.toUpperCase()
}
```

## Component — `edit-price-alert.js`

Renders the single price alert currently being edited. Follows the TV `edit-alerts.js` PriceAlert component.

### Structure

```js
const EditPriceAlert = () => {
  const {readyToDraw, chartController, chartColors} = useSuperChart()
  const {currentMarket} = useContext(MarketTabContext)
  const alertsForm = useSelector(state => state.alertsForm)
  const chartSettings = useSelector(state => state.chartSettings)
  const dispatch = useDispatch()

  const clearEditAlert = util.useImmutableCallback(() => {
    chartController?.clearOverlays("editAlert")
  })

  useEffect(() => {
    clearEditAlert()
    if (!readyToDraw) return
    if (!alertsForm.isEditing || alertsForm.alert.alertType !== "price") return

    const {alert, isSubmitting} = alertsForm
    const {price} = alert
    if (!price || !price.gt(0) || !chartSettings.alertsEnableEditing) return

    const color = chartColors.alert

    if (isSubmitting) {
      chartController.createSavingPriceAlert(+price, {
        color,
        showLine: chartSettings.alertsShowLine,
      })
    } else {
      const {precisionPrice, quoteCurrency} = currentMarket.getMarket()
      chartController.createEditingPriceAlert(+price, {
        color,
        bodyText: i18n.t("containers.trade.market.marketGrid.centerView.tradingView.editAlerts.alertMeWhen"),
        quantityText: `${util.correctNumberPrecision(precisionPrice, price)} ${quoteCurrency}`,
        onModify: {params: {}, callback: () => dispatch(submitAlertsForm())},
        onMoveEnd: {params: {}, callback: (_params, event) => {
          const newPrice = event?.overlay?.points[0]?.value
          if (newPrice === undefined) return
          dispatch(editAlert({
            ...alert,
            price: util.correctNumberPrecision(precisionPrice, newPrice),
          }))
        }},
        onCancel: {params: {}, callback: () => dispatch(resetAlertForm())},
      })
    }
  }, [readyToDraw, alertsForm, chartColors, chartSettings])

  return null
}
```

### `onMoveEnd` price retrieval

SC's `onMoveEnd` callback signature is `(params, event)` where the new price is at `event.overlay.points[0].value`. The `params` object is whatever was passed in `onMoveEnd: {params, callback}`. See `Orders.stories.tsx` `handleOnMoveEnd` for reference.

## Wiring — `super-chart.js`

Import and render both components alongside existing overlays:

```js
import PriceAlerts from "./overlays/price-alerts"
import EditPriceAlert from "./overlays/edit-price-alert"

// Inside render:
<PriceAlerts/>
<EditPriceAlert/>
```

## Open Questions

1. ~~**`onMoveEnd` signature**~~ — Resolved. Callback is `(params, event)`, price at `event.overlay.points[0].value`.
2. ~~**`editable: false` + drag**~~ — Resolved. SC's `editable` prop exists and controls drag behavior.
