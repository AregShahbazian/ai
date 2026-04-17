---
id: sc-trendline-alerts
---

# PRD: Trendline Alerts — SuperChart Integration

## Overview

Reimplement the trendline alert chart overlay for SuperChart using SC's `segment` overlay. Trendline alerts render as a straight solid line between two points (price + time each). Submitted mode is locked (click to enter edit mode); editing mode allows moving individual endpoints and the line itself. This follows the pattern established by price alerts (`sc-price-alerts`) and time alerts (`sc-time-alerts`).

## Current Behavior (TradingView)

### Submitted trendline alerts (`alerts.js` → `drawTrendLine`)

A submitted trendline alert is a line segment between two points:

- **Shape**: `trend_line` or `ray` (based on `lineType` — `LineToolTrendLine` or `LineToolRay`)
- **Points**: Two `{time, price}` coordinates stored in `alert.data.points`
- **Color**: `chartColors.alert` (pending) or `chartColors.closedAlert` (triggered)
- **Label**: Note text + indicator icon — pending: `"{note} 🔔"`, triggered: `"{note} 🏁"`. Webhook alerts show "Webhook Alert!" instead.
- **Line width**: 2
- **Lock**: `true` — endpoints are NOT individually draggable in submitted mode
- **Line properties**: Custom styling from `alert.data.properties` (JSON string, parsed and applied)

### Submitted trendline alert interactions

- **On select (TV `onSelect`)**: Reads the line's current points, calculates `priceAtTime` (projected price at current time), determines `direction` (up/down relative to current market price), and dispatches `editAlert()` — sends to edit mode
- **On delete (TV `onDelete`)**: Opens a confirm modal "Delete Trend line alert" → on confirm: removes entity, dispatches `deleteAlert(alert.id)`

### Editing trendline alerts (`edit-alerts.js` → `drawTrendLine`)

Visually similar to submitted but interactive:

- **Color**: `chartColors.alert` (always alert color during editing)
- **Label**: Not explicitly set (uses default)
- **Lock**: `false` — both endpoints are movable, line itself is movable
- **Line properties**: Restored from `alert.data.properties`

### Editing trendline alert interactions

- **On mouse up (TV `mouse_up`)**: Reads the line's current points and properties, calculates `priceAtTime` and `direction`, captures `lineType` and serialized properties, dispatches `editAlert()` — updates the local form values
- **On delete (TV `onDelete`)**: Same confirm modal pattern as submitted

## Data Sources

### Alert object
- `id`, `note`, `webhookEnabled`, `alertType: "trend_line"`
- `data.points`: Array of two `{time, price}` objects
- `data.lineType`: `"LineToolTrendLine"` or `"LineToolRay"`
- `data.properties`: JSON string of line style overrides
- `data.triggerType`: `"ONCE"`, `"ONCE_ON_BAR_CLOSE"`, `"ONCE_PER_BAR"`, `"ONCE_PER_BAR_CLOSE"`
- `data.triggerResolution`: Required for some trigger types
- `data.data`: Legacy nested structure (migration path)

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

### Market data
| Source | Description |
|---|---|
| `currentMarket.getMarket().lastPrice` | Used to calculate alert direction (up/down) |

## Requirements

### R1 — Line segment rendering

Trendline alerts render as a straight solid line between two points. Each point has a timestamp and a price value.

### R2 — Submitted appearance

- **Line color**: `chartColors.alert` (pending) or `chartColors.closedAlert` (triggered)
- **Line style**: Solid, width 2
- **Line type**: Segment (finite between two points) — note: TV supports `ray` type too, but for SC we start with segment only
- **Bell icon** (deferred — see T1): A 🔔 icon next to the endpoint with the latest timestamp. For triggered alerts, 🏁 instead.
- **Lock**: `false` — matching time alert pattern where `onPressedMoveEnd` handles both click-to-edit and drag. TV used `lock: true` with `onSelect`, but SC has no equivalent select event for locked overlays.

### R3 — Editing appearance

- **Line color**: `chartColors.alert`
- **Line style**: Solid, width 2
- **Lock**: `false` — both endpoints are individually movable, and the line itself can be dragged as a whole

### R4 — Submitted interactions

- **On click/drag** (`onPressedMoveEnd`): Reads current points, calculates `priceAtTime` and `direction`, dispatches `editAlert()` to enter edit mode. Follows time alert pattern — single `onPressedMoveEnd` callback handles both click and drag-end.
- No delete-via-overlay. TV used right-click `onDelete` context menu which SC overlays don't have. Delete is handled through the alert form UI (matching price/time alert pattern).

### R5 — Editing interactions

- **On move end** (`onPressedMoveEnd`): After any point or line move, reads the updated points, recalculates `priceAtTime` and `direction`, dispatches `editAlert()` to update local form values.
- No delete-via-overlay (same as R4).

### R6 — Direction calculation

`priceAtTime` is calculated by projecting the line formed by the two points to the current time. If `priceAtTime > lastPrice`, direction is `"up"`, otherwise `"down"`. This is used by the alert form to set the alert's trigger direction.

Existing `util.priceAtTime(points, time)` expects `{time, price}` fields (TV uses epoch seconds). SC overlay points use `{timestamp, value}` (epoch milliseconds). The design must handle this field mapping — either adapt the utility call or map fields before calling it.

### R7 — Line properties persistence (deferred — see T3)

TV captures line visual properties (style overrides from its entity system) and stores them as `data.properties` (JSON string). SC overlays are recreated from state each render cycle (like price/time alerts) — there's no equivalent entity property capture. Existing `data.properties` values are in TV format and don't map to SC. Deferred until we define what SC-specific properties (if any) need persistence.

### R8 — Visibility gating

- Only draw when `alertsShow` is on
- Filter out the currently-editing alert from submitted list
- Triggered alerts shown only when `alertsShowClosed` is on

### R9 — Follow overlay component patterns

Three separate components (matching price/time alert split):
- `trendline-alerts.js` — submitted (pending) trendline alerts. Overlay group: `"trendlineAlerts"`
- `edit-trendline-alert.js` — editing trendline alert. Overlay group: `"editTrendlineAlert"`
- `triggered-trendline-alerts.js` — triggered (closed) trendline alerts. Overlay group: `"triggeredTrendlineAlerts"`

Each component:
- Gets `readyToDraw`, `chartController`, `chartColors` from `useSuperChart()`
- Uses `chartController.clearOverlays("<group>")` for cleanup
- Uses `useSymbolChangeCleanup` hook (submitted + triggered components)
- Uses `util.useImmutableCallback` for stable callback refs
- Includes `chartColors` in effect deps (controller owns colors, not components)

### R10 — Chart-controller methods

The chart-controller encapsulates visual logic (colors, styling) — components pass raw data. Following the price/time alert pattern:

- `createTrendlineAlert(group, key, points, callbacks)` — submitted/editing alert. Creates a `segment` overlay with `lock: false` and `chartColors.alert` color. Accepts `onPressedMoveEnd` callback. Used by both submitted and editing components (same as `createTimeAlert` pattern).
- `createTriggeredTrendlineAlert(key, points)` — triggered alert. Creates a `segment` with `lock: true` and `chartColors.closedAlert` color. No callbacks.
- `priceAtTime` / direction calculation stays in `util` — called by the component, not the controller.

## SuperChart API Assessment

### Candidate: `segment`

The `segment` overlay creates a line between two `{timestamp, value}` points. It supports:
- **Line styling**: `lineColor`, `lineWidth`, `lineStyle` (solid/dashed) — **does not work** (see confirmed gap)
- **Text/label**: `text`, `textColor`, `textFontSize`, `textBackgroundColor`, text padding properties
- **Dragging**: `lock: false` enables dragging of points and the line

Already used in the codebase for bases (`_createBaseSegment` in chart-controller), but only with `lock: true` and no callbacks.

### Confirmed gap

| Gap | Status |
|---|---|
| `segment` color props not applied | `segment` does not respect `lineColor`, `lineWidth`, `lineStyle` properties — same issue as `verticalStraightLine`. Line renders with defaults. Deferred until SC fixes this (see T2). |

### Confirmed (from `createOverlay` shared API)

`createOverlay` is the shared API for all overlay types (`verticalStraightLine`, `segment`, etc.). Callback support is overlay-agnostic — verified working for `verticalStraightLine` in time alerts:

- **Callbacks**: `onPressedMoveEnd`, `onClick`, `onRightClick`, `onSelected`, `onDeselected` — all work via `createOverlay`. Event includes `overlay.points` with updated coordinates.
- **Lock**: `lock: false` enables dragging; `lock: true` disables it. Both passed via `createOverlay`.

### Verified in storybook

Segment interactions confirmed working in storybook story:

- **Point drag**: Individual endpoints can be dragged independently (other endpoint stays fixed)
- **Line drag**: Entire segment can be dragged as a whole (translates both points)
- **Callbacks**: `onPressedMoveEnd` fires with updated point coordinates

### Unknowns

1. **Label/icon near endpoint**: Can text or an icon (🔔) be positioned near a specific endpoint rather than at the center of the line?

### SuperChart dev tasks (if API gaps found)

| Gap | What SC needs to provide |
|---|---|
| No endpoint label | Ability to attach a label/icon to a specific endpoint (not just center of line) |
| No ray type | A `ray` overlay type that extends a line infinitely from one point through another (deferred — not blocking) |

## To-do (deferred)

### T1 — Bell icon / label text at endpoints

R2 requires a 🔔 icon near the endpoint with the latest timestamp (🏁 for triggered). `segment` text/label positioning at a specific endpoint is unverified and likely not supported. Deferred until SC adds endpoint label support or an alternative is found.

### T2 — Line color styling

`segment` does not respect `lineColor`, `lineWidth`, `lineStyle` properties — same gap as `verticalStraightLine`. Lines render with default styling regardless of color props. The controller will set colors in the API call, but they won't take effect until SC fixes this. No workaround needed — the code will be correct, just visually using defaults.

### T3 — Line properties persistence

TV captures entity visual properties (style overrides) and stores them as `data.properties` (JSON string). SC overlays are stateless — recreated from Redux state each render cycle. Existing `data.properties` values are in TV format. Deferred until we define what SC-specific properties (if any) need persistence. Existing TV properties are ignored during rendering.

## Non-Requirements

- No changes to Redux state shape or alert actions
- No changes to the trendline alert form component
- No ray-type line support in initial implementation (segment only)
- No handling of price alerts or time alerts (separate PRDs)
- No custom line properties editor (TV's property dialog) — SC uses its own drawing tools
