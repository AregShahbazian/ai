# Tasks: Phase 3c — Market Data Overlays

## 1. Bid/Ask overlay

Create `src/containers/trade/trading-terminal/widgets/super-chart/overlays/bid-ask.js`.

**Data sources:**
- `currentMarket` from `MarketTabContext` — `subscribeMarketUpdates()` for bid/ask prices
- `chartSettings.miscShowOrderBookAskBid` from Redux

**Implementation:**
- Gate on `readyToDraw` from `useSuperChart()`
- Draw bid/ask as `horizontalStraightLine` overlays via `chart.createOverlay()`
- Update via `chart.overrideOverlay({id, points: [{value: newPrice}]})`
- Remove via `chart.removeOverlay({id})`
- On symbol change: remove lines, recreate
- On `miscShowOrderBookAskBid` toggle: create or remove lines
- Skip drawing when setting is off
- Renders `null` (no DOM)

**Reference:** `tradingview/bid-ask.js`

---

## 2. Break-even overlay

Create `src/containers/trade/trading-terminal/widgets/super-chart/overlays/break-even.js`.

**Data sources:**
- `CurrentPositionContext` — `currentPosition`
- `MarketTabContext` — `id`
- Redux: `positionDates`, `hideAmounts`, `selectedCurrency`, chart settings

**Implementation:**
- P&L position handle: `createOrderLine(chart)` with text, quantity, colors, cancel button
- Break-even line: `chart.createOverlay({name: 'priceLine', points: [{value}]})` — canvas line, NOT a handle
- On position change: update or recreate P&L handle
- On `miscShowBreakEvenPoint` toggle: create or remove break-even line
- `onCancel` callback dispatches close/delete position

**Reference:** `tradingview/break-even.js`

---

## 3. Trades overlay

Create `src/containers/trade/trading-terminal/widgets/super-chart/overlays/trades.js`.

**Data sources:**
- `MarketTabContext` — market trades
- `MarketTabDataContext` — `wsTradeUpdates`
- `CurrentPositionContext` — `currentPosition`
- Chart settings: `closedOrdersShow`, `closedOrdersShowAll`, `closedOrdersNumber`, etc.
- Visible range from `chart.getVisibleRange()` + `subscribeAction('onVisibleRangeChange')`

**Implementation:**
- Trade markers via `chart.createOverlay({name: 'simpleAnnotation', ...})`
- `simpleAnnotation` only draws upward arrows — may need custom `tradeMarker` overlay
  via `registerOverlay()` for buy (up) vs sell (down) arrows
- Track shapes in ref by `trade.externalId`
- Filter trades by visible range and settings
- On visible range change: remove out-of-view, draw newly visible
- On position change: clear all and redraw

**Reference:** `tradingview/trades.js`

---

## 4. Price/Time Select utility

Create `src/containers/trade/trading-terminal/widgets/super-chart/overlays/price-time-select.js`.

**Implementation:**
- Module-level state (not a React component): `callback`, `chart` refs
- `startPriceTimeSelect(cb)` / `stopPriceTimeSelect()` / `isPriceTimeSelecting()`
- Crosshair tracking: `chart.subscribeAction('onCrosshairChange', cb)`
- Mouse up: DOM `mouseup` listener on chart container
- Helper functions: `getPriceOffset()`, `getTimeOffset()`, `getVisiblePriceRange()`
- Crosshair callback data shape needs verification during implementation

**Reference:** `tradingview/price-time-select.js`

---

## 5. Wire overlays into SuperChartWidget

Modify `super-chart/super-chart.js`:
- Import and render overlay components inside `SuperChartContextProvider`
- Overlays render as siblings of `SuperChartWidget` inside the provider

---

## 6. Verify

- Bid/ask lines appear when `miscShowOrderBookAskBid` is enabled
- Lines update in real-time as bid/ask prices change
- Break-even line shows when position is open and setting enabled
- P&L handle shows with correct text, color, close button
- Trade arrows appear for closed trades in visible range
- TV chart widget still works normally
