---
id: sc-price-alerts
---

# PRD: Price Alerts — SuperChart Integration

## Overview

Reimplement the price alert chart overlays for SuperChart using `createOrderLine()`. Price alerts render as horizontal handles on the chart, with different appearances for **submitted** (display-only) and **editing** (interactive) modes. This follows the pattern established by the PnL handle (`sc-pnl-handle`).

## Current Behavior (TradingView)

### Submitted price alerts (`alerts.js` → `createPositionLine`)

A submitted price alert is a horizontal handle at the alert's price:

- **Body text**: Not shown (empty)
- **Quantity text**: Truncated alert note (max 20 chars), uppercase. If no note, shows "ALERT". Recurring alerts append pause/play indicator.
- **Cancel button**: Visible when `alertsEnableEditing` and `alertsEnableCanceling` are on. Clicking dispatches `deleteAlert(id)`.
- **Line**: Controlled by `alertsShowLine` setting — dashed, alert color
- **Editable**: No — not draggable
- **onModify**: Opens alert in edit mode via `dispatch(editAlert(alert))`
- **Color**: `chartColors.alert` (dark: `#3ea6ff`, light: `#007FFF`)

### Editing price alerts (`edit-alerts.js`)

Two states during editing:

#### Saving state (`createPositionLine`)
- **Body text**: "Saving"
- **Quantity text**: Not shown
- **Line**: Controlled by `alertsShowLine`
- **Editable**: No
- **Color**: `chartColors.alert`

#### Active editing state (`createOrderLine`)
- **Body text**: "Alert me when" (i18n)
- **Quantity text**: Price formatted to market precision + quote currency
- **Cancel button**: Visible — cancels editing via `dispatch(resetAlertForm())`
- **Line**: Shown (solid)
- **Editable**: Yes — draggable
- **onModify**: Submits the alert via `dispatch(submitAlertsForm())`
- **onMove**: Updates alert price to handle's new position
- **Color**: `chartColors.alert`

## Data Sources

### Alert object
- `id`, `price`, `note`, `recurring`, `status`, `alertType: "price"`
- `data.triggerType`: "ONCE" etc.

### Chart settings (Redux: `state.chartSettings`)
| Setting | Description |
|---|---|
| `alertsShow` | Master toggle for alert visibility |
| `alertsShowLine` | Whether the horizontal line is drawn |
| `alertsShowNote` | Whether note text is shown |
| `alertsEnableEditing` | Whether clicking opens edit mode |
| `alertsEnableCanceling` | Whether cancel/delete button is shown |
| `alertsShowClosed` | Whether triggered alerts are shown |

### Colors (from `chartColors`)
| Key | Description |
|---|---|
| `alert` | Alert color — dark: `#3ea6ff`, light: `#007FFF` |
| `closedAlert` | Triggered alert color — `#2563EB` |

### Edit state (Redux: `state.alertsForm`)
| Field | Description |
|---|---|
| `isEditing` | Whether an alert is being edited |
| `isSubmitting` | Whether alert is being saved |
| `alert` | The alert object being edited |
| `deletingAlertIds` | Array of IDs currently being deleted |

## Requirements

### R1 — Use options-object API

Use `createOrderLine(chart, { ...options })` for both submitted and editing handles, matching the PnL handle pattern. Use the chart-controller to encapsulate visual logic.

### R2 — Submitted alert appearance

The submitted alert handle must use explicit color properties (SC does not have theme-aware defaults like TV):

- **Align**: Right
- **Editable**: `false`
- **Body**: Not visible (`isBodyVisible: false`)
- **Quantity**: Solid alert-color background, alert-color border, white text
  - `quantityTextColor: "#FFFFFF"`
  - `quantityBackgroundColor: chartColors.alert`
  - `quantityBorderColor: chartColors.alert`
- **Cancel button**: Alert-color background, white icon
  - `cancelButtonBackgroundColor: chartColors.alert`
  - `cancelButtonBorderColor: chartColors.alert`
  - `cancelButtonIconColor: "#FFFFFF"`
- **Y-axis label**: Alert-color background, white text
  - `yAxisLabelTextColor: "#FFFFFF"`
  - `yAxisLabelBackgroundColor: chartColors.alert`
  - `yAxisLabelBorderColor: chartColors.alert`
- **Line color**: `chartColors.alert`

### R3 — Editing alert appearance

The editing alert handle uses the same color scheme but with body visible and dragging enabled:

- **Align**: Right
- **Editable**: `true`
- **Body**: Visible — white background, alert-color text
  - `bodyTextColor: chartColors.alert`
  - `bodyBackgroundColor: "#FFFFFF"`
  - `bodyBorderColor: chartColors.alert`
- **Quantity**: Solid alert-color background, alert-color border, white text (same as submitted)
- **Cancel button**: White background, alert-color icon (same as submitted)
- **Y-axis label**: Alert-color background, white text (same as submitted)
- **Line color**: `chartColors.alert` (solid, full width)
- **onModify**: Submits the alert
- **onMoveEnd**: Updates alert price to handle's new position (TV uses `onMove` which fires at end — SC's `onMoveEnd` is the equivalent)
- **onCancel**: Removes alert from edit mode, does NOT delete the alert

### R4 — Submitted alert interactions

- `onModify`: Dispatches `editAlert(alert)` to enter edit mode (when `alertsEnableEditing` is on)
- `onCancel`: Dispatches `deleteAlert(id)` (when `alertsEnableCanceling` is on)
- No `onMove` / `onMoveEnd` — submitted alerts are not draggable

### R5 — Saving state

When `isSubmitting` is true, show a non-editable handle with body text "Saving" (i18n key: `containers.trade.market.marketGrid.centerView.tradingView.editAlerts.saving`).

### R6 — Triggered/closed alerts (deferred)

Triggered alerts are **not** order-line handles. They are bell icon markers rendered on the candle at the alert's price and time (TV uses `drawClosedAlert` → `createMultipointShape` with Font Awesome bell icon `0xf0f3`). SC does not currently have an API for custom icon overlays — `createTradeLine` only supports arrow types (`wide`, `arrow`, `tiny`), and `simpleTag` renders as a horizontal line rather than a point marker. **Deferred until SC adds icon/marker overlay support.**

When implemented:
- **Shape**: Icon marker at `{time: alert.updatedAt, price: alert.price}`
- **Icon**: Bell
- **Color**: `chartColors.closedAlert` (`#2563EB`)
- **Z-order**: Controlled by `closedOrdersShowTop` setting (top or bottom)
- **Visibility**: Only shown when `alertsShowClosed` is on
- **Component**: Separate overlay file `triggered-price-alerts.js`

### R7 — Deleting state

When alert ID is in `deletingAlertIds`, quantity text shows "deleting..." instead of the note.

### R8 — Follow overlay component patterns

The component must follow SC overlay patterns (same as PnL handle):
- Get `readyToDraw`, `chartController`, `chartColors` from `useSuperChart()`
- Use `chartController.clearOverlays("alerts")` for cleanup
- Use `useSymbolChangeCleanup` hook
- Use `util.useImmutableCallback` for stable callback refs

### R9 — Chart-controller owns visual logic

The chart-controller exposes methods like `createPriceAlert(price, options)` and `createEditingPriceAlert(price, options)`. The component passes raw alert data — no text formatting or color logic in the component.

## To-do (deferred)

### T1 — Dashed line from y-axis to handle

Submitted alerts should have a dashed line that extends only from the y-axis to the handle (not full width). SuperChart's `createOrderLine` does not currently support partial-width lines. This will be addressed when SC adds line clipping support.

### T2 — Triggered alert bell icons (R6)

Triggered alerts should render as bell icon markers on the candle, not order-line handles. SC does not currently have an icon/marker overlay API. Currently using `createTradeLine` with a hardcoded bright blue arrow as a placeholder. Will be replaced with proper bell icons when SC adds icon overlay support.

## Non-Requirements

- No changes to Redux state shape or alert actions
- No changes to alert form components
- No storybook story — price alerts use `createOrderLine` which is already proved in storybook
- No time alert or trendline alert handling (separate PRDs)
