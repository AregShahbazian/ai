# Trigger Timing Offset — Fix Plan

Companion to [`research.md`](./research.md) and
[`reproducer-logs.md`](./reproducer-logs.md). This file prescribes the exact
edits and then digs into every side effect the edits will have.

Semantic target: **"the replay cursor IS the current moment"**. If the cursor
displays `08:00`, the time traveler is *at* `08:00` — the `07:00–08:00` candle
is completed history, and the `08:00–09:00` candle is "now, about to form".
Every trigger, alert, trade, and reset comparison should respect that frame.

---

## 1. The edits

### 1.1 Drop the `-1000` subtraction

**File**: `src/containers/trade/trading-terminal/widgets/super-chart/controllers/smart-replay-controller.js`

**Line 62** (`_currentActualTime` getter):

```js
// BEFORE
get _currentActualTime() { return this._currentTime - 1000 }

// AFTER
get _currentActualTime() { return this._currentTime }
```

This is the root of the entire offset. Every downstream site that reads
`_currentActualTime` inherits the fix automatically:

- **Line 69** — `_lastDrawnCandleWithCurrentTime.time` now ships the hour
  boundary (`close_sec`) to the backend instead of `close_sec - 1`.
- **Line 502** — `_pruneExpiredAlerts` compares against the boundary.
- **Line 524** — time-alert detection compares against the boundary.
- **Line 529** — trend-line alert evaluation uses the boundary seconds value.
- **Line 554** — triggered alerts are stamped with `updatedAt = close_ms`.
- **Line 577** — `_backtest.checkTriggers(candle, this._currentActualTime)`
  feeds the frontend time-trigger pre-check with the boundary.
- **Line 617, 624, 627** — `_anyAlertWouldFire` mirror of the above, used
  by the sync pre-pause path.

The name `_currentActualTime` is now a misnomer (it's identical to
`_currentTime`). Collapse the two: delete the getter entirely and replace
all call sites with `_currentTime`. The rename is mechanical and worth
doing in the same commit so future readers don't wonder which to use.

### 1.2 Use strict `<` on `closeTime` in `checkResetToPossible`

**File**: same file, **lines 733–757**.

The `isClosed` branch uses strict `<` on both `openTime` and
`closeTime`. Only **mid-lifetime** targets (strictly between open and
close) are irreversible. Boundary targets are reversible:

- `target == openTime` — reversible (backend deletes the whole position
  via `open_time >= target`).
- `target == closeTime` — reversible. The cursor lands exactly on the
  close moment. The position stays cleanly closed at that boundary;
  any close trade renders at the cursor (not stranded in the cursor's
  future). Common case: a LIMIT entry that expired without filling has
  `closeTime = cancellation_cursor` and no trades — flagging it would
  trap the user behind an invisible wall.
- `openTime < target < closeTime` — irreversible. Position would
  appear closed with `closeTime` in the future of the cursor.

```js
if (isClosed) {
  if (time > util.valueOfDate(openTime) && time < util.valueOfDate(closeTime)) {
    irreversiblePositions.push(position)
  }
}
```

**History note**: this comparator pivoted twice during development.
The original code used `<=`. An early draft of this fix tightened it
to `<` to match boundary-on-cursor semantics. A reproducer for a
manual MARKET-open/MARKET-close sequence then surfaced "reset sent on
step N, warning on step N+1" — `_hasChangesSince` returned true at
`target == closeTime` because of the close trade, firing a no-op
reset, then `<` wouldn't flag, so the warning came one step later.
We reverted to `<=` to align the warning with the would-be no-op
reset.

Then a reproducer for an expired LIMIT entry (no trades, no fills,
auto-cancelled at the configured expiry) showed `<=` was
over-restrictive — it flagged `target == closeTime` as irreversible
even though the position has no trades to strand. Stepping back to
exactly the cancellation moment is a clean cursor-only operation.

Settled: `<`. The "no-op reset on the manual-close boundary" is a
minor cost (one wasted HTTP call per such step-back); the cursor
moves correctly and no trade is visually stranded. The win is that
boundary step-backs work in the no-trade case, which is the common
expired-LIMIT scenario.

The `isOpen` branch below it (`if (isOpen && time > util.valueOfDate(openTime))`)
is already semantically correct: a reset target equal to `openTime` means
"rewind to exactly when the position opened", and the backend's
`open_time >= reset_to` rule will delete the position cleanly. The `>`
correctly excludes that boundary case from the "irreversible" set.

### 1.2.1 Mid-lifetime guard is intentional and load-bearing

The "positions partially closed" warning that fires when a step-back
or jump targets a time strictly between `openTime` and `closeTime` is
**a deliberate frontend guard**, not a bug. **Keep it.**

**Why it exists**: the backend's reset endpoint
(`backtests.rb:397-404`) only deletes positions whose
`open_time >= reset_to`. It cannot:

- partially revert a close (re-open a closed position),
- remove a single fill or reduce trade,
- un-cancel an expired position.

If a step-back lands inside `(openTime, closeTime)`, the position is
in a state the backend can't repair: openTime is in the past relative
to the new cursor (so the position survives the reset), but closeTime
is in the future of the cursor (so the position appears "closed in
the future"). The frontend pre-flights this and blocks the step-back
to keep the chart consistent with what the backend can actually
represent.

**Applies to all closed positions**, regardless of how they got
closed:

- Manual MARKET close.
- Filled-then-reduced position.
- Filled position closed by SL/TP order.
- **Unfilled LIMIT entry that expired** via `entry_expiration` (the
  position is `status: "canceled"` with `closeTime = cancellation
  cursor`; same guard rule applies).

**TV behaviour parity**: the legacy TradingView replay implementation
had the identical guard for the identical reason. This was not a bug
in TV that we fixed — it's an intentional cross-implementation policy.

**To remove the guard, the backend would need to gain the ability to
partially revert position lifecycles**. That is a much larger change
(new endpoints, new state machine on the rollback side, possibly
schema changes for "soft-delete trades after a target time"). Out of
scope for any frontend-only PRD.

**Workaround the user always has**: use the chart context-menu "Jump
back to here" on a candle ≤ `openTime`. That deletes the entire
position cleanly via `open_time >= reset_to`.

### 1.3 Nothing else changes

**No backend edits.** `entry_condition.rb:57` already uses `>=`;
`backtests.rb:399` already uses `>=`; `Backtest#trigger` is a pass-through.
Once the frontend sends hour-boundary values, the existing comparators line
up on their own. Zero lines of Ruby change.

**No `canStepBack` change.** Section §4.4 of `research.md` initially
flagged this as a candidate, but reconsideration lands on: blocking
step-back when `currentTime == startTime` is semantically correct for a
time traveler. You cannot un-draw the session's first candle. The first-
candle undo flow is *step forward → place trade → step back → deleted*,
which works cleanly under the new semantics.

---

## 2. Side effects — deep dive

Every meaningful downstream effect of dropping the `-1000`, grouped by
severity. Each entry names the file/line, explains the shift, and states
whether it is a fix, a correct-but-visible behavior change, or a risk.

### 2.1 Alerts

#### 2.1.1 Time alerts fire one candle earlier (FIX — this is the point)

`smart-replay-controller.js:522-525`. An alert set for `11:00` used to fire
when the cursor reached `12:00`; now it fires when the cursor reaches
`11:00`. Scenario A in `reproducer-logs.md` is the confirming evidence.

#### 2.1.2 Trend-line alerts — 1 second x-axis shift (negligible)

`smart-replay-controller.js:529, 627`. The linear interpolation
`trendLinePriceAtTime(points, time)` receives `_currentActualTime / 1000` as
its `time` argument. The new value is 1 second later than before. For a
trend line spanning hours or days, the `y` difference is imperceptible
(sub-basis-point on typical slopes). No risk.

#### 2.1.3 Alert expiry: `>=` → `>` so the final-candle detection still runs

`smart-replay-controller.js:497-509, 613-631`. An alert with
`expiresAt = 10:00` and a price that would cross during the
`09:00–10:00` candle:

- **Old code (`_currentActualTime - 1s`, `>=`)**: at cursor `10:00`,
  `_currentActualTime = 09:59:59 < 10:00` → not expired → detection
  runs on the `09:00–10:00` candle's OHLC → alert fires if price
  crossed. Pruning happens on the `11:00` step.
- **Fix v1 (`_currentTime`, `>=`)**: at cursor `10:00`,
  `_currentTime = 10:00 >= 10:00` → pruned immediately. The
  `09:00–10:00` candle's OHLC is not checked. Alert never fires even
  though the crossing price happened before expiry. **Wrong.**
- **Fix v2 (`_currentTime`, `>`)**: at cursor `10:00`,
  `_currentTime > 10:00` → false → not expired → detection runs on
  the `09:00–10:00` candle → alert fires if price crossed. At cursor
  `11:00`, `11:00 > 10:00` → true → pruned. **Correct.**

Semantic: "expires at 10:00" = "valid for any candle activity *before*
10:00, including the candle whose close equals 10:00." The candle
whose close equals `expiresAt` is the final window of validity — its
OHLC is inspected once, then the alert is pruned on the next step.

**Lazy-prune fix** (same commit): `_pruneExpiredAlerts` previously
only ran inside `checkAlerts`, which was gated by the sync pre-pause
(i.e. only ran when some other trigger fired on that step). An alert
that expired without firing stayed visible in the UI until some other
trigger happened. The fix adds `_pruneExpiredAlertsNow` and calls it
unconditionally at the top of `updateCurrentState`, so expiry cleanup
happens on every step regardless of other triggers. The prune block
is removed from `checkAlerts` (no longer needed there).

#### 2.1.4 Triggered alert `updatedAt` shift (internal, safe)

`smart-replay-controller.js:554`. Under the old code, a triggered alert
was stamped `updatedAt = close_ms - 1000`. Under the fix it's stamped
`close_ms`. The only consumer of `updatedAt` is `_untriggerAlertsSince`
(line 723-731), which drops triggered alerts whose `updatedAt >= target`
during a step-back. Walked through both semantics:

- Alert fires at step `N` (cursor = `close_ms_N`). Old `updatedAt =
  close_ms_N - 1s`. New `updatedAt = close_ms_N`.
- Step back to `N-1`: target = `close_ms_N - resolution_ms`.
- Old: `(close_ms_N - 1000) >= (close_ms_N - resolution_ms)` → true for
  `resolution_ms > 1000` → dropped. ✓
- New: `close_ms_N >= (close_ms_N - resolution_ms)` → true → dropped. ✓

Identical behavior. No regression. Mixed old/new alerts in the same
session also behave identically (verified by the same walk-through with
different `updatedAt` values).

### 2.2 Order time-triggers

#### 2.2.1 Backend fires one candle earlier (FIX — this is the point)

`entry_condition.rb:57-59`. `last_candle_seen_at` now equals the hour
boundary instead of `boundary - 1`, so `time >= start_at` fires exactly
when the cursor reaches the user's configured `start_at`. Scenario B
confirms.

#### 2.2.2 Frontend `checkTriggers` pre-pause (same fix, sync)

`smart-replay-controller.js:577` → `backtest.js:476`. The frontend runs a
mirror of the backend's time-trigger check to pause the engine
synchronously before the async backend call lands. Under the fix this
mirror uses the boundary value too, so pre-pause fires on the same candle
as the backend's actual evaluation. Consistent with the backend fix — no
timing divergence between pre-pause and fire.

### 2.3 Positions & trades

#### 2.3.1 `open_time` / `created_at` shift by 1s (expected, harmless)

`backtests.rb:209-210`. New positions have `created_at = Time.at(close_sec)`
instead of `Time.at(close_sec - 1)`. Every downstream use of these fields
— stats, progress, chart overlays, reports — sees values 1 second later.

#### 2.3.2 `close_time` shift by 1s

`backtest_position.rb:202-205`. `close_time` is written from the `time`
argument passed into `SpotPosition#close`, which traces back to
`params[:candle][:time]`. It also includes a `max(close_time, open_time)`
guard to prevent close < open. Under the fix, both values sit on boundaries
and the guard becomes a no-op in practice (close/open are either equal or
close > open by full candles). No regression.

#### 2.3.3 `update_exchange(..., time)` shift

`api/api_v3/backtests.rb:213, 234, 280, 282, 304, 329`. The `time` argument
flows into order fills and trade records. These are written at hour
boundaries post-fix. Stats aggregation is unchanged (aggregate counts and
sums are insensitive to a 1 second shift). Chart overlay rendering of
trades is discussed below in §2.4.1.

#### 2.3.4 `set_current_time(time)` shift

Called by `cancel`, `reduce`, `increase`. Used by `smart_position` to
compute cool-down timers and similar time-relative behavior. The shift of
1 second will have negligible effect on cool-down calculations (the
shortest configurable cool-down is in the minute range).

#### 2.3.5 Mixed in-flight backtests with old + new positions (safe)

A backtest session paused under the old code will have positions stored
with `open_time = close_sec - 1`. Resuming it under the new code, any
subsequent step-back runs the backend's unchanged
`where("open_time >= reset_to")` against those pre-fix rows:

- Reset target from cursor `N` stepping back to `N-1`: target =
  `close_sec_N - resolution_ms = close_sec_{N-1}`.
- Pre-fix position opened on candle `N-1` has `open_time = close_sec_{N-1} - 1`.
- `(close_sec_{N-1} - 1) >= close_sec_{N-1}` → **false**.

**Wait.** That looks like a regression — pre-fix positions can't be reset
under post-fix code. Let me re-walk to make sure this is right.

Actually no — the `_currentTime` the step-back reads from the engine is
still `close_ms`, and `currentTime - resolution_ms = close_ms -
resolution_ms = open_ms` of the just-stepped-from candle. That's
`close_sec_{N-1}` = boundary. And the pre-fix position's `open_time` is
`close_sec_{N-1} - 1`, which is `< close_sec_{N-1}`. So `(close_sec_{N-1}
- 1) >= close_sec_{N-1}` → **false** → position NOT deleted → orphan in
the mixed-semantics case.

**This is a real regression for resumed pre-fix sessions.** Before calling
it a blocker, walk through the most common flow:

- User placed a position at cursor `15:00` under old code. `open_time =
  14:59:59`. Cursor currently at `15:00`.
- Step back from `15:00` under old code: target = `14:00`. Backend:
  `14:59:59 >= 14:00:00` → **true** → deleted. Works under old code.
- User pauses the session. Fix ships. User resumes and steps back: target
  is still `14:00` (reset target computation unchanged by the fix).
  `14:59:59 >= 14:00:00` → **true** → deleted. Works under the mix too.

Ah — I was computing the wrong target. The reset target is
`currentTime - resolution_ms` where `currentTime` is the *cursor's current*
close_ms, not the candle where the position was opened. The position's
opening candle could be any earlier candle; the comparison is always
`position.open_time >= reset_to`, and the offset-shifted old `open_time`
is always 1s *after* the open boundary, so it's always `>=` any reset
target that lands on a boundary ≤ its own opening candle's open. **No
regression.**

I'm leaving the corrected walkthrough in the plan because the scenario
is subtle enough to be worth documenting: anyone reviewing the fix should
be able to follow the math and convince themselves it's safe.

#### 2.3.6 Chart trade overlay rendering at boundary timestamps

`trades-controller.js:49` renders each trade at `trade.time * 1000`.
Post-fix, `trade.time` is on an hour boundary. Klinecharts/SC renders the
marker at the x-axis position corresponding to that timestamp:

- **If the boundary-timestamped candle is drawn**: marker sits at the left
  edge of that candle. Visually fine — clearly "on" the candle.
- **If the boundary-timestamped candle is not yet drawn** (session start,
  no forward step): the last drawn candle is the *previous* one, and the
  trade timestamp is one full resolution past the last candle's open.
  Klinecharts typically places this at the implied next x-axis tick —
  effectively "floating" just past the last candle.

This is the "floating trade" problem that the original `-1000` was almost
certainly introduced to avoid (per the user's guess in the conversation
trail). **Needs visual QA.** Three possible outcomes and responses:

1. Klinecharts renders it cleanly on the right edge of the last drawn
   candle → no action needed.
2. Klinecharts renders it floating in empty space past the last candle →
   the trade is "invisible" until the user steps forward, at which point
   it snaps into place. Acceptable if the trade is committed to the
   backend (user sees it in the widget list) and appears on the chart on
   the next forward step.
3. Klinecharts refuses to render and logs a warning → fix the overlay
   layer: anchor boundary-timestamped markers to the last drawn candle
   visually while keeping the stored `.time` on the boundary.

**Recommendation**: implement the fix, reproduce Scenario D (place trade
on first drawn candle without stepping forward), visually confirm the
trade marker's behavior. If it's outcome 3, add a small adjustment inside
the trade overlay layer — not back in `_currentActualTime`, because the
logical time of the trade *is* the boundary.

#### 2.3.7 Multi-candle rewind consistency

`_hasChangesSince` (smart-replay-controller.js:714) walks
`backtestPositions.openTime >= target` and `trades.time * 1000 >= target`.
Under new semantics both sides sit on boundaries. The existing `>=`
operator continues to match the same rows. Multi-candle rewinds are
unaffected.

### 2.4 Reset path

#### 2.4.1 `checkResetToPossible` — strict `<` on `closeTime` (see §1.2)

Only mid-lifetime step-back targets are flagged. Boundary cases
(`target == openTime` or `target == closeTime`) are reversible — the
cursor moves cleanly and no trade is stranded. Trade-off: in the
manual-close case, stepping back to `closeTime` fires a wasted no-op
HTTP call (backend doesn't delete because `openTime < target`), but
it doesn't break anything visually.

#### 2.4.2 Reset target computation unchanged

`replay-controller.js:645-648`. `_stepBackOnce` builds the reset target
from `engine.getReplayCurrentTime() - resolution_ms`. The engine's
`getReplayCurrentTime` is unchanged by the fix (it always returned
`close_ms`). The reset target was always on a boundary and remains so.

#### 2.4.3 Backend `where("open_time >= reset_to")` unchanged

The existing `>=` comparator is correct under the new semantics; see
§4.2.2 of `research.md` for the walk-through. Zero backend edits.

### 2.5 `last_candle_seen_at` and resume

#### 2.5.1 Stored value shifts by 1 second (safe via existing rounding)

`smart-replay-controller.js:219`. On backtest resume, the frontend reads
`lastCandleSeenAt` from the backend payload and does:

```js
const safeLastCandleSeenAt = !lastCandleSeenAt
  ? startTime
  : util.roundTimeToNextMinute(lastCandleSeenAt)
```

Pre-fix values (`close_sec - 1 → 07:59:59`) round up to the next minute
(`08:00:00`), matching the new-fix stored value (`close_sec → 08:00:00`).
Post-fix values round to themselves (already on minute/hour boundaries).
**Resume behavior is identical across old and new sessions.** The
`roundTimeToNextMinute` guard becomes a no-op for new sessions but stays
useful for pre-fix sessions.

#### 2.5.2 Backtest progress % (imperceptible)

`backtest.rb:102-106`. Progress computed as
`(last_candle_seen_at - replay_start_at) / (replay_end_at - replay_start_at)`.
Under the fix, the numerator is 1 second larger per step. For typical
backtest windows (hours to weeks), the percentage change per step is the
same in aggregate. The final progress now lands on exactly `100%` instead
of `99.9999…%`. Cosmetic improvement.

#### 2.5.3 Time-trigger `check_at` scheduling

`smart_positionable.rb:98-99`. When a position has a pending time-trigger,
the backend writes `self.check_at = Time.at(settings.entry_condition.start_at)`
so the scheduler knows when to re-evaluate. `check_at` itself is
computed from `start_at`, which is user-provided and unchanged. The only
shift is that `time_triggered?(current_time.to_i)` now returns true one
candle earlier (§2.2.1), so the `check_at` bookkeeping is released one
candle earlier. Matches the fix intent.

### 2.6 Non-replay code paths

#### 2.6.1 `ReplayTradingController` (default replay)

`replay-trading-controller.js` also references `_currentTime` /
`_currentActualTime`. Default replay is client-side only (no backend),
but it shares the same `_currentActualTime = _currentTime - 1000` getter
through inheritance from `BaseReplayController`-adjacent code. **Must
apply the same fix there**, otherwise default replay's client-side alert
detection will still lag by one candle. Verify the inheritance chain
before landing the fix.

#### 2.6.2 Grid bot replay / backtests

Grid-bot backtests use a separate code path
(`MockBacktestingService` + `MockTradingService`) and do not share the
`smart-replay-controller.js` timestamp handling. **Unaffected by the
fix.** No cross-contamination risk.

#### 2.6.3 Live trading

Live trading does not go through replay at all. `_currentActualTime` is
only read inside smart replay context. **Unaffected.**

### 2.7 Held-step autorepeat and fast-play

`_lastCandle` is set inside `updateCurrentState(candle)` and read by
`checkTriggers` and `_anyAlertWouldFire`. Under fast-play (20 candles/sec)
or held-step autorepeat, the engine fires back-to-back step callbacks.
The existing sync pre-pause
(`smart-replay-controller.js:578-584`) assumes `_lastCandle` is fresh
when the pause decision is made.

Under the fix, nothing in the pause logic changes — only the value it
compares against (`_currentActualTime`). Since `_lastCandle` and
`_currentActualTime` are both set from the same `onReplayStep` callback
atomically, there is no new race. **No regression.**

### 2.8 Persisted backtests that contain pre-fix time-triggers

A backtest paused with a pending time-trigger at `start_at = 15:00:00`
and `last_candle_seen_at = 14:59:59` (old):

- On resume, the frontend fast-forwards the cursor to
  `roundTimeToNextMinute(14:59:59) = 15:00:00`.
- Engine advances; on the next forward step, the cursor reaches
  `close_ms = 16:00:00`, and the fix ships `candle.time = 16:00:00`
  unix seconds to `POST /trigger`.
- Backend: `last_candle_seen_at = 16:00`, `16:00 >= 15:00` → **true** →
  trigger fires.

Under the old code, this same resume would fire the trigger on the same
step (at cursor `16:00`, old `candle.time = 15:59:59`, `15:59:59 >=
15:00` → true). **Same behavior on resume.** No migration needed, no
migration concern.

---

## 3. Recommended QA before shipping

1. **Scenario A (alerts)** — rerun with fix applied. Confirm alert at
   `11:00` fires at cursor `11:00`, not `12:00`.
2. **Scenario B (order triggers)** — rerun. Confirm trigger at `15:00`
   fires at cursor `15:00`.
3. **Scenario C (resolution switch)** — rerun. Confirm 1h alert at
   `18:00` fires on the `18:00` step; 1m path continues to work.
4. **Scenario D (first trade undo)** — rerun with the "step forward then
   back" flow. Confirm position deletes cleanly. Visually inspect the
   trade marker at session start (pre-forward-step) to confirm the
   "floating trade" outcome from §2.3.6.
5. **Pre-fix backtest resume** — take a backtest paused under the old
   code, resume it under the fix, step forward and back. Confirm no
   orphans, resume cursor lands correctly.
6. **Time-expiring alert** — set an alert with expiry at a specific hour
   boundary. Confirm the final candle (closing AT the expiry time) gets
   its detection pass on that cursor step, and the alert is pruned on
   the NEXT step (behavior from §2.1.3 — strict `>`, intentionally
   asymmetric with triggers' `>=`).
7. **Default replay (non-smart)** — place a trade, step back, confirm
   local revert still works after applying the same `_currentActualTime`
   fix to `ReplayTradingController`.

---

## 4. Rollout

- Land §1.1 and §1.2 together — `_currentActualTime` removal +
  `checkResetToPossible` strict `<` on `closeTime`.
- Apply the same `_currentActualTime` rename to `ReplayTradingController`
  in the same commit (§2.6.1).
- Keep the QA list above attached to the PR for reviewer sanity.
- No backend release, no migration, no feature flag. The fix is
  self-contained in the SC replay controllers.
