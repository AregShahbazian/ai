# Design: Grid Bot Overlays — SuperChart Integration

## Key Design Decisions

### 1. GridBotSuperChartWidget — standalone SC widget

The trading terminal's `SuperChartWidget` (`super-chart.js`) depends on `MarketTabContext` and `WidgetContext`. Grid bot pages don't have these contexts. Rather than making the existing widget conditional, we create `GridBotSuperChartWidget` that:

- Accepts `coinraySymbol` as a prop (no `MarketTabContext`)
- Uses a `ResizeObserver` for resize (no `WidgetContext`)
- Skips `TradingTabsController` symbol/period/VR sync — grid bot chart doesn't persist state to market tabs
- Skips symbol change callback (`_onChartSymbolChange`) — grid bot chart symbol is controlled by the parent page, not by chart UI
- Reuses: `CoinrayDatafeed`, `ChartController`, `SuperChartContextProvider`, `toSymbolInfo`, `toPeriod`, `toSuperchartTheme`, `SUPPORTED_PERIODS`

The `ChartController` is reused as-is. Grid bot passes no `marketTabId`, so the constructor skips symbol/period change subscriptions (these callbacks call `TradingTabsController.get().getTabById(marketTabId)` which would throw on `undefined`). Guard in the constructor:

```js
this._unsubSymbol = marketTabId ? superchart.onSymbolChange(this._onChartSymbolChange) : () => {}
this._unsubPeriod = marketTabId ? superchart.onPeriodChange(this._onChartPeriodChange) : () => {}
```

The VR change subscription (`_onChartVisibleRangeChange`) is safe — it just updates `_visibleRange` and calls `_setVisibleRange`. Grid bot passes a no-op `setVisibleRange`.

Other unused features are inert:
- `_tradeForm` — unused for grid bot
- `visibleRangeFromTo` / `restoreVisibleRange` — `chartSettings?.miscRememberVisibleRange` check guards it
- `getState` — still needed for `this.colors` (reads theme + chart color overrides from Redux)

### 2. useDrawOverlayEffect and MarketTabContext

`useDrawOverlayEffect` calls `useContext(MarketTabContext)` to get `currentMarket` for `useSymbolChangeCleanup`. Grid bot pages don't have `MarketTabContext`.

**Solution**: No changes needed. `MarketTabContext` is created with `createContext({currentMarket: undefined, ...})`, so `useContext(MarketTabContext)` outside a provider returns the default value with `currentMarket: undefined`. `useSymbolChangeCleanup` already returns early when `!currentMarket` (line 8). Everything works out of the box.

Grid bot pages don't need symbol change cleanup anyway — the symbol doesn't change via the chart UI.

### 3. Grid bot price handles — controller methods

Four domain methods on `ChartController`, each owning its own visual logic:

- `createGridBotUpperPrice(price, onUpdate)` — alert color, `extendLeft: false, extendRight: true`
- `createGridBotLowerPrice(price, onUpdate)` — alert color, `extendLeft: false, extendRight: true`
- `createGridBotStopLoss(stopLoss, onUpdate)` — sell color, extends both sides, gates on `enabled`
- `createGridBotTakeProfit(takeProfit, onUpdate)` — buy color, extends both sides, gates on `enabled`

All delegate to `_createGridBotHandle(key, price, color, {extendLeft, extendRight, onUpdate})` which:

- Resolves label text: `i18n.t(\`actions.trading.triggerHandles.${key}.left\`).toUpperCase()`
- Body: white background, colored text + border
- No quantity, no cancel button
- `onMoveEnd` passed as **constructor option** via `_buildMoveEndCallback(onUpdate)` — reads new price from `event.overlay.points[0].value`, NOT from `line.getPrice()` (which returns the original price after drag)

Each `updateOrCreate*` method first tries `_updateGridBotHandle(key, price)` which calls `line.setPrice()` on the existing handle. Only creates if none exists.

SL/TP methods wrap the `onUpdate` callback to spread the object: `(newPrice) => onUpdate({...stopLoss, price: newPrice})`.

### 4. Grid bot order lines — controller method

`createGridBotOrderLine(order, index)` — resolves `order.side === "buy"` → buy color, else sell color. Creates a `createPriceLine` with `yAxisLabelVisible: true`, `labelVisible: false`.

### 5. Trades overlay — reuse existing component

The trading terminal's `Trades` component (`super-chart/overlays/trades.js`) already supports `localTrades` prop. When provided, it uses those directly instead of reading from `MarketTabDataContext`. All other context reads (`MarketTabContext`, `CurrentPositionContext`, `MarketTabDataContext`) have defaults and return safely when no provider exists.

No new overlay code needed — just wire `Trades` into `GridBotSuperChartWidget` and pass the `trades` prop.

### 6. Mutable object reactivity

`stopLoss` and `takeProfit` are mutable class instances on the `botForm` singleton. Their `update()` method mutates properties in place — the object reference never changes. React deps don't detect mutations.

**Solution**: Spread at the parent boundary in `grid-bot-settings.js`: `stopLoss={{...botForm.stopLoss}}`. This creates a new reference each render, allowing effect deps to detect changes. The component uses primitive deps (`stopLoss?.enabled`, `stopLoss?.price`) as an additional guard.

### 7. Dual-chart layout

TV and SC stacked vertically in a flex column, each `flex-1 min-h-0`:

```jsx
<div tw="flex flex-col flex-1">
  <div tw="flex-1 min-h-0">
    <GridBotTradingWidget .../>
  </div>
  <div tw="flex-1 min-h-0">
    <GridBotSuperChartWidget .../>
  </div>
</div>
```

Applied to both desktop and mobile layouts in both overview and settings tabs.

### 8. Symbol sync

`coinraySymbol` prop → `superchart.setSymbol(toSymbolInfo(coinraySymbol))` on change. No bidirectional sync.

### 9. Theme sync

`useContext(ThemeContext)` → `syncThemeToChart(theme._name)`.

### 10. Resize handling

`ResizeObserver` on the container div instead of `WidgetContext`.

## Data Flow

```
grid-bot-overview.js / grid-bot-settings.js
  ├── GridBotTradingWidget (TV)  — existing, unchanged
  └── GridBotSuperChartWidget (SC)
        ├── SuperChartContextProvider
        │     ├── GridBotSuperChart (chart container + init)
        │     ├── GridBotPrices (overlay)
        │     ├── GridBotOrders (overlay)
        │     └── Trades (reused from trading terminal, with localTrades prop)
        └── Props: coinraySymbol, orders, trades, edited,
                   upperPrice, lowerPrice, stopLoss, takeProfit,
                   updateXxx callbacks, visible
```

## File Changes

### New files

| File | Purpose |
|---|---|
| `super-chart/grid-bot-super-chart.js` | `GridBotSuperChartWidget` — standalone SC widget for grid bot pages |
| `super-chart/overlays/grid-bot/grid-bot-prices.js` | Upper/lower + SL/TP overlay component |
| `super-chart/overlays/grid-bot/grid-bot-orders.js` | Grid level price lines overlay component |

### Modified files

| File | Changes |
|---|---|
| `super-chart/overlay-helpers.js` | Add `gridBotPrices`, `gridBotOrders` to `OverlayGroups` |
| `super-chart/chart-controller.js` | Add grid bot handle + order line methods, guard constructor subscriptions |
| `grid-bot-overview.js` | Import `GridBotSuperChartWidget`, render below TV, split layout, pass all overlay props |
| `grid-bot-settings.js` | Same — both desktop and mobile layouts, spread `stopLoss`/`takeProfit` |
