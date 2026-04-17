# Review: Orders — SuperChart Integration

## Round 1: Step 1 bugs (2026-03-25)

### Bug 1: TradeFormConfirmation crash on mount

**Root cause:** `TradeFormConfirmation` reads `tradeForm` from `TradeFormContext`, which requires `TradeFormContextProvider` as an ancestor. The SC `EditOrders` component was missing this wrapper.
**Fix:** Wrapped `EditOrders` in `<TradeFormContextProvider>`, matching TV's `edit-orders.js` pattern.
**Files:** `edit-orders.js`

### Bug 2: Changing condition/expiration prices in form or TV doesn't update SC handles

**Root cause:** `form.current.entryCondition` is a mutable object — its fields get mutated in place rather than the object being replaced. The child's `useEffect` dep (`entryCondition`) uses `Object.is` comparison, sees the same reference, and skips the effect. The parent re-renders and the child re-renders, but the effect never re-runs.

TV avoids this because it draws inside the effect (no child components, no prop-based dep comparison).

**Fix:** Spread the mutable object when passing as props: `entryCondition={{...form.current.entryCondition}}`. This creates a new reference each render, so the child's effect detects the change. The parent only re-renders when `tradeForm` actually changes, so this doesn't cause unnecessary effect runs.

**Design note:** This shallow spread works for flat objects (entry conditions, expirations). For nested objects (e.g. stop loss with `coolDown`), nested spreads are needed: `{...stopLoss, coolDown: {...stopLoss.coolDown}}`. This is a trade-off of the split-by-type child component pattern vs TV's monolithic draw-in-effect approach.

**Files:** `edit-orders.js`

### Bug 3: Submitted entry condition/expiration time lines not rendered

**Root cause:** Timestamps stored in epoch seconds, SC expects milliseconds. Lines were drawn at 1970.
**Fix:** Multiply by 1000 when passing to controller, divide by 1000 in callbacks.
**Files:** `entry-conditions.js`, `entry-expirations.js`, `edit-entry-conditions.js`, `edit-entry-expirations.js` (later moved into controller methods)

### Bug 4: Edit condition/expiration handles don't clear on exit

**Root cause:** Child effects (`edit-entry-conditions.js`, `edit-entry-expirations.js`) didn't return a cleanup function. When the parent returns `null` on exit, children unmount but overlays stay on the chart.
**Fix:** Added `return clear` to both edit effects.
**Files:** `edit-entry-conditions.js`, `edit-entry-expirations.js`

### Verification
1. ✅ Changing entry condition price in trade form updates SC edit handle position
2. ✅ Changing entry expiration price in trade form updates SC edit handle position
3. ✅ Moving TV condition/expiration handle updates SC edit handle position
4. ✅ Dragging SC condition price handle updates trade form
5. ✅ Dragging SC condition time line updates trade form (SC-only feature)
6. ✅ Edit handles clear when exiting edit mode
7. ✅ Submitted condition/expiration price lines render
8. ✅ Submitted condition/expiration time lines render
9. TradeFormConfirmation modal works when submitting (N/A for step 1 — no submit-from-chart yet, testable in step 4)

## Round 2: Steps 2–3 bugs (2026-03-26)

### Bug 5: No "DELETING..." label on entry orders being deleted

**Root cause:** `entry-orders.js` effect deps were `[position, openOrders, editingOrderIds, chartColors]` — missing `deletingOrderIds` and `chartSettings`. When an order enters deleting state, the controller's `_isDeletingOrder` reads the new state, but the effect doesn't re-run to recreate the handle with the updated label.
**Fix:** Added `deletingOrderIds` and `chartSettings` to effect deps.
**Files:** `entry-orders.js`

### Bug 6: CREATING handles remain after orders complete or openOrdersShow toggled off

**Root cause:** `creating-orders.js` lacked a dedicated unmount cleanup effect and `useSymbolChangeCleanup`. The draw effect's `return clear` should handle unmount, but the component was missing robustness for edge cases.
**Fix:** Added explicit unmount effect (`useEffect(() => clear, [])`), `useSymbolChangeCleanup`, and `currentMarket` context.
**Files:** `creating-orders.js`

### Bug 7: Shared overlay group across multiple positions — deleting one position clears all

**Root cause:** All `EntryOrders` instances shared `OverlayGroups.submittedEntryOrders`. When one position is deleted and its `EntryOrders` unmounts, `clearOverlays("submittedEntryOrders")` wipes ALL positions' entry order handles. Other positions' components don't re-run (their deps didn't change), so their handles disappear permanently. Same issue existed for `EntryConditions` and `EntryExpirations`.

**Fix:** Per-position overlay groups: `${OverlayGroups.submittedEntryOrders}-${position.id}`. Each position's overlays are isolated — unmounting one doesn't affect others. Applied to `entry-orders.js`, `entry-conditions.js`, `entry-expirations.js` and their corresponding controller methods.

**Design note:** Any overlay component rendered per-item (per position, per order) must use per-item groups. Shared groups only work for singleton components (one instance at a time).

**Files:** `entry-orders.js`, `entry-conditions.js`, `entry-expirations.js`, `chart-controller.js`

### Bug 8: CREATING handles not cleared — key collision

**Root cause:** `createCreatingOrder` used `creating-${order.id || Date.now()}` as key. Creating orders may lack `id`, and `Date.now()` produces the same value within a tight loop. Multiple overlays get the same key — the registry Map overwrites previous entries, losing track of them. `clearOverlays` can't find the overwritten ones.
**Fix:** Fall back to `order.orderId` then `line.id` (overlay's own unique ID).
**Files:** `chart-controller.js`

### Bug 9: Buy orders shown in sell color

**Root cause:** `_getOrderColor` compared `side === "BUY"` (uppercase) but order data uses `"buy"` (lowercase).
**Fix:** Case-insensitive comparison via `side?.toLowerCase() === "buy"`.
**Files:** `chart-controller.js`

### Verification
1. ✅ Buy entry order → green handle
2. ✅ Sell entry order → red handle
3. ✅ Buy CREATING handle → green
4. ✅ Sell CREATING handle → red
5. ✅ Entry order handles show "DELETING..." when order is being canceled
6. ✅ CREATING handles disappear after orders are created on exchange
7. ✅ CREATING handles disappear when openOrdersShow is toggled off
8. ✅ Ladder orders (5 entries) all show and all clear correctly
9. ✅ Deleting ladder (5 orders) → all 5 clear, no stray handles remain
10. ✅ Deleting one position doesn't clear other positions' entry orders
11. ✅ Cancel button works on submitted entry orders
12. ✅ Click entry order handle → enters edit mode
13. ✅ Deleting ladder → ALL handles show "DELETING..." (SC improvement over TV)
14. ✅ Deleting/creating handles have no cancel button
15. ✅ Toggle `openOrdersShowLabels` off → quantity text + cancel button + stop/trigger handles hidden
16. ✅ Toggle `openOrdersShowSide` → side text appears/disappears in label
17. ✅ Toggle `openOrdersShowLine` → dashed line extends/hides
18. ✅ Toggle `openOrdersEnableEditing` off → clicking handle does nothing
19. ✅ Toggle `openOrdersEnableCanceling` off → no cancel button on handles
20. ✅ Toggle hideAmounts → amounts masked in entry order labels
21. ✅ Entry order with stop price → two handles (regular + stop colored)
22. ✅ Error/pending status order → darkened color
23. ✅ Switch market → all entry + saving handles clear
24. ✅ Enter edit mode → submitted handles for that position disappear

### Round 3: i18n + renames (2026-03-26)

- Translated: "SAVING", "DELETING...", "Break even", "Stop for {price}", "Buy"/"Sell", time label prefixes
- Renamed: createCreatingOrder → createSavingOrder, creating-orders.js → saving-orders.js
- i18n keys under `containers.trade.market.marketGrid.centerView.superChart.overlays.*`

#### Verification
1. ✅ Saving handle shows translated text
2. ✅ Deleting label shows translated text
3. ✅ Break even label shows translated text
4. ✅ Stop handle label shows translated "Stop for" text
5. ✅ Side text (Buy/Sell) shows translated text
6. ✅ Switch language → overlay texts update on next redraw

## Round 4: Steps 4–5 (2026-03-27)

### Bug 10: Dragging entry handle doesn't move TP handles along

**Root cause:** `EditEntryOrders` and `EditExitOrders` are separate components with independent effects. `form.current.exitOrders` is a mutable array — same reference after mutations, so the exit effect deps don't change when entry price is updated.
**Fix:** Both editing components now subscribe to `tradeForm` from Redux directly and include it in effect deps. Any form mutation redraws all editing handles.
**Files:** `edit-entry-orders.js`, `edit-exit-orders.js`

### Bug 11: Submitted trailing TP missing stop handle

**Root cause:** `createSubmittedExitOrder` only drew the main price handle — didn't check `stopPrice`/`triggerPrice` on the order. TV's generic `drawOrder` handles those for all order types including trailing TPs.
**Fix:** Added trigger price line + stop handle ("STOP FOR X.XX") logic to `createSubmittedExitOrder`, matching the pattern from `createSubmittedEntryOrder`.
**Files:** `chart-controller.js`

### Bug 12: Stop handle double-darkened when order has error/pending status

**Root cause:** SC applied darken(10) for same-color stop THEN darken(20) for status, producing `#a30e0e` instead of TV's `#F15959`. TV compares raw stopColor against the already status-adjusted order color — when status darkens the order color, the comparison fails, so stop uses its raw color without any darkening.
**Fix:** Restructured `_createSubmittedOrderHandle` to compute `statusAdjustedOrderColor` first, then compare raw stopColor against it. Matches TV's exact logic.
**Files:** `chart-controller.js`

### Verification
1. ✅ Limit entry + TP: drag limit handle → TP handle moves along (matches TV)
2. ✅ Drag TP handle → entry handle reflects any form recalculations
3. ✅ TP handles show correct labels: "TP #1: {amount} {currency}" + "{percentage}%"
4. ✅ Trailing TP enabled → both price handle + trailing price handle appear in edit mode
5. ✅ Submitted trailing TP → "STOP FOR X.XX" handle visible
6. ✅ Drag trailing TP handle → trailing price updates in form
7. ✅ Click modify → order submits (or confirmation modal)
8. ✅ Click cancel → form resets, handles disappear
9. ✅ Submitted TP handles show "TP 1: {amount} {currency} %{percentage}"
10. ✅ Delete TP order → shows "DELETING..." label
11. ✅ Toggle openOrdersShow off → submitted TP handles disappear
12. ✅ Enter edit mode → submitted TP handles for that position disappear

## Round 5: Step 6 — Stop loss orders (2026-03-27)

### Bug 13: Stop-limit SL missing limit price handle

**Root cause (submitted):** `createSubmittedStopLoss` only drew the stop handle — never checked `order.price` for the limit price. TV's `drawOrder` draws the limit price via the generic `price > 0 && externalOrderType !== TAKE_PROFIT` branch.
**Root cause (editing):** `createEditingEntryOrder`'s STOP_LOSS_LIMIT case read `order.price`, but StopLoss form objects store the limit price as `order.limitPrice`.
**Fix (submitted):** Added limit price handle when `price > 0` in `createSubmittedStopLoss`.
**Fix (editing):** Read `order.limitPrice || order.price` in the STOP_LOSS_LIMIT case. Merged STOP_LOSS_LIMIT/MARKET cases with fallthrough for shared protection + cooldown logic.
**Files:** `chart-controller.js`

### Verification
1. ✅ Submitted STOP_LOSS_MARKET → stop-colored handle with "Stop Loss: {price}" or "Stop Loss: {percentage}%"
2. ✅ Submitted STOP_LOSS_LIMIT → TWO handles: limit price (order color) + stop price (stop color)
3. ✅ Trailing stop loss (protectionType PRICE) → trigger price line visible
4. ✅ Cooldown cancel enabled → "Emergency SL" handle visible
5. ✅ Edit STOP_LOSS_MARKET → draggable stop handle appears
6. ✅ Edit STOP_LOSS_LIMIT → draggable stop handle + limit price handle appear
7. ✅ Drag stop handle → stop price updates in form
8. ✅ Drag limit price handle → limit price updates in form
9. ✅ Trailing protection → trailing price + distance handles appear in edit mode
10. ✅ Cooldown cancel → cancel price handle appears in edit mode
11. ✅ Drag trailing/distance/cancel handles → respective form fields update
12. ✅ Click modify → order submits
13. ✅ Click cancel → form resets, handles disappear
14. ✅ Delete stop loss order → shows "DELETING..." label
15. ✅ Toggle openOrdersShow off → submitted stop loss handles disappear
16. ✅ Enter edit mode → submitted stop loss handles for that position disappear
17. ✅ Moving entry/TP handles → stop loss handles redraw correctly

## Round 6: Steps 7–8 — Smart orders + standalone orders (2026-03-27)

### How to reproduce

**Standalone orders (step 8):** Place an order directly on the exchange platform (e.g. Binance web → Trade → place a limit order). These are non-smart orders not created through Altrady's position system — they appear in `openOrders` but aren't linked to any position.

**Smart orders (step 7):** `openSmartOrders` contains stop-market orders for exchanges that don't natively support stop-market order types. Altrady emulates them server-side as smart orders. To reproduce: use an exchange without native stop-market support and place a stop-market order through Altrady.

### Verification — Standalone orders (step 8)
1. ✅ Place a limit order on Binance platform (not through Altrady) → handle appears on SC chart
2. ✅ Standalone order with stop price → two handles (price + stop)
3. ✅ Click handle → enters edit mode
4. ✅ Cancel button → cancels order
5. ✅ Toggle openOrdersShow off → handle disappears
6. ✅ Delete standalone order → shows "DELETING..." label
7. ✅ Standalone order NOT shown if linked to a position (rendered by entry/exit/stop-loss components instead)

### Verification — Smart orders (step 7)
8. ✅ Smart stop-market order on exchange without native support → stop-colored handle visible on SC chart
9. ✅ Smart trailing stop → trigger price line + price handle + stop handle
10. ✅ Click smart order handle → enters edit mode
11. ✅ Toggle openOrdersShow off → smart order handles disappear
