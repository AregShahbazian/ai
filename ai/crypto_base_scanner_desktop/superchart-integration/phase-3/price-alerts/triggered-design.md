# Design: Triggered Price Alerts — SuperChart Integration

## Approach

Two files change:

1. **`chart-controller.js`** — add `createTriggeredAlert` method
2. **`overlays/triggered-price-alerts.js`** — new overlay component

Plus wiring in `super-chart.js`.

## Chart Controller — `createTriggeredAlert`

Triggered alerts are icon markers at a point, not order-line handles. TV uses `createMultipointShape` with a Font Awesome bell icon (`0xf0f3`). SC doesn't have icon overlays, so we use `simpleTag` annotation with "🔔" text.

`simpleTag` uses `annotationSchema` which supports `textSection` (color, background, font) and `lineSection`. We style it to show just the bell icon with the `closedAlert` color.

```js
createTriggeredAlert(key, timestamp, price, {color}) {
  const chart = this.getChart()
  if (!chart) return null
  const id = chart.createOverlay({
    name: "simpleTag",
    points: [{timestamp, value: this._toPrice(price)}],
    extendData: "🔔",
    lock: true,
  })
  if (id) {
    this._applyOverlayProperties(id, {
      textColor: color,
      textFontSize: 14,
      textBackgroundColor: "transparent",
      lineColor: "transparent",
      lineWidth: 0,
    })
    this._register("triggeredAlerts", key, id)
  }
  return id
}
```

Key decisions:
- Uses `simpleTag` overlay with "🔔" emoji as `extendData` (text content)
- `lock: true` — not interactive
- Line hidden via `lineColor: "transparent"` — we only want the tag, not a leader line
- Registered under `"triggeredAlerts"` group (separate from `"alerts"` which holds order-line handles)
- Color passed from component — `chartColors.closedAlert` for triggered, but could also be used for other alert icon markers in the future

## Component — `triggered-price-alerts.js`

Follows the same pattern as `trades.js` — filters visible triggered alerts and renders markers.

### Data flow

```
MarketTabDataContext.marketTradingInfo.triggeredAlerts → filter(alertType === "price") → createTriggeredAlert()
```

### Structure

```js
const TriggeredPriceAlerts = () => {
  const {readyToDraw, chartController, chartColors} = useSuperChart()
  const {marketTradingInfo} = useContext(MarketTabDataContext)
  const {currentMarket} = useContext(MarketTabContext)
  const {alertsShowClosed, alertsShow} = useSelector(state => state.chartSettings)
  const dispatch = useDispatch()

  const clear = util.useImmutableCallback(() => {
    chartController?.clearOverlays("triggeredAlerts")
  })
  useSymbolChangeCleanup(currentMarket, clear)

  useEffect(() => {
    clear()
    if (!readyToDraw || !alertsShow || !alertsShowClosed) return

    const {triggeredAlerts} = marketTradingInfo || EMPTY_MARKET_TRADING_INFO
    const color = chartColors.closedAlert

    triggeredAlerts
      .filter(a => a.alertType === "price")
      .forEach(alert => {
        if (!alert.updatedAt) return
        const timestamp = new Date(alert.updatedAt).getTime()
        chartController.createTriggeredAlert(`triggered-${alert.id}`, timestamp, +alert.price, {color})
      })
  }, [readyToDraw, marketTradingInfo, alertsShowClosed, alertsShow, chartColors])

  return null
}
```

Key decisions:
- Gated on both `alertsShow` and `alertsShowClosed`
- Uses `alert.updatedAt` for timestamp (when the alert was triggered) — same as TV
- Skips alerts without `updatedAt`
- Separate overlay group `"triggeredAlerts"` for independent lifecycle

## Wiring — `super-chart.js`

```js
import TriggeredPriceAlerts from "./overlays/triggered-price-alerts"

// Inside render:
<TriggeredPriceAlerts/>
```
