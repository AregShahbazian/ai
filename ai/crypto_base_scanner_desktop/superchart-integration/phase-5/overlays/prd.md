---
id: sc-replay-overlays
---

# Phase 5: Replay Overlays

Overlay behavior during SC replay sessions: which overlays to hide, which to keep
with modified behavior, and which new replay-only overlays to add.

Default replay only. Smart replay overlay behavior deferred to `prd-smart.md`.

---

## 1. Overlay Visibility

Controlled in the parent (`super-chart.js`) via conditional rendering based on
`replayMode` from Redux. Overlay components themselves are unaware of replay —
the parent decides what to mount.

### Hidden during replay (unmounted)

These overlays show live/current data that is irrelevant during replay:

- BidAsk
- Orders
- EditOrders
- PriceAlerts
- EditPriceAlert
- TriggeredPriceAlerts
- TimeAlerts
- EditTimeAlert
- TriggeredTimeAlerts
- TrendlineAlerts
- EditTrendlineAlert
- TriggeredTrendlineAlerts
- OverlayContextMenu

### Always mounted (replay-aware)

These stay mounted but change data source or filtering:

- **Trades** — switches data source based on mode:
  - Live: regular trades from Redux
  - Default replay: `trades` from replay Redux session
  - Data source switching done in the Trades component, not the controller

- **Bases** — stays visible, filtered by replay time:
  - Live: filtered by visible range (existing behavior)
  - Replay: filtered by `replayTime` — bases with `formedAt < replayTime` are shown,
    appearing as the user travels through time
  - Filtering switch done in the Bases component

- **BreakEven** — single component, switches data source:
  - Live: `currentPosition` from `CurrentPositionContext`
  - Default replay: `currentPosition` from replay Redux session
  - Non-interactive during replay (no close button)

- **PnlHandle** — same pattern as BreakEven:
  - Live: live position data
  - Default replay: replay position data
  - Non-interactive during replay (visual only, no close button)

- **PriceTimeSelect** — stays mounted (may be used for replay start time selection)

- **Screenshot** — stays mounted

### Shown only during replay (mounted when `replayMode`)

- **ReplayTimelines** — new overlay component (see Section 2)

---

## 2. ReplayTimelines

New overlay component showing vertical timeline markers during replay.

Three `timeLine` overlays:

| Line | Color key | When shown |
|------|-----------|------------|
| Start time | `chartColors.replayStartTime` | Always during replay |
| End time | `chartColors.replayEndTime` | Always during replay (smart: backtest `replayEndAt`; default: `Date.now()` snapshot taken at session start) |
| Current time | `chartColors.replayCurrentTime` | During playback (not at start/finish) |

**Default replay end-time semantics.** Default replay doesn't have a
user-supplied end boundary, so `_startSession` snapshots `Date.now()` at the
moment the session starts and stores it as `session.endTime`. This matches the
engine's buffer boundary (the engine loads history up to its own `Date.now()`
call at the same moment, which is effectively the same instant). The overlay
is static for the rest of the session — even if real time marches on, the
stored endTime reflects "end of historical data available at session start",
which is the conceptually meaningful boundary. `handleBackToStartClick`
preserves the original endTime on restart (doesn't refresh).

Each line has a label showing the formatted timestamp in the user's timezone.

Implementation follows the SC overlay pattern:
- `useDrawOverlayEffect` with `OverlayGroups.replayTimelines`
- Controller method `chartController.replay.createTimelines(startTime, endTime, currentTime, status)`
  builds the overlays using `chart.createOverlay()` with the `timeLine` overlay type
- Redrawn on every replay state change (time, status)

Color keys (`replayStartTime`, `replayEndTime`, `replayCurrentTime`) must be added
to the chart colors configuration, using the same values as the TV implementation.

---

## 3. Conditional Rendering Pattern

In `super-chart.js`, the overlay section becomes:

```jsx
{/* Always mounted */}
<Trades/>
<Bases/>
<BreakEven/>
<PnlHandle/>
<PriceTimeSelect/>
<Screenshot/>

{/* Hidden during replay */}
{!replayMode && <>
  <BidAsk/>
  <PriceAlerts/>
  <EditPriceAlert/>
  <TriggeredPriceAlerts/>
  <TimeAlerts/>
  <EditTimeAlert/>
  <TriggeredTimeAlerts/>
  <TrendlineAlerts/>
  <EditTrendlineAlert/>
  <TriggeredTrendlineAlerts/>
  <Orders/>
  <EditOrders/>
  <OverlayContextMenu/>
</>}

{/* Replay-only */}
{replayMode && <>
  <ReplayTimelines/>
</>}
```

`replayMode` read from Redux via `useSelector(selectReplayMode(chartId))` in a
wrapper component or in `SuperChartWidgetWithProvider` directly.

---

## Non-Requirements

- No smart replay overlay behavior (deferred to `prd-smart.md`)
- No replay position overlay as a separate component — BreakEven and PnlHandle
  switch data source instead
- No trade marker visual differences between live and replay trades
- No overlay interaction during replay (no editing alerts, orders, or positions)
