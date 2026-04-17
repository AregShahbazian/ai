# Design: PnL Handle — SuperChart Integration

## Approach

Two files change:

1. **`chart-controller.js`** — rewrite `createPnlHandle` to use options-object API
2. **`overlays/pnl-handle.js`** — clean up component to follow SC overlay patterns (use `useSymbolChangeCleanup`, `util.useImmutableCallback`, remove manual subscription wiring)

## Chart Controller — `createPnlHandle`

### Current (chained setters)

```js
createPnlHandle(price, {text, quantityText, profit, cancelVisible}) {
  const chart = this.getChart()
  if (!chart) return null
  const color = profit < 0 ? this.colors.openSellOrder : this.colors.openBuyOrder
  const line = createOrderLine(chart)
    .setPrice(price)
    .setText(text)
    .setQuantity(quantityText)
    .setBodyBackgroundColor(this.colors.grid)
    .setBodyTextColor(color)
    .setQuantityColor(color)
    .setCancelButtonVisible(cancelVisible)
  if (line) this._register("pnl", "line", line)
  return line
}
```

### New (options object)

```js
createPnlHandle(price, {text, quantityText, profit, cancelVisible, onCancel}) {
  const chart = this.getChart()
  if (!chart) return null
  const color = profit < 0 ? this.colors.openSellOrder : this.colors.openBuyOrder
  const line = createOrderLine(chart, {
    price,
    text,
    quantity: quantityText,
    align: "left",
    editable: false,
    lineColor: "transparent",
    bodyTextColor: color,
    bodyBackgroundColor: this.colors.grid,
    bodyBorderColor: this.colors.grid,
    quantityTextColor: color,
    quantityBackgroundColor: this.colors.grid,
    quantityBorderColor: this.colors.grid,
    isCancelButtonVisible: cancelVisible,
    onCancel,
  })
  if (line) this._register("pnl", "line", line)
  return line
}
```

Key changes:
- Options object instead of chained setters
- `onCancel` passed in options (moved from component post-creation wiring)
- `align: "left"` and `editable: false` set explicitly
- `lineColor: "transparent"` hides the line (matches TV's `showLine: false`)
- Body and quantity border/background both set to grid color (TV used `bodyBackgroundColor: chartColors.grid`)
- `setQuantityColor` → `quantityTextColor` (old API used a non-standard setter name)

## Component — `pnl-handle.js`

### Current issues
- Manual `subscribeCoinraySymbolWillChange` / `unsubscribe` — should use `useSymbolChangeCleanup` hook
- Manual `needsRefreshPositionOnMarketUpdates` wiring — keep as-is (PnL-specific, not in other overlays)
- Post-creation `onCancel` wiring — move into `createPnlHandle` options
- Missing `useSymbolChangeCleanup` hook

### New structure

Follow `break-even.js` pattern:
1. `useSuperChart()` for `readyToDraw`, `chartController`, `chartColors`
2. `util.useImmutableCallback` for `clearPnlLine`
3. `useSymbolChangeCleanup(currentMarket, clearPnlLine)` for symbol change
4. Single `useEffect` for draw, gated on `readyToDraw`
5. Build `onCancel` as `OrderLineEventListener` object `{params: {}, callback: fn}` before passing to controller
6. Keep position refresh and `needsRefreshPositionOnMarketUpdates` wiring (PnL-specific)

### onCancel wiring

Current: component creates line, then calls `orderLine.onCancel({}, callback)`.
New: component builds `{params: {}, callback}` and passes to `createPnlHandle`. The controller passes it through to `createOrderLine` options.

This matches the storybook pattern where `onCancel` is an `OrderLineEventListener` object.
