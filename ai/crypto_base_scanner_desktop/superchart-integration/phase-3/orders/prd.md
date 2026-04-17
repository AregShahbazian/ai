---
id: sc-orders
---

# PRD: Orders — SuperChart Integration

## Overview

Reimplement all order chart overlays for SuperChart. Orders are the most complex overlay type — the TV implementation bundles all order types into two monolithic components (`orders.js` for submitted, `edit-orders.js` for editing). For SC, these are split into separate files per order type, with parent components that iterate orders and delegate rendering to type-specific children.

This PRD covers submitted (display-only) order handles, editing (interactive/draggable) order handles, entry conditions, entry expirations, and the creating/saving state. It follows the patterns established by price alerts (`sc-price-alerts`) and the PnL handle (`sc-pnl-handle`).

## Current Behavior (TradingView)

### Submitted orders (`orders.js`)

All submitted orders are rendered in a single component. It reads from three data sources and delegates to draw functions by type:

#### Smart orders (`openSmartOrders`)
- **TAKE_PROFIT** → watch order handle + profit target handle
- **STOP_LOSS / STOP_ORDER** → stop price handle
- **TRAILING_STOP_LIMIT / TRAILING_STOP_MARKET / TRAILING_STOP** → trigger price line + order price handle + stop price handle

#### Position orders (from `positions` with `smartSettings`)
For each position:
- **Entry orders** → each entry order's `externalId` maps to an `openOrders` item → regular order handle
- **Exit orders** → `externalOrderType` set to `TAKE_PROFIT` → TP handle with position percentage
- **Stop loss** → `externalOrderType` set to `STOP_LOSS` → stop loss handle, optionally with trailing trigger price line and cooldown cancel handle
- **Entry conditions** → price line (`drawPriceLine`) + time line (`drawTimeLine`) if condition is enabled and not yet active
- **Entry expirations** → price line + time line if expiration is enabled

#### Standalone orders (`openOrders` not linked to positions)
Regular order handles via `drawOrder`.

#### Creating orders (`creatingOrders`)
"Creating" text handles — saving state while order is being submitted to the exchange.

### Submitted order appearance

All submitted handles use `createPositionLine` (TV's display-only handle):

- **Body**: Solid side-colored background, white text (uppercased)
- **Quantity**: Label text with order info (side, amount, currency) — or "deleting..." during deletion
- **Line**: Dashed, controlled by `openOrdersShowLine` setting
- **Cancel button**: Visible when `openOrdersEnableCanceling` is on → dispatches `cancelOrder(order)`
- **onModify**: Dispatches `editOrder(order)` when `openOrdersEnableEditing` is on
- **Editable**: No — not draggable

#### Colors
| Order type | Buy side | Sell side |
|---|---|---|
| Regular order | `chartColors.openBuyOrder` (`#43B581`) | `chartColors.openSellOrder` (`#F15959` dark / `#F04747` light) |
| Stop price | `chartColors.stopBuyPrice` (`#43B581`) | `chartColors.stopSellPrice` (`#F15959` dark / `#F04747` light) |
| Trigger price line | `chartColors.triggerPrice` (`#204e8a` dark / `#00468c` light) | — |
| Error/pending status | Darkened 20% via `tinycolor.darken(20)` | — |

#### Entry conditions / expirations on positions (submitted)
- **Price**: Horizontal price line via `drawPriceLine` — `chartColors.triggerPrice` color, label text
- **Time**: Vertical time line via `drawTimeLine` — `chartColors.triggerPrice` color
- Both are **not interactive** in TV

### Editing orders (`edit-orders.js`)

All editing handles are rendered in a single component. Uses `createOrderLine` (TV's draggable handle).

#### Handle types
| Handle | What it controls | Left text | Right text |
|---|---|---|---|
| `createPriceHandle` | Entry/exit price | "{side} {amount}" | "{quoteAmount}" |
| `createStopHandle` | Stop price | "Stop" | "{side} {amount}" (with confirm) or "" |
| `createStopLossHandle` | Stop loss price | "Stop loss" | Fixed price or percentage |
| `createTriggerHandle` | Trigger price | "Trigger" | "Trigger" |
| `createStopTrailingHandle` | Trailing trigger price | "Trigger price" | Trailing percentage (if POSITION type) |
| `createStopDistanceHandle` | Trailing distance | "Distance" | — |
| `createTakeProfitHandle` | Take profit price | "TP #{index}: {amount}" | "{volumePercentage}%" |
| `createStopLimitHandle` | Stop limit other price | "Stop limit" | "{quoteAmount}" |
| `createCoolDownCancelHandle` | Emergency SL price | "Cancel price" | "{price}" |

#### Editing appearance
- **Body**: White background, side-colored text + border
- **Quantity**: Side-colored background, opacity reduced when invalid (`hex2rgba(color, 0.4)`)
- **Line**: Solid, shown
- **Editable**: Yes — draggable
- **onMove**: Updates the form price (`form.current.updatePrice(orderId, handle.getPrice())`)
- **onModify**: Submits the trade form (with optional confirmation modal)
- **onCancel**: Resets the trade form (`form.current.resetTradeForm(true)`)

#### Drawing logic
The component reads the trade form state and draws handles for:
1. Entry orders (filtered by entry type — single or ladder)
2. Exit orders (if exit ladder enabled)
3. Stop loss (if enabled)

Each order may produce multiple handles (e.g., a STOP_LOSS_LIMIT order produces both a stop handle and a price handle).

### Editing entry conditions (`edit-entry-conditions.js`)

- **Price condition**: Draggable handle via `createTriggerPriceHandle` — `chartColors.triggerPrice` color, `onMove` updates `entryCondition.price`
- **Time condition**: Vertical line via `drawTimeLine` — **not interactive** in TV
- Only drawn when `entryCondition.enabled` is true

### Editing entry expirations (`edit-entry-expirations.js`)

- **Price expiration**: Draggable handle via `createTriggerPriceHandle` — `chartColors.triggerPrice` color, `onMove` updates `entryExpiration.price`
- **Time expiration**: Vertical line via `drawTimeLine` — **not interactive** in TV
- Only drawn when `entryExpiration.enabled` is true

## Data Sources

### Open orders (Redux via `MarketTabDataContext.marketTradingInfo`)
| Field | Description |
|---|---|
| `openOrders` | Array of open exchange orders |
| `openSmartOrders` | Array of open smart orders (TP, SL, trailing) |

### Order object
- `externalId` — exchange order ID
- `side` — `BUY` or `SELL`
- `orderType` — `LIMIT`, `MARKET`, `STOP_LOSS_LIMIT`, `STOP_LOSS_MARKET`, `OCO`, `TRAILING_STOP_LIMIT`, `TRAILING_STOP_MARKET`, `TRAILING_TAKE_PROFIT`
- `status` — `OPEN`, `PENDING`, `ERROR`, `FAILED`, `CLOSED`, `CANCELED`
- `price`, `stopPrice`, `triggerPrice`, `remaining`
- `linkedOrderId`, `linkedOrderType` — links to position
- `externalOrderType` — set dynamically: `TAKE_PROFIT`, `STOP_LOSS`
- `positionPercentage`, `exitPriceType`, `coolDownCancelPrice`

### Smart order object
- `id`, `orderType` — `TAKE_PROFIT`, `STOP_LOSS`, `STOP_ORDER`, `TRAILING_STOP_LIMIT`, `TRAILING_STOP_MARKET`, `TRAILING_STOP`
- `status`, `side`, `triggerPrice`, `profitPrice`
- `orders` — array of child exchange orders
- `externalId` — exchange ID

### Positions (`MarketTabDataContext.marketPositions`)
- `id`, `status`
- `smartSettings.entryOrders[]` — `{externalId}`
- `smartSettings.exitOrders[]` — `{externalId, positionPercentage, pricePercentage}`
- `smartSettings.exitLadder` — `{exitPriceType, enabled}`
- `smartSettings.stopLoss` — `{enabled, externalId, protectionType, trailingPrice, exitPriceType, stopPercentage, coolDownEnabled, coolDown}`
- `smartSettings.entryCondition` — `{enabled, active, priceEnabled, price, timeEnabled, startAt}`
- `smartSettings.entryExpiration` — `{enabled, priceEnabled, price, timeEnabled, expiresAt}`

### Trade form state (Redux: `MarketTabsSelectors.selectActiveTradingTabTradeFormState`)
| Field | Description |
|---|---|
| `creatingOrders` | Array of orders being submitted (saving state) |
| `editingOrderIds` | Array of order IDs currently in edit mode |
| `deletingOrderIds` | Array of order IDs being deleted |

### Chart settings (Redux: `state.chartSettings`)
| Setting | Description |
|---|---|
| `openOrdersShow` | Master toggle for order visibility |
| `openOrdersShowLabels` | Whether label text is shown on handles |
| `openOrdersShowSide` | Whether side (Buy/Sell) is shown in labels |
| `openOrdersShowLine` | Whether the horizontal line is drawn |
| `openOrdersEnableEditing` | Whether clicking opens edit mode |
| `openOrdersEnableCanceling` | Whether cancel button is shown |

### Colors (from `chartColors`)
| Key | Description |
|---|---|
| `openBuyOrder` | Buy order color (`#43B581`) |
| `openSellOrder` | Sell order color (`#F15959` dark / `#F04747` light) |
| `stopBuyPrice` | Buy stop color (`#43B581`) |
| `stopSellPrice` | Sell stop color (`#F15959` dark / `#F04747` light) |
| `triggerPrice` | Trigger/condition price color (`#204e8a` dark / `#00468c` light) |

### Balance masking (Redux: `state.balances.hideAmounts`)
When `hideAmounts === BALANCES_MASKING.ALL`, amounts are replaced with `BALANCES_MASKED` constant.

## Requirements

### R1 — Submitted order handles

Submitted orders render as non-editable order-line handles at the order's price. Use `createOrderLine` from SuperChart (same API as price alerts).

- **Editable**: `false` — not draggable
- **Body**: Not shown (`isBodyVisible: false`) — matching price alerts pattern
- **Quantity**: Label text with order info, solid side-colored background, white text
- **Line**: Dashed, controlled by `openOrdersShowLine` setting. Hidden via `lineColor: transparent` when off.
- **Cancel button**: Visible when `openOrdersEnableCanceling` is on. Dispatches `cancelOrder(order)`.
- **onModify**: Dispatches `editOrder(order)` when `openOrdersEnableEditing` is on
- **Y-axis label**: Side-colored background, white text

### R2 — Editing order handles

Editing orders render as draggable order-line handles. Use `createOrderLine` from SuperChart.

- **Editable**: `true` — draggable
- **Body**: Visible — white background, side-colored text + border
- **Quantity**: Side-colored background (opacity reduced when invalid), white text
- **Line**: Solid, shown
- **onMoveEnd**: Controller updates form price via `this._tradeForm.updateXxx(orderId, newPrice)`
- **onModify**: Controller submits trade form (with optional confirmation modal)
- **onCancel**: Controller resets trade form via `this._tradeForm.resetTradeForm(true)`

### R3 — Creating orders (saving state)

When orders are being submitted to the exchange, display a "Creating" handle:

- **Body**: "Creating" text, side-colored background, white text
- **Editable**: `false`
- **No cancel button, no onModify**

This applies to any order type during submission — the `creatingOrders` array contains `{price, side}` objects.

### R4 — Entry conditions (submitted + editing)

**Submitted** (on positions):
- **Price condition**: Horizontal price line at condition price — `chartColors.triggerPrice` color, label "Entry Condition"
- **Time condition**: Vertical time line at `startAt` timestamp — `chartColors.triggerPrice` color
- Only drawn when `entryCondition.enabled && !entryCondition.active`

**Editing**:
- **Price condition**: Draggable order-line handle — `chartColors.triggerPrice` color, controller wires `onMoveEnd` to update `entryCondition.price` via `this._tradeForm`
- **Time condition**: Interactive vertical time line via `_createTimeLine` with `lock: false` — controller wires `onPressedMoveEnd` to update `entryCondition.startAt` via `this._tradeForm`. (TV renders this as non-interactive; SC makes it draggable.)

### R5 — Entry expirations (submitted + editing)

**Submitted** (on positions):
- **Price expiration**: Horizontal price line — `chartColors.triggerPrice` color, label "Entry Expiration"
- **Time expiration**: Vertical time line at `expiresAt` timestamp — `chartColors.triggerPrice` color
- Only drawn when `entryExpiration.enabled`

**Editing**:
- **Price expiration**: Draggable order-line handle — `chartColors.triggerPrice` color, controller wires `onMoveEnd` to update `entryExpiration.price` via `this._tradeForm`
- **Time expiration**: Interactive vertical time line with `lock: false` — controller wires `onPressedMoveEnd` to update `entryExpiration.expiresAt` via `this._tradeForm`. (TV renders this as non-interactive; SC makes it draggable.)

### R6 — Visibility gating

- Only draw when `openOrdersShow` is on
- Filter out orders with `editingOrderIds` from submitted view (avoid duplication with editing handles)
- Filter out canceled / closed orders
- Respect `openOrdersShowLabels`, `openOrdersShowSide`, `openOrdersShowLine` for label/line display
- Respect `openOrdersEnableEditing`, `openOrdersEnableCanceling` for interaction enablement

### R7 — Color logic

Colors are resolved by the chart-controller based on:
- **Order side** (`BUY` → buy color, `SELL` → sell color)
- **Handle type** (regular → `openXxxOrder`, stop → `stopXxxPrice`, trigger → `triggerPrice`)
- **Status** (error/pending → darkened 20%)

Components pass raw data objects (the order, smart order, or position) — the controller extracts side, type, and status internally to resolve colors. Components never pass extracted fields like `side`, `isStop`, or `status`.

### R8 — Deleting state

When an order's `externalId` is in `deletingOrderIds`, quantity text shows "deleting..." instead of the normal label.

### R9 — Follow overlay component patterns

Use `useDrawOverlayEffect(group, draw, deps)` per the standard overlay pattern (see `context.md`). This handles cleanup, `readyToDraw` guard, symbol change cleanup, and common deps (`readyToDraw`, `chartColors`, `language`) automatically. Components only provide:

- The overlay group (from `OverlayGroups`)
- The draw callback (calls `chartController.createXxx(data)`)
- Component-specific deps

For editing overlays that can unmount while drawn, return `clear` for unmount cleanup. For non-standard patterns (update-or-create, partial redraw), use `useOverlayDeps()` directly.

### R10 — Chart-controller methods

The chart-controller encapsulates all visual logic. Methods receive raw data objects — the controller internally extracts keys, prices, labels, colors, and wires callbacks.

**Submitted:**
- `createSubmittedEntryOrder(order, position)` — non-editable handle, side color, label, cancel/modify callbacks
- `createSubmittedExitOrder(order, position)` — TP handle with position percentage
- `createSubmittedStopLoss(order, position)` — stop-colored handle, optional trailing/cooldown handles
- `createSubmittedSmartOrder(smartOrder)` — standalone smart order handles (TP, SL, trailing)
- `createSubmittedStandaloneOrder(order)` — unlinked open order handle
- `createSubmittedEntryCondition(position)` — price line + time line for entry condition
- `createSubmittedEntryExpiration(position)` — price line + time line for entry expiration
- Reuse existing `_createTimeLine` for time lines

**Editing:**
- `createEditingEntryOrder(order)` — draggable handle, controller wires onMoveEnd/onModify/onCancel via `this._tradeForm`
- `createEditingExitOrder(order)` — draggable TP handle
- `createEditingStopLoss(order)` — draggable stop + trailing + cooldown handles
- `createEditingEntryCondition(entryCondition)` — draggable price handle + interactive time line
- `createEditingEntryExpiration(entryExpiration)` — draggable price handle + interactive time line
- Reuse `_createTimeLine` with `lock: false` for interactive time lines

**Creating:**
- `createCreatingOrder(creatingOrder)` — "Creating" text handle from `{price, side}` object

### R11 — Trade form integration (editing)

The editing components use the imperative trade form object (`form.current` from `dispatch(getInitializedTradeForm())`):

- **Owned by the edit-orders parent component** — not in chart context
- **Wired to controller via `setTradeForm`**: the parent calls `chartController.setTradeForm(form.current)` when the form is initialized. The controller owns all form callbacks (`updatePrice`, `updateStopPrice`, `resetTradeForm`, etc.) via `this._tradeForm` — children never receive form methods as props
- **Children pass raw data only**: each child passes the order/position object to the controller's `createEditingXxx()` method, and the controller internally wires `onMoveEnd`, `onModify`, `onCancel` callbacks using `this._tradeForm`
- **Reactivity**: form mutations trigger `onChange` → dispatch to Redux → selector re-render → effect re-runs
- The `TradeFormConfirmation` modal is rendered at the edit-orders parent level (or higher in `super-chart.js`)

## File Structure

### Design requirement: split by order type

The TV implementation bundles all order types into two monolithic components. For SC, these are split into separate files per order type. Parent components iterate orders and delegate rendering to type-specific children.

### Submitted overlays

```
overlays/orders/
  orders.js                         # Parent — iterates positions, openSmartOrders, openOrders
                                    #   Renders type-specific children, passing raw data objects as props
  entry-orders.js                   # Submitted entry order handles (from position.smartSettings.entryOrders)
  exit-orders.js                    # Submitted exit/TP order handles (from position.smartSettings.exitOrders)
  stop-loss-orders.js               # Submitted stop loss handles (from position.smartSettings.stopLoss)
  smart-orders.js                   # Standalone smart orders (TAKE_PROFIT, STOP_ORDER, TRAILING_STOP)
  standalone-orders.js              # Open orders not linked to positions
  creating-orders.js                # Saving state handles
  entry-conditions.js               # Price lines + time lines on positions
  entry-expirations.js              # Price lines + time lines on positions
```

**`orders.js` parent pattern:**
- Reads `positions`, `openSmartOrders`, `openOrders`, `creatingOrders`
- Iterates positions and renders `<EntryOrders>`, `<ExitOrders>`, `<StopLossOrders>`, `<EntryConditions>`, `<EntryExpirations>` for each position
- Renders `<SmartOrders>` for `openSmartOrders`
- Renders `<StandaloneOrders>` for unlinked `openOrders`
- Renders `<CreatingOrders>` for saving state
- Handles shared state: `editingOrderIds`, `deletingOrderIds`, chart settings

### Editing overlays

```
overlays/orders/
  edit-orders.js                    # Parent — holds form.current, wires it to controller via setTradeForm
                                    #   Renders type-specific children, passing raw order/position data as props
  edit-entry-orders.js              # Draggable entry order handles
  edit-exit-orders.js               # Draggable exit/TP handles
  edit-stop-loss.js                 # Draggable stop loss + trailing + cooldown handles
  edit-entry-conditions.js          # Draggable price handle + interactive time line
  edit-entry-expirations.js         # Draggable price handle + interactive time line
```

**`edit-orders.js` parent pattern:**
- Holds `form.current` ref and wires it to controller via `chartController.setTradeForm(form.current)`
- Reads `tradeForm` from Redux selector for reactivity
- Passes raw order/position data as props to children — no form callbacks
- Renders `TradeFormConfirmation` modal
- Each child owns its own overlay group (per-item for per-position children) for independent cleanup

### Overlay groups

Each component gets its own group via `useDrawOverlayEffect`. Per-position children (rendered once per position) **must use per-item groups** to avoid one instance's cleanup wiping another's overlays. Only singleton components use plain groups.

**Per-position children** (use `${OverlayGroups.xxx}-${position.id}`):

| Component | Group pattern |
|---|---|
| `entry-orders.js` | `` `${OverlayGroups.submittedEntryOrders}-${position.id}` `` |
| `exit-orders.js` | `` `${OverlayGroups.submittedExitOrders}-${position.id}` `` |
| `stop-loss-orders.js` | `` `${OverlayGroups.submittedStopLossOrders}-${position.id}` `` |
| `entry-conditions.js` | `` `${OverlayGroups.submittedEntryConditions}-${position.id}` `` |
| `entry-expirations.js` | `` `${OverlayGroups.submittedEntryExpirations}-${position.id}` `` |
| `edit-entry-orders.js` | `` `${OverlayGroups.editEntryOrders}-${position.id}` `` |
| `edit-exit-orders.js` | `` `${OverlayGroups.editExitOrders}-${position.id}` `` |
| `edit-stop-loss.js` | `` `${OverlayGroups.editStopLoss}-${position.id}` `` |
| `edit-entry-conditions.js` | `` `${OverlayGroups.editEntryConditions}-${position.id}` `` |
| `edit-entry-expirations.js` | `` `${OverlayGroups.editEntryExpirations}-${position.id}` `` |

**Singleton components** (plain groups):

| Component | Group |
|---|---|
| `smart-orders.js` | `OverlayGroups.submittedSmartOrders` |
| `standalone-orders.js` | `OverlayGroups.submittedStandaloneOrders` |
| `creating-orders.js` | `OverlayGroups.creatingOrders` |

## Incremental Implementation Plan

Each step is independently testable. Submitted + editing for each type are done together.

### Step 1: Entry conditions + expirations (submitted + editing)
Simplest scope. Reuses existing `createOrderLine` and `_createTimeLine`. Tests the parent→child pattern for both submitted and editing. Also proves SC's interactive time lines (draggable, unlike TV).

**Files:** `entry-conditions.js`, `entry-expirations.js`, `edit-entry-conditions.js`, `edit-entry-expirations.js`, plus wiring in parent stubs.

### Step 2: Creating orders
Simple "Creating" handle. Tests saving state pattern.

**Files:** `creating-orders.js`

### Step 3: Submitted entry orders
First real order type. Entry limit orders from positions — non-editable `createOrderLine` handles with side colors, labels, modify/cancel callbacks.

**Files:** `orders.js` (parent), `entry-orders.js`

### Step 4: Edit entry orders
Draggable entry price + stop handles. First use of `form.current` integration.

**Files:** `edit-orders.js` (parent), `edit-entry-orders.js`

### Step 5: Exit / take-profit orders (submitted + editing)
TP-specific labels with position percentage and profit target.

**Files:** `exit-orders.js`, `edit-exit-orders.js`

### Step 6: Stop loss orders (submitted + editing)
Stop loss handles with trailing trigger price, distance, cooldown cancel — most complex handle set.

**Files:** `stop-loss-orders.js`, `edit-stop-loss.js`

### Step 7: Smart orders (submitted only)
Standalone TAKE_PROFIT, STOP_ORDER, TRAILING_STOP from `openSmartOrders`.

**Files:** `smart-orders.js`

### Step 8: Standalone orders (submitted only)
Open orders not linked to positions.

**Files:** `standalone-orders.js`

## Non-Requirements

- No changes to Redux state shape, trade form actions, or order actions
- No changes to the trade form UI components
- No grid bot order handling (separate PRD — `sc-grid-bot-orders`)
- No replay mode order handling (Phase 5)
- No trigger condition overlays (not implemented in TV's orders.js either)
- No storybook stories — order handles use `createOrderLine` which is already proved
