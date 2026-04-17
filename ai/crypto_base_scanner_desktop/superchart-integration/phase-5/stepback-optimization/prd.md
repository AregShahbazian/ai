---
id: sc-replay-stepback-optimization
---

# Phase 5: Replay Step Back — Backend-Call Optimization

Follow-up to `../stepback/prd.md` (id `sc-replay-stepback`). The base step-back
feature unconditionally calls the backend `PATCH /backtests/:id/reset` endpoint on
every smart-mode step-back, even when the candle being removed has no backtest
positions and no triggered alerts. Holding `shift+left` across many "quiet" candles
produces N backend round-trips where 0 are strictly needed, and each call flashes
the `updatingPosition` loading state.

This PRD mirrors the existing forward-playback pattern where the backend is only
touched on trigger/alert hits, and defers work until it's actually needed.

---

## Motivation

Current base behaviour (smart replay only — default replay is already fully local):

- Every step-back awaits `smart.resetTo(time)` → `_resetBacktest` → backend PUT
- Every call updates `last_candle_seen_at`, destroys matching positions, refreshes
  stats, and returns the updated backtest
- `updatingPosition` flips to `true` → `false` each step, driving a brief UI
  loading state
- Held-key continuous rewind is rate-limited by backend latency

Forward playback already skips backend on quiet candles
(`smart-replay-controller.js:560`):

```js
if (!triggerHit && !alertWillFire) return
```

Step-back should achieve the same asymmetry: local-only until something actually
needs reverting.

---

## Scope

### In scope

- Local detection of "is there anything to revert in the removed candle"
- Local un-trigger of alerts whose `updatedAt` falls in the removed window (move
  back from `triggeredAlerts` to active `alerts`)
- Deferred `last_candle_seen_at` sync via a `_pendingResetTo` accumulator
- Flush of pending reset on session-ending actions
- Apply to both the single-candle step-back button and the future multi-candle
  `goBackTo(time)` jump

### Out of scope

- Default replay — already fully local, nothing to optimize
- Changes to the backend `/reset` endpoint
- Changes to how positions / triggered alerts are created or tracked on the
  forward path
- New user-facing controls or settings

---

## Requirements

### R1: Local "needs revert" detection

On each step-back, compute the removed candle window
`[newCurrentTime, oldCurrentTime)`. Before touching the backend, check locally:

- **Positions check:** does any entry in `backtest.backtestPositions` have
  `open_time` in the window?
- **Triggered alerts check:** does any entry in `triggeredAlerts` have
  `updatedAt` in the window?

Both checks are synchronous, O(N) where N is small (typically < 100 over a full
session). No network.

### R2: Branching on detection result

| Positions in window | Alerts in window | Behaviour |
|-|-|-|
| No | No | Skip backend. Just move the engine. Accumulate `_pendingResetTo`. |
| No | Yes | Skip backend. Un-trigger alerts locally. Move engine. Accumulate `_pendingResetTo`. |
| Yes | No or Yes | Flush (`_pendingResetTo ∪ newTime → one backend call`). Backend returns updated backtest which clears the positions server-side and updates `last_candle_seen_at`. Move engine. |

Local un-trigger means: move matching entries from `triggeredAlerts` back into
`alerts` (the active list), clearing their `updatedAt`. This is the inverse of
the existing forward-path logic that moves alerts from `alerts` → `triggeredAlerts`
on hit.

### R3: `_pendingResetTo` accumulator

A private field on `SmartReplayController`:

```js
_pendingResetTo = null  // earliest "quiet" step-back target since last flush
```

On each quiet step-back: `_pendingResetTo = min(_pendingResetTo ?? Infinity, newTime)`.
On each "dirty" step-back (backend call): `flushPendingReset()` folds the
accumulator into the reset target, then clears it.

Earliest-wins semantics: stepping back is monotonic (time only decreases), so the
earliest pending target is the one that captures the full pending rewind.

### R4: Flush points

`_pendingResetTo` must be flushed (sent as a final `smart.resetTo` call) before
any operation that reads or advances `last_candle_seen_at` server-side, or that
ends the session while it's non-null:

- `ReplayController.handleStop` (user exits session)
- `ReplayController.handleBackToStartClick` (restart)
- `SmartReplayController.exitSmartMode` (mode switch)
- Before any trade-widget order placement (cancel / reduce / increase / new
  position / new order) so the position lands at the user-visible time, not the
  stale backend time. Hook this via `ReplayController.replaySafeCallback` or a
  new `_beforeTradeAction` helper.
- `ReplayController._stop({keepEngine})` — covers the `handleSwitchReplayMode`
  path too.

Not required on:
- Forward step / play — position ops inside `_processTriggerAsync` will naturally
  advance `last_candle_seen_at` via `backtest.trigger(...)`, and the pending
  rewind target is stale by definition once the user plays forward past it. On
  the first forward `_processTriggerAsync`, we clear `_pendingResetTo` without
  flushing — the forward path's own backend call will overwrite the field
  anyway.

### R5: Reset accumulator lifecycle

Clear (without flushing) on:
- Session start (`_startSession` / `loadBacktest`) — new session, no pending
  state
- Any forward playback event that advances the engine past the pending target —
  the pending target is stale
- After a successful flush

### R6: Behaviour preservation

With the optimization enabled, step-back MUST remain semantically equivalent to
the current un-optimized behaviour from the user's point of view:

- After any sequence of step-backs followed by any session-ending action
  (stop / restart / exit mode / order placement), the backend state must match
  what an un-optimized sequence would have produced
- Backtest positions destroyed by a flushed reset must match what the
  un-optimized sequence would have destroyed
- Triggered alerts un-triggered locally must match the set that the un-optimized
  `smart.resetTo` would have filtered out
- Resume from the Backtests widget after a flushed session must land the engine
  at the stepped-back position, not the pre-step-back position

### R7: Forward-symmetry guarantee

Holding `shift+left` across N consecutive quiet candles must produce:
- **0 backend calls** (until flush)
- **0 `updatingPosition` flashes**
- N `engine.stepBack()` calls (serialized via `_stepInFlight`)
- 0 Redux trade/position churn (triggered alerts ARE moved locally per R2)

This matches the forward-equivalent of holding `shift+right` across N quiet
candles, where the engine draws each candle and no backend is touched.

---

## Non-Requirements

- No changes to the backend `/reset` endpoint (no new "lightweight update
  last_candle_seen_at" endpoint)
- No changes to `ReplayTradingController.resetTo` (default replay) — already
  purely local
- No changes to forward playback — already optimized
- No new user-visible setting to enable/disable the optimization — it's always
  on once shipped
- No backpressure / debounce — `_stepInFlight` already serializes step-backs, and
  the optimization removes the main latency source (backend call) so there's
  nothing left to debounce against
- No batched "destroy N positions across M windows" — positions only get
  destroyed by an actual backend call, and the pending accumulator handles the
  timing (earliest target wins)
- No snapshot / replay-log mechanism — we rely on the backend to be the source of
  truth at flush time

---

## Open questions to resolve during design

1. **Position `open_time` units.** Backend stores `open_time` as an integer
   (seconds? ms?). Client has `position.open_time` which is returned by
   `Entities::Backtest`. Confirm units before writing the window-check.
2. **`updatedAt` on triggered alerts.** Currently set to `this._currentActualTime`
   (ms, with the `-1000` offset) when an alert fires. The R1 window check needs
   to use the same offset semantic — so `updatedAt >= newTime` compares
   `_currentActualTime_at_trigger` against the step-back's new engine time.
   Double-check the comparison direction doesn't have an off-by-one at the
   candle boundary (same category as the default-replay trade filter bug from
   `../stepback/review.md` Round 3).
3. **Trade-widget order placement flush.** Where exactly to hook the flush
   before a new position is created. Options: `ReplayController.replaySafeCallback`
   wrapper around trading-terminal actions, a dedicated
   `SmartReplayController._ensureBackendSynced()` called at the top of each
   trade API action, or middleware on the trading thunks. Needs a design pass.
4. **Flush on browser close / reload.** Unavoidable data loss — pending reset is
   discarded. Acceptable. Document that resume from the widget after an
   unclean exit will not reflect quiet step-backs since the last position op.
5. **Held-hotkey held-open mid-flush.** If user is still holding `shift+left`
   when a flush fires (`handleStop` from a keyboard shortcut), make sure the
   flush completes before the stop proceeds, and that no further step-backs
   race against it. `_stepInFlight` should cover this but verify.

---

## Dependencies

- `../stepback/prd.md` (id `sc-replay-stepback`) must be shipped and verified
  first. This PRD is strictly an optimization on top of the base feature and
  assumes the base controller methods (`goBackTo`, `handleStepBack`,
  `_revertAndSeek`, `_stepInFlight`) exist.
