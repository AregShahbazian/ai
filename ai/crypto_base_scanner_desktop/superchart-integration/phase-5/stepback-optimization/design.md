# Phase 5: Replay Step Back — Backend-Call Optimization — Design

PRD: `prd.md` (id `sc-replay-stepback-optimization`)
Base feature: `../stepback/prd.md` (id `sc-replay-stepback`)

---

## Goal recap

On smart replay, skip the `PATCH /backtests/:id/reset` round-trip when a
step-back removes a "quiet" candle — no backtest position opened in the removed
window, no triggered alert fired in the removed window. Accumulate the earliest
quiet target in a controller field and flush it on session-ending actions or
before any trade API call.

Forward-path already has this asymmetry (`updateCurrentState` returns early
when neither `triggerHit` nor `alertWillFire`). Step-back should match.

---

## Architecture overview

Current flow — every step-back calls backend:

```
_revertAndSeek(time, engineMove)
 └── smart.resetTo(time)
      ├── checkResetToPossible(time)          // local validation
      ├── setUpdatingPosition(true)            // UI loading flicker
      ├── triggeredAlerts filter                // local
      ├── _resetBacktest(id, time)              // BACKEND PUT — always
      └── updateBacktest(...)                   // stats refresh
```

New flow — branches on "is anything to revert in the removed window":

```
_revertAndSeek(time, engineMove)
 └── smart.resetTo(time)
      ├── checkResetToPossible(time)                                           // unchanged
      ├── newTarget = min(_pendingResetTo ?? ∞, time)                           // accumulator
      ├── dirty = hasPositionsSince(newTarget)                                  // local check
      ├── if dirty:
      │    ├── _flushPendingReset(newTarget)                                    // backend PUT
      │    └── _pendingResetTo = null
      ├── else:
      │    ├── untriggerAlertsSince(newTarget)                                  // local only
      │    └── _pendingResetTo = newTarget
      └── (engine move happens in _revertAndSeek outer)
```

The accumulator is the only new piece of state. Everything else is branching
on a local-array scan and routing the existing `_resetBacktest` call through
one new flush helper.

---

## `_pendingResetTo` field

```js
// SmartReplayController
_pendingResetTo = null  // ms timestamp, or null if nothing pending
```

Semantics:
- `null` — no pending work, backend is in sync with engine time
- `T` (ms) — backend thinks the session is at a time ≥ T, but the user has
  visually rewound to T. A flush at any time ≥ T will bring them back in sync.

Earliest-wins because step-back is monotonic — each quiet step-back moves the
target earlier, never later. Forward playback resets the accumulator (see
"Clear points" below).

---

## Modified `smart.resetTo(time)` contract

Existing contract (post-base feature):
- Returns `undefined` on success, throws on backend error, returns validation
  error (React node) when partial split detected.

New contract — unchanged from caller's perspective. Internal branching:

```js
resetTo = async (time) => {
  const resetError = this.checkResetToPossible(time)
  if (resetError) return resetError

  const newTarget = Math.min(this._pendingResetTo ?? Infinity, time)
  const dirty = this._hasPositionsSince(newTarget)

  if (dirty) {
    await this._flushPendingReset(newTarget)
  } else {
    this._untriggerAlertsSince(newTarget)
    this._pendingResetTo = newTarget
  }
}
```

No `setUpdatingPosition` on the quiet path. The UI loading flicker the PRD
calls out in R7 is eliminated by NOT flipping `updatingPosition` when nothing
is going to the backend.

`_flushPendingReset` keeps the `setUpdatingPosition(true/false)` wrap — the
brief loading state on a dirty step-back is the same as the current base
behaviour.

---

## New private methods

### `_hasPositionsSince(target)`

O(N) scan of `this._backtest.backtestPositions` where N ≈ number of positions
opened during the session (typically < 50). Synchronous, no network.

```js
_hasPositionsSince = (target) => {
  if (!this._backtest) return false
  return this._backtest.backtestPositions.some(({openTime}) =>
    util.valueOfDate(openTime) >= target
  )
}
```

Uses `util.valueOfDate(openTime)` to match the existing pattern in
`checkResetToPossible` (`smart-replay-controller.js:669`). `openTime` is an ISO
string or Date; `valueOfDate` normalizes to ms.

**Boundary:** `>= target`. Matches the backend's
`backtest_positions.where("open_time >= ?", reset_to).destroy_all` inclusive
semantic — a position with `open_time === target` IS destroyed by a real
flush, so it must also trigger the dirty branch.

### `_untriggerAlertsSince(target)`

Move entries from `triggeredAlerts` back to `alerts` (active) when their
`updatedAt >= target`. Clears `updatedAt` on the restored entries so a future
re-trigger on the forward path sets a fresh value.

```js
_untriggerAlertsSince = (target) => {
  const affected = this.triggeredAlerts.filter(({updatedAt}) => updatedAt >= target)
  if (!affected.length) return
  const keepTriggered = this.triggeredAlerts.filter(({updatedAt}) => updatedAt < target)
  const restored = affected.map(({updatedAt, ...alert}) => alert)
  this._setSession({
    alerts: [...this.alerts, ...restored],
    triggeredAlerts: keepTriggered,
  })
}
```

**This is a behaviour change from the base feature.** The current `resetTo`
(post-base) does:

```js
const triggeredAlerts = this.triggeredAlerts.filter(({updatedAt}) => updatedAt < time)
this._setSession({triggeredAlerts})
```

— i.e. it DROPS the affected alerts instead of restoring them. See "Open
question A" below. If we want to preserve the drop-on-reset behaviour exactly,
replace the body of `_untriggerAlertsSince` with just the filter and remove the
`alerts: [...]` patch.

**Boundary:** `updatedAt` is written as `this._currentActualTime` on trigger
(`checkAlerts` line 535), which is `_currentTime - 1000` (ms). `target` is the
new engine current time. `updatedAt >= target` filters alerts whose trigger
time sits in the `[target, old_current]` window. Same category as the default
trade filter bug from the base feature's review Round 3 — verify with a test
case that places an alert on the exact candle boundary.

### `_flushPendingReset(target)`

Fold the accumulator into a target and call the backend. Returns the updated
backtest or propagates errors (same throw behaviour as the existing
`_resetBacktest`).

```js
_flushPendingReset = async (target) => {
  const flushTarget = Math.min(this._pendingResetTo ?? Infinity, target)
  this._pendingResetTo = null
  if (!Number.isFinite(flushTarget)) return

  await this.setUpdatingPosition(true)
  try {
    const triggeredAlerts = this.triggeredAlerts.filter(({updatedAt}) => updatedAt < flushTarget)
    const restored = this.triggeredAlerts.filter(({updatedAt}) => updatedAt >= flushTarget)
      .map(({updatedAt, ...alert}) => alert)
    this._setSession({
      alerts: [...this.alerts, ...restored],
      triggeredAlerts,
    })
    const backtest = await this._resetBacktest(this._backtest.id, flushTarget)
    if (backtest) await this.updateBacktest(backtest)
  } finally {
    await this.setUpdatingPosition(false)
  }
}
```

Matches the existing `resetTo` side effects (alert filter + `_resetBacktest`
+ `updateBacktest`) plus the un-trigger behaviour from
`_untriggerAlertsSince`. This is the single place a backend `/reset` call
lives after the optimization — every dirty path and every flush point routes
through here.

### `_flush()` — public entry for flush points

Idempotent wrapper for external callers (`ReplayController.handleStop` etc).
No-op if `_pendingResetTo == null`.

```js
_flush = async () => {
  if (this._pendingResetTo == null) return
  await this._flushPendingReset(this._pendingResetTo)
}
```

All five flush points in the PRD R4 list call this.

### `_clearPendingReset()` — drop without flushing

Used on session start and on forward playback past the pending target.

```js
_clearPendingReset = () => { this._pendingResetTo = null }
```

---

## Flush points (R4)

Each of these MUST `await smart._flush()` before doing its existing work:

| Caller | Where | Why |
|---|---|---|
| `ReplayController.handleStop` | Top of the method, before `confirmStop` | Session ends, pending target must hit backend so resume shows the stepped-back state |
| `ReplayController.handleBackToStartClick` | Top, before the restart logic | Restart re-seeks the engine; stale pending target must be flushed first (or explicitly discarded — see below) |
| `SmartReplayController.exitSmartMode` | Top, before backtest teardown | Mode switch leaves the backtest persisted on backend; pending must land first |
| Trade API calls | Top of each | Each trade action uses `_currentActualTime` as the position's `open_time` — if backend is ahead of engine, the new position lands at the wrong time |
| `ReplayController._stop({keepEngine})` | Already covered if it goes through `_flush` — verify path from `handleSwitchReplayMode` | Covers the `handleStop` → `_stop` chain plus the direct `_stop` from mode switch |

**Trade API hook — which methods?** All four backtest-write methods on
`SmartReplayController`:

- `submitBacktestPosition`
- `cancelBacktestPosition`
- `increaseBacktestPosition`
- `reduceBacktestPosition`

Plus alert ops that write backend state? No — `submitBacktestAlert` /
`cancelBacktestAlert` are local-only (no API call, just `setAlerts` +
`loadBacktestTradingInfo`). They don't need a flush.

**Hook implementation:** add a single `await this._flush()` as the first line
of each of the four backtest-write methods. Cleaner than wrapping in a helper
— the call sites are already long and the flush is cheap when pending is
null.

### Implementation correction (during Task 6/7/10)

The design initially planned to special-case `handleBackToStartClick` with
`_clearPendingReset` instead of `_flush`, on the assumption that the smart
restart issues its own `/reset(startTime)` which subsumes any pending
target.

**That assumption was wrong.** Reading `replay-controller.js:573`, the
smart branch of `handleBackToStartClick` does `await this._stop()` then
`await this.smart.quickStartBacktest({replayStartAt, replayEndAt})` — it
creates a **new** backtest. The old backtest is left on the server in
whatever state it was last synced to. Without a flush, the orphaned
backtest keeps a stale `last_candle_seen_at` (the pre-stepback value),
violating PRD R6.

Same reasoning applies to `_startReplayInMode` (cross-mode restart at
line 454) which also calls `_stop()` then starts a fresh session.

**Centralized fix.** Instead of adding `_flush` calls at each of the three
`_stop` call sites (`handleStop`, `handleBackToStartClick`,
`_startReplayInMode`), add a single flush at the TOP of `_stop` itself:

```js
_stop = async ({keepEngine = false} = {}) => {
  if (!this._replayEngine) return
  if (this.replayMode === REPLAY_MODE.SMART && this.smart) {
    await this.smart._flush()
  }
  // ... existing teardown
}
```

This must run before `this.smart.reset()` because `reset()` clears
`_pendingResetTo` — a flush after `reset` would be a no-op.

**Effect on Tasks 6/7/10:** Task 6 (`handleStop`), Task 7 (`handleBackToStartClick`),
and Task 10 (`_stop`) collapse into a single edit in `_stop`. `exitSmartMode`
still needs its own explicit flush (Task 8) because it doesn't go through
`_stop`.

---

## Clear points (R5)

`_pendingResetTo` is cleared (not flushed) on:

1. **Session start** — `_startSession` (default/smart entry) and
   `SmartReplayController.loadBacktest` (resume from widget). Fresh session,
   no pending state.
2. **Successful flush** — handled inside `_flushPendingReset` (sets to
   `null` before awaiting the backend call so re-entry during the await sees
   a clean state).
3. **Forward playback past the pending target** — when the forward path
   would otherwise hit `_processTriggerAsync`, the pending target is stale
   by definition (the user played forward past it, the positions that would
   have been destroyed are now real again).

For case 3, the hook point is `_processTriggerAsync` at the first forward
trigger after a pending step-back. But — subtlety — the trigger's own
`triggerBacktest` will call the backend, and the backend's
`last_candle_seen_at` is still the OLD (pre-step-back) value. So the
trigger call will simply advance `last_candle_seen_at` from that old value
to the new, higher value. This is consistent — no flush needed, just clear
the accumulator to drop the stale target.

```js
// In _processTriggerAsync, before `if (triggerHit)` block:
this._clearPendingReset()
```

Or more defensively, anywhere the engine advances forward past the pending
target:

```js
// In the onReplayStep handler, direction === "forward" branch:
if (this._pendingResetTo != null && this.time > this._pendingResetTo) {
  this._clearPendingReset()
}
```

**Decision:** clear inside `_processTriggerAsync` only. The forward path's
per-step hook would add overhead on every candle and the only observable
effect of a stale pending target during forward playback is the next
backend call (via `_processTriggerAsync`) picking up a slightly-stale
accumulator — which is cheap to handle at that moment.

---

## `_stepInFlight` interaction

The base feature's `_stepInFlight` guard in `_revertAndSeek` already
serializes step-back calls. The optimization inherits this unchanged — each
step-back completes (including any flush or local un-trigger) before the
next starts.

One subtlety: on a quiet step-back, the `smart.resetTo` path no longer
awaits the backend. It becomes essentially synchronous (`setSession` +
field assignment). That means held-`shift+left` repeats drain much faster
— `_stepInFlight` goes true → false in a microtask, not a 100ms network
round-trip. This is the intended R7 behaviour and matches held-`shift+right`
on forward playback.

---

## `updatingPosition` flicker removal (R7)

The PRD R7 says held-key continuous rewind should produce zero
`updatingPosition` flashes. Achieved by:

- Quiet branch does NOT call `setUpdatingPosition(true)` — it skips the
  backend and the UI loading flag.
- Dirty branch still calls `setUpdatingPosition(true)` inside
  `_flushPendingReset` — one flicker per real backend call, unchanged from
  base behaviour.

Held-key rewind through N quiet candles = 0 flickers. Held-key rewind
through a mix (Q quiet, D dirty) = D flickers. Held-key rewind through N
dirty candles = D flickers — but with accumulator batching, multiple
consecutive dirty step-backs still collapse into a single backend call IF
the user's held-key fires them fast enough that subsequent step-backs see
`_pendingResetTo` already set by the first quiet prefix. In practice each
dirty step-back flushes immediately, so dirty candles don't batch.

---

## Files touched

**Controller code**
- `src/containers/trade/trading-terminal/widgets/super-chart/controllers/smart-replay-controller.js`
  - Add `_pendingResetTo` field
  - Add `_hasPositionsSince`, `_untriggerAlertsSince`, `_flushPendingReset`,
    `_flush`, `_clearPendingReset`
  - Modify `resetTo` to branch
  - Modify `_processTriggerAsync` to clear accumulator
  - Modify `loadBacktest` / session-start path to clear accumulator
  - Modify `exitSmartMode` to flush before teardown
  - Modify `submitBacktestPosition`, `cancelBacktestPosition`,
    `increaseBacktestPosition`, `reduceBacktestPosition` to flush first
- `src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js`
  - `handleStop` — flush before proceeding (if smart mode)
  - `handleBackToStartClick` — clear (not flush) before the restart flow
    (smart mode only)
  - `_stop({keepEngine})` — flush before teardown (if smart mode)
  - `_startSession` — clear accumulator

**No changes to:**
- `ReplayEngine` / SC library — accumulator is purely Altrady-side
- `ReplayTradingController` — default replay is already fully local
- Backend `/reset` endpoint — semantics unchanged
- `_revertAndSeek` or `handleStepBack` / `goBackTo` — they still call
  `smart.resetTo`; the branching is internal to `resetTo`
- UI (`replay-controls.js`) — no new buttons, no new affordances

---

## Open questions

### A. Alert un-trigger: drop vs restore

**Status:** Behaviour discrepancy between base feature and this optimization.

Current base `smart.resetTo` (`smart-replay-controller.js:698`) drops
triggered alerts when stepping back past them:

```js
const triggeredAlerts = this.triggeredAlerts.filter(({updatedAt}) => updatedAt < time)
this._setSession({triggeredAlerts})
```

— the filter removes them from `triggeredAlerts` but does NOT add them back
to `alerts` (active). So stepping back past a triggered alert makes it
disappear entirely.

This optimization PRD R2 says "move matching entries from `triggeredAlerts`
back into `alerts`" — the inverse of the forward-path trigger. That's
behaviourally nicer (user can re-trigger on the next forward play) but
it's a change from current behaviour.

**Options:**
1. **Preserve current (drop) behaviour.** Match base for semantic parity
   with R6, defer the restore fix to a separate PRD.
2. **Fix as part of this optimization.** Restore alerts to active, clear
   `updatedAt`. Means this PRD changes observable behaviour beyond pure
   optimization.
3. **Fix as a preparatory base-feature patch.** Change base `resetTo` to
   restore (matching R2), then this optimization inherits correct behaviour.

**Lean:** Option 3, but it's cheap enough to do inline (Option 2). Needs
user sign-off before implementation — flagged for the design review.

### B. `updatedAt` off-by-one at candle boundary

`updatedAt` is written as `_currentActualTime` (= `_currentTime - 1000` ms).
`target` in the window check is the new engine current time (`_currentTime`
after the step-back). Same category as the Round 3 bug in the base feature
— the `- 1000` offset needs a consistent comparison.

Concretely: an alert fires at `_currentTime = T_candle_close` (e.g. 08:00
UTC for a 1h candle whose close is 08:00) and stores
`updatedAt = T_candle_close - 1000` (= 07:59:59).

If the user steps back to engine time `T_candle_close - 3600000`
(= 07:00:00, the previous candle close), the window check
`updatedAt >= target` evaluates `07:59:59 >= 07:00:00` → true → un-trigger.
Correct.

If the user steps back to engine time `T_candle_close`
(= 08:00:00, same candle we're on), window check: `07:59:59 >= 08:00:00` →
false → keep triggered. Also correct — stepping back to the same candle
that triggered the alert keeps the alert triggered.

**Conclusion:** the `>=` comparison is correct for alerts. Verify with a
test case placing an alert to fire on candle C, stepping back from C+1 to
C exactly, and confirming the alert is restored.

**Edge case:** trendline alerts and price alerts also use `_currentActualTime`
to set `updatedAt` (see `checkAlerts` line 535 — single assignment for all
types). Same math applies.

### C. Resolution change mid-session (from earlier conversation)

Not added to R4 flush points. Verified during design: the resolution-change
handler in SC is purely engine-side (re-fetch candles at new resolution,
client-side re-seek). No backend call touches `last_candle_seen_at` on
resolution change. No flush needed.

If a future feature adds a backend sync on resolution change, revisit this.

### D. Flush-point hook granularity for trade actions

Four methods get the hook (submit/cancel/increase/reduce position).
`submitBacktestAlert` / `cancelBacktestAlert` do NOT — they're local-only.

**Risk:** if a future backend-sync is added to alert ops (e.g. time alerts
that need server-side scheduling), the hook list needs to grow. Flag in
the review checklist.

---

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Flush point missed, backend state stale on session end | Enumerated list in `design.md` + review checklist item per flush point |
| Position `open_time` unit mismatch | Use `util.valueOfDate()` — same pattern as existing `checkResetToPossible` |
| Alert off-by-one at candle boundary | Explicit test case in review (see Open Q B) |
| Concurrent step-back during a mid-flight flush | `_stepInFlight` already serializes — flush completes before next step-back enters |
| User holds shift+left across a dirty candle, expects all previous quiet steps to have no backend cost | Accumulator collapses quiet prefix into the single flush call when the dirty candle is hit — R7 holds for the quiet portion |
| Resume from widget after browser crash loses pending rewind | Acknowledged data loss (PRD Open Q 4). Document in release notes. |
