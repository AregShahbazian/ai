---
id: sc-overlay-ctx-menu
---

# Overlay Context Menu (Phase 4a-2)

Right-click context menu for chart overlays in the SuperChart TT main chart.

## Scope

- **In scope:** All overlays created with `chart.createOverlay()` in the TT main chart.
- **Out of scope:**
  - Overlays created with `createOrderLine` or `createTradeLine` (no `onRightClick` support).
  - Grid bot chart overlays (`grid-bot-super-chart.js`).
  - Backtest overlays.
  - Empty chart area right-click (phase 4a-1).

## Behavior

Right-clicking a `createOverlay` overlay opens a context menu (Popup with PopupItems), positioned
at the click coordinates. The menu shows only the options applicable to the clicked overlay.

The overlay is identified by reverse-looking up `event.overlay.id` in the controller's `_overlays`
registry to find the group and key.

### Context menu options

Menu item order: Edit, Save, Delete/Cancel edit, separator, Settings, Color, separator, Info.

#### Edit

Sends the overlay's associated alert or position to edit mode.
Label is "Edit alert" or "Edit position" depending on the overlay type.

- **Time alert** (`timeAlerts`): dispatches `editAlert(alert)`.
- **Trendline alert** (`trendlineAlerts`): dispatches `editAlert(alert)`.
- **Submitted entry condition** (`submittedEntryConditions-{posId}`): finds any open order belonging
  to the position (via `posId` from the group name) and dispatches `editOrder(order)`, which sends
  the position to the trade form.
- **Submitted entry expiration** (`submittedEntryExpirations-{posId}`): same as entry condition.

Edit is **not shown** on:
- Triggered alerts (read-only historical).
- Bid/ask, break-even, bases (not independently editable).
- Trigger price lines (visual accessories, not independently actionable).
- Editing overlays (already in edit mode).
- Trading overlays where no position ID is available in the group name.
- When `alertsEnableEditing` is false (for alert overlays).
- When `openOrdersEnableEditing` is false (for position overlays).

#### Save

Saves the current edit. Only shown on editing overlays.

- **Editing time/trendline alert**: dispatches `submitAlertsForm()`.
- **Editing entry condition/expiration**: calls `_onSubmitTradeForm()`.

#### Delete

Deletes or cancels the overlay's associated alert, or cancels the current edit.

**On submitted (non-editing) overlays:**
- **Time alert** (`timeAlerts`): dispatches `deleteAlert(alertId)`.
- **Trendline alert** (`trendlineAlerts`): same as above.

Delete respects `alertsEnableEditing` and `alertsEnableCanceling` — not shown if either is false.

**On editing overlays (cancel edit):**
Labeled "Cancel edit" instead of "Delete".
- **Editing time/trendline alert**: dispatches `resetAlertForm()`.
- **Editing entry condition/expiration**: calls `resetTradeForm(true)`.

Delete is **not shown** on:
- Triggered alerts, bid/ask, break-even, bases, trigger price lines.
- Submitted entry conditions/expirations.

#### Settings

Available on **all** overlays in scope. Opens the chart settings modal on the **General Settings**
tab. The relevant settings section is highlighted with a box-shadow and scrolled into view.

Displayed as "Settings" with a cog icon.

#### Color

Available on **all** overlays in scope. Opens the chart settings modal on the **Color** tab.
The specific color row is highlighted if a single color key maps to the overlay (e.g. "Alert",
"Closed Alert", "Break Even"). Otherwise the color section is highlighted.

Displayed as "Color" with a palette icon.

#### Info

Available on **all** overlays in scope. Opens a small modal showing:
- **Type**: human-readable overlay label (e.g. "Time Alert", "Trendline Alert (editing)")
- **Alert ID / Position ID**: entity ID if applicable
- **Overlay-specific details**: price, time, or trendline points depending on overlay type
- **Overlay**: klinecharts overlay type name
- **Overlay ID**: klinecharts overlay instance ID

A horizontal divider separates domain info from klinecharts debug info.

Displayed as "Info" with an info-circle icon. Always last in the menu, with a separator above it.

### Options per overlay

| Overlay | Group | Edit | Save | Delete | Settings | Color | Info |
|---|---|---|---|---|---|---|---|
| Time alert | `timeAlerts` | "Edit alert" | - | yes | yes | yes | yes |
| Trendline alert | `trendlineAlerts` | "Edit alert" | - | yes | yes | yes | yes |
| Triggered price alert | `triggeredPriceAlerts` | - | - | - | yes | yes | yes |
| Triggered time alert | `triggeredTimeAlerts` | - | - | - | yes | yes | yes |
| Triggered trendline alert | `triggeredTrendlineAlerts` | - | - | - | yes | yes | yes |
| Bid line | `bidAsk` | - | - | - | yes | yes | yes |
| Ask line | `bidAsk` | - | - | - | yes | yes | yes |
| Break-even | `breakEven` | - | - | - | yes | yes | yes |
| Base segment | `bases` | - | - | - | yes | yes | yes |
| Submitted entry condition | `submittedEntryConditions-{posId}` | "Edit position" | - | - | yes | yes | yes |
| Submitted entry expiration | `submittedEntryExpirations-{posId}` | "Edit position" | - | - | yes | yes | yes |
| Trigger price line | (various order groups) | - | - | - | yes | yes | yes |
| Editing time alert | `editTimeAlert` | - | yes | cancel | yes | yes | yes |
| Editing trendline alert | `editTrendlineAlert` | - | yes | cancel | yes | yes | yes |
| Editing condition time | `editEntryConditions` | - | yes | cancel | yes | yes | yes |
| Editing expiration time | `editEntryExpirations` | - | yes | cancel | yes | yes | yes |

## Settings respect

- Edit and drag on time/trendline alerts respect `alertsEnableEditing`. When false, overlays
  are locked (no drag) and edit is hidden from context menu.
- Delete on time/trendline alerts respects both `alertsEnableEditing` and `alertsEnableCanceling`.
- Edit on entry conditions/expirations respects `openOrdersEnableEditing`.

## Popup style

Reuses the `ContextMenuPopup` component extracted from `context-menu.js`. Handles off-screen
detection, portal rendering, backdrop dismiss (mousedown), scroll dismiss, and mobile close button.

## Non-requirements

- No per-overlay color picker — color option opens the settings modal's color tab.
- No per-overlay hide toggle — settings option opens the settings modal's general settings tab.
- No context menu on `createOrderLine` / `createTradeLine` overlays.
- No context menu on empty chart area (phase 4a-1).
- No context menu on grid bot or backtest overlays.
- Base box overlay does not receive right-click events (SC `box` template `ignoreEvent` not
  overridden — not needed since base segments cover the interaction).

## References

- `onRightClick` usage: `$SUPERCHART_DIR/.storybook/overlay-stories/Alerts.stories.tsx`
- Overlay registry: `chart-controller.js` `_overlays` Map
- Overlay-to-color/toggle mapping: `ai/superchart-integration/chart-overlay-mapping.md`
- Chart settings modal: `src/containers/trade/trading-terminal/widgets/center-view/tradingview/settings/`
- Alert delete callback: `src/containers/trade/trading-terminal/widgets/my-alerts/alert-row.js`
- ContextMenuPopup: `src/components/elements/context-menu.js`
