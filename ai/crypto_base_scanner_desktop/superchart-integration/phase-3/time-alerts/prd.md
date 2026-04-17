---
id: sc-time-alerts
---

# PRD: Time Alerts — SuperChart Integration

## Overview

Reimplement the time alert chart overlay for SuperChart using SC's `verticalStraightLine` overlay via the `createTimeAlertLine()` helper. Time alerts render as vertical lines at a specific timestamp. Unlike price alerts (which use `createOrderLine`), time alerts use a vertical line overlay. This follows the pattern established by the price alerts PRD (`sc-price-alerts`).

## Current Behavior (TradingView)

TV uses a single `TimeAlert` component (`alerts.js`) for both pending and triggered alerts, differing only by color. For SC, these are split into separate components (matching the price alerts pattern).

### Pending time alerts (`alerts.js` → `drawTimeLine`)

- **Shape**: Vertical line (`vertical_line`) spanning the full chart height
- **Color**: `chartColors.alert` (dark: `#3ea6ff`, light: `#007FFF`)
- **Label**: "Trigger At {formatted date}" — if alert has a note, appended as " - {note}"
- **Line style**: Solid, width 1
- **Movable**: Yes
- **On select (TV `onSelect`)**: Reads the line's point position, converts to UTC time, and dispatches `editAlert({...alert, data: {..., time: newTime}})` — enters edit mode

### Triggered time alerts (`alerts.js` → same `drawTimeLine`, `triggered` prop)

Visually identical to pending except for color. TV does not differentiate interactions (same `onSelect`, `allowMove`) — this is a bug we won't replicate:

- **Color**: `chartColors.closedAlert` (`#2563EB`)
- **Label**: Same format as pending (note text, `withText: true`)
- **Line style**: Solid, width 1
- **Movable**: Yes (TV bug — should be immovable)
- **Interactions**: Same as pending (TV bug — should have none)

### Editing time alerts (`edit-alerts.js` → `drawTimeLine`)

Visually identical to pending state:

- **Color**: `chartColors.alert` (always alert color, not closedAlert)
- **Label**: Formatted time only (no "Trigger At" prefix, no note)
- **Movable**: Yes
- **On move end (TV `mouse_up`)**: Reads the line's new position, converts to UTC, and dispatches `editAlert({...alert, data: {..., time: newTime}})` — updates local form value only (does NOT submit)

## Data Sources

### Alert object
- `id`, `note`, `alertType: "time"`
- `data.time`: UTC string (e.g. `"Thu, 20 Mar 2026 14:00:00 GMT"`)
- `data.data.time`: Legacy nested structure (some alerts store time here)

### Chart settings (Redux: `state.chartSettings`)
| Setting | Description |
|---|---|
| `alertsShow` | Master toggle for alert visibility |
| `alertsShowClosed` | Whether triggered alerts are shown |

### Colors (from `chartColors`)
| Key | Description |
|---|---|
| `alert` | Pending alert color |
| `closedAlert` | Triggered alert color |

### Edit state (Redux: `state.alertsForm`)
| Field | Description |
|---|---|
| `isEditing` | Whether an alert is being edited |
| `alert` | The alert object being edited |

## Requirements

### R1 — Vertical line rendering

Time alerts render as a vertical line at the alert's timestamp. The line spans the full chart height.

### R2 — Submitted (pending) appearance

- **Line color**: `chartColors.alert`
- **Line style**: Solid, width 1
- **Label** (deferred — see T1): Formatted as "Trigger At {DD MMM 'YY HH:mm}" with optional " - {note}" suffix

### R3 — Triggered appearance

- **Line color**: `chartColors.closedAlert` (`#2563EB`)
- **Line style**: Solid, width 1
- **Label** (deferred — see T1): Same format as pending (note text)
- **Movable**: No (`lock: true`)
- **Interactions**: None — display only
- **Visibility**: Only shown when `alertsShowClosed` is on
- **Component**: Separate overlay file `triggered-time-alerts.js`

### R4 — Editing appearance

- **Line color**: `chartColors.alert`
- **Line style**: Solid, width 1
- **Label** (deferred — see T1): Formatted time only (no "Trigger At" prefix)

### R5 — Movable (pending and editing only)

Pending submitted alerts and editing alerts are draggable along the time axis (`lock: false`). Triggered alerts are NOT movable (see R3):

- **Submitted (pending) — on select** (`onClick`): Reads the line's position, dispatches `editAlert()` which sends the alert to edit mode (opens alert form), with the time set to the current position
- **Editing — on move end** (`onPressedMoveEnd`): Dispatches `editAlert()` which updates the local form value only (does NOT submit)

### R6 — Time format alignment

Three systems handle timestamps and may use different formats/units:
- **Internal data** (`alert.data.time`): UTC string (e.g. `"Thu, 20 Mar 2026 14:00:00 GMT"`)
- **TradingView**: Uses seconds (TV `points[0].time` is epoch seconds — see `alerts.js` line 132: `points[0].time * 1000`)
- **SuperChart**: Uses milliseconds in overlay points (`{timestamp: ms, value: 0}`) — see `createTimeAlertLine`

The design phase must trace the full conversion path: alert object → chart overlay creation, and callback position → alert update. Verify units at each boundary to avoid ms/s mismatches.

### R7 — Visibility gating

- Only draw when `alertsShow` is on
- Triggered alerts only draw when `alertsShowClosed` is also on
- Only draw if the alert's time is within the chart's visible range (use `timeIsInVisibleRange` or equivalent SC check)
- Filter out the currently-editing alert from the submitted list to avoid duplication

### R8 — Follow overlay component patterns

- Get `readyToDraw`, `chartController`, `chartColors` from `useSuperChart()`
- Use `chartController.clearOverlays("timeAlerts")` for cleanup
- Use `useSymbolChangeCleanup` hook

### R9 — Chart-controller methods

The chart-controller exposes:
- `createTimeAlert(timestamp, options)` — wraps `createTimeAlertLine()`, sets line color, style, `lock: false`, and callbacks. Accepts a `text` option for the label but does NOT pass it to `createTimeAlertLine()` yet (see T1)
- `createTriggeredTimeAlert(timestamp, options)` — wraps `createTimeAlertLine()` with `lock: true`, triggered color, no callbacks
- Methods to update/remove time alert overlays
- Label formatting lives in the controller (timezone-aware date formatting)

### R10 — Use `createTimeAlertLine()` helper

Use the SC-provided `createTimeAlertLine(chart, timestamp, options)` helper. It wraps `chart.createOverlay()` for `verticalStraightLine` and accepts:
- Line styling: `color`, `lineWidth`, `lineStyle`
- Text: `text`, `textColor`, `textBackgroundColor`, `textFontSize`
- Drag: `lock` (false = draggable)
- Callbacks: `onPressedMoveEnd` (drag complete), `onClick`, `onRightClick`, `onSelected`, `onDeselected`

The chart-controller calls this helper — the component does not call it directly.

## SuperChart API Status

### `createTimeAlertLine()` — verified in storybook

The `createTimeAlertLine(chart, timestamp, options)` helper wraps `verticalStraightLine` and is confirmed working:

- **Line styling**: `color`, `lineWidth`, `lineStyle` (solid/dashed) — works
- **Dragging**: `lock: false` enables horizontal dragging — works
- **Callbacks**: `onPressedMoveEnd`, `onClick`, `onRightClick`, `onSelected`, `onDeselected` — all work
- **Text/label**: `text` param exists (passed via `extendData`) — **does not render visually yet**

### Confirmed gap

| Gap | What SC needs to provide |
|---|---|
| Label text not rendering | `verticalStraightLine` text/`extendData` must render visually on or near the line |
| `styles.line.*` not applied | `verticalStraightLine` must respect `styles.line.color`, `styles.line.size`, `styles.line.style` passed via `chart.createOverlay()` |

## To-do (deferred)

### T1 — Label text rendering

R2 and R3 require label text on the vertical line. The `text` parameter is accepted by `createTimeAlertLine()` but does not render visually yet. The component builds the label string and passes it to the chart-controller method, but the controller does NOT forward it to `createTimeAlertLine()` until SC fixes `verticalStraightLine` text rendering. When the API is ready, the controller just needs to pass `text` through.

## Non-Requirements

- No changes to Redux state shape or alert actions
- No changes to the time alert form component
- No handling of price alerts or trendline alerts (separate PRDs)
