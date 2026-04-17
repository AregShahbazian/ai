# PRD: Orders Storybook Story (Superchart)

## Goal

Prove the `createOrderLine()` superchart API in Storybook with interactive
controls that mirror Altrady's chart settings panel. This is the most important
storybook story — `createOrderLine` is used by orders, PNL handle, edit-orders,
grid-bot-prices, edit-alerts, and edit-entry-conditions/expirations.

## All work in Superchart repo

```
$SUPERCHART_DIR/.storybook/overlay-stories/
```

No Altrady code changes.

---

## API to Prove

```ts
import {createOrderLine} from "superchart"

const line = createOrderLine(chart)
  .setPrice(price)
  .setText("LIMIT BUY 0.5 BTC")
  .setQuantity("@ $67,000")
  .setBodyBackgroundColor(color)
  .setBodyBorderColor(color)
  .setBodyTextColor(textColor)
  .setQuantityColor(color)
  .setQuantityBackgroundColor(color)
  .setLineColor(color)
  .setLineWidth(1)
  .setLineStyle(2)            // dashed
  .setTooltip("Change price")
  .setCancelButtonVisible(true)
  .setCancelButtonIconColor(iconColor)
  .setBodyVisible(true)
  .setQuantityVisible(true)

// Events — each takes (params, callback)
line.onMove({}, ({price}) => { /* drag in progress */ })
line.onMoveEnd({}, ({price}) => { /* drag finished */ })
line.onModify({}, () => { /* edit button clicked */ })
line.onCancel({}, () => { /* cancel/X button clicked */ })

line.getProperties()  // → OrderLineProperties
line.remove()
```

### API Differences from TradingView

TV's `createOrderLine` / `createPositionLine` use `setExtendLeft(showLine)` to
control whether the horizontal line extends across the chart. Superchart's
OrderLine has no `setExtendLeft`. Alternatives to test:

- `setLineColor("transparent")` — hide line, keep label
- `setLineWidth(0)` — might hide line
- The line may always be visible

This is a key question the story must answer.

---

## Altrady Chart Settings (mapped to Storybook controls)

These come from Altrady's Settings > Chart > Orders panel:

| Altrady Setting | Redux key | Storybook Control | Default |
|----------------|-----------|-------------------|---------|
| Show open orders in chart | `openOrdersShow` | `showOrders` (boolean) | true |
| Show labels on open orders | `openOrdersShowLabels` | `showLabels` (boolean) | true |
| Show side on open orders | `openOrdersShowSide` | `showSide` (boolean) | false |
| Enable editing orders from the chart | `openOrdersEnableEditing` | `enableEditing` (boolean) | true |
| Enable canceling orders from the chart | `openOrdersEnableCanceling` | `enableCanceling` (boolean) | true |
| Enable line across the chart | `openOrdersShowLine` | `showLine` (boolean) | false |

---

## Files

```
.storybook/overlay-stories/
  Orders.stories.tsx         # Story file
  overlays/order-line.ts     # Overlay module (pure functions)
```

## Overlay Module: `overlays/order-line.ts`

Simple pure functions, same pattern as `break-even.ts` and `trades.ts`.
The overlay module handles only the klinecharts API call — no settings logic.
The story handles settings (which functions to call, what text to build).

```ts
import type {Chart} from "klinecharts"
import {createOrderLine, type OrderLine} from "superchart"

export function createOrder(chart: Chart, price: number, color: string, textColor?: string): OrderLine
export function removeOrder(line: OrderLine): void
```

The story calls `createOrder()`, then uses chainable setters on the returned
OrderLine to configure text, quantity, cancel button, callbacks etc. based on
the current control values. Cleanup via `removeOrder()` (calls `line.remove()`).

---

## Story: `Orders.stories.tsx`

### Controls

| Control | Type | Default | Description |
|---------|------|---------|-------------|
| **Settings** | | | |
| `showOrders` | boolean | true | Master toggle — show/hide all |
| `showLabels` | boolean | true | Show text labels on order lines |
| `showSide` | boolean | false | Include "Buy"/"Sell" in label text |
| `enableEditing` | boolean | true | Enable onModify (edit button) |
| `enableCanceling` | boolean | true | Enable cancel (X) button |
| `showLine` | boolean | false | Horizontal line across chart |
| **Demo data** | | | |
| `numOrders` | number (1–5) | 3 | Number of mock orders |
| `scenario` | select | `mixed` | Order type mix (see below) |
| **Colors** | | | |
| `buyColor` | color | `#4CAF50` | Buy order color |
| `sellColor` | color | `#F44336` | Sell order color |
| `stopColor` | color | `#FF9800` | Stop price color |
| `triggerColor` | color | `#9E9E9E` | Trigger price color |
| **Chart** | | | |
| `symbol` | text | `BINA_USDT_BTC` | Chart symbol |

### Scenarios

The `scenario` select switches between mock order sets to test different order types:

| Scenario | Orders Generated |
|----------|-----------------|
| `mixed` | 1 limit buy, 1 limit sell, 1 stop loss — default |
| `limit` | N limit orders alternating buy/sell |
| `stopLoss` | Limit entry + stop loss at lower price |
| `takeProfit` | Limit entry + take profit target at higher price |
| `trailingStop` | Trigger price line + stop price line + limit price |
| `creating` | Order in "Creating..." state (no cancel, no edit) |
| `stacked` | Multiple orders at close prices — tests overlap rendering |

### Behavior

- `showOrders` = false → remove all lines, show nothing
- `showLabels` = false → `setBodyVisible(false)` + `setQuantityVisible(false)`
- `showSide` = true → label includes "Buy" / "Sell" prefix
- `enableEditing` = false → no onModify callback (or no edit button if API supports)
- `enableCanceling` = false → `setCancelButtonVisible(false)`
- `showLine` = true → line extends across chart (test: `setLineColor` visible vs transparent)
- `showLine` = false → line hidden but label visible (test how to achieve this)

### Mock Order Data

Orders are placed relative to current price using `useCurrentPrice()`:

```ts
interface MockOrder {
  side: "buy" | "sell"
  type: "limit" | "stop_loss" | "take_profit" | "trailing_stop"
  priceOffset: number    // % offset from current price
  stopOffset?: number    // % offset for stop price
  triggerOffset?: number // % offset for trigger price
  amount: number
  label: string          // e.g. "LIMIT BUY 0.5 BTC"
}
```

Each order in the scenario creates 1–3 order lines (e.g. trailing stop has
trigger line + stop line + price line).

### Label Construction

Matches Altrady's format:

```
{showSide ? "Buy " : ""}{amount} {baseCurrency}
```

Examples:
- Labels on, side off: `"0.5 BTC"`
- Labels on, side on: `"Buy 0.5 BTC"`
- Stop loss: `"Stop Loss: $65,000"`
- Take profit: `"TP #1: 5%"`
- Trailing stop: `"TS #1: Buy 0.5 BTC"`
- Creating state: `"Creating"`

### Callbacks

Interactive stories log to Storybook actions panel:

```ts
import {action} from "@storybook/addon-actions"

if (enableEditing) line.onModify({}, action(`order-${i}-edit`))
if (enableCanceling) line.onCancel({}, action(`order-${i}-cancel`))
line.onMove({}, action(`order-${i}-move`))
line.onMoveEnd({}, action(`order-${i}-move-end`))
```

Install `@storybook/addon-actions` if not already available.

---

## What This Story Proves

### Must-answer questions

1. **Line visibility control** — How to hide the horizontal line but keep the
   label? TV uses `setExtendLeft(false)`. Superchart has no equivalent. Test:
   `setLineColor("transparent")`, `setLineWidth(0)`, other approaches.

2. **Cancel button** — Does `setCancelButtonVisible(true/false)` work as
   expected? Does the cancel button render?

3. **Edit button** — Does `onModify` show a visible edit/modify button? Or is it
   just the callback?

4. **Drag behavior** — Does `onMove` fire during drag or only on release? Is
   `onMoveEnd` the release event? Does `onMoveStart` fire at the start?

5. **Body visibility** — Does `setBodyVisible(false)` hide the text label while
   keeping the line? (Needed for `showLabels` = false.)

6. **Overlap rendering** — Do multiple order lines at close prices stack
   cleanly or overlap/clip?

7. **Quantity text** — Does `setQuantity` render a second text block? What does
   it look like alongside `setText`?

### API surface validated

Once this story works, the following Altrady overlays can be ported with
confidence:

| Altrady File | Uses |
|-------------|------|
| `orders.js` | `createPositionLine` → `createOrderLine` |
| `edit-orders.js` | `createOrderLine` with onMove/onModify |
| `break-even.js` (PNL handle) | `createOrderLine` with setText/setQuantity/onCancel |
| `grid-bot-prices.js` | `createOrderLine` with onMove, setLineVisible(false) |
| `edit-alerts.js` | `createOrderLine` / `createPositionLine` |
| `edit-entry-conditions.js` | `createTriggerPriceHandle` → `createOrderLine` |
| `edit-entry-expirations.js` | `createTriggerPriceHandle` → `createOrderLine` |

---

## Implementation Notes

- Reuse `SuperchartCanvas` and `useCurrentPrice` from existing helpers
- Each scenario is a function returning `MockOrder[]`
- The story component creates/removes order lines in a `useEffect` gated on
  all controls
- Order line handles stored in a ref array, cleaned up on unmount or control change
- `@storybook/addon-actions` needed for callback logging

## Out of Scope

- Actual order execution or API calls
- Redux integration
- WebSocket order updates
- Entry condition / entry expiration handles (same API, tested implicitly)
- Order type icons or custom shapes
