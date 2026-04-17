# Tasks: Grid Bot Overlays — SuperChart Integration

## Step 1: Dual-chart layout ✅

### Task 1.1: Guard ChartController subscriptions on marketTabId ✅

**File:** `chart-controller.js`

Guarded symbol/period subscriptions on `marketTabId` in constructor. VR subscription stays (safe with no-op).

### Task 1.2: Create GridBotSuperChartWidget ✅

**File:** `grid-bot-super-chart.js` (new)

Standalone SC widget: `CoinrayDatafeed` + `Superchart` + `ChartController` (no `marketTabId`, no-op `setVisibleRange`), `ResizeObserver` for resize, symbol/theme sync via props.

### Task 1.3: Add SC to grid-bot-overview.js ✅

TV + SC stacked 50/50 in chart area. SC gets `coinraySymbol` only (overlays wired in later steps).

### Task 1.4: Add SC to grid-bot-settings.js ✅

Both desktop and mobile layouts. SC gets `coinraySymbol` only (overlays wired in later steps).

---

## Step 2: Grid bot prices overlay ✅

### Task 2.1: Add overlay groups ✅

**File:** `overlay-helpers.js`

Added `gridBotPrices`, `gridBotOrders` to `OverlayGroups`.

### Task 2.2: Add controller methods ✅

**File:** `chart-controller.js`

- `_createGridBotHandle(key, price, color, {extendLeft, extendRight, onUpdate})` — private, creates order line with i18n label (uppercase), white bg / colored text, `onMoveEnd` via `_buildMoveEndCallback`
- `_updateGridBotHandle(key, price)` — `setPrice()` on existing handle
- `updateOrCreateGridBotUpperPrice(price, onUpdate)` — alert color, extendLeft false, extendRight true
- `updateOrCreateGridBotLowerPrice(price, onUpdate)` — alert color, extendLeft false, extendRight true
- `updateOrCreateGridBotStopLoss(stopLoss, onUpdate)` — sell color, both extend, gates on `enabled`, wraps callback
- `updateOrCreateGridBotTakeProfit(takeProfit, onUpdate)` — buy color, both extend, gates on `enabled`, wraps callback
- `createGridBotOrderLine(order, index)` — price line, resolves side→color, y-axis label visible

### Task 2.3: Create GridBotPrices overlay component ✅

**File:** `overlays/grid-bot/grid-bot-prices.js` (new)

Uses `useDrawOverlayEffect`. Passes raw data to controller. Deps include primitive values for mutable objects: `stopLoss?.enabled`, `stopLoss?.price`, `takeProfit?.enabled`, `takeProfit?.price`.

### Task 2.4: Wire into widget + pass props from pages ✅

- `grid-bot-super-chart.js` — renders `GridBotPrices` inside provider
- `grid-bot-overview.js` — passes read-only price props + `{...spread}` on SL/TP
- `grid-bot-settings.js` — passes interactive price props + `{...spread}` on SL/TP (both desktop + mobile)

---

## Step 3: Grid bot orders overlay

### Task 3.1: Create GridBotOrders overlay component

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/overlays/grid-bot/grid-bot-orders.js` (new)

```js
import PropTypes from "prop-types"
import {OverlayGroups} from "../../overlay-helpers"
import {useSuperChart} from "../../context"
import useDrawOverlayEffect from "../../hooks/use-draw-overlay-effect"

const GridBotOrders = ({orders, visible = true}) => {
  const {chartController} = useSuperChart()

  useDrawOverlayEffect(OverlayGroups.gridBotOrders, () => {
    if (!visible || !orders || !orders.length) return

    orders.forEach((order, index) => {
      chartController.createGridBotOrderLine(order, index)
    })
  }, [visible, orders])

  return null
}

GridBotOrders.propTypes = {
  orders: PropTypes.array,
  visible: PropTypes.bool,
}

export default GridBotOrders
```

Component passes raw order objects — controller resolves side→color internally.

### Task 3.2: Wire GridBotOrders into widget + pass props from pages

**File:** `grid-bot-super-chart.js`

Import and render `GridBotOrders` inside provider:

```jsx
<GridBotOrders visible={props.visible} orders={props.orders}/>
```

Add `orders` propType to `GridBotSuperChartWidget`.

**File:** `grid-bot-overview.js`

Add `orders={botOrders}` to the SC widget (overview shows order lines).

**File:** `grid-bot-settings.js`

Add `orders={botForm.orders}` to SC widget in both desktop and mobile layouts.

**Verify:**
- Overview tab: horizontal lines at each grid level matching TV
- Settings tab: lines update when price range or order count changes
- Buy = green, sell = red. Y-axis labels visible.

---

## Step 4: Trades overlay

### Task 4.1: Wire Trades into GridBotSuperChartWidget

**File:** `grid-bot-super-chart.js`

Import existing `Trades` component from `./overlays/trades`. Render inside provider:

```jsx
<Trades localTrades={props.trades}/>
```

Add `trades` propType to `GridBotSuperChartWidget`.

**File:** `grid-bot-overview.js`

Add `trades={trades}` to the SC widget.

**Verify:**
- Overview tab: buy/sell arrow markers on candles matching TV
- Settings tab: no trades (no `trades` prop passed)
- Trade markers respect chart settings (show prices, show quantities, etc.)
