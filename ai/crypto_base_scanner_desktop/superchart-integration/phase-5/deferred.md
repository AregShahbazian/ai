# Phase 5: Deferred Items

Items excluded from `replay/prd.md` (default replay). Each becomes its own PRD.

## Prerequisites resolved

- ~~**Chart Background Context Menu plumbing** (`[sc-chart-ctx-menu]`)~~ — ✅ Done.
  Phase 4a-1 deliverable, listed here because it was the blocker for "Start replay
  here" and "Jump back to here" chart context-menu entries referenced in the
  `dialogs/` and `stepback/` sections below. Plumbing landed in commit `2bff0cc78`
  — right-click on the chart background opens an empty `ContextMenuPopup` via
  `InteractionController`'s persistent-mode `onRightSelect` consumer. The concrete
  entries ported from TV (alerts, trading, replay start, step-back jump,
  play/pause, speed up/down, stop) are delivered in the follow-up
  `[sc-chart-ctx-menu-options]`.

## Feature PRDs

### ~~`smart/` — Smart Replay / Backtest~~ — ✅ Done

Implemented:
- `SmartReplayController` wrapping `ReplayController` with backtest business logic
- Backtest creation / loading / resumption / view-on-chart
- `ReplayTradingController` (simulated buy/sell) + smart position/order/alert
  flows routed through the backend via `getSmartReplayController` helper
- `ToggleReplayModeButton` switches between default and smart replay mid-session
  (pre-fills start time on default→smart, resets engine to startTime on smart→default)
- Auto-resume playback after a trigger/alert fires (setting: `smartReplayAutoResumePlayback`)
- Backtests widget fully wired via `useActiveSmartReplay` hook + `ChartRegistry`
- "Exit Backtesting" vs "Exit Replay" labels in controls panel
- Finished-backtest UX: chart overlays stay visible but non-interactive; context-menu
  edit/save/delete gated; orders/alerts on chart can't be clicked; trade/alert forms
  disabled; position controls hidden in default replay, shown for backtest positions
  in smart replay
- View-on-chart mode (read-only playback of finished backtest) with play/step disabled
- Replay range clamped to available data before creating a backtest row (no orphan rows)

Wave of post-review fixes applied and verified via `smart/review.md` (238 test
cases, all passing).

### ~~`stepback/` — Step Back + Trading Reverts~~ — ✅ Done

Implemented:
- `sc.replay.stepBack()` wired to a Step Back button in `ReplayControls`
- `handleStepBack` in `ReplayController` with `_revertAndSeek` shared helper
- Default-mode trade reverts via `ReplayTradingController.resetTo`
- Smart-mode reverts via `SmartReplayController.resetTo` →
  `PATCH /backtests/:id/reset` with backend rollback of positions/trades
- `goBackTo(time)` for arbitrary multi-candle rewinds (used by chart context menu)
- `_stepInFlight` re-entrancy guard for held-key repeats (`shift+left`)
- Hotkey binding: `replayStepBack` → `shift+left`
- `canStepBack` getter gating the button + hotkey on session bounds and status

### ~~`stepback-optimization/` — Defer Backend Calls on Quiet Step-Backs~~ — ✅ Done

Implemented:
- `_pendingResetTo` accumulator on `SmartReplayController` captures the
  earliest quiet step-back target between flushes
- `resetTo` branches via `_hasPositionsSince`: dirty step crosses a
  position and flushes; quiet step just accumulates and un-triggers local
  alerts via `_untriggerAlertsSince`
- `_flush` / `_flushPendingReset` send one `PATCH /backtests/:id/reset`
  per flush point instead of one per candle
- Flush points centralised on `_stop` (covers `handleStop`,
  `handleBackToStartClick` smart branch, cross-mode restart via
  `_startReplayInMode`) + `exitSmartMode` + the four trade-action
  methods (`submit/cancel/increase/reduceBacktestPosition`)
- Forward-past-rewind path (`_processTriggerAsync`) clears pending as
  its first line so re-played trades aren't double-flushed
- `_clearPendingReset` wired into `loadBacktest`, `reset`, `destroy`,
  and `_startSession` to eliminate cross-session leakage
- Alert un-trigger is drop-only (no restore) — matches pre-optimization
  behaviour

Commit: `4c46af17a` `[sc-replay-stepback-optimization]`. PRD:
`stepback-optimization/prd.md`. Review verification matrix authored but
not ticked off — implementation is in but formal sign-off round hasn't
been walked.

### `trigger-timing-offset/` — Research: One-Candle Time-Trigger Lag

Research-only PRD. Both TV and SC replay share a one-candle timing offset:
on a 1h chart, an alert or order time-trigger set for `08:00` only fires
when the replay's current time reaches `09:00`. Related symptom: a trade
placed on the very first candle of a session cannot be undone by stepping
back, because the timestamp the frontend sends to the backend isn't
recognised as a revert target for that first trade.

The deliverable is `trigger-timing-offset/research.md`: traces the origin
of the offset (frontend `_currentActualTime = _currentTime − 1000`),
enumerates every frontend → backend timestamp call site, traces the
backend comparison operators in `crypto_base_scanner`, and decides
whether the fix is frontend-only, backend-only, or coordinated. A
follow-up implementation PRD will be written from the report.

PRD: `trigger-timing-offset/prd.md` (id `sc-replay-trigger-timing`).

### `reset-to-orphan-trades/` — Research: Stale Trades After Step-Back

Research-only PRD. Both TV and SC smart replay exhibit the same bug: after
stepping back through filled smart-trading orders, `PATCH /backtests/:id/reset`
is called but the affected trades are not removed from the backend response,
leaving them visually "hanging in the air" past the new replay time. The
controller then fires a reset on every subsequent candle step because the
still-present orphan trades read as a persistent divergence.

The fix almost certainly lives in the backend's reset handler
(`crypto_base_scanner`), but the frontend `resetTo` flow needs to be ruled out
or co-fixed before that can be claimed. Possibly related to the
`trigger-timing-offset` one-candle skew.

The deliverable is `reset-to-orphan-trades/research.md`: traces the frontend
`resetTo` flow in both SC and TV, the backend reset handler and its
record-deletion comparisons, and documents whether the fix is frontend-only,
backend-only, or coordinated.

PRD: `reset-to-orphan-trades/prd.md` (id `sc-replay-reset-orphans`).

### ~~`overlays/`~~ — ✅ Done

Implemented: conditional rendering, ReplayTimelines, data source switching for
Trades/BreakEven/PnlHandle, overlay visibility during replay.

### ~~`dialogs/` — Replay Dialogs & Session Start Flows~~ — ✅ Done

Implemented:
- Confirmation modal (stop/restart with trades — both default trades and smart
  backtest positions, with mode-specific header/message)
- Replay mode dialog (default vs backtest, with "don't ask again" → `chartSettings.replayShowModeDialog`)
- Unified `_handleFirstReplay` → `_startReplayInMode` pipeline for all entry points
  (header PriceTimeSelect, Random Bar, console)
- Quick-start flow for smart replay via `replaySettings.quickStartFromChart`
- Mode switching during session (`handleSwitchReplayMode`) with start-time carry-over
- `replaySafeCallback` global guard resolving the active controller via
  `ChartRegistry` (no `replayContextGlobal`)

The "Start replay here" context-menu entry is delivered in
`[sc-chart-ctx-menu-options]` alongside the full set of Altrady context-menu
entries ported from TV (create alert / buy / sell / break-even / replay
start / jump back / play-pause / speed up / slow down / stop).

### ~~Session Persistence Across Remount~~

Moved to `INTEGRATION.md` → "Pending / Needs Investigation". Not replay-specific —
affects any SC feature that needs to survive remount. SC engine `restoreSession` API
is implemented (`Superchart/ai/features/replay-restore-session.md`).

## SC Library Changes

- ~~**Expose `getFirstCandleTime` on ReplayEngine**~~ — ✅ Solved at datafeed level.
  `CoinrayDatafeed.getFirstCandleTime` now caches by `ticker_resolution`. Both our
  controller and the SC engine (via DataLoader) hit the same cache.

- ~~**Emit `onReplayStep` on init**~~ — ✅ Implemented in SC engine. Altrady's
  `getDataList` hack removed — initial price now comes via `onReplayStep` callback.

## Other Deferred Items

- ~~**PriceTimeSelect for replay**~~ — ✅ Done. Chart-click replay start-time
  picker built on SC's new pointer-event callbacks, plus the `quickStartFromChart`
  setting wired into the backtest flow.

  Implementation:
  - **`InteractionController`** (`controllers/interaction-controller.js`) — generic
    single-consumer multiplexer over SC's `onCrosshairMoved` / `onSelect` /
    `onRightSelect` / `onDoubleSelect`. Auto-cancels on supersede, symbol change,
    dispose, Escape, and (for `once:true` consumers) mousedown outside the chart
    container. Enriches results with `pageX`/`pageY` from the container rect so
    future consumers (e.g. chart-background context menu) can position DOM popups
    without waiting for SC to add page coords to `PriceTimeResult`.
  - **Replay button wiring** — `ReplayController.handleSelectReplayStartTimeClick`
    toggles selection mode and registers a replay consumer. Left-click commits to
    `_handleFirstReplay(result.point.time * 1000)` (SC hands back unix seconds;
    replay engine uses ms). Right-click cancels. `onCancel` clears
    `selectingStartTime` regardless of cancel reason.
  - **Quick-start branching** — `_startReplayInMode` now reads
    `replaySettings.quickStartFromChart` and, in SMART mode, calls either
    `smart.quickStartBacktest({replayStartAt})` (flag ON — no modal, fictional
    balances) or `smart.goToReplayBacktest(undefined, true, {initiatedFromChart, replayStartAt})`
    (flag OFF — backtest-edit modal prefilled with the picked time). Stop/confirm
    semantics are handled by the existing `_stop({keepEngine:true})` +
    `confirmStop` flow, matching TV's `handleStop(() => handleFirstReplay(time))`.
  - **Removed**: the old imperative `overlays/price-time-select.js` stub (zero real
    consumers), its mount in `super-chart.js`, and the document-mousedown cancel
    effect in `replay-context.js` (the controller now owns cancellation via its
    outside-click global listener).

  The chart background context menu itself landed in `[sc-chart-ctx-menu]` with an
  empty body. The "Start replay here" entry is delivered in
  `[sc-chart-ctx-menu-options]`, which adds every Altrady-specific entry that
  TV had (alerts, trading, replay) in one pass.

- **Quiz integration** — progressive candle reveal for quiz mode using SC replay engine.
  Separate initiative, may not use the same controllers.
