# Tasks: Orders — SuperChart Integration

## Step 1: Entry Conditions + Expirations

### Task 1.1: Chart-controller — trigger price line + editing trigger handle

**File:** `chart-controller.js`

**Changes:**
- Add `_getOrderColor(side, isStop)` helper
- Add `_getStatusColor(color, status)` helper
- Add `createTriggerPriceLine(group, key, price, labelText)` — uses `createPriceLine`, trigger color, label
- Add `createEditingTriggerHandle(group, key, price, {bodyText, quantityText, onMoveEnd, onModify, onCancel})` — uses `createOrderLine`, trigger color, editable

**Verify:** Methods exist, no syntax errors.

### Task 1.2: Create `entry-conditions.js` (submitted)

**File:** `overlays/orders/entry-conditions.js` (new)

**Changes:**
- Receives `position` as prop from parent
- Reads `position.smartSettings.entryCondition`
- If `enabled && !active && priceEnabled` → `createTriggerPriceLine` at condition price
- If `enabled && !active && timeEnabled` → `_createTimeLine` with `lock: true` at `startAt`
- Overlay group: `"submittedEntryConditions"`
- Uses `useSymbolChangeCleanup`

**Verify:**
1. Position with entry condition → price line + time line appear
2. Active condition → lines don't appear
3. Symbol change → lines clear

### Task 1.3: Create `entry-expirations.js` (submitted)

**File:** `overlays/orders/entry-expirations.js` (new)

**Changes:**
- Same pattern as entry-conditions but reads `entryExpiration`
- If `enabled && priceEnabled` → `createTriggerPriceLine` at expiration price, label "Entry Expiration"
- If `enabled && timeEnabled` → `_createTimeLine` with `lock: true` at `expiresAt`
- Overlay group: `"submittedEntryExpirations"`

**Verify:** Same as 1.2 but for expirations.

### Task 1.4: Create `edit-entry-conditions.js` (editing)

**File:** `overlays/orders/edit-entry-conditions.js` (new)

**Changes:**
- Receives `entryCondition`, `updateEntryCondition`, `resetTradeForm`, `handleSubmitTradeForm` as props
- If `priceEnabled` → `createEditingTriggerHandle` with `onMoveEnd` that calls `updateEntryCondition({...entryCondition, price: newPrice})`
- If `timeEnabled` → `_createTimeLine` with `lock: false` and `onPressedMoveEnd` that calls `updateEntryCondition({...entryCondition, startAt: newTimestamp})`
- Overlay group: `"editEntryConditions"`

**Verify:**
1. Edit a position with entry condition → price handle + time line appear
2. Drag price handle → condition price updates in form
3. Drag time line → condition startAt updates in form (SC improvement over TV)
4. Cancel → form resets

### Task 1.5: Create `edit-entry-expirations.js` (editing)

**File:** `overlays/orders/edit-entry-expirations.js` (new)

**Changes:**
- Same pattern as edit-entry-conditions but for `entryExpiration`
- `onMoveEnd` calls `updateEntryExpiration({...entryExpiration, price: newPrice})`
- Time line `onPressedMoveEnd` calls `updateEntryExpiration({...entryExpiration, expiresAt: newTimestamp})`
- Overlay group: `"editEntryExpirations"`

**Verify:** Same as 1.4 but for expirations.

### Task 1.6: Create parent stubs + wiring

**Files:**
- `overlays/orders/orders.js` (new) — stub parent, only renders `EntryConditions` + `EntryExpirations` for now
- `overlays/orders/edit-orders.js` (new) — stub parent, only renders `EditEntryConditions` + `EditEntryExpirations` for now
- `super-chart.js` — import and render `<Orders/>` and `<EditOrders/>`

**Verify:**
1. Both submitted and editing conditions/expirations render on SC chart
2. No errors when no positions or no conditions

---

## Step 2: Creating Orders

### Task 2.1: Chart-controller — creating order method

**File:** `chart-controller.js`

**Changes:**
- Add `createCreatingOrder(key, price, side)` — "CREATING" body text, side-colored, non-editable

**Verify:** Method exists, no syntax errors.

### Task 2.2: Create `creating-orders.js`

**File:** `overlays/orders/creating-orders.js` (new)

**Changes:**
- Receives `orders` (creatingOrders array) as prop from parent
- Each order: `chartController.createCreatingOrder(key, +order.price, order.side)`
- Overlay group: `"creatingOrders"`

**Verify:**
1. Submit a new order → "CREATING" handle appears at the order's price
2. Order created → handle disappears
3. Buy = green, Sell = red

### Task 2.3: Wire into `orders.js` parent

**File:** `overlays/orders/orders.js`

**Changes:**
- Read `creatingOrders` from `MarketTabsSelectors.selectActiveTradingTabTradeFormState`
- Render `<CreatingOrders orders={creatingOrders} />`

---

## Step 3: Submitted Entry Orders

### Task 3.1: Chart-controller — submitted order method

**File:** `chart-controller.js`

**Changes:**
- Add `createSubmittedOrder(group, key, price, {side, isStop, status, quantityText, showLine, onModify, onCancel})`
- Non-editable, side-colored, dashed line, quantity label
- Matches `createPriceAlert` pattern but with side-based colors

**Verify:** Method exists, no syntax errors.

### Task 3.2: Create `entry-orders.js` (submitted)

**File:** `overlays/orders/entry-orders.js` (new)

**Changes:**
- Receives `position`, `openOrders`, `editingOrderIds`, `deletingOrderIds`, `chartSettings`, `hideAmounts`, `currentMarket` as props
- Iterates `position.smartSettings.entryOrders`
- For each: find matching order in `openOrders` by `externalId`
- Skip if in `editingOrderIds`, canceled, or closed
- Build label: `"{side} {remaining} {baseCurrency}"` (respecting `openOrdersShowSide`, `hideAmounts`)
- Build stop label if `stopPrice > 0`
- Call `chartController.createSubmittedOrder("submittedEntryOrders", key, price, {...})`
- Add onModify/onCancel per chart settings
- Handle `triggerPrice` → `createTriggerPriceLine`
- Handle `stopPrice` → second handle with `isStop: true`
- Overlay group: `"submittedEntryOrders"`

**Verify:**
1. Position with entry limit order → handle appears at correct price
2. Click handle → enters edit mode
3. Cancel button → cancels order
4. Order with stop → stop handle also appears
5. Toggle `openOrdersShow` off → handles disappear

### Task 3.3: Wire into `orders.js` parent

**File:** `overlays/orders/orders.js`

**Changes:**
- Full parent implementation: read all data sources, iterate positions
- Render `<EntryOrders>` for each position
- Pass shared props

---

## Step 4: Edit Entry Orders

### Task 4.1: Chart-controller — editing entry order method

**File:** `chart-controller.js`

**Changes:**
- Add `createEditingEntryOrder(order)` — receives raw order object
  - Extracts price, side, orderType, stopPrice, triggerPrice from the order
  - Builds label text internally (using `this._currentMarket` for currency, `this.chartSettings` for label options)
  - By `orderType`: LIMIT → price handle, STOP_LOSS_LIMIT → stop + price handles, STOP_LOSS_MARKET → stop loss handle, OCO → stop + price + stop-limit handles, TRAILING_STOP_LIMIT → trigger + stop + price, TRAILING_STOP_MARKET → trigger + stop
  - Wires `onMoveEnd` → `this._tradeForm.updatePrice(orderId, newPrice)` (or `updateStopPrice`, `updateTriggerPrice`, `updateOtherPrice` as appropriate)
  - Wires `onModify` → submit via `this._tradeForm` / dispatch
  - Wires `onCancel` → `this._tradeForm.resetTradeForm(true)`
- Uses internal `_createEditingOrderLine` helper for shared handle styling
- Handles protection type PRICE → trailing handle + distance handle via `this._tradeForm.updateStopTrailingPrice()` / `updateStopTrailingDistance()`
- Handles cooldown cancel via `this._tradeForm.updateCoolDownCancelPrice()`

**Verify:** Method exists, no syntax errors.

### Task 4.2: Create `edit-entry-orders.js` (editing)

**File:** `overlays/orders/edit-entry-orders.js` (new)

**Changes:**
- Receives `orders`, `entrySide`, `entryType` as props — **no form methods**
- Uses `useDrawOverlayEffect(OverlayGroups.editEntryOrders, (clear) => {...}, deps)`
- For each order (filtered by status !== "closed"):
  - Calls `chartController.createEditingEntryOrder(order)` — controller handles everything
- Returns `clear` for unmount cleanup
- Overlay group: `OverlayGroups.editEntryOrders`

**Verify:**
1. Edit a limit order → price handle appears, draggable
2. Drag → price updates in trade form
3. Click modify (checkmark) → order submitted
4. Cancel → form resets
5. Edit a stop-limit → both stop and price handles appear

### Task 4.3: Wire into `edit-orders.js` parent

**File:** `overlays/orders/edit-orders.js`

**Changes:**
- Wire `chartController.setTradeForm(form.current)` in the form init effect
- Read tradeForm from Redux, initialize form on change
- Render `<EditEntryOrders orders={displayEntryOrders} entrySide={entrySide} entryType={entryType} />` — raw data only, no form callbacks
- Render `<TradeFormConfirmation>` modal

---

## Step 5: Exit / Take-Profit Orders

### Task 5.1: Create `exit-orders.js` (submitted)

**File:** `overlays/orders/exit-orders.js` (new)

**Changes:**
- Receives `position`, `openOrders`, shared props (editingOrderIds, deletingOrderIds, chartSettings, hideAmounts)
- Uses `useDrawOverlayEffect` with per-position group: `` `${OverlayGroups.submittedExitOrders}-${position.id}` ``
- Iterates `position.smartSettings.exitOrders`, passes each order to `chartController.createSubmittedExitOrder(order, position)`
- Controller extracts price, builds TP label, sets `externalOrderType = TAKE_PROFIT`

**Verify:**
1. Position with exit orders → TP handles appear with percentage labels
2. Click → enters edit mode

### Task 5.2: Create `edit-exit-orders.js` (editing)

**File:** `overlays/orders/edit-exit-orders.js` (new)

**Changes:**
- Receives `orders` (exit orders) as props — **no form methods**
- Uses `useDrawOverlayEffect(OverlayGroups.editExitOrders, (clear) => {...}, deps)`, returns `clear`
- For each order: `chartController.createEditingExitOrder(order)` — controller wires callbacks via `this._tradeForm`

**Verify:**
1. Edit position with exit ladder → TP handles appear
2. Drag → price updates
3. Trailing TP → both trigger and price handles

### Task 5.3: Wire into parents

- `orders.js` — render `<ExitOrders>` per position
- `edit-orders.js` — render `<EditExitOrders orders={exitOrders} />` when `exitLadder.enabled`

---

## Step 6: Stop Loss Orders

### Task 6.1: Create `stop-loss-orders.js` (submitted)

**File:** `overlays/orders/stop-loss-orders.js` (new)

**Changes:**
- Receives `position`, `openOrders`, shared props
- Uses `useDrawOverlayEffect` with per-position group: `` `${OverlayGroups.submittedStopLossOrders}-${position.id}` ``
- Calls `chartController.createSubmittedStopLoss(order, position)` — controller extracts stopLoss settings, builds label, handles trailing/cooldown sub-handles internally

**Verify:**
1. Position with stop loss → stop handle appears
2. With trailing → trigger price line appears
3. With cooldown → emergency SL handle appears

### Task 6.2: Create `edit-stop-loss.js` (editing)

**File:** `overlays/orders/edit-stop-loss.js` (new)

**Changes:**
- Receives `stopLoss` as prop (spread at parent boundary) — **no form methods**
- Uses `useDrawOverlayEffect(OverlayGroups.editStopLoss, (clear) => {...}, deps)`, returns `clear`
- Calls `chartController.createEditingStopLoss(stopLoss)` — controller wires callbacks via `this._tradeForm` (updateStopPrice, updateStopTrailingPrice, updateStopTrailingDistance, updateCoolDownCancelPrice)

**Verify:**
1. Edit position with stop loss → stop handle appears
2. Drag → stop price updates
3. Trailing stop → trailing + distance handles appear

### Task 6.3: Wire into parents

- `orders.js` — render `<StopLossOrders>` per position
- `edit-orders.js` — render `<EditStopLoss stopLoss={{...stopLoss, coolDown: {...stopLoss.coolDown}}} />` when `stopLoss.enabled`

---

## Step 7: Smart Orders

### Task 7.1: Create `smart-orders.js` (submitted)

**File:** `overlays/orders/smart-orders.js` (new)

**Changes:**
- Receives `smartOrders` (openSmartOrders), shared props
- Uses `useDrawOverlayEffect(OverlayGroups.submittedSmartOrders, ...)` — singleton, plain group
- For each smart order: `chartController.createSubmittedSmartOrder(smartOrder)` — controller handles orderType routing (TP, SL, trailing), builds sub-handles internally
- Skip orders in `editingOrderIds`

**Verify:**
1. Smart TP order → two handles (watch + target)
2. Smart stop order → stop handle
3. Trailing stop → trigger line + handles
4. Click → edit mode

### Task 7.2: Wire into `orders.js` parent

Already done in step 3 — just uncomment/add `<SmartOrders>` rendering.

---

## Step 8: Standalone Orders

### Task 8.1: Create `standalone-orders.js` (submitted)

**File:** `overlays/orders/standalone-orders.js` (new)

**Changes:**
- Receives `openOrders`, `positions`, shared props
- Uses `useDrawOverlayEffect(OverlayGroups.submittedStandaloneOrders, ...)` — singleton, plain group
- Filter: orders NOT linked to any position
- Skip edited, canceled, closed orders
- For each: `chartController.createSubmittedStandaloneOrder(order)` — controller handles price/stop/trigger sub-handles

**Verify:**
1. Standalone limit order → handle appears
2. Order linked to position → NOT rendered here (rendered by entry/exit/stop children)
3. Click → edit mode

### Task 8.2: Wire into `orders.js` parent

Already done in step 3 — just uncomment/add `<StandaloneOrders>` rendering.
