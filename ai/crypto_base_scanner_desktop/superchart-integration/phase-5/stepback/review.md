# Phase 5: Replay Step Back — Review

PRD: `prd.md` (id `sc-replay-stepback`)

---

## Round 4: Pause-on-last-candle for continuous playback (2026-04-15)

### Feature: Continuous playback pauses before finishing
**Motivation:** Before this change, continuous playback ran until the buffer was
empty and auto-transitioned to `finished` — also marking smart backtests finished
on the backend. This gave the user no chance to step back from the last candle.
Manual stepping already had a "one extra step to finish" grace period; continuous
playback now matches.
**Change:** `ReplayController._wireCallbacks` → `onReplayStep` handler calls
`engine.pause()` after a forward step if `isPlaying && getReplayBufferLength() === 0`.
Manual `handleStep()` is unaffected because its direction-forward callbacks run
outside `playing` state.
**Files:** `replay-controller.js`
**PRD docs:** `../replay/prd.md` — "Playback end-of-data behaviour — pause on
last candle (Altrady deviation)" note added under §1 Engine wrapping.

### Verification
1. ✅ Default replay, press play, let it run to the end. Chart stops on the last
   candle; status is `paused`, not `finished`. Play button shows pause/play icon
   (not restart).
2. ✅ From that paused state, click step-back. Rewinds correctly.
3. ✅ From paused state, click play. Engine resumes, hits empty buffer, transitions
   to `finished`. Play button now shows restart.
4. ✅ From paused state, click step forward. Same result — one manual step →
   `finished`.
5. ✅ Smart replay, play all the way to the end. On last candle: status `paused`,
   backend backtest status still `running` (NOT finished). Confirm via backtests
   widget or network tab.
6. ✅ From smart paused-at-last state, click step-back. Rewinds without flashing
   `updatingPosition` (if the candle was quiet per Round 3 logic, or normally if
   it had a trade). Note: this interacts with the upcoming `stepback-optimization`
   PRD — verify once that ships.
7. ✅ From smart paused-at-last state, click play or step → backend
   `setBacktestFinished` fires, status `finished`, backtests widget shows
   "Finished".
8. ✅ Held `shift+right` all the way to the end: same pause-on-last behaviour; held
   key doesn't override the pause.
9. ✅ Trigger or alert fires on the last candle with `smartReplayAutoResumePlayback`
   enabled: current behaviour (trigger processes, auto-resume plays, empty
   buffer → finished) still reaches `finished` via the trigger path. The
   pause-on-last hook is redundant here — the smart trigger path's own pause
   fires first, then our hook's `engine.pause()` is a no-op. Verify no duplicate
   state updates or console errors.
10. ✅ Resolution change mid-session: after changing resolution, the engine re-seeks
    and the buffer repopulates. Play to end — pause-on-last fires correctly at
    the new resolution's last candle.

---

## Round 3: First trade not removed on full step-back (2026-04-14)

### Bug: Position non-zero after stepping back past the first trade
**Symptom:** User places 4 trades during default replay, steps back all the way to
startTime. Trades D/C/B get undone (position reverts correctly) but trade A (the
first placed, last to be undone) stays in the session — position still non-zero.
**Root cause (two parts):**

1. `replay-trading-controller.js:52` — `resetTo(time)` filter was
   `t.time * 1000 < time`. Trades are stored with
   `t.time = (candleClose − 1000) / 1000` (see `currentActualTime`, lines 41 /
   109 / 123). For steps back to the close of an earlier candle the strict `<`
   against `t.time * 1000` happens to work, because the trade's owning candle
   lies above the target. But for the final step back to `startTime` (which
   isn't itself a candle close — it's the session open), the arithmetic breaks:
   `(T0+res−1000) < T0` → `res < 1000` → false → first trade kept.
2. `replay-trading-controller.js:62` — `updateCurrentState` early-returned on
   empty trades, leaving `currentPosition` stale in Redux. Would also have
   masked this bug even if the filter had been correct, because the position
   wouldn't clear after the last trade was removed.

**Fix:**
- Filter now encodes the candle semantic directly:
  `(t.time * 1000 + 1000) <= time`. Keep trades whose owning candle closes at or
  before the new current time.
- `updateCurrentState` now explicitly sets `currentPosition: undefined` when
  trades is empty instead of early-returning.

**Files:** `replay-trading-controller.js` (`resetTo`, `updateCurrentState`).

**Smart replay impact:** Not affected. Backend `backtests/:id/reset` endpoint uses
`backtest_positions.where("open_time >= ?", reset_to).destroy_all` — the `>=` is
inclusive so positions opened during the first candle after startTime are correctly
destroyed (`(T0+res−1000) >= T0` holds). Needs manual verification but unlikely to
repro there. `ReplayTradingController.updateCurrentState` is default-mode only;
smart mode uses its own state flow.

### Verification
1. ✅ Default replay, place 4 trades spread across 4 candles, step back all the way
   — position reaches zero after the last step-back; trades array is empty.
2. ✅ Default replay, place 1 trade, step back once — position clears; no stale
   `currentPosition` in Redux state.
3. ✅ Default replay, place trades at non-adjacent candles (skip some candles between
   trades), step back to between two trades — only the later trades are removed,
   earlier ones intact, position recalculated correctly.
4. ✅ Smart replay, same scenario (4 positions, step back past first) — confirm the
   backend `>=` filter actually works end-to-end; verify no stale
   `backtestPositions` remain after the last step-back.

---

## Round 2: Replace setCurrentTime with stepBack for single-candle (2026-04-14)

### Bug: Loading flicker on every step back
**Symptom:** Clicking step-back (or holding `shift+left`) briefly shows the chart's
loading overlay between each step. Not seen in `Replay.stories.tsx` storybook.
**Root cause:** `handleStepBack` routed through `goBackTo(time)` which used
`engine.setCurrentTime(prevTime)`. `setCurrentTime` rebuilds the replay buffer and
always cycles through `loading → ready`. `engine.stepBack()` is atomic — no round
trip — which is what the storybook uses (`ctrl.stepBack()` at line 153).
**Fix:** Split the engine-move path. `handleStepBack` now uses
`engine.stepBack()` for the single-candle case; `goBackTo(time)` keeps
`setCurrentTime(time)` for arbitrary multi-candle seeks (future context-menu).
Common trade-revert + `_stepInFlight` guard extracted to `_revertAndSeek(time,
engineMove)`.
**Files:** `replay-controller.js` (`handleStepBack`, `goBackTo`, `_revertAndSeek`).
**Design notes:** See updated `design.md` → "Split engine-call paths".

### Verification
1. ✅ Step back once, default replay — no loading overlay flashes between candles.
2. ✅ Hold `shift+left`, default replay — continuous rewind with zero flicker.
3. ✅ Step back once, smart replay — backend PUT still fires; no extra loading
   overlay on top of the normal `updatingPosition` flag.
4. ✅ Future multi-candle `goBackTo(time)` path (not yet wired to a UI) — expected to
   still show the loading overlay since `setCurrentTime` is used there.

---

## Round 1: Initial verification (2026-04-15)

### Verification

#### A. Default replay — core flow

1. ✅ Start default replay mid-history with 3–4 trades placed across different candles.
   Click the step-back button once. Chart rewinds one candle.
2. ✅ Trade placed on the removed candle is filtered out of `trading.trades`.
3. ✅ `Position.positionFromTrades()` recalculates the open position from the remaining
   trades; position row updates accordingly.
4. ✅ Trades widget, Base Price overlay, Break-Even overlay, PnL Handle overlay, and any
   position handles re-render with the reverted state.
5. ✅ `replay.time` in Redux matches `engine.getReplayCurrentTime()` after the step.
6. ✅ Step-back at the session start candle: button is `disabled` (not merely silent) and
   clicking does nothing.
7. ✅ Step back until one candle above `startTime`, then one more step — button becomes
   disabled after the last valid step and is not clickable again.
8. ✅ Step back, then step forward (`handleStep`): the forward step restores the same
   candle position but trades are NOT re-added (step-back is destructive).

#### B. Smart replay — core flow

9. ✅ Start a backtest session with 2 backtest positions opened at different candles.
   Step back past the most recent open: backend `PUT /backtests/{id}/reset` fires
   with `{resetTo: targetTime/1000, resolution}`.
10. ✅ Backend response updates the backtest; the reverted position disappears from the
    Positions widget and from the chart overlays.
11. ✅ `triggeredAlerts` past the target time are filtered locally.
12. ✅ `updatingPosition` flag goes true during the backend call and back to false on
    completion; controls are gated during the loading window.
13. ✅ Step back to before an open position that has exit orders after the target (partial
    split): `checkResetToPossible` returns an error, a 10s-autoClose toast shows the
    message, the engine does NOT move, and `updatingPosition` stays false.
14. ✅ Simulate backend failure (offline / 500): error toast shows, engine does NOT move,
    and `updatingPosition` returns to false.
15. ✅ Step back in a finished backtest (view mode): button is disabled.
16. ✅ Resume a backtest from the widget, step back: same behavior as a fresh session.

#### C. Hotkey — single press

17. ✅ Bind `shift+left` to `replayStepBack` (default). Focus the chart, press once:
    behaves exactly like the button click.
18. ✅ `shift+left` during default replay with `isLoading=true`: no-op (hotkey respects
    the same guard as the button).
19. ✅ `shift+left` in view mode / finished backtest: no-op.
20. ✅ Confirm no collision with the crosshair arrow-keys or with any existing
    `src/actions/constants/hotkeys.js` binding on `shift+left`.

#### D. Hotkey — **held continuous step-back**

The user should be able to hold `shift+left` and watch the chart rewind continuously,
mirroring how holding `shift+right` drives continuous forward stepping. Each repeat
event must block until the previous step's position/alert processing has fully
completed so state never races.

21. ✅ **Default replay, hold `shift+left`:** chart rewinds continuously; each repeat
    fires one step-back. While a step's `trading.resetTo` + `onReplayStep` state
    update is mid-flight, the next repeat event is ignored (or queued). State is
    never observed in a torn condition — no half-reverted position, no stale
    `replay.time`.
22. ✅ **Default replay, hold `shift+left` down to session start:** rewinding stops at
    the boundary. Additional repeats are no-ops (button disabled, hotkey guarded by
    `canStepBack`). Releasing and pressing again does nothing.
23. ✅ **Default replay, hold `shift+right` (forward), release, then hold `shift+left`:**
    transition between continuous forward and continuous back works without races.
    No zombie in-flight forward step corrupting the step-back state.
24. ✅ **Smart replay, hold `shift+left`:** each repeat awaits the backend `PUT
    /backtests/{id}/reset` before the next step-back is allowed to begin. Network
    tab shows one PUT per step, serialized, never overlapping. While a PUT is in
    flight, `isLoading` / `updatingPosition` is true and the hotkey is a no-op.
25. ✅ **Smart replay, hold `shift+left` across a position-split boundary:** the
    pre-split steps succeed; the step that would split a position fails
    `checkResetToPossible`, toasts once, and the engine stops at the boundary.
    Further held repeats are no-ops.
26. ✅ **Smart replay, hold `shift+left` with simulated slow backend (throttle to 1s/req):**
    each held-key tick produces exactly one serialized PUT — not a burst of parallel
    requests. Releasing the key mid-flight lets the in-flight step complete; no
    orphan state.
27. ✅ **Smart replay, backend failure mid-hold:** first few steps succeed, one fails
    (500). Error toast shows once, hold continues firing but all subsequent repeats
    are no-ops while the error state persists; engine stays at the last successful
    step.
28. ✅ **Default replay, hold `shift+left` while alerts are being evaluated:** when an
    alert evaluation / trigger flow is running for the current candle, the next
    step-back waits for it to settle. No alert is fired "twice" and no alert is
    skipped for a candle that's being removed.

**Note on implementation — `_stepInFlight` guard.** To satisfy §D the controller
needs a re-entrancy guard (e.g. `_stepInFlight` bool or returning the in-flight
promise) around `handleStepBack`. The guard must mirror whatever pattern the
existing `handleStep` uses for continuous forward playback under `shift+right`
hold. If the forward path does not currently serialize, §D tests will expose it and
the fix should generalize to both step directions.

#### E. UI state and affordance

29. ✅ Button placement: `[⏮ back-to-start] [◀ step-back] [▶ step-forward] […]` — adjacent
    to the forward Step button, matching the existing replay-controls row layout.
30. ✅ Tooltip text is i18n-driven and includes the hotkey chord (e.g. `Step Back
    (Shift+Left)`), matching the Step forward button's tooltip pattern.
31. ✅ Icon renders `arrow-left-to-line` in both light and dark themes.
32. ✅ Disabled state: button is visibly disabled (grey) when `canStepBack` is false —
    during loading, finished, view mode, at session start.

#### F. Trading Terminal context — change mid-session

Test cases per `ai/workflow.md` requirement that features are exercised alongside
common Trading Terminal actions.

33. ✅ **Change TradingTab during an active replay session, step back on the new tab's
    chart:** the step-back uses the new tab's `ReplayController` via `ChartRegistry`,
    not the previous tab's. The previous tab's session stays untouched.
34. ✅ **Change `coinraySymbol` on the active tab:** replay engine auto-exits
    (`REPLAY_STATUS.IDLE`), step-back button is gone. Re-enter a new session and
    confirm the button re-enables correctly.
35. ✅ **Change resolution mid-session, then step back:** step-back uses the NEW
    `resolutionMs` to compute the target; the chart rewinds by one candle at the new
    resolution. Position recalculation reflects the remaining trades.
36. ✅ **Change `exchangeApiKeyId`:** for default replay, confirm step-back still
    operates on the local trades list. For smart replay, confirm the backtest is
    tied to its original exchangeApiKeyId and step-back continues to target the
    correct backtest id regardless of the current terminal API key selection.

#### G. Regressions in adjacent flows

37. ✅ `handleBackToStartClick` (restart-to-start) still works after a series of
    step-backs.
38. ✅ `handleStop` / confirmStop flow still works after step-backs; `willLoseDataIfStopped`
    correctly reflects the reverted trade/position state.
39. ✅ Toggle replay mode mid-session (default ↔ smart) after step-backs: the new
    session's `startTime` carries over correctly.
40. ✅ `ReplayModeDialog` and `_handleFirstReplay` unaffected — no regressions in the
    Phase 5 `dialogs/` scope.
