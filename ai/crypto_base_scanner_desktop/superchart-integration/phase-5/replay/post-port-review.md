# Post-Port Review: SC Replay + TV Decommission

Critical code review comparing `feature/superchart-integration` to `release-5.2.x`.
Covers the SC default replay port, SC smart replay port, and TradingView
decommission from the Trading Terminal.

**Date:** 2026-04-13
**Scope:** All replay-related code and cross-cutting concerns.

---

## Summary

The SC replay port is **functionally incomplete** but architecturally sound.
12 issues identified across completeness gaps, fragile logic, and dead code
residue. The port successfully delegates candle management to SuperChart's
native replay engine (eliminating ~690 lines of manual stepping from TV), but
sacrifices granular control over edge cases (partial candles, resolution
changes mid-session, finished state handling).

**Risk level: HIGH for production without fixes.**

---

## 1. Completeness gaps vs TV baseline

### 1.1 Missing: Partial candle construction at jump time (CRITICAL) ✅ RESOLVED

**TV:** `ReplayController.getPartialCandle()` — when jumping to a time
mid-candle (e.g., resuming backtest), TV constructs a synthetic candle using
1H and 1M child candles, preventing price spoiling.

**SC:** No equivalent. `ReplayController._handleError()` catches
`partial_construction_failed` error from engine but doesn't implement fallback
or retry logic.

**Impact:** If SC engine cannot construct partial candle at jump time, replay
fails silently (only a generic toast) and session hangs in loading state.

**File/Line:**
`src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js:159-179`

**Severity:** CRITICAL — Backtest resume flows broken for non-round-hour jump
times.

### 1.2 Missing: Mid-replay resolution change validation (HIGH) ✅ RESOLVED

**TV:** Validates `!SECOND_RESOLUTIONS.includes(resolution)` before starting.

**SC:** Only reacts to engine errors after attempting change. No pre-flight
check.

**Consequence:** User can start replay → switch to second resolution → replay
crashes with `unsupported_resolution` error. Engine restores previous
resolution, but state may be stale if other charts changed it concurrently.

**File/Line:**
`src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js:159-179`

**Severity:** HIGH — User-facing error; no protection against misconfiguration.

### 1.3 Missing: Unsupported resolution check on startup (MEDIUM) ✅ RESOLVED

**TV:** `loadFirstCandleTime()` calls `checkResolutionSupport()`, failing
gracefully before fetching.

**SC:** No equivalent check in `getRandomReplayStartTime()`. If user picks
random start on second resolution, flow proceeds to engine which rejects it.

**File/Line:**
`src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js:204-228`

**Severity:** MEDIUM — No user warning, relies on engine error.

### 1.4 Missing: Explicit end-of-replay detection (MEDIUM) ✅ RESOLVED

**TV:** `handleReady()` detects `sessionEnded` flag and sets status to
`FINISHED`. Engine steps until data exhausted.

**SC:** Engine should emit `status → finished` when replay ends, but no
explicit check that all candles were consumed. If engine emits `ready` instead
of `finished`, replay appears stuck.

**File/Line:**
`src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js:110-146`

**Severity:** MEDIUM — Edge case, but breaks UI responsiveness.

### 1.5 Missing: Trendline alert sync on backtest load (HIGH) ✅ RESOLVED

**Behavior:** SmartReplayController implements `trendLineShouldTrigger()` (lines
473-478, 512-516) and checks on each `onReplayStep`, BUT only checks alerts
that exist in `state.alerts`. Existing chart drawings (trendlines placed before
backtest starts) are not synced into `state.alerts`. Only newly-created alerts
via the alerts form are tracked.

**Impact:** User creates trendline → starts backtest → trendline rendered on
chart but NOT checked during replay. Partially broken feature.

**File/Line:**
`src/containers/trade/trading-terminal/widgets/super-chart/controllers/smart-replay-controller.js:512-516`

**Severity:** HIGH — Trendline alert feature broken by default.

### 1.6 Inconsistent: Back-in-time with partial position check (MEDIUM) ❌ NOT APPLICABLE

**Re-analysis:** `checkResetToPossible` exists because smart positions have
entry/exit orders tied together — you can't undo an exit without also undoing
the entry. Default replay has no such concept: trades are atomic events tracked
in `ReplayTradingController.trades`, and `resetTo(time)` just filters them by
time. Filtering is naturally consistent — no partial state possible. Review
was wrong to flag this for default replay.

### 1.7 Not persisted: `smartReplayAutoResumePlayback` setting (MEDIUM) ❌ FALSE FINDING

**Verification:** `smartReplayAutoResumePlayback` lives inside `replaySettings`
in `src/reducers/replay.js:34`. The `replay` reducer has a persist filter in
`src/store-config.js:134-141` that whitelists `replaySettings`, so the setting
IS persisted across sessions. Review was wrong.

---

## 2. Code quality issues

### 2.1 Memory leak: polling interval not cleared on error (HIGH) ✅ RESOLVED

`_pollForEngine()` (lines 86-105) creates `setInterval` with no max-attempts
counter. If engine is never found (e.g., SuperChart destroyed before init), the
interval polls every 50ms indefinitely.

```javascript
this._pollInterval = setInterval(() => {
  // ... if sc.replay never appears, this runs forever
}, 50)
```

`destroy()` only clears if `this._pollInterval !== null`, but no timeout.

**File/Line:**
`src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js:97-104`

**Severity:** HIGH — Production memory leak on failed SC init.

### 2.2 Race condition: `_startTime` state inconsistency (HIGH) ✅ RESOLVED

`_startTime` is instance variable (line 23), but session is Redux state.
Mismatch in stop paths:

- `_stop()` sets `this._startTime = null` **then** clears Redux
- `_onAutoExit()` does same but ALSO clears mode before sub-controller reset
- If Redux dispatch fails, instance var is null but Redux still has data →
  `willLoseDataIfStopped` returns false → silent data loss

**Scenario:**
1. User starts replay → `_startTime` set, Redux state set
2. Engine auto-exits on symbol change → `_onAutoExit()` clears both
3. If `setReplayMode()` dispatch fails (Redux middleware error), `_startTime`
   is already null → `willLoseDataIfStopped` returns false → data loss without
   confirmation

**File/Line:**
`src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js:148-157, 375-391`

**Severity:** HIGH — Silent data loss risk.

### 2.3 Inconsistent status constants: strings scattered (MEDIUM) ✅ RESOLVED

TV used enum `REPLAY_STATUS = {READY, PLAYING, PAUSED, ...}`.

SC uses lowercase strings: `"idle"`, `"loading"`, `"ready"`, `"playing"`,
`"paused"`, `"finished"`. Two status systems coexist:

- Redux selectors use lowercase string literals
- Engine callbacks emit lowercase string literals
- No central constant file; strings scattered and typos possible

**Impact:** If engine emits `"Finished"` (wrong case), status check
`=== "finished"` fails silently.

**File/Line:**
- `src/models/replay/selectors.js:6-7`
- `src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js:115-125`

**Severity:** MEDIUM — Fragile; easy to introduce typos.

### 2.4 Dual session path: `_sessionChartId` vs `_chartId` (MEDIUM) ✅ RESOLVED

ReplayController maintains `_sessionChartId` (initialized null, set on session
start, cleared on stop) AND has `_chartId` (chart's market tab ID). Getter uses
fallback:

```javascript
get _chartId() { return this._chartController?._marketTabId || "main" }
get state() { return selectReplaySession(this._sessionChartId || this._chartId)(this.getState()) }
```

**Problem:** Dual-path design creates orphan session risk if user switches
market tabs during session and cleanup fails.

**File/Line:**
- `src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js:42-53`
- `src/containers/trade/trading-terminal/widgets/super-chart/controllers/smart-replay-controller.js:43-51`

**Severity:** MEDIUM — Footgun; requires careful cleanup ordering.

### 2.5 Unhandled promise rejection in SmartReplayController (MEDIUM) ✅ RESOLVED

```javascript
Promise.all(newTriggeredAlerts.map(this.notifyAlert)).catch(console.error)
```

If `notifyAlert` fails (dispatch error), it's silently swallowed. Alerts may
not trigger UI notifications.

**File/Line:**
`src/containers/trade/trading-terminal/widgets/super-chart/controllers/smart-replay-controller.js:527`

**Severity:** MEDIUM — Silent failures; alerts won't notify user.

### 2.6 Missing error handling in resetTo (MEDIUM) ✅ RESOLVED

`SmartReplayController.resetTo()` calls `_resetBacktest()` which makes an API
call. If API fails, no error handling — promise rejection bubbles up.

**File/Line:**
`src/containers/trade/trading-terminal/widgets/super-chart/controllers/smart-replay-controller.js:643-654`

**Severity:** MEDIUM — API errors not caught; UI doesn't show failure.

### 2.7 Alert mutation race in checkAlerts (MEDIUM) ✅ RESOLVED

`checkAlerts()` mutates original alert objects in-place:

```javascript
const newTriggeredAlerts = triggeredAlertIds.map(alertId => {
  const alert = this.getAlertById(alertId)
  alert.updatedAt = this._currentActualTime  // mutates original!
  return alert
})
```

If multiple candle steps happen before Redux dispatch completes, second step
overwrites `updatedAt`.

**File/Line:**
`src/containers/trade/trading-terminal/widgets/super-chart/controllers/smart-replay-controller.js:518-526`

**Severity:** MEDIUM — Silent state corruption; alert timing data wrong.

---

## 3. Dead code and decommissioning residue

### 3.1 TV replay context stub (KEEP)

`src/containers/trade/trading-terminal/widgets/center-view/tradingview/context/use-replay.js`
is a stub providing empty `ReplayContext` and passthrough `withHideInReplayMode`
HOC. **Not dead code** — necessary bridge so TV components (still used by grid
bots, quizzes, customer service) compile. No action needed.

### 3.2 TV components with dead replay branches (LOW PRIORITY CLEANUP) ✅ RESOLVED

~~8 TV files have replay-aware code that reads the stub context (always falsy):~~

Removed `withHideInReplayMode` HOC from 8 files, removed `ReplayContext` and
`replayMode` reads from 6 files, simplified the replay-derived conditionals,
and deleted the entire `context/use-replay.js` stub. `data-provider.js` also
lost its dead `_replayController` positional arg (and its lone caller was
updated).

**Severity:** LOW — Technical debt, no functional issue.

### 3.3 `REPLAY_STATUS` constant removed (CORRECT)

TV's `REPLAY_STATUS` enum is removed. SC uses lowercase strings. No residual
imports found. Clean.

---

## 4. Architectural observations

### 4.1 Engine delegation reduces code complexity

SC delegates candle stepping and data fetching to SuperChart's native engine.
This eliminates ~690 lines of TV's manual candle queuing (`takeCandles`,
`fetchCandles`, `step` loop).

**Trade-off:** SC has less granular control. Engine errors are consumed as
toasts rather than recovered. TV could retry with different strategies.

**Assessment:** Correct architecture for a UI library integration. Complexity
is moved to engine layer.

### 4.2 Session state split across Redux and instance variables

`ReplayController._startTime` and `_sessionChartId` are instance state, while
`state.replay.sessions[chartId]` is Redux. Both represent "is a session active?"
but are not synchronized.

**Why:** Redux state must persist across re-renders and be accessible from
outside the chart tree. Instance vars are faster for controller-internal checks.

**Risk:** Cleanup ordering matters (lines 382-385 explicitly clear Redux mode
before sub-controllers to avoid stale routing). If order changes, silent data
loss.

**Assessment:** Design is sound but brittle. The dependency is not enforced by
type system. Fix: eliminate instance state and read from Redux only (see fix
#2 below).

### 4.3 Controller hierarchy

```
ChartController
  ├── replay (ReplayController)
  │   ├── trading (ReplayTradingController)
  │   └── smart (SmartReplayController)
  │       └── backtest (ReplayBacktest, parsed per session)
```

Hierarchy is clear. Each level has single responsibility.

**Concern:** `SmartReplayController` is 757 lines with tight coupling to
`ReplayController` (injects refs). If ReplayController changes status constants
or session shape, Smart must follow. Functional but could be refactored into
smaller pieces.

---

## 5. Risk hotspots

### 5.1 Engine polling race condition (CRITICAL)

If SuperChart init fails or is destroyed before engine is available,
`_pollInterval` polls forever.

**Repro:**
```javascript
chartController.destroy() // clears interval
// But if timing is off:
// destroy() called before setInterval completes
// → _pollInterval not set, cleanup skipped
```

### 5.2 Session cleanup ordering (HIGH)

If `setReplayMode(undefined)` dispatch fails, sub-controllers' `reset()` will
read stale `replayMode` from Redux and route backtest calls into live paths.

### 5.3 Time sync from engine (MEDIUM)

Engine emits `onReplayStep(candle)` with candle time, but controller also calls
`engine.getReplayCurrentTime()` on status change. If getters and callbacks
disagree, session time is inconsistent.

### 5.4 Partial candle construction failure (CRITICAL)

Engine cannot construct partial at jump time → returns error → toast shown →
session stays in "loading" state → user must manually stop.

**Repro:** Resume backtest at time = 12:34:56 (not round hour/minute).

### 5.5 Backtest auto-resume loop (MEDIUM)

If trigger fires and auto-resume is enabled, but `checkAlerts()` immediately
triggers again on next step, replay pauses → resumes → pauses (flicker).

---

## 6. Recommended fixes

### HIGH priority

| # | Fix | File | Effort |
|---|---|---|---|
| 1 | ✅ Cap `_pollForEngine` at 20 attempts (~1s); clear on timeout | `replay-controller.js:97-104` | 5 min |
| 2 | ✅ Remove `_startTime` instance var; read from Redux | `replay-controller.js:375-391` | 15 min |
| 3 | ✅ Partial candle retry — round up to next candle boundary | `replay-controller.js:159-179` | 20 min |
| 4 | ✅ Pre-flight resolution check in `getRandomReplayStartTime` | `replay-controller.js:204-228` | 10 min |
| 5 | ✅ Sync existing chart trendlines into `state.alerts` on backtest load | `smart-replay-controller.js:512-516` | 30 min |

### MEDIUM priority

| # | Fix | File | Effort |
|---|---|---|---|
| 6 | ✅ Add `.catch()` to `notifyAlert` promise chain | `smart-replay-controller.js:527` | 5 min |
| 7 | ✅ Clone alert objects in `checkAlerts` instead of mutating | `smart-replay-controller.js:518-526` | 5 min |
| 8 | ✅ Add error handling to `resetTo` API call | `smart-replay-controller.js:643-654` | 10 min |
| 9 | ❌ NOT APPLICABLE — default replay has no partial-close concept | `replay-controller.js:322-332` | — |
| 10 | ❌ FALSE — already persisted via `replaySettings` filter | `reducers/replay.js` | — |
| 11 | ✅ Create central `REPLAY_STATUS` string constants; replace literals | `models/replay/constants.js` | 20 min |

### LOW priority

| # | Fix | File | Effort |
|---|---|---|---|
| 12 | ✅ Eliminate `_sessionChartId` dual-path; always use `_chartId` | `replay-controller.js:42-53` | 30 min |
| 13 | ✅ Remove replay checks from TV components (dead code) | 8 TV files | 30 min |

### Quick wins (top 5)

Fixes 1, 2, 4, 6, 7 — total **~40 minutes** — eliminate most of the immediate
brittleness.

---

## 7. Test coverage gaps

No test files found for replay controllers. Recommend:

1. **Unit tests:** ReplayController polling, state sync, cleanup
2. **Integration tests:** Engine callback wiring, error recovery
3. **E2E tests:** Resume backtest at non-round time, resolution change
   mid-replay, symbol change

---

## Conclusion

The SC replay port is ~60% complete with **high-risk gaps** in error handling
and edge cases. Architecture is sound but implementation has brittle state
management and missing validation paths.

**Fix HIGH priority items before production; MEDIUM items should be in next
sprint.** Without fixes, users will experience silent failures (partial candle
construction, alert timing) and data loss (session state inconsistency).
