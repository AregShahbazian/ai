# Review: Grid Bot Overlays — SuperChart Integration

## Step 1: Dual-chart layout

### Verification
1. ✅ Open a running grid bot's **overview** tab — both TV (top) and SC (bottom) render the same market with candles
2. ✅ Open grid bot **settings** tab (desktop) — both charts render, split 50/50 vertically
3. ✅ Open grid bot **settings** tab (mobile/collapsed) — toggle to chart view, both charts visible
4. ✅ Switch themes — SC chart updates theme
5. ✅ Resize the browser window — SC chart resizes correctly
6. ✅ Trading terminal SC chart still works (symbol/period sync unaffected by constructor guard)

## Step 2: Grid bot prices overlay

### Round 1 bugs

#### Bug 1: Upper/lower handles jump back after drag
**Root cause:** `onMoveEnd` was wired via `line.onMoveEnd()` using `line.getPrice()` to read the new price. SC's `getPrice()` returns the **original** price, not the dragged-to position. The new price comes from `event.overlay.points[0].value`. Additionally, `onMoveEnd` must be passed as a **constructor option** `{params, callback}`, not via the fluent API.
**Fix:** Use `_buildMoveEndCallback(onUpdate)` which reads `event.overlay.points[0].value` and passes it as a constructor option — matching the existing pattern used by all other draggable handles.

#### Bug 2: extendLeft/extendRight not working
**Root cause:** Code explicitly set `extendLeft: !!extendLeft` and `extendRight: !!extendRight`, turning `undefined` into `false` — overriding the SC defaults (both `true`).
**Fix:** Pass `extendLeft`/`extendRight` explicitly per handle type. Upper/lower: `extendLeft: false, extendRight: true`. SL/TP: defaults (both `true`).

#### Bug 3: Labels/colors in component instead of controller
**Root cause:** Component was passing `label`, `color`, `showLine` to a generic `createGridBotPriceHandle`. Violates the controller-owns-visuals pattern.
**Fix:** Replaced with four domain methods (`updateOrCreateGridBotUpperPrice`, etc.) that resolve i18n labels, colors, and extend settings internally. Component passes raw data only.

#### Bug 4: Handle labels not uppercase
**Fix:** Controller applies `.toUpperCase()` to label text in `_createGridBotHandle`. Added global requirement to phase-3 `prd.md` Known Issues.

#### Bug 5: TP/SL handles appear with ~10s delay, don't update when dragged in TV
**Root cause:** `stopLoss`/`takeProfit` are mutable class instances on the `botForm` singleton. `update()` mutates properties in place — the object reference never changes. React deps (`Object.is`) don't detect the mutation, so the effect doesn't re-run. TV avoids this by redrawing synchronously during render (no deps).
**Fix:** (a) Spread objects at the parent boundary: `stopLoss={{...botForm.stopLoss}}` in `grid-bot-settings.js`. (b) Use primitive deps in the effect: `stopLoss?.enabled`, `stopLoss?.price`, `takeProfit?.enabled`, `takeProfit?.price`.

### Verification
1. ✅ **Overview** tab — upper/lower handles visible (alert color), SL/TP visible if enabled, none are draggable
2. ✅ **Settings** tab — drag upper price handle in SC → form updates, handle stays at new position
3. ✅ **Settings** tab — drag lower price handle in SC → form updates, handle stays at new position
4. ✅ **Settings** tab — drag SL handle in SC → form updates, TV updates
5. ✅ **Settings** tab — drag TP handle in SC → form updates, TV updates
6. ✅ **Settings** tab — drag SL handle in TV → SC handle moves to match
7. ✅ **Settings** tab — drag TP handle in TV → SC handle moves to match
8. ✅ **Settings** tab — drag upper/lower in TV → SC handles move to match
9. ✅ Upper/lower: line extends right only. SL/TP: line extends both sides
10. ✅ All handle labels are uppercase
11. ✅ Enable SL/TP in form → handles appear in SC immediately. Disable → disappear immediately
12. ✅ TP/SL handles appear on initial load without delay
13. ✅ Compare handle positions against TV chart — same price levels
14. ✅ Switch themes — handle colors update

## Step 3: Grid bot orders overlay

### Verification
1. ✅ **Overview** tab — horizontal lines at each grid level, buy = green, sell = red, matching TV
2. ✅ **Overview** tab — y-axis price labels visible for each order line
3. ✅ **Settings** tab — order lines shown, update when price range or order count changes
4. ✅ **Settings** tab — compare SC order lines against TV — same positions, same colors
5. ✅ Order lines are non-interactive (no drag, no click) — **known issue:** PriceLine draggable bug, waiting for SC dev fix

## Step 4: Trades overlay

### Verification
1. ✅ **Overview** tab — buy/sell trade arrow markers visible on SC, matching TV positions
2. ✅ **Overview** tab — trade marker colors match TV (green buy, red sell)
3. ✅ **Settings** tab — no trade markers (no `trades` prop passed)
4. ✅ Trade markers respect chart settings (show prices, show quantities)
