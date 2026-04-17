# Phase 5: Replay Step Back — Optimization — Tasks

PRD: `prd.md` (id `sc-replay-stepback-optimization`)
Design: `design.md`

Tasks are ordered so each commit is independently verifiable. All changes live
in two files: `smart-replay-controller.js` (primary) and `replay-controller.js`
(flush-point wiring). No UI, hotkey, or i18n work.

---

## Task 0 — Resolve design open questions

Before touching code, get user sign-off on:

1. **Open Q A — alert un-trigger (drop vs restore).** Lean Option 3 or 2 per
   design. Decision determines `_untriggerAlertsSince` body and affects review
   expectations. This is a prerequisite for Task 2.
2. Confirm R4 flush-point list (five entries) is complete for the project.
3. Confirm that `handleBackToStartClick` (smart) uses `_clearPendingReset`, not
   `_flush` — see design "Special case".

No file changes. Update `design.md` if the decisions diverge.

---

## Task 1 — Add `_pendingResetTo` field and lifecycle helpers

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/controllers/smart-replay-controller.js`

1. Add private field `_pendingResetTo = null` next to the other instance
   fields (top of `SmartReplayController`, near `_backtest` / `_lastCandle`).
2. Add `_clearPendingReset = () => { this._pendingResetTo = null }`.
3. Add `_flush = async () => { if (this._pendingResetTo == null) return; await this._flushPendingReset(this._pendingResetTo) }`
   (the private flushPendingReset ships in Task 4).
4. Wire `_clearPendingReset()` into `loadBacktest` (before the engine
   `setCurrentTime(jumpTime, endTime)` call) and into `reset()` (the
   session-teardown method at the bottom of the file).
5. Wire `_clearPendingReset()` into `destroy()` for good measure.

**Verification:** no behavioural change yet — accumulator is always null.
Sanity: app still starts, replay still works, nothing regressed. No review
items ticked.

---

## Task 2 — Add `_hasPositionsSince` and `_untriggerAlertsSince`

**File:** `smart-replay-controller.js`

1. Add `_hasPositionsSince(target)` — synchronous O(N) scan using
   `util.valueOfDate(openTime) >= target`. Return false if no backtest or
   empty positions. See `design.md` for the exact body.
2. Add `_untriggerAlertsSince(target)` — implementation depends on Task 0
   decision:
   - **If Option 2/3 (restore):** move `triggeredAlerts` with `updatedAt >= target`
     back into `alerts`, strip `updatedAt`, then `_setSession` both.
   - **If Option 1 (drop, current behaviour):** just filter `triggeredAlerts`
     and `_setSession` the filtered list. Same as today's `resetTo`.
3. Both methods are private (underscore-prefixed arrow functions), no toasts,
   no awaits.

**Verification:** still no behavioural change — these are unused until
Task 3.

---

## Task 3 — Branch `smart.resetTo` on dirty/quiet

**File:** `smart-replay-controller.js`

Replace the body of `resetTo = async (time) => { ... }` with the new branch
(see `design.md` → "Modified `smart.resetTo(time)` contract"):

1. Keep the `checkResetToPossible` guard at the top, unchanged.
2. Compute `newTarget = Math.min(this._pendingResetTo ?? Infinity, time)`.
3. Check `_hasPositionsSince(newTarget)`.
4. **Dirty branch:** `await this._flushPendingReset(newTarget)`. Do NOT
   include a `_pendingResetTo = null` here — `_flushPendingReset` clears it
   internally (Task 4).
5. **Quiet branch:** `this._untriggerAlertsSince(newTarget)`; then
   `this._pendingResetTo = newTarget`.
6. Return `undefined` on success (unchanged contract).
7. Do NOT set `updatingPosition` on the quiet branch. The dirty branch's
   loading state is owned by `_flushPendingReset`.

**Verification:** Task 4 finishes the dirty path; until then, dirty
step-backs will fail because `_flushPendingReset` doesn't exist. Do Task 4
in the same commit.

---

## Task 4 — Implement `_flushPendingReset`

**File:** `smart-replay-controller.js`

Body per `design.md` → "_flushPendingReset(target)":

1. Compute `flushTarget = Math.min(this._pendingResetTo ?? Infinity, target)`.
2. Clear `_pendingResetTo = null` BEFORE the await (so concurrent re-entry
   sees a clean accumulator).
3. Return early if `flushTarget` is not finite.
4. `setUpdatingPosition(true)` inside a `try/finally`.
5. Compute new `triggeredAlerts` (filter `< flushTarget`) and `restored`
   (filter `>= flushTarget`, strip `updatedAt`).
6. `_setSession({alerts: [...this.alerts, ...restored], triggeredAlerts})`
   — only if Task 0 decision is Option 2/3. Under Option 1, only
   `triggeredAlerts` is patched.
7. `await this._resetBacktest(this._backtest.id, flushTarget)`; on success
   `await this.updateBacktest(backtest)`.
8. Errors propagate (outer `_revertAndSeek` catches — same contract as
   base).
9. `finally: await this.setUpdatingPosition(false)`.

**Verification after Task 3 + 4 together:**
- Smart replay, single step-back on a quiet candle → NO backend PUT in
  network tab, no loading flicker.
- Smart replay, single step-back across a position boundary → ONE backend
  PUT, position reverted, `updatingPosition` flickers once.
- Smart replay, step back → play forward → same candle → no duplicate
  alerts, position history matches un-optimized base behaviour.
- Held `shift+left` across 10 quiet candles → 0 backend PUTs, 0 flickers,
  10 visible rewinds.

---

## Task 5 — Wire flush point into `_processTriggerAsync` (clear on forward)

**File:** `smart-replay-controller.js`

In `_processTriggerAsync = async (triggerHit, wasPlaying) => { ... }`, add
`this._clearPendingReset()` as the first line (before `await this.checkAlerts()`).

**Why here:** this is the only forward-path method that touches backend
state. Clearing the accumulator here covers the "user rewinds, then plays
forward past the rewind target" case. The trigger's own backend call
advances `last_candle_seen_at` correctly.

**Verification:**
- Smart replay, step back 5 quiet candles, play forward past them, let a
  trigger fire → backend PUT fires at the trigger time, position opens
  correctly, no stale pending state lingers.

---

## Task 6 — Wire flush into `ReplayController.handleStop`

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js`

1. At the top of `handleStop = async (callback, {keepEngine} = {}) => { ... }`,
   before any existing logic, add:
   ```js
   if (this.replayMode === REPLAY_MODE.SMART && this.smart) {
     await this.smart._flush()
   }
   ```
2. Grep for `handleStop` callers — all go through user action (button /
   hotkey) so there's no auto-call path to worry about.

**Verification:**
- Smart replay, step back 3 quiet candles, click Exit → confirmation,
  confirm → exactly ONE backend PUT at the flush point (at the earliest
  stepped-back time), session ends correctly.
- Smart replay, step back 3 quiet candles, click Exit → cancel → pending
  state intact (not flushed because user cancelled). Next action still
  batches correctly.
- Backtests widget shows `last_candle_seen_at` at the stepped-back time.

---

## Task 7 — Wire clear into `handleBackToStartClick`

**File:** `replay-controller.js`

At the top of `handleBackToStartClick = async (autoPlay = false) => { ... }`,
in the smart branch (before the existing restart logic), add
`this.smart?._clearPendingReset()`.

**NOT a flush** — the restart itself issues a backend `/reset(startTime)`
which subsumes any pending target (startTime is the earliest possible
value).

**Verification:**
- Smart replay, step back 3 quiet candles, click Back to Start → exactly
  ONE backend PUT (the existing restart call at `startTime`), no double
  call. Session restarts at `startTime`.

---

## Task 8 — Wire flush into `exitSmartMode`

**File:** `smart-replay-controller.js`

At the top of `exitSmartMode = async () => { ... }`, before the backtest
teardown, add `await this._flush()`.

**Verification:**
- Smart session, step back 2 quiet candles, click Toggle Replay Mode →
  ONE backend PUT fires (the flush), backtest persisted with stepped-back
  `last_candle_seen_at`, default mode starts from the current engine time.
- Resume the backtest from the widget → lands at the stepped-back
  position, not the pre-stepback position.

---

## Task 9 — Wire flush into trade API methods

**File:** `smart-replay-controller.js`

Add `await this._flush()` as the first line of each:

1. `submitBacktestPosition`
2. `cancelBacktestPosition`
3. `increaseBacktestPosition`
4. `reduceBacktestPosition`

NOT added to `submitBacktestAlert` / `cancelBacktestAlert` — local-only,
no backend call involved.

**Verification:**
- Smart replay, step back 3 quiet candles, place a new position (buy
  button) → TWO backend calls in order: (1) `/reset` at the stepped-back
  time, (2) `/positions` create for the new position. Position's
  `openTime` on the server equals the new engine current time, NOT the
  stale pre-stepback time.
- Smart replay, step back 3 quiet candles, cancel an existing position →
  same sequence, cancel lands at the correct time.

---

## Task 10 — Wire flush into `_stop({keepEngine})`

**File:** `replay-controller.js`

If `_stop` is reachable via a path that bypasses `handleStop` (e.g.
`handleSwitchReplayMode`), add a `_flush` guard at the top of `_stop`:

```js
if (this.replayMode === REPLAY_MODE.SMART && this.smart) {
  await this.smart._flush()
}
```

Grep for `_stop(` call sites first. If all paths to `_stop` already go
through `handleStop` (which was hooked in Task 6), skip this task and note
in the commit that `_stop` is already covered transitively.

**Verification:**
- Toggle Replay Mode (smart → default): flush fires, backtest persisted
  with stepped-back state.
- Any other `_stop` path: pending state is flushed before teardown.

---

## Task 11 — Wire clear into `_startSession`

**File:** `replay-controller.js`

At the top of `_startSession = async (startTime, mode, {endTime} = {}) => { ... }`,
add `this.smart?._clearPendingReset()`.

**Why:** a new session starts clean — no pending state from a previous
session should leak in. Defensive; in practice the session-teardown path
should already have cleared it, but this guards against any reset path
that forgets.

**Verification:**
- Start a smart session, step back, exit, start a new smart session →
  new session's `_pendingResetTo` starts null. (Hard to observe directly;
  covered by the sequence tests in later tasks.)

---

## Task 12 — Review pass

**File:** create `ai/superchart-integration/phase-5/stepback-optimization/review.md`

Walk through the PRD's R1–R7 + the Trading Terminal context cases. Suggested
checklist, numbered for reference:

### A. Quiet step-back — no backend
1. Default replay, step back 5 candles (no trades) — zero network calls (baseline).
2. Smart replay empty session, step back 5 candles — zero `/reset` PUTs.
3. Smart replay with 1 position far back, step back 5 candles not reaching it — zero `/reset` PUTs.
4. `updatingPosition` never flips during 1–3.

### B. Dirty step-back — one backend call
5. Smart replay, 3 positions opened at candles C1 < C2 < C3. Step back past C3 (nothing else in between) — ONE PUT, position at C3 gone.
6. Step back 2 quiet + 1 dirty in sequence — ONE PUT when the dirty candle is crossed, `newTarget` equals the earliest (quiet) target.
7. Held `shift+left` across 10 quiet + 1 dirty at the end — ONE PUT, positions destroyed match un-optimized behaviour.

### C. Alert un-trigger (decision-dependent)
8. Smart replay, trigger a price alert on candle C. Step back past C. Alert is restored to active (Option 2/3) OR disappears (Option 1). Next forward play re-triggers or not accordingly.
9. Candle-boundary alert test: alert fires exactly at C's close. Step back to C. Window check does NOT un-trigger (per off-by-one analysis in design Open Q B). Step back to C-1. Window check DOES un-trigger.

### D. Flush points
10. `handleStop` flush: step back 3 quiet, exit — ONE PUT with earliest target.
11. `handleStop` cancel: step back 3 quiet, Exit → cancel dialog — zero PUTs, pending intact.
12. `handleBackToStartClick`: step back 3 quiet, back-to-start — ONE PUT at `startTime`, no double call.
13. `exitSmartMode` (toggle replay mode): step back 3 quiet, toggle — ONE PUT, backtest persisted at stepped-back time.
14. `submitBacktestPosition` flush: step back 3 quiet, place position — TWO calls in order (reset + create), new position at current engine time.
15. `cancelBacktestPosition` flush: same as 14 but cancel.
16. `increaseBacktestPosition` flush: same.
17. `reduceBacktestPosition` flush: same.
18. Alert ops do NOT flush: step back 3 quiet, create a price alert → zero PUTs.

### E. Clear points
19. `_processTriggerAsync` clear: step back 3 quiet, play forward past them, let trigger fire — trigger's own PUT fires, no extra flush.
20. `_startSession` clear: exit session, start new session — new session's pending is null (verify via lack of stale flush on first step-back).
21. `loadBacktest` clear (resume from widget): after a flushed exit, resume backtest — pending starts null.

### F. R6 — behavioural equivalence
22. Full sequence with optimization off (temporarily) vs on: backtest positions destroyed at session end match exactly.
23. `last_candle_seen_at` on the server matches the stepped-back engine time after any flush point is hit.
24. Resume from widget after flush lands at the stepped-back position.

### G. R7 — held-key performance
25. Held `shift+left` across 30 quiet candles: 0 PUTs, 0 `updatingPosition` flashes, ~30 rewinds observed.
26. Network tab throttled to 1s/req + 30-candle held rewind: still 0 PUTs until flush.

### H. Trading Terminal context
27. Change TradingTab during pending state: pending is per-controller (per chart), so the new tab starts with null and the old tab's pending is preserved when switching back.
28. Change symbol / resolution mid-pending: symbol change exits replay — `_startSession` clear fires on re-entry. Resolution change is engine-only — pending stays valid across resolutions (same backtest, same `open_time` values).
29. Change `exchangeApiKeyId`: replay-side unaffected, pending intact.

### I. Edge cases
30. Step back past `checkResetToPossible` partial split: toast fires, pending UNCHANGED, engine does NOT move. Subsequent step-backs still batch correctly from the unchanged pending state.
31. Backend failure on a dirty flush (simulate 500): error toast fires, `_pendingResetTo` state after failure — should be cleared (already cleared before await per Task 4) so the next step-back starts fresh on the local-only path.
32. `goBackTo(arbitrary time)` multi-candle jump (once wired to a UI): same branching applies, no regression.
33. Smart replay in view mode (finished backtest): `canStepBack` is false, never reaches the branch.
34. Session ends via `onReplayStatusChange(FINISHED)` — does any path trigger a flush? Trace: finished transition → `setBacktestFinished` → `updateBacktest`. No `_flush` call. Verify that a pending state at the moment of natural session end is either (a) impossible because forward playback clears it in `_processTriggerAsync`, or (b) handled by an explicit flush in `setBacktestFinished`. If (b), add to Task 6/8 list — otherwise document as a known-null case.

Each item gets ✅ when verified. Failures go into a `## Round N` section per
workflow format.

---

## Out-of-task items

- Backend endpoint for "just update `last_candle_seen_at`" (no destroy) —
  would allow flushing quiet rewinds cheaply but still incur a round-trip.
  Not pursued per PRD Non-Requirements.
- Per-step detection window widened to include pre-session orders / open
  positions that span the window — not needed, `checkResetToPossible`
  already rejects partial-split step-backs before the branch is reached.
- Batch-on-timer / debounce flush — unnecessary, accumulator collapses
  consecutive quiet steps and `_stepInFlight` serializes naturally.
- User-facing indicator that a flush is pending ("unsaved rewind" badge) —
  defer unless users request it.
