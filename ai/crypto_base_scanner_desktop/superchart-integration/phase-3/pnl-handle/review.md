# Review: PnL Handle — SuperChart Integration

## Round 1: Handle not visible (2026-03-24)

### Bug 1: orderLine overlay template tree-shaken from Superchart build

**Root cause:** Superchart's `package.json` `sideEffects` only listed `**/*.css`. The `extension/index.ts` module calls `registerOverlay(orderLineTemplate)` as a side effect, but the bundler (Vite/Rollup) tree-shook it out. Result: `chart.createOverlay({name: 'orderLine'})` returned null because klinecharts didn't know the template.

**Fix:** Added `src/lib/extension/index.ts` to `sideEffects` in Superchart's `package.json`, then rebuilt.

**Files:** `$SUPERCHART_DIR/package.json`

### Bug 2: BigNumber passed as price to createOrderLine

**Root cause:** `currentPosition.openPrice` is a BigNumber object. The old chained-setter API happened to work because `.setPrice()` eventually coerced it, but the new options-object API passes it directly to `chart.createOverlay({points: [{value: price}]})` which expects a JS number. The overlay was created with `id` but rendered at an invalid position.

**Fix:** Added `_toPrice(value)` helper to ChartController using `util.toSafeNumber()`. Applied to all price entry points across all overlay methods (createPnlHandle, createTrade, createBreakEven, createBidAskLine, updateBidAskLine, updatePriceLine, _createBaseSegment, _createBaseBox).

**Files:** `chart-controller.js`

### Additional improvements (same round)

- **Text building moved to controller:** `createPnlHandle` and `createTrade` now build their display text internally instead of receiving pre-formatted text from the component.
- **Options-object pattern for all overlays:** `createBreakEven` and `createBidAskLine` converted from chained setters to options-object pattern, matching `createPnlHandle` and `createTrade`.

### Verification
- [x] PnL handle renders on chart with open position
- [ ] Body shows PnL in currency, quantity shows PnL percentage
- [ ] Toggle positionsShowPnl off — handle disappears
- [ ] Toggle positionsEnableCanceling — cancel button appears/disappears
- [ ] Switch symbols — handle clears and redraws
- [ ] With hideAmounts on — body shows ****
- [ ] Break-even line still renders correctly
- [ ] Bid/ask lines still render correctly
- [ ] Trade markers still render correctly
- [ ] Bases still render correctly
