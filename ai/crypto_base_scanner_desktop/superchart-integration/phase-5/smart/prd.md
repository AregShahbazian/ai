---
id: sc-smart-replay
---

# SC Smart Replay / Backtest

Port the TV smart replay (backtesting) system to SuperChart. Smart replay extends
default replay with server-persisted backtest sessions: positions created via backend
API, trigger-based order execution, alert management, and a dedicated backtests widget.

## Depends On

- `sc-replay` (default replay) — implemented
- `sc-replay-dialogs` — replay mode dialog (default vs smart chooser)

## Terminology

- **Default replay** — simple replay with local trades (buy/sell at market price).
  Already implemented (`sc-replay`).
- **Smart replay** — backtest session persisted on the backend. Positions are created
  via API, the server handles triggers and order execution. This PRD.
- **Backtest** — a smart replay session. Has an ID, name, start/end times, balances,
  positions, and stats. Stored server-side.

## Scope

### In scope

1. **Backtest session management** — create, load, resume, finish, delete
2. **Smart position management** — create, increase, reduce, cancel, close via backend
3. **Trigger system** — server-defined price/time triggers that pause replay and
   execute pending orders
4. **Alert system** — price, time, and trendline alerts checked each candle step
5. **Backtest widget** — list/detail views, create/edit modal, position tables
6. **Mode switching** — toggle between default and smart replay during a session
7. **Fictional balances** — $10k USD equivalent starting capital
8. **Auto-resume** — optionally resume playback after trigger execution
9. **Reset-to** — jump backward in time with server-side position rollback
10. **Backtest stats** — position count, win rate, PnL, progress

### Out of scope

- Step back (separate PRD: `stepback/`)
- Replay dialogs / mode selection UI (separate PRD: `sc-replay-dialogs`)
- Session persistence across remount (INTEGRATION.md pending)
- PriceTimeSelect for replay start (deferred)
- Quiz integration

## Requirements

### R1: Backtest Session Lifecycle

#### R1.1: Create

- User clicks "New Backtest" (from backtests widget or replay controls)
- Opens backtest edit modal with fields:
  - Market (pre-filled with current chart market)
  - Start date / End date (date pickers)
  - Base balance / Quote balance (pre-filled with fictional balances)
  - Name (auto-generated default: `"{SYMBOL} {date}, {time}"`)
  - Description (optional, max 240 chars)
  - Leverage (for futures markets)
- On submit: `POST /backtests` with config
- On success: load the new backtest into replay

#### R1.2: Load / Resume

- Loading a backtest (from widget list or after creation):
  - Switch to the backtest's market if different from current chart
  - Set chart resolution to the backtest's resolution
  - Start replay at `replayStartAt`, jump to `lastCandleSeenAt` if resuming
  - Set end time to `replayEndAt`
  - Load positions, balances, and trading info from backend response
- The backtest's `lastCandleSeenAt` is the resume checkpoint — replay jumps to this
  point without replaying intermediate candles

#### R1.3: Finish

- User clicks "Finish" in backtest widget header
- Marks backtest `status: 'finished'` via `PATCH /backtests/{id}`
- Cancels all active alerts
- Stops replay playback
- Backtest appears in "Finished" tab of widget

#### R1.4: Delete

- User clicks "Delete" in backtest widget header
- Confirmation dialog
- `DELETE /backtests/{id}`
- If the deleted backtest was active, stop replay session

#### R1.5: View Finished Backtest

- User clicks "View on Chart" for a finished backtest
- Loads the backtest in read-only mode: positions visible on chart, no trading

### R2: Smart Position Management

All position operations go through the backend. The current candle and resolution are
sent with each request so the server can calculate fills accurately.

#### R2.1: Create Position

- `POST /backtests/{id}/positions` with `{candle, resolution, smartPosition}`
- `smartPosition` contains order type, side, price, amount, etc.
- Server returns updated backtest with new position

#### R2.2: Increase Position

- `PATCH /backtests/{id}/positions/{positionId}/increase`
- Params: `{candle, resolution, orderType, price, amountType, baseAmount, quoteAmount}`

#### R2.3: Reduce Position

- `PATCH /backtests/{id}/positions/{positionId}/reduce`
- Params: `{candle, resolution, orderType, price, amountType, baseAmount, quoteAmount, closeFully}`
- `closeFully: true` closes the entire position

#### R2.4: Cancel Position

- `PATCH /backtests/{id}/positions/{positionId}/cancel` with `{candle, resolution}`
- Removes unfilled order

#### R2.5: Trading Info Sync

After every position operation, rebuild and dispatch market trading info to Redux:
- Fictional balances (updated from backtest response)
- Open positions mapped to Position model
- Open orders
- Trade history
- Alert counts

This enables the existing Trading Terminal widgets (order form, positions panel, etc.)
to display backtest data using their existing Redux selectors.

### R3: Trigger System

The backend defines triggers on the backtest: `upTrigger`, `downTrigger`, `checkAt`.

#### R3.1: Trigger Check

- Each candle step: check if candle high/low crosses trigger prices or if time >= checkAt
- If trigger hit:
  1. Pause replay
  2. Set `updatingPosition: true` (disables trading UI)
  3. `POST /backtests/{id}/trigger` with `{candle, resolution}`
  4. Server executes the pending order, returns updated backtest
  5. Refresh trading info from response
  6. Set `updatingPosition: false`
  7. If auto-resume enabled: resume playback

#### R3.2: Auto-Resume

- Controlled by `smartReplayAutoResumePlayback` setting (default: true)
- After trigger execution completes, automatically call `play()` if enabled
- User can toggle this in replay settings

### R4: Alert System

Alerts are managed locally (not server-persisted). Three types:

#### R4.1: Price Alert

- Triggers when candle crosses alert price
- One-shot: removed after triggering

#### R4.2: Time Alert

- Triggers when replay time reaches alert time
- One-shot: removed after triggering

#### R4.3: Trendline Alert

- Triggers when candle crosses a trendline (defined by two price/time points)
- One-shot: removed after triggering

#### R4.4: Alert Behavior

- Each candle step: check all active alerts
- On trigger: show notification, add to `triggeredAlerts` list, remove from active
- On session finish: cancel all remaining alerts

#### R4.5: Time comparisons use `currentActualTime` (one-candle lag — intentional)

All time-based comparisons in `smart-replay-controller.js` for alerts and for
`checkTriggers` use `_currentActualTime = _currentTime − 1000`, not `_currentTime`:

- `expiresAt >= _currentActualTime` (alert expiry check)
- `_currentActualTime >= alert.data.time` (time alert trigger)
- `trendLineShouldTrigger(_currentActualTime / 1000, ...)` (trendline alert)
- `checkTriggers(candle, _currentActualTime)` (entry time triggers — `checkAt`)

**Observable behaviour.** A time alert scheduled at 05:00 fires when the engine draws
the candle closing at **06:00**, not the one closing at 05:00 — because at engine
time 05:00, `_currentActualTime` is 04:59:59 and `04:59:59 >= 05:00` is false. The
same lag applies to `checkAt` position triggers.

**Why it's intentional.** The `-1000ms` offset keeps replay's time semantics aligned
with how the backend evaluates position triggers on the backtest server side. Alerts
and client-side triggers intentionally fire at the same moment as backend-side
position triggers, so that a `checkAt` time condition and a time alert set to the
same moment don't drift apart from each other, and so that backtested behaviour
matches what the backend would do in a live evaluation. Ported as-is from TV 5.2.x
(`replay-smart-trading-controller.js:198` pre-port).

**Do NOT "fix" this** by replacing `_currentActualTime` with `_currentTime` in just
one of the comparisons. If the lag ever does need to be removed, all four
comparison sites must change together, and that change must be coordinated with the
backend's position-trigger timing semantics — otherwise alerts and triggers will
diverge by one candle.

Trade storage (`createTrade`) and `updatedAt` tagging on triggered alerts are a
different concern — they use `_currentActualTime` to represent "inside the owning
candle", which IS the right semantic for those fields. Leave them alone.

### R5: Backtest Widget

A dedicated widget panel for managing backtests.

#### R5.1: Backtests List

- Two tabs: "Running" / "Finished" (filter by backtest status)
- Search by name
- Pagination (10 per page)
- Each row shows: name, market, start/end dates, PnL, progress
- Click row → backtest detail view

#### R5.2: Backtest Detail View

- Header: editable name, action buttons (Resume, View on Chart, Stop, Delete, Finish)
- Stats row: position count, win rate, PnL %, PnL value, progress bar
- Positions table/list: open and closed positions with cost, PnL, duration
- Position actions: increase, reduce, cancel (for open positions in running sessions)

#### R5.3: Create/Edit Modal

- Fields per R1.1
- Validation:
  - Name: 2-40 characters
  - Market: required
  - Both balances: > 0
  - Start date: required, before end date
  - End date: required, not in future
  - Description: max 240 chars
- Edit mode: only name, leverage, end time editable

#### R5.4: Widget Wiring

- Widget appears in Trading Terminal layout (same panel as other widgets)
- `replayBacktestsWidget` Redux state controls which view is shown (list vs detail)
- Widget interacts with smart replay controller via context/registry

### R6: Mode Switching

#### R6.1: Toggle Between Modes

- During an active default replay: user can switch to smart replay
  - Opens backtest creation flow
  - Existing default replay session is stopped
- During an active smart replay: user can switch to default replay
  - Confirmation if has trades
  - Stops smart session, starts default replay at same time

#### R6.2: Toggle Button

- In replay controls: shows "Backtest" (when in default mode) or "Replay" (when in
  smart mode)
- Already implemented in shared `toggle-replay-mode-button.js`

### R6.3: Chart Type Coexistence (TV / SC)

During coexistence, both TV and SC replay modes remain fully functional. The backtest
widget and edit modal must work with both chart types.

**Backtest sessions are chart-agnostic.** The backend stores candle data, positions,
timestamps, and balances — no chart type. A backtest created on TV can be resumed on
SC and vice versa. The chart type is purely a client-side choice of which replay engine
renders the session.

**When the chart type is obvious** (session initiated from the chart itself — e.g.,
mode switch button in replay controls, "Start replay here" context menu):
- The session targets the chart it was initiated from
- No chart type selector shown

**When the chart type is ambiguous** (session initiated from the backtest widget —
"New" button, resume, view on chart):
- If both TV and SC are available for the active trading tab, show a simple chart type
  select (TV / SC) in:
  - The backtest edit modal (for new sessions)
  - The resume confirmation dialog
  - The "View on Chart" action
- If only one chart type is available, no selector — use the available one
- The selected chart type determines which controller handles the session
  (TV's `ReplaySmartTradingController` or SC's `ScSmartReplayController`)

**Widget access pattern:**
- The backtest widget checks both `selectReplayContextGlobal` (TV) and ChartRegistry
  (SC) to determine which controllers are available
- Controller methods called by the widget (fetch, filter, navigate) work identically
  on both — the widget doesn't need to know which chart type is active except for
  the chart type selector

### R7: Reset-To (Go Back in Time)

- During smart replay: user can jump backward to a previous candle time
- Validates no partially-closed positions exist in the skipped range
- `PATCH /backtests/{id}/reset` with `{resetTo: seconds, resolution}`
- Server rolls back positions that were opened/modified after the reset point
- Client restarts replay from the reset time

### R8: Fictional Balances

- New backtests start with $10,000 USD equivalent
- Converted to base and quote currencies using current exchange rates
- Balances update as positions are opened/closed (server-managed)

## Backend API Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/backtests` | List backtests (status, page, per, search) |
| GET | `/backtests/{id}` | Fetch single backtest |
| POST | `/backtests` | Create new backtest |
| PATCH | `/backtests/{id}` | Edit backtest metadata |
| DELETE | `/backtests/{id}` | Delete backtest |
| PATCH | `/backtests/{id}/reset` | Reset to time |
| POST | `/backtests/{id}/positions` | Create position |
| PATCH | `/backtests/{id}/positions/{pid}` | Update position |
| PATCH | `/backtests/{id}/positions/{pid}/cancel` | Cancel position |
| PATCH | `/backtests/{id}/positions/{pid}/increase` | Increase position |
| PATCH | `/backtests/{id}/positions/{pid}/reduce` | Reduce position |
| POST | `/backtests/{id}/trigger` | Execute pending trigger |

All position/trigger endpoints include `{candle, resolution}` in the request body.

## State Architecture

### Redux as source of truth (no mirroring)

Same pattern as SC default replay (`sc-replay`). Controllers extend `ReduxController`,
read state via selectors, write via `dispatch(setReplaySession(chartId, patch))`. No
local controller state mirrored to Redux — Redux IS the state.

TV's `replayContextGlobal` (mirrored controller state) is not used.

### Controller hierarchy

```
ChartController
  └─ ScReplayController          (default replay — implemented)
       ├─ ScReplayTradingController  (simple buy/sell — implemented)
       └─ ScSmartReplayController    (backtest session + smart trading)
```

`ScSmartReplayController` is a sub-controller of `ScReplayController`, created in its
constructor. Access paths are the same three as default replay: ReplayContext (shared
UI), `useSuperChart` (SC components), ChartRegistry (thunks/external).

### State locations

Two distinct state locations in the same `replay` reducer:

**Session state** — `state.replay.sessions[chartId]`

Per-chart, ephemeral. Created on session start, cleared on stop. Default replay fields
plus smart-specific fields in the same slice:

```
sessions[chartId]: {
  // Default replay fields (existing)
  startTime, endTime, time, price, status, selectingStartTime,

  // Smart replay fields (new)
  backtestId,        // server ID of active backtest
  backtest,          // full backtest object from server
  alerts,            // active local alerts (price/time/trendline)
  triggeredAlerts,   // alerts that fired this session
  updatingPosition,  // true while trigger is executing (disables trading UI)
}
```

**Widget state** — `state.replay.backtests`, `backtestsFilters`, `replayBacktestsWidget`

Global (not per-chart). Persists across sessions. Already exists in the reducer:

- `backtests` — `{data: [], loading, total}` (list from server)
- `backtestsFilters` — `{status, page, per, query}` (list filters)
- `replayBacktestsWidget` — `{loading, editModal, backtest}` (which widget view is shown)

No new reducer needed. No new action types for the widget state — existing
`SET_REPLAY_BACKTESTS`, `SET_BACKTESTS_FILTERS`, `SET_REPLAY_BACKTEST_WIDGET` are
reused as-is.

## Non-Requirements

- **No new backend endpoints** — all endpoints already exist and are used by TV
- **No new backtest widget design** — reuse existing widget components, just wire to SC
  controller instead of TV controller
- **No trendline alert creation UI** — trendline alerts depend on drawing tools which
  are handled by SC's drawing system; only the check/trigger logic is in scope
- **No order form changes** — the existing order form works with Redux trading info;
  smart replay just needs to dispatch the right data to Redux
