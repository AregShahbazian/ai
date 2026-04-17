# Design: Orders — SuperChart Integration

## Approach

This follows the 8-step incremental plan from the PRD. The design covers shared patterns first, then step-specific details.

### Files overview

**Chart controller additions** (`chart-controller.js`):
- Submitted order methods
- Editing order methods
- Creating order method
- Trigger price line method

**Submitted overlays** (`overlays/orders/`):
- `orders.js` — parent iterator
- `entry-orders.js`, `exit-orders.js`, `stop-loss-orders.js` — position-linked
- `smart-orders.js`, `standalone-orders.js` — non-position
- `creating-orders.js` — saving state
- `entry-conditions.js`, `entry-expirations.js` — condition/expiration lines

**Editing overlays** (`overlays/orders/`):
- `edit-orders.js` — parent (form.current, submission, confirmation modal)
- `edit-entry-orders.js`, `edit-exit-orders.js`, `edit-stop-loss.js` — order handles
- `edit-entry-conditions.js`, `edit-entry-expirations.js` — condition/expiration handles

**Wiring** (`super-chart.js`):
- Import and render `<Orders/>` and `<EditOrders/>`
- Parents handle rendering their children internally

## Chart Controller Methods

### Principles

Controller methods receive **raw data objects** (order, position, entryCondition, etc.) — never extracted fields. The controller internally:
- Extracts keys, prices, side, status, labels
- Resolves colors from `this.colors` based on side/type/status
- Wires callbacks via `this._tradeForm` (for editing) or Redux dispatch (for submitted)
- Registers overlays in the correct group

### Color resolution helpers (internal)

```js
_getOrderColor(side, isStop = false) {
  if (isStop) {
    return side?.toLowerCase() === "buy" ? this.colors.stopBuyPrice : this.colors.stopSellPrice
  }
  return side?.toLowerCase() === "buy" ? this.colors.openBuyOrder : this.colors.openSellOrder
}

_getStatusColor(color, status) {
  if (["PENDING", "ERROR", "FAILED"].includes(status?.toUpperCase())) {
    return tinycolor(color).darken(20).toString()
  }
  return color
}
```

### Implemented methods (steps 1–3)

These take raw data objects, matching the PRD's R10 pattern:

- `createSubmittedEntryOrder(order, positionId, {deleting} = {})` — non-editable handle, side color, label, cancel/modify callbacks. Controller extracts price, side, status, stopPrice, triggerPrice from the order object.
- `createSavingOrder(order)` — "SAVING" body text, side-colored, non-editable. Extracts price/side from order.
- `createSubmittedEntryConditions(position)` — price line + time line. Extracts `position.smartSettings.entryCondition`.
- `createSubmittedEntryExpirations(position)` — price line + time line. Extracts `position.smartSettings.entryExpiration`.
- `createEditingEntryConditions(entryCondition)` — draggable price handle + interactive time line. Wires callbacks via `this._tradeForm`.
- `createEditingEntryExpirations(entryExpiration)` — same pattern for expirations.

### Internal helpers

- `_createTriggerPriceLine(group, key, price)` — horizontal dashed line in trigger color
- `_createEditingTriggerPriceLine(group, key, price, {bodyText, quantityText, onMoveEnd, onModify, onCancel})` — editable trigger handle
- `_createTimeLine` — vertical time line, `lock: true` for submitted, `lock: false` for editing (draggable)
- `_createSubmittedOrderLine(group, key, order, {isStop, quantityText})` — shared submitted handle builder, resolves color from order.side/status
- `_createEditingOrderLine(group, key, price, {side, isStop, isValid, bodyText, quantityText, onMoveEnd, onModify, onCancel})` — shared editing handle builder

### Planned methods (steps 4–8)

Following the same raw-data-objects pattern:

- `createEditingEntryOrder(order)` — draggable handle(s) based on orderType. Controller wires `onMoveEnd` to `this._tradeForm.updatePrice()`, `onModify` to submit, `onCancel` to reset.
- `createSubmittedExitOrder(order, position)` — TP handle with position percentage
- `createEditingExitOrder(order)` — draggable TP handle
- `createSubmittedStopLoss(order, position)` — stop-colored handle, optional trailing/cooldown
- `createEditingStopLoss(order)` — draggable stop + trailing + cooldown handles
- `createSubmittedSmartOrder(smartOrder)` — standalone smart order handles
- `createSubmittedStandaloneOrder(order)` — unlinked open order handle

## Parent Component Patterns

### Submitted parent (`orders.js`)

```js
const Orders = () => {
  const {readyToDraw, chartController, chartColors} = useSuperChart()
  const {marketTradingInfo, marketPositions} = useContext(MarketTabDataContext)
  const {currentMarket} = useContext(MarketTabContext)
  const chartSettings = useSelector(state => state.chartSettings)
  const {creatingOrders, editingOrderIds, deletingOrderIds} = useSelector(
    MarketTabsSelectors.selectActiveTradingTabTradeFormState
  )
  const hideAmounts = useSelector(state => state.balances.hideAmounts === BALANCES_MASKING.ALL)

  if (!readyToDraw || !chartSettings.openOrdersShow) return null

  const {openOrders, openSmartOrders} = marketTradingInfo || EMPTY_MARKET_TRADING_INFO
  const positions = (marketPositions || []).filter(p => !["closed", "canceled"].includes(p.status))

  // Determine which position is being edited (to skip its submitted orders)
  const firstEditingOrder = openOrders.find(({externalId}) => editingOrderIds.includes(externalId))
  const editingPositionId = firstEditingOrder?.linkedOrderType === "SmartPosition"
    ? firstEditingOrder.linkedOrderId : undefined

  // Shared props for all children
  const shared = {editingOrderIds, deletingOrderIds, chartSettings, hideAmounts, currentMarket}

  return <>
    {positions
      .filter(p => p.id.toString() !== editingPositionId)
      .map(position => (
        <React.Fragment key={position.id}>
          <EntryOrders position={position} openOrders={openOrders} {...shared} />
          <ExitOrders position={position} openOrders={openOrders} {...shared} />
          <StopLossOrders position={position} openOrders={openOrders} {...shared} />
          <EntryConditions position={position} />
          <EntryExpirations position={position} />
        </React.Fragment>
      ))
    }
    <SmartOrders smartOrders={openSmartOrders} {...shared} />
    <StandaloneOrders openOrders={openOrders} positions={positions} {...shared} />
    <CreatingOrders orders={creatingOrders} />
  </>
}
```

Key decisions:
- Parent handles `readyToDraw` and `openOrdersShow` gating — children don't need to check
- Position filtering (closed, editing) done in parent
- `editingOrderIds` filtering passed to children — each child skips orders being edited
- `useSymbolChangeCleanup` is per-child (each owns its overlay group)
- Parent does NOT own overlay groups — it's a pure data router

### Editing parent (`edit-orders.js`)

```js
const EditOrders = () => {
  const {readyToDraw, chartController, chartColors} = useSuperChart()
  const {currentMarket} = useContext(MarketTabContext)
  const tradeForm = useSelector(MarketTabsSelectors.selectActiveTradingTabTradeFormState)
  const {autoConfirmOrders} = useSelector(MarketTabsSelectors.selectTradeFormSettings)
  const dispatch = useDispatch()
  const form = useRef()
  const [showConfirmModal, setShowConfirmModal] = useState(false)

  const handleSubmitTradeForm = useCallback((ignoreConfirm = false) => {
    if (!ignoreConfirm && !autoConfirmOrders) {
      setShowConfirmModal(true)
      return
    }
    const tradeForm = dispatch(getInitializedTradeForm())
    const {formValid, isSubmitting} = tradeForm
    if (!formValid || isSubmitting) return
    setTimeout(() => {
      tradeForm.updateSubmitting(true)
      dispatch(_handleSubmitTradeForm(tradeForm))
    }, 200)
  }, [autoConfirmOrders])

  useEffect(() => {
    form.current = dispatch(getInitializedTradeForm())
    form.current.onChange((state) => dispatch(updateAndSaveTradeForm(state)))
    chartController?.setTradeForm(form.current)
  }, [tradeForm])

  if (!readyToDraw || !form.current?.edited) return null

  const {entryType, entryOrders, exitOrders, exitLadder, stopLoss, entrySide} = form.current

  // Filter entry orders for display
  const displayEntryOrders = entryType === "LADDER" || entryOrders.length === 0
    ? entryOrders : [entryOrders[0]]

  return <>
    <EditEntryOrders orders={displayEntryOrders} entrySide={entrySide} entryType={entryType} />
    {exitLadder.enabled && <EditExitOrders orders={exitOrders} />}
    {stopLoss.enabled && <EditStopLoss stopLoss={{...stopLoss, coolDown: {...stopLoss.coolDown}}} />}
    {form.current.entryCondition.enabled &&
      <EditEntryConditions entryCondition={{...form.current.entryCondition}} />}
    {form.current.entryExpiration.enabled &&
      <EditEntryExpirations entryExpiration={{...form.current.entryExpiration}} />}
    <TradeFormConfirmation
      isOpen={showConfirmModal}
      onConfirm={() => { setShowConfirmModal(false); handleSubmitTradeForm(true) }}
      onCancel={() => setShowConfirmModal(false)}
    />
  </>
}
```

Key decisions:
- `form.current` is initialized in an effect that depends on `tradeForm` (Redux selector)
- **Controller owns all form callbacks** via `chartController.setTradeForm(form.current)` — children never receive form methods as props
- Children receive only raw data (orders, stopLoss, entryCondition, etc.)
- Mutable objects are spread at the parent→child boundary (`{...form.current.entryCondition}`) to trigger effect deps
- `readyToDraw` and `edited` gating in parent — children can assume they should render
- `TradeFormConfirmation` rendered at parent level

## Child Component Pattern (submitted)

Each submitted child uses `useDrawOverlayEffect` and passes raw data to the controller:

```js
const EntryOrders = ({position, openOrders, editingOrderIds, deletingOrderIds, chartSettings, hideAmounts}) => {
  const {chartController} = useSuperChart()

  useDrawOverlayEffect(`${OverlayGroups.submittedEntryOrders}-${position.id}`, () => {
    const {smartSettings} = position
    if (!smartSettings) return

    smartSettings.entryOrders.forEach(entryOrder => {
      const order = openOrders.find(o => o.externalId === entryOrder.externalId)
      if (!order || editingOrderIds.includes(order.externalId)) return
      const anyDeleting = deletingOrderIds.includes(order.externalId)
      chartController.createSubmittedEntryOrder(order, position.id, {deleting: anyDeleting})
    })
  }, [position, openOrders, editingOrderIds, deletingOrderIds, chartSettings, hideAmounts])

  return null
}
```

Key: `useDrawOverlayEffect` handles cleanup, readyToDraw guard, symbol change cleanup, and common deps (`readyToDraw`, `chartColors`, `language`) automatically. Per-position group avoids cross-instance cleanup.

## Child Component Pattern (editing)

Each editing child uses `useDrawOverlayEffect` with `return clear` for unmount cleanup. Children pass raw data to the controller — **no form methods as props**. The controller wires callbacks internally via `this._tradeForm`.

```js
const EditEntryOrders = ({orders, entrySide, entryType}) => {
  const {chartController} = useSuperChart()

  useDrawOverlayEffect(OverlayGroups.editEntryOrders, (clear) => {
    orders.forEach(order => {
      if (order.status === "closed") return
      chartController.createEditingEntryOrder(order)
    })
    return clear
  }, [orders, entrySide, entryType])

  return null
}
```

Key: the controller's `createEditingEntryOrder(order)` internally extracts price, side, orderType, builds labels, and wires `onMoveEnd` → `this._tradeForm.updatePrice()`, `onModify` → submit, `onCancel` → reset.

## Entry Conditions / Expirations (Step 1 detail)

### Submitted entry conditions (`entry-conditions.js`)

Renders price line + time line for each position with an active entry condition. Passes raw `position` to controller.

```js
// Props: position (from parent)
useDrawOverlayEffect(`${OverlayGroups.submittedEntryConditions}-${position.id}`, () => {
  chartController.createSubmittedEntryConditions(position)
}, [position])
```

The controller's `createSubmittedEntryConditions(position)` extracts `position.smartSettings.entryCondition`, checks `enabled && !active`, draws price line and/or time line as needed.

### Editing entry conditions (`edit-entry-conditions.js`)

```js
// Props: entryCondition (spread at parent boundary)
useDrawOverlayEffect(OverlayGroups.editEntryConditions, (clear) => {
  if (!entryCondition) return
  chartController.createEditingEntryConditions(entryCondition)
  return clear
}, [entryCondition])
```

The controller's `createEditingEntryConditions(entryCondition)` builds price handle + time line, wires `onMoveEnd` → `this._tradeForm.updateEntryCondition(...)` and `onCancel` → `this._tradeForm.resetTradeForm(true)`.

Entry expirations follow the same pattern with `createSubmittedEntryExpirations(position)` and `createEditingEntryExpirations(entryExpiration)`.

## drawOrder mapping (Steps 3–8)

TV's `drawOrder` is a 100-line function that handles many order sub-types via conditionals. In SC, the parent routes to the right child, and each child only handles its own type. Here's how TV's conditionals map:

| TV condition | SC child | Controller method |
|---|---|---|
| `parseFloat(price) > 0 && externalOrderType !== TAKE_PROFIT` | `entry-orders.js` | `createSubmittedEntryOrder(order, positionId)` |
| `externalOrderType === TAKE_PROFIT` | `exit-orders.js` | `createSubmittedExitOrder(order, position)` |
| `externalOrderType === STOP_LOSS` | `stop-loss-orders.js` | `createSubmittedStopLoss(order, position)` |
| `parseFloat(stopPrice) > 0` (non-SL) | handled within controller | internal `_createSubmittedOrderLine` with `isStop: true` |
| `triggerPrice` | handled within controller | internal `_createTriggerPriceLine` |
| `coolDownCancelPrice` | handled within controller | internal stop handle at cancel price |

## Open Questions

None — patterns are established from alerts. Implementation-specific details (exact label text formatting) are derived from the TV code during each step.
