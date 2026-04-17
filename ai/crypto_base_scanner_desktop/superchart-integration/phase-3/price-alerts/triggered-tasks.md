# Tasks: Triggered Price Alerts — SuperChart Integration

## Task 1: Add `createTriggeredAlert` to chart-controller

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`

**Changes:**
- Add `createTriggeredAlert(key, timestamp, price, {color})` method
  - Uses `chart.createOverlay({name: "simpleTag", ...})` with "🔔" as `extendData`
  - `lock: true` — not interactive
  - Apply properties: `textColor: color`, `textFontSize: 14`, `textBackgroundColor: "transparent"`, `lineColor: "transparent"`, `lineWidth: 0`
  - Register under `"triggeredAlerts"` group

**Verify:** Method exists, no syntax errors.

## Task 2: Create `triggered-price-alerts.js` overlay component

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/overlays/triggered-price-alerts.js` (new)

**Changes:**
- Renders triggered price alerts as bell icon markers
- Filter `marketTradingInfo.triggeredAlerts` by `alertType === "price"`
- Uses `alert.updatedAt` for timestamp, `alert.price` for value
- Skip alerts without `updatedAt`
- Color: `chartColors.closedAlert`
- Gated on `alertsShow` AND `alertsShowClosed`
- Uses `useSuperChart()`, `useSymbolChangeCleanup`, `util.useImmutableCallback`
- Safe access: `marketTradingInfo || EMPTY_MARKET_TRADING_INFO`

**Verify:**
1. Toggle `alertsShowClosed` on — bell icons appear at triggered alert positions
2. Toggle off — icons disappear
3. Switch symbols — icons clear and redraw
4. Icons appear at correct price/time coordinates

## Task 3: Wire into `super-chart.js`

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/super-chart.js`

**Changes:**
- Import `TriggeredPriceAlerts` from `./overlays/triggered-price-alerts`
- Render `<TriggeredPriceAlerts/>` alongside existing overlays

**Verify:**
1. Triggered alerts show as bell markers, not order-line handles
2. No duplicate triggered alerts between components
