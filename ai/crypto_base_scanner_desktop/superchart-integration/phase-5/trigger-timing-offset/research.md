# Trigger Timing Offset — Research

Research report for `prd.md`. No code changes.

Runtime evidence backing this report: [`reproducer-logs.md`](./reproducer-logs.md).

---

## 1. Origin of the one-candle offset

The offset lives in **two independent places** that both happen to produce the
same one-candle lag.

### Source 1 — Frontend: `_currentActualTime = _currentTime - 1000`

The SuperChart replay engine's `getReplayCurrentTime()` returns the **close
time** of the last visible candle (per
`ai/deps/SUPERCHART_API.md:776`:
`getReplayCurrentTime(): number | null // Unix ms close-time of last visible candle`).

That raw close-time value is what the UI cursor displays, but trigger/alert
comparisons in the SC replay code use a derived value:

- `smart-replay-controller.js:61` — `get _currentTime() { return this._replayController.time }`
  (close-time in ms)
- `smart-replay-controller.js:62` — `get _currentActualTime() { return this._currentTime - 1000 }`
  (close-time in ms minus exactly 1 second)

`_currentActualTime` is fed into every place that asks "what is the replay's
current moment?":

- alert evaluation: `smart-replay-controller.js:524` —
  `if (this._currentActualTime >= new Date(time).getTime()) ids.push(id)`
  (time alerts)
- alert sync pre-pause: `smart-replay-controller.js:617, 624, 627`
  (`_anyAlertWouldFire` — mirror of above, used to pause the engine
  synchronously when a trigger is about to fire)
- frontend time-trigger pre-check: `smart-replay-controller.js:577` —
  `const triggerHit = this._backtest.checkTriggers(candle, this._currentActualTime)`
  feeds into `backtest.js:476` —
  `const timeTriggerHit = this.checkAt && time >= (new Date(this.checkAt).valueOf())`
- triggered-alert stamping: `smart-replay-controller.js:554` —
  `.map(alert => ({...alert, updatedAt: this._currentActualTime}))`
- trend-line alert evaluation: `smart-replay-controller.js:529` —
  `this.trendLineShouldTrigger(this._currentActualTime / 1000, ...)`

Tick advancement happens one candle at a time via the engine. On every
`onReplayStep` callback, `replay-controller.js:285` writes
`engine.getReplayCurrentTime()` into `state.time`. That value is
`open_time + resolution_ms` of the just-drawn candle (close time), so the tick
size is exactly `resolutionToMs(resolution)` (e.g. `3600000` for 1h) per
step.

**Net effect on the frontend side**: at the moment the UI cursor displays
`T`, the alert evaluator compares against `T - 1s`, which is still inside the
previous candle, so an alert targeting exactly `T` (the open time of the
newly-drawn candle) only fires on the *next* step when cursor = `T + 1h`.

Scenario A confirms this exactly: alert set at `11:00`, cursor stepped through
`08:00 → 09:00 → 10:00 → 11:00 → 12:00`, fired on the `12:00` step.

### Source 2 — Backend: `candle.time = _currentActualTime / 1000`

Every frontend API call that reports "current replay time" to the backend
packs it into a `candle` hash via
`smart-replay-controller.js:67-70`:

```js
get _lastDrawnCandleWithCurrentTime() {
  if (!this._lastCandle) return null
  const {open, high, low, close} = this._lastCandle
  return {open, high, low, close, time: (this._currentActualTime) / 1000}
}
```

So `candle.time` (unix **seconds**) = `(close_ms - 1000) / 1000` = close_sec -
1. For a 1h candle closing at `16:00:00` UTC, `candle.time = 15:59:59`.

Scenario B's order-placement curl confirms it: `candle.time: 1776239999`
(`= Wed Apr 15 2026 07:59:59 +04:00`) — one second before the hour boundary.

This value lands in `app/api/api_v3/backtests.rb` — every endpoint that takes
the `:candle` helper params (`positions`, `positions/:id`,
`positions/:id/cancel`, `positions/:id/reduce`, `positions/:id/increase`,
`trigger`) extracts `time = params[:candle][:time]` and passes it to:

- `backtest.rb:70-75` — `Backtest#trigger(price, time, resolution)` writes
  `last_candle_seen_at: Util.normalize_time(time)`
- `backtest_position.rb` / `concerns/position_calculations.rb:17` — position
  `open_time` is set from `created_at` (which the backtests controller sets
  with `created_at: Time.at(time)` at `app/api/api_v3/backtests.rb:209`)
- `smart_position/entry_condition.rb:57-59` — time trigger is evaluated with
  `time >= self.start_at` (more on this in §3)

So the backend uses the exact same `close - 1s` value the frontend computed.
The offset is *inherited* by the backend, not re-introduced there.

---

## 2. Why the current behaviour exists

There is **no explicit design note** justifying the one-candle lag.
`_currentActualTime` has no comment explaining the `-1000` subtraction
(`smart-replay-controller.js:62` is a one-line getter).

The most plausible intent — and the one the user also called out in
`reproducer-logs.md` notes — is "klinecharts/SC already report the **close**
time of the last visible candle, and subtracting 1 second nudges that into
the previous second boundary so the candle's own time field (seconds,
exclusive of the next candle's open) matches the value klinecharts wants."

That is: the offset was introduced to make `candle.time` fit a "seconds
since epoch, end of the interval minus 1s" convention that some candle
pipelines use (e.g. `1776239999` instead of `1776240000`). Once that
convention was in place, the rest of the logic — alerts, triggers — was
written to evaluate against the same "actual time" value for consistency.

The user's explicit note in `reproducer-logs.md`:

> Alerts are handled fully in frontend, and could have been adapted to the
> backend's behavior. This logic could have been ported like this from the TV
> implementation.

confirms this was a direct port from the legacy TV replay path, not a
deliberate design decision. The TV replay implementation is no longer in the
repo (no `tradingview/controllers/replay/` directory — the SC
`smart-replay-controller.js` is the only live copy of this logic).

---

## 3. Frontend → backend timestamp flow

Every frontend site that sends a replay time to the backend, with exact
field, format, and backend consumer.

### 3.1 `POST /backtests/:backtest_id/positions` — create smart position

- **FE builder**: `smart-replay-controller.js:317-345`
  (`submitBacktestPosition`)
- **Field**: `candle: this._lastDrawnCandleWithCurrentTime` (`{open, high,
  low, close, time: (_currentTime - 1000) / 1000}`), `resolution`,
  `smartPosition`
- **Format**: `candle.time` = **unix seconds**, value = `close_ms - 1000`
  → seconds (i.e. last second of the previous candle window).
- **BE consumer**: `app/api/api_v3/backtests.rb:176-240`
  - `close = params[:candle][:close]`, `time = params[:candle][:time]`
  - Calls `backtest.trigger(close, time, params[:resolution])` —
    `backtest.rb:70-75` writes `last_candle_seen_at = Util.normalize_time(time)`
  - Builds position with `created_at: Time.at(time), updated_at: Time.at(time)`
    (`backtests.rb:209-210`)
  - `smart_position.update_exchange(true, close, close, time)` (`:213`)
- **Offset compensation anywhere in path**: none. Backend uses the raw value
  as-is.

### 3.2 `PATCH /backtests/:backtest_id/positions/:id` + `/cancel` + `/reduce` + `/increase`

- **FE builders**: `smart-replay-controller.js:347-400`
- **Field**: same `candle` shape, same `.time = close_sec - 1` semantics.
- **BE consumer**: `app/api/api_v3/backtests.rb:256-388`
  - All four routes start with `backtest.trigger(close, time, resolution)`
    → writes `last_candle_seen_at`.
  - `cancel` + `reduce` + `increase` additionally call
    `smart_position.set_current_time(time)` before the operation.
  - `increase` and `reduce` use `time` for their `update_exchange` calls.
- **Offset compensation**: none.

### 3.3 `POST /backtests/:backtest_id/trigger` — order time-trigger + price trigger evaluation

- **FE builder**: `smart-replay-controller.js:402-414` (`triggerBacktest`)
- **Field**: `{candle: this._lastDrawnCandleWithCurrentTime, resolution}`
- **BE consumer**: `app/api/api_v3/backtests.rb:413-437`
  - `time = params[:candle][:time]` (same close-1s value)
  - Transaction:
    1. `backtest.trigger(close, time, resolution)` — writes
       `last_candle_seen_at` on `Backtest`.
    2. For each open position:
       - `position.service.check_orders(low, high)` — price-trigger check
         (**not time-dependent**).
       - `position.update_exchange(false, low, high, time)` — this path is
         where the time-trigger actually fires. It walks into
         `concerns/smart_positionable.rb:1415` →
         `settings.entry_condition.triggered?(low, high, current_time.to_i)`
         where `current_time = last_candle_seen_at.to_i` (set two steps up).
  - **The comparison that matters**: `smart_position/entry_condition.rb:57-59`
    ```ruby
    def time_triggered?(time)
      self.start_at > 0 && time >= self.start_at
    end
    ```
    `time` here = `last_candle_seen_at` = `candle.time` from the FE =
    `close_sec - 1`. `start_at` is the user-configured target (open-of-hour,
    e.g. `1776250800` = `15:00:00`).
  - At cursor `15:00`: last_candle_seen_at = `14:59:59`. `14:59:59 >= 15:00:00` →
    **false**.
  - At cursor `16:00`: last_candle_seen_at = `15:59:59`. `15:59:59 >= 15:00:00` →
    **true** → fires. Matches Scenario B (trigger set `15:00`, fired `16:00`).
- **Offset compensation**: none.

### 3.4 `PATCH /backtests/:backtest_id/reset` — step-back rollback

- **FE builder chain**:
  `replay-controller.js:644-648` (`_stepBackOnce`) →
  `replay-controller.js:675-699` (`_revertAndSeek`) →
  `smart-replay-controller.js:770-781` (`resetTo`) →
  `smart-replay-controller.js:783-796` (`_flushPendingReset`) →
  `smart-replay-controller.js:798-807` (`_resetBacktest`)
- **Target computation**: `replay-controller.js:645-648`:
  ```js
  const currentTime = this._replayEngine.getReplayCurrentTime()  // close_ms
  const ms = resolutionToMs(this._getCurrentResolution())         // e.g. 3600000
  await this._revertAndSeek(currentTime - ms, () => ...)
  ```
  So the rewind target is `(close_ms - resolution_ms)` = the open time of
  the last drawn candle, in ms.
- **Field**: `_resetBacktest` at line 798-807 converts and sends:
  ```js
  const resetTo = resetToMs / 1000            // unix seconds
  const body = {resetTo, resolution}
  api.updateResource(`backtests/${backtestId}/reset`, {body})
  ```
  `resetTo` is **open-of-candle in unix seconds**. This is a *different*
  convention from `candle.time` (which is close-1s). The reset path is
  the only one that sends the open-time rather than the close-1s.
- **BE consumer**: `app/api/api_v3/backtests.rb:397-404`
  ```ruby
  patch '/backtests/:backtest_id/reset' do
    backtest = current_account.backtests.find(params[:backtest_id])
    backtest.backtest_positions.where("open_time >= ?", params[:reset_to]).destroy_all
    backtest.update(last_candle_seen_at: Util.normalize_time(params[:reset_to]))
    backtest.update_stats
    ...
  end
  ```
  - Deletes `backtest_positions` whose `open_time >= reset_to`.
  - `open_time` column is `integer` (unix seconds) per `db/schema.rb:315,2351`.
  - `open_time` is set from `created_at.to_i` via
    `concerns/position_calculations.rb:17`:
    `self.open_time ||= persisted? ? created_at.to_i : Time.now.to_i`
    and `created_at` was set at position creation to
    `Time.at(params[:candle][:time])` (= close_sec - 1).
  - Writes `last_candle_seen_at = reset_to` (open-of-candle seconds — note
    the inconsistency with the other endpoints' writes, which use
    close_sec - 1).
- **Offset compensation**: partial/incoherent. The reset path sends the
  **correct** open-time but is comparing against `open_time` which was
  populated with the **offset** close-1s. See §4 for the consequences.

### 3.5 `checkResetToPossible` — client-side only

`smart-replay-controller.js:733-757`. This runs on the FE before any reset
request goes out and uses `util.valueOfDate(openTime)` from the FE's copy of
the backtest state. `openTime` there comes from the backend response's
`backtestPositions` entries, whose value was originally set from
`created_at.to_i` (= close_sec - 1). So this local validator is also
operating on offset values. **No network request**; no contribution to the
FE→BE flow, but relevant to §4's ripple analysis.

### 3.6 `lastCandleSeenAt` resume marker

- **Written by backend**: every `backtest.trigger(...)` call sets
  `last_candle_seen_at` to `Util.normalize_time(params[:candle][:time])` —
  offset close-1s — via positions/trigger endpoints. The `reset` endpoint
  writes it to the (un-offset) `params[:reset_to]` instead.
- **Read by backend**: `backtest.rb:78-79` — `current_time` getter
  (`last_candle_seen_at.to_i`), consumed by
  `concerns/smart_positionable.rb:98-100` (entry condition check-at
  calculation) and `smart_positionable.rb:1415` (entry condition triggered
  check).
- **Read by frontend**: `smart-replay-controller.js:219` —
  `safeLastCandleSeenAt` is used on backtest resume to jump the replay cursor
  to the last known position. The FE rounds the stored value to the next
  minute (`util.roundTimeToNextMinute`) to paper over the close-1s sub-minute
  artefact, and then passes it to `_replayEngine.setCurrentTime(jumpTime,...)`
  as the resume ms — so resume loses at most the sub-minute offset but
  inherits the same hour-level offset the rest of the flow has.

---

## 4. Required changes

The fix must remove the `close - 1s` offset from both the frontend
comparison and the backend store, because:

- Alerts are evaluated frontend-only against `_currentActualTime` (Scenario
  A confirms this is purely FE).
- Order time-triggers are evaluated backend-only, against
  `last_candle_seen_at`, which is set from the frontend-supplied
  `candle.time` (Scenario B confirms this is purely BE).
- The reset path (Scenario D) already sends the correct open-time, but the
  backend compares it against `open_time` values that were populated with
  the offset — so the fix has to line those up too.

### 4.1 Frontend changes

**File**: `src/containers/trade/trading-terminal/widgets/super-chart/controllers/smart-replay-controller.js`

1. **Line 62** — change the semantic. Two equivalent options:
   ```js
   // Option A: use the engine's own close-of-candle value as "now"
   get _currentActualTime() { return this._currentTime }

   // Option B: represent "the open time of the last visible candle"
   get _currentActualTime() {
     return this._currentTime - resolutionToMs(this._resolution)
   }
   ```
   Option A keeps "now = close of last candle", option B shifts it to
   "now = open of last candle". Both eliminate the `-1000` artefact. Option
   A matches what the user sees in the cursor (the UI already displays
   `this.time` = close), so it's the less surprising choice and makes the
   rule "cursor value IS the replay time" hold.

2. **Line 69** — `_lastDrawnCandleWithCurrentTime` must stop subtracting 1
   from the seconds value it ships to the backend:
   ```js
   return {open, high, low, close, time: this._currentActualTime / 1000}
   ```
   Once (1) fixes `_currentActualTime`, this line needs no further edit,
   but the downstream effect is that `candle.time` in every request body
   becomes `close_sec` (hour boundary) instead of `close_sec - 1`.

3. **Line 577 and 554** — no edits; these sites read `_currentActualTime`
   and will automatically use the new value.

4. **Line 524, 617, 624, 627** — same, no edits.

5. **`checkResetToPossible` (line 733-757)** — **no edit.** The
   comparators (`time > openTime && time <= closeTime` for isClosed,
   `time > openTime` for isOpen) happen to line up correctly with the
   backend's `open_time >= reset_to` rule under the new semantics:

   - `target == openTime`: `time > openTime` is false → not flagged →
     reset proceeds → backend deletes (since `open_time >= openTime`).
     Correct.
   - `openTime < target < closeTime`: flagged → warning. Correct
     (backend would leave position in a mid-lifetime state).
   - `target == closeTime` with `openTime < closeTime`: flagged
     (`time > openTime && time <= closeTime`) → warning. Correct —
     backend would leave the closed position in place because
     `open_time < target`, so the reset would be a no-op. Flagging
     here surfaces the warning on the same step as the would-be
     no-op reset, avoiding a confusing "reset sent on step N,
     warning on step N+1" sequence.

   An earlier draft of this research proposed tightening to
   `time < closeTime`; follow-up reproducer evidence showed that
   change produces exactly the confusing delayed-warning sequence
   above. Reverted.

6. **`canStepBack` (replay-controller.js:152-171)** — unchanged. But see
   §4.4 for the first-candle symptom, which requires a semantically
   separate fix.

**Every frontend call site using `candle.time` is routed through
`_lastDrawnCandleWithCurrentTime`** (lines 324, 350, 367, 386, 404) so a
single fix at line 69 covers all five endpoints (positions create, cancel,
reduce, increase, trigger).

### 4.2 Backend changes

**File**: `/home/areg/git/altrady/crypto_base_scanner/app/api/api_v3/backtests.rb`

1. **Line 209, 210, 213, 262, 277, 280** — nothing to change here. The
   routes pass whatever `candle.time` the frontend sends; once the
   frontend change in §4.1 lands, these lines will store open-sec instead
   of close_sec - 1 without any backend edit.

2. **Line 397-404 (`PATCH /backtests/:backtest_id/reset`)** — the
   comparison `where("open_time >= ?", reset_to)` is correct under the new
   semantics. Both sides will be open-sec after the fix. No edit needed
   *as long as the fix in 4.1 is shipped together*.

   If the backend change is shipped *without* the frontend change (or in
   a different order), the reset will delete positions whose
   `open_time >= reset_to`, but `open_time` will still be `close_sec - 1`
   from already-created positions and the reset target is open-sec — so the
   orphan symptom in the sister PRD
   [`reset-to-orphan-trades/prd.md`](../reset-to-orphan-trades/prd.md) is
   partially entangled with this. See §4.3 ripple.

**File**: `/home/areg/git/altrady/crypto_base_scanner/app/models/smart_position/entry_condition.rb`

3. **Line 57-59** — `time_triggered?(time)` uses `time >= start_at` with
   `time = last_candle_seen_at`. Under the new FE semantics,
   `last_candle_seen_at` becomes "close-of-hour = open-of-next" instead of
   "close-of-hour - 1". That means for `start_at = 15:00` and cursor at
   `15:00`:
   - new last_candle_seen_at = `15:00:00` → `15:00 >= 15:00` → true → fires.
   - old last_candle_seen_at = `14:59:59` → false → did NOT fire.

   **No code edit needed** — the comparison is already `>=`, and the fix
   comes for free once the frontend stops subtracting 1.

**File**: `/home/areg/git/altrady/crypto_base_scanner/app/models/backtest.rb`

4. **Line 70-75 (`Backtest#trigger`)** — no edit. Just writes whatever
   `time` the frontend sends.

**Summary**: **backend changes are zero lines.** The entire fix is a
frontend semantic change to `_currentActualTime` and the one comparator
tweak in `checkResetToPossible`. Everything downstream inherits the fix
automatically.

### 4.3 Ripple effects

- **Alert evaluation (frontend)**: fixed directly. Scenario A's
  `11:00`-set alert will fire on the `11:00` step instead of `12:00`.
- **Order time-trigger evaluation (backend)**: fixed automatically via
  `last_candle_seen_at >= start_at`. Scenario B's `15:00` trigger will
  fire on the `15:00` step.
- **Position SL/TP/trailing triggers**: these are *price* triggers, not
  time — they evaluate `check_orders(low, high)` on the candle OHLC, not
  against `last_candle_seen_at`. Unaffected by the fix. Confirm by
  inspection: `backtests.rb:426` calls `position.service.check_orders(low,
  high)` which reads only price; no time comparison.
- **`last_candle_seen_at` semantics**: shifts from "close_sec - 1" to
  "close_sec" (open of next candle). This is a *wider* shift because
  every endpoint that writes it is now consistent. The only consumer of
  `last_candle_seen_at` is the backtest resume path (FE) which rounds to
  the next minute anyway — the rounding becomes a no-op but is harmless.
- **Backtest stats / progress**: `backtest.rb:102-106` computes progress as
  `(last_candle_seen_at - replay_start_at) / (replay_end_at - replay_start_at)`.
  Under the old semantics, progress was always 1s short of the true
  boundary. Under the new semantics, it is exact. No bug introduced, and
  progress bars become subtly more accurate.
- **`checkResetToPossible`**: no edit — existing comparators line up
  with the backend's rule. See §4.1.5.
- **`_hasChangesSince(target)` (smart-replay-controller.js:714)**: reads
  `openTime` and `trades[i].time`. Under the fix, these are all exact
  open-sec values. The existing `>=` comparison continues to match the
  same rows it used to, shifted by 1 second — behaviourally identical.
- **Resume-from-widget**: the stored `last_candle_seen_at` after the fix
  is exactly the close/open boundary. The FE's `roundTimeToNextMinute`
  guard (line 219) is now a no-op but still harmless. Backtests created
  *before* the fix lands will have `last_candle_seen_at` at `close - 1s`;
  on resume those will round up to the next minute as before, no
  migration needed.
- **Existing in-flight backtest positions** (created under the old
  semantics, with `open_time = close_sec - 1`) will be *1 second earlier*
  than new ones. If a user had a backtest session running when the fix
  ships, any step-back on a pre-fix position could attempt to delete
  `open_time >= X` and the old `close_sec - 1` value would still match the
  `>=` comparison correctly as long as the reset target is the same
  granularity or coarser — i.e. step-back on a pre-fix position still
  works. Confirm by walking through the numbers:
  pre-fix open_time = `14:59:59`, reset_to = `14:00:00` (one candle back),
  `14:59:59 >= 14:00:00` → true → deleted. Correct. No migration needed.

### 4.4 The "first-trade cannot be undone via step-back" symptom

This symptom is **entangled with the offset fix but not fully resolved by
it**. Scenario D's evidence is clear: the user stepped back from the first
drawn candle and **no `PATCH /reset` request was sent** at all. The request
is gated off upstream in `canStepBack` (replay-controller.js:170):

```js
return currentTime - ms >= startTime
```

At session start, `currentTime = startTime + ms` (engine places the cursor
at the close of the first drawn candle), so `currentTime - ms = startTime`
and `startTime >= startTime` → `true`. **But the user's actual trace
showed the opposite: step-back was silently blocked.** The most likely
explanation is the session's `startTime` (Redux state) was captured at the
engine's internal start time (`08:00:00` per the reproducer setup), and
the engine's `getReplayCurrentTime()` at the moment of the first click was
still `08:00:00` too (not yet advanced past the first candle because the
user hadn't stepped forward yet). In that state `currentTime - ms = 07:00`
and `07:00 >= 08:00` → **false** → step-back blocked.

Once that gate is passed (user stepping forward once, then back), the fix
chain plays out:

1. FE sends `resetTo = 08:00:00` (open of first candle, unix sec).
2. BE runs `where("open_time >= 08:00:00").destroy_all`.
3. Under the **old** offset: the position was created with
   `open_time = 07:59:59` (close_sec - 1). `07:59:59 >= 08:00:00` → false
   → position NOT deleted → orphan.
4. Under the **new** semantics (§4.1 applied): position created with
   `open_time = 08:00:00`. `08:00:00 >= 08:00:00` → true → deleted.

So the offset fix *does* resolve the "orphan after first-candle step-back"
symptom, but only after the user has stepped past the session start at
least once. The *literal* reproducer (place trade on first candle, click
step-back without moving) is blocked at `canStepBack` and is a **separate
issue** — it would require either:

- relaxing `canStepBack` to permit `currentTime - ms >= startTime` when
  `currentTime == startTime` (change `>=` to allow equality on the first
  candle), or
- making the UX cancel the position in-place without a true step-back
  (different feature, out of scope here).

**Recommendation**: call this out as a follow-up scoped to the orphan PRD,
since it overlaps with reset-path semantics and belongs with the reset
work rather than the timing offset. The timing fix alone will resolve the
scenario where a user moves one candle forward, places a trade, and steps
back — which is the realistic flow.

---

## 5. Frontend-only feasibility

**Answer: Yes — a pure-frontend fix is feasible and is actually the
recommended path.**

The mechanism is already there: the offset originates in the frontend's
`_currentActualTime = _currentTime - 1000` line and propagates to the
backend only because the frontend ships a derived value in `candle.time`.
Change the derivation on the frontend, and every downstream site — alert
evaluation, backend time-trigger evaluation, reset deletion — lines up
automatically with the user's expectation.

**Zero backend changes are strictly required**, because:

- `entry_condition.rb:57` already uses `>=`, which is the correct
  comparator once `last_candle_seen_at` is at the right boundary.
- `backtests.rb:399` already uses `>=` on `open_time`, which will match
  correctly once `open_time` is stored at the right boundary.
- `Backtest#trigger` (backtest.rb:70) is a pure pass-through.

The `checkResetToPossible` comparator needs **no change** — see
§4.1.5 for the walk-through.

**Limits of the frontend-only path**:

- **Pre-fix backtests**: any backtest session that already has persisted
  positions with `open_time = close_sec - 1` will be 1 second off. Walk-
  through in §4.3 shows this is behaviourally harmless for step-back (the
  `>=` comparison still matches), but statistics, progress, and the exact
  trade rendering on the chart overlay will be 1 second earlier than new
  positions. That's cosmetic; no migration needed.
- **The first-candle-step-back symptom is not fully fixed** by the offset
  alone — see §4.4.

**Recommended path**: **frontend-only**. One line at
`smart-replay-controller.js:62`, one comparator tweak at
`checkResetToPossible`, zero backend edits. Justification: the backend
comparisons are already correct under "now = open of next candle"
semantics; the bug is that the frontend has been feeding them a different
convention.

---

## 6. Risks and open questions

- **`canStepBack` vs. first-candle step-back**: §4.4 assumes the silent
  block in Scenario D is from `canStepBack` returning false. The user's
  log confirms "no reset request was sent" but does not distinguish
  between `canStepBack = false` and `checkResetToPossible` early-return.
  Validation: add a `console.log` in `handleStepBack` (before `canStepBack`
  is read) and in `checkResetToPossible`'s early-return branch; rerun
  Scenario D. Not required for the timing fix itself.

- **Resolution switch firing (Scenario C)**: 1h alert at `18:00` did not
  fire at `18:00` cursor, but fired at `18:01` on a 1m step. Under the
  proposed fix, the 1h case will fire at `18:00` directly. The 1m path
  works today because the step is 1 minute, so `_currentActualTime` at
  cursor `18:01` is `18:00:59`, which is `>= 18:00:00`. The 1m path will
  continue to fire on the `18:00` step (new semantics: `_currentActualTime
  = 18:00:00 → 18:00 >= 18:00 → true`). No regression. No edit needed in
  the resolution-switch code.

- **Integer seconds drift in `Util.normalize_time`**: the backend helper
  is a pass-through for integer params in the curls we inspected. Assumed
  behaviour: `Util.normalize_time(1776250800) == 1776250800`. If it does
  any rounding (e.g. to minute), the fix is unaffected because the value
  already sits on an hour boundary. Validate with a single spec run or a
  `tail -20` of the helper if doubtful.

- **Legacy TV replay cross-reference unavailable**: the repository no
  longer contains the TV replay controller
  (`tradingview/controllers/replay/` does not exist — SC is the only
  live replay code). The PRD's mention of it is stale. The user's note in
  `reproducer-logs.md` corroborates that the SC logic was a direct port
  of the TV logic, so identical-but-bugged behaviour across both is
  expected. The user's concurrent observation that the legacy TV path
  exhibits the same symptoms (per PRD description) is consistent with
  the port having copied `_currentActualTime = _currentTime - 1000` intact.

- **`_lastCandle` freshness**: `updateCurrentState(candle)` sets
  `_lastCandle = candle` before calling `checkTriggers`. On a held-step
  autorepeat or fast-play, there is a theoretical window where
  `_lastCandle` is the previous candle and `_currentActualTime` has
  already advanced. Not observed in the reproducer logs; flagging as an
  open question for the implementation PRD because any change to the
  semantics of "current time" needs to avoid introducing a 2-candle lag
  on fast-play. Recommended: verify with a 1m 20x play that trigger fires
  on the right candle post-fix.

- **Resume-from-widget with pre-fix sessions**: migration concern is
  "none required" but the exact semantics are worth calling out in the
  implementation PRD's QA plan. A session paused under the old offset
  stored `last_candle_seen_at = close_sec - 1`; on resume under the new
  build, the FE's `roundTimeToNextMinute` already rounds it up to the
  next minute, and the engine's `setCurrentTime(jumpTime)` places the
  cursor at the matching candle close. Behaviour is unchanged. Confirm
  with a persisted backtest before + after the fix.
