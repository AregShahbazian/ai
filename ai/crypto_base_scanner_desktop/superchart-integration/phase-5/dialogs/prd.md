---
id: sc-replay-dialogs
---

# Phase 5: Replay Dialogs & Session Start Flows

Wire the replay session start/stop dialogs and flows for the SC chart. This PRD
covers the confirmation modal, the default-vs-backtest mode chooser, the quick-start
flow for smart replay, and the unified session-start pipeline that ties all entry
points together.

> **Status (2026-04-14):** Fully implemented. Each requirement below has a **Status**
> note describing the current state. The "Start replay here" context menu entry is
> delivered in `[sc-chart-ctx-menu-options]` (chart context menu plumbing landed
> in `[sc-chart-ctx-menu]`, entries in the follow-up).

---

## Scope

### In scope

- Confirmation modal (stop/restart with trades or backtest positions)
- Replay mode dialog (default vs backtest, with "don't ask again")
- Quick-start flow for smart replay (bypass backtest edit modal)
- Entry points: header button (desktop PriceTimeSelect + mobile random bar),
  Random Bar dropdown, console dev hook
- Mode switching during session (toggle replay mode button)
- `replaySafeCallback` global guard

### Out of scope

- Backtest edit modal UI (already exists, just needs wiring — done)
- Smart replay controller implementation (separate PRD: `../smart/prd.md`)
- Context menu "Start replay here" entry — delivered in
  `[sc-chart-ctx-menu-options]`

---

## Requirements

### 1. Confirmation Modal

Shown before stopping or restarting a session that would discard user data (local
trades in default replay, or open backtest positions in smart replay).

**When shown:**
- `handleStop` is called AND `willLoseDataIfStopped` is true
- `handleBackToStartClick` (Back to Start / Random Bar restart) during an active
  session AND data would be lost
- `_startReplayInMode` when a session is already active AND data would be lost

**Default replay:**
- `willLoseDataIfStopped = replayMode === DEFAULT && trades.length > 0`
- Header: `"Stop Replay session?"`
- Message: `"You have made trades in the current Replay session.\n\nStopping/restarting
  will clear these trades.\n\nAre you sure you want to stop?"`
- Buttons: Yes / Cancel

**Smart replay:**
- `willLoseDataIfStopped = replayMode === SMART && backtest.backtestPositions.length > 0`
- Header: `"Stop Backtest session?"`
- Message: `"You have positions in the current Backtest session.\n\nYou can resume
  this Backtest any time from the \"Backtests\" widget.\n\nAre you sure you want to
  stop?"`
- Buttons: Yes / Cancel

The smart-replay message reminds the user they can resume from the widget, since
stopping does not delete the backtest on the server — only its chart session state.

**Status:** ✅ Implemented. `ReplayController.willLoseDataIfStopped`,
`confirmStopHeader`, `confirmStopMessage`, and `confirmStop` in
`replay-controller.js` cover both modes.

### 2. Replay Mode Dialog

Shown when starting a fresh replay session. Lets the user choose Default Replay or
Backtest mode.

**When shown:**
- `_handleFirstReplay(time)` is called AND `chartSettings.replayShowModeDialog` is true

**When skipped:**
- `replayShowModeDialog` is false (user checked "don't ask again") → uses
  `replaySettings.isSmartReplay` to decide the mode automatically
- Session already active → handled by `_startReplayInMode` which reuses the existing
  flow without reopening the chooser

**Dialog content:**
- Two clickable boxes: "Replay" (default) and "Backtest" (smart) with short
  descriptions
- "Don't ask again" checkbox → writes `replayShowModeDialog: false` to `chartSettings`
- Cancel button

**Flow after selection:**
- User picks Default → starts default replay at the picked time
- User picks Backtest → either quick-starts a backtest or opens the backtest edit
  modal (see §4)

**"Don't ask again" reset:**
- Can be undone in chart general settings: "Show Replay/Backtesting mode select
  modal".

**Status:** ✅ Implemented. `ReplayModeDialog` component is wired into
`ReplayController._handleFirstReplay`. Note: the controller defers the controller
call inside `onSelect` to the next tick so the dialog's own `closeModal("confirm")`
flushes BEFORE `confirmStop` dispatches a new `openModal("confirm", ...)` —
otherwise the two dispatches collide on the shared `"confirm"` modal key.

### 3. Session Start Flow

Unified flow for all entry points that start a replay session:

```
Entry point → time picked
  → _handleFirstReplay(time)
      → guard: time > Date.now() → toast, abort
      → if replayShowModeDialog: show mode dialog → user picks mode
      → else: mode = isSmartReplay ? SMART : DEFAULT
      → _startReplayInMode(time, mode)
          → if existing session && willLoseDataIfStopped: confirmStop → run
          → else: run
          → run() → _stop({keepEngine: true}) if existing → start in picked mode
```

**Entry points:**
| Entry point | Status |
|-------------|--------|
| Header "Replay" button → PriceTimeSelect (desktop) | ✅ Implemented via `handleSelectReplayStartTimeClick` → `ChartController.interaction.start({id: "replay", ...})` |
| Header "Replay" button → random bar (mobile) | ✅ Implemented — mobile delegates to `handleRandomReplayStartTime` |
| "Random Bar" dropdown | ✅ Implemented via `handleRandomReplayStartTime` |
| Context menu "Start replay here" (right-click on chart) | ✅ Implemented — chart context menu plumbing (`[sc-chart-ctx-menu]`) + entries (`[sc-chart-ctx-menu-options]`) |
| Console: `chartController.replay._startSession(time)` (dev only) | ✅ Always available |

All entry points converge at `_handleFirstReplay(time)` which decides whether to
show the mode dialog, confirm a stop, and start the new session.

**Restart during an active session (Random Bar / Back to Start while playing):**
- Skip the mode dialog (the current mode is kept)
- Show the stop-confirmation if data would be lost
- For default replay: re-seek the engine in place without exiting (keeps the chart
  inside the replay session — avoids a `setCurrentTime(null)` round-trip that can
  briefly show live data)
- For smart replay: stop the session and create a fresh backtest at the backend

**Status:** ✅ Implemented. `_handleFirstReplay`, `_startReplayInMode`, and
`handleBackToStartClick` together cover the above. `_stop({keepEngine: true})` is
used for same-mode restarts so the engine stays inside the replay session.

### 4. Quick-Start Flow (Smart Replay)

When smart replay is selected from the mode dialog (or when `isSmartReplay` is the
remembered mode), the start can go two ways:

**Normal start (edit modal):**
- `SmartReplayController.goToReplayBacktest(undefined, true, {initiatedFromChart: true, replayStartAt: time})`
- Opens the backtest edit modal prefilled with the picked start time
- User fills balances / end time / name and submits; the submit path creates the
  backtest and starts the session

**Quick-start:**
- `SmartReplayController.quickStartBacktest({replayStartAt: time})`
- Bypasses the edit modal — creates a backtest with fictional balances and the
  current resolution, then starts the session

**When quick-start is used:**
- `replaySettings.quickStartFromChart` is true
- AND the start time came from a chart interaction (header button, random bar,
  future context menu)

**When quick-start is NOT used:**
- Starting from the Backtests widget (always shows the edit modal)
- `quickStartFromChart` is false

**Status:** ✅ Implemented. `_startReplayInMode` branches on `quickStartFromChart`
and dispatches to `smart.quickStartBacktest` or `smart.goToReplayBacktest`
accordingly.

### 5. Mode Switching During Session

Toggle between default and smart replay mid-session.

**Default → Smart:**
1. `handleSwitchReplayMode` captures the current default replay `startTime` before
   the stop flow clears it
2. Calls `smart.handleNewBacktest({initiatedFromChart: true, replayStartAt})` which
   opens the backtest edit modal prefilled with the captured start time
3. Submit path stops the default session and starts a new smart session at the same
   start time

**Smart → Default:**
1. `handleSwitchReplayMode` delegates to `smart.exitSmartMode`
2. Stops the smart session (with confirmation if positions exist) and starts a
   default replay at the same start time

**Status:** ✅ Implemented in `ReplayController.handleSwitchReplayMode` (used by the
shared `toggle-replay-mode-button.js`).

### 6. `replaySafeCallback` Global Guard

Wraps callbacks that would interfere with an active replay session.

**Behavior:**
- No session OR `willLoseDataIfStopped` is false → execute callback directly
- Session with unsaved data → show info modal: `"You have a running Replay session.
  Stop or finish the session first."` with OK button (no confirm/cancel)

**Used by:**
- `actions/replay.js` → `replaySafeCallback` thunk: resolves the active
  `ReplayController` via `ChartRegistry.getActive().replay` and delegates to
  `ReplayController.replaySafeCallback`
- Any action that shouldn't happen during replay (symbol switch from non-chart UI,
  order placement from trade widget, etc.)

**Status:** ✅ Implemented. `ReplayController.replaySafeCallback` is in place, and
the `actions/replay.js` thunk reads from `ChartRegistry` (no longer from the
TV-era `replayContextGlobal`).

---

## Non-Requirements

- No new dialog UI components — reuse existing `ReplayModeDialog`, `confirmStop`
  modal pattern, backtest edit modal
- No backtest business logic (owned by `../smart/prd.md`)
- No new entry points beyond the ones listed in §3
- No changes to the "don't ask again" persistence — uses existing `chartSettings`
