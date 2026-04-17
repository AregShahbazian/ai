# Design: Phase 3c — Market Data Overlays

## Drawing Primitive Mapping

TV has two distinct visual elements that must not be confused:
- **Chart overlays** (`chart.createShape()`) — lines/shapes drawn on the chart canvas
- **Order line handles** (`chart.createOrderLine()`) — interactive handles on the price axis

klinecharts has the same split:
- **Overlays** (`chart.createOverlay({name, points, ...})`) — canvas shapes
- **OrderLine** (`createOrderLine(chart)`) — interactive price axis handles

| TV Method | SuperChart Equivalent | Visual Type |
|---|---|---|
| `drawPriceLine(name, price, opts)` | `chart.createOverlay({name: 'horizontalStraightLine', points: [{value: price}]})` | Canvas line |
| `drawPriceLine(... {showPrice: true})` | `chart.createOverlay({name: 'priceLine', points: [{value: price}]})` | Canvas line + price label |
| `updatePriceLine(entity, price)` | `chart.overrideOverlay({id, points: [{value: price}]})` | — |
| `removePriceLine(entity)` | `chart.removeOverlay({id})` | — |
| `createPositionLine({price, text, ...})` | `createOrderLine(chart).setPrice(price).setText(text)...` | Price axis handle |
| `drawTrade(trade, inPosition)` | `chart.createOverlay({name: 'simpleAnnotation', ...})` | Canvas annotation |
| `removeEntity(entityId)` | `chart.removeOverlay({id: entityId})` | — |
| `crossHairMoved().subscribe()` | `chart.subscribeAction('onCrosshairChange', cb)` | — |
| `tvWidget.subscribe("mouse_up")` | DOM `mouseup` listener on chart container | — |

`createOrderLine` is imported from `"superchart"`, takes the klinecharts `chart` instance:
```js
import {createOrderLine} from "superchart"
const chart = chartController.getChart()
const handle = createOrderLine(chart).setPrice(price).setText(text)
```

---

## Common Overlay Pattern

All 3c overlays follow the same structure:

```js
import {useSuperChart} from "../context"

const SomeOverlay = () => {
  const {readyToDraw, chartController} = useSuperChart()
  // ... data from Redux/context
  const lineRef = useRef(null)

  useEffect(() => {
    if (!readyToDraw) return
    const chart = chartController.getChart()
    // draw using chart / createOrderLine(chart)
    return () => { /* remove overlays */ }
  }, [readyToDraw, /* data deps */])

  return null  // overlays render nothing to DOM
}
```

Key differences from TV overlays:
- `useSuperChart()` replaces `useContext(ChartContext)`
- `readyToDraw` replaces `tvWidget?.drawing` guard
- No `withHideInReplayMode` HOC needed yet (replay is Phase 5 — add it then)
- `chart.createOverlay()` replaces `chartFunctions.drawPriceLine()` (canvas lines)
- `createOrderLine(chart)` replaces `chartFunctions.createPositionLine()` (interactive handles)

---

## Bid/Ask (`overlays/bid-ask.js`)

**Data sources (unchanged):**
- `currentMarket` from `MarketTabContext` — subscribe to market updates for bid/ask prices
- `chartSettings.miscShowOrderBookAskBid` from Redux

**Drawing:**
```js
const chart = chartController.getChart()

// Bid line — canvas overlay, not an interactive handle
bidRef.current = chart.createOverlay({
  name: "horizontalStraightLine",
  points: [{value: bidPrice}],
  styles: {line: {color: chartColors.bidLine}},
  lock: true,
})

// Ask line — same pattern, different color
```

**Updates:** `chart.overrideOverlay({id: bidRef.current, points: [{value: newBidPrice}]})` on market update.

**Cleanup:** `chart.removeOverlay({id: bidRef.current}); chart.removeOverlay({id: askRef.current})`

**Lifecycle:**
1. Subscribe to `currentMarket.subscribeMarketUpdates()` on mount
2. On market update → `setPrice()` on existing lines
3. On symbol change → remove lines, recreate after new data
4. On `miscShowOrderBookAskBid` toggle → create or remove lines

---

## Break-Even (`overlays/break-even.js`)

**Data sources (unchanged):**
- `CurrentPositionContext` — `currentPosition` (openPrice, unrealizedProfit, breakEven, etc.)
- `MarketTabContext` — `id` (marketTabId)
- Redux: `positionDates`, `hideAmounts`, `selectedCurrency`, chart settings
  (`positionsShowPnl`, `positionsEnableCanceling`, `miscShowBreakEvenPoint`)
- `mainChart` flag from props or context

**Drawing — P&L position line:**
```js
pnlRef.current = createOrderLine(chart)
  .setPrice(openPrice)
  .setText(pnlText)           // "{+|-}{pnl} {currency}"
  .setQuantity(pnlPercent)    // "{+|-}{pnlPercent}%"
  .setBodyBackgroundColor(chartColors.grid)
  .setBodyTextColor(color)    // buy or sell color
  .setQuantityColor(color)
  .setCancelButtonVisible(canClose)

if (canClose) {
  pnlRef.current.onCancel({}, () => {
    // dispatch closeOrDeletePosition() or onDeleteSmartPosition()
  })
}
```

**Drawing — break-even line (canvas overlay with price label, NOT an interactive handle):**
```js
breakEvenRef.current = chart.createOverlay({
  name: "priceLine",
  points: [{value: breakEvenPoint}],
  styles: {line: {color: chartColors.breakEven}},
  lock: true,
})
```

**Updates:** `.setPrice()` and `.setText()` on position/market change.

**Cleanup:** `.remove()` on both refs.

---

## Trades (`overlays/trades.js`)

**Data sources (unchanged):**
- `MarketTabContext` — market trades
- `MarketTabDataContext` — `wsTradeUpdates` (WebSocket trade stream)
- `CurrentPositionContext` — `currentPosition` (for position filtering)
- Chart settings: `closedOrdersShow`, `closedOrdersShowAll`, `closedOrdersNumber`,
  `closedOrdersShowPosition`, `closedOrdersShowPrices`, `closedOrdersShowQuantities`,
  `closedOrdersShowTop`
- Visible range from `chart.getVisibleRange()`

**Drawing:**
Trade markers are arrow/icon annotations at specific price/time coordinates.

klinecharts approach — use `chart.createOverlay()` with annotation overlays:
```js
const id = chart.createOverlay({
  name: "simpleAnnotation",
  points: [{timestamp: trade.time, value: trade.price}],
  styles: {
    symbol: {type: trade.side === "buy" ? "triangle" : "triangleDown"},
    color: trade.side === "buy" ? chartColors.buy : chartColors.sell,
  },
  lock: true,
})
shapesRef.current[trade.externalId] = id
```

> **Note:** `simpleAnnotation` always draws an upward arrow. For sell trades (down arrow),
> we'll likely need a custom overlay registered via `registerOverlay()`. The built-in `arrow`
> overlay exists but is a pro drawing tool (user-placed), not a programmatic annotation.
> Simplest approach: register a `tradeMarker` custom overlay that accepts a `side` param
> in `extendData` and draws up/down arrows accordingly.

**Visible range filtering:**
```js
const {from, to} = chart.getVisibleRange()
// replaces useContext(VisibleRangeContext)
chart.subscribeAction("onVisibleRangeChange", () => { /* redraw visible trades */ })
```

**Cleanup:** `chart.removeOverlay({id})` for each tracked shape.

---

## Price/Time Select (`overlays/price-time-select.js`)

**Current behavior:** Utility module (not a typical overlay). Exposes functions to
start/stop a price/time selection mode. When active, captures crosshair position on
mouse up and calls a callback with `(price, time)`.

**SuperChart equivalent:**

Crosshair tracking:
```js
chart.subscribeAction("onCrosshairChange", ({x, y, kLineData, ...}) => {
  price.current = /* extract price from crosshair data */
  time.current = /* extract time from crosshair data */
})
```

Mouse up:
```js
chartController.getChart().getDom().addEventListener("mouseup", handler)
```

Visible range helpers (`getPriceOffset`, `getTimeOffset`, `getVisiblePriceRange`):
```js
const range = chart.getVisibleRange()
// price range needs coordinate conversion — may need chart.convertFromPixel()
```

> **Note:** The crosshair callback data shape (`onCrosshairChange` payload) needs
> verification during implementation. The price/time extraction may differ from TV's
> `crossHairMoved` event shape.

---

## Files

- New: `super-chart/overlays/bid-ask.js`
- New: `super-chart/overlays/break-even.js`
- New: `super-chart/overlays/trades.js`
- New: `super-chart/overlays/price-time-select.js`
- Modify: `super-chart/super-chart.js` — compose overlay components inside provider

## ChartController Changes

None. Overlays access `chartController.getChart()` directly and import `createOrderLine`
from `"superchart"`. Convenience methods will be added if implementation reveals repeated
boilerplate.

## What Doesn't Change

- TV overlays (`tradingview/bid-ask.js`, etc.) — untouched
- `CoinrayDatafeed`, `helpers.js` — untouched
- `chart-controller.js`, `context.js` — untouched
