# Trigger Timing Offset — Review Tests

Verification checklist for the fix described in
[`fix-plan.md`](./fix-plan.md). Runs against the reproducer flows from
[`reproducer-logs.md`](./reproducer-logs.md) plus additional boundary cases
and side effects from the plan.

Tests are grouped by method: **sight** (visual check in the app),
**logs** (read / paste console output), **scenario+logs** (run a user
flow then paste the resulting logs for the main session to interpret).

All logs added by the fix are tagged with `[tto]` (trigger-timing-offset)
for easy filtering. To collect them: open DevTools → Console, filter by
`[tto]`, run the scenario, and copy the relevant block into the test
below.

---

## T1 — Scenario A: time alert fires on target candle

**Type**: scenario + logs

**Setup**: fresh smart replay session, 1h resolution, liquid market.
Session start at an hour boundary (e.g. start cursor at `08:00`).

**Steps**:
1. Create a **time alert** (alertType = `time`) set ~3 candles ahead of
   the session start (e.g. `11:00`).
2. Step forward one candle at a time. Note the cursor value at each step.
3. At the moment the alert fires, copy the `[tto] alert-check (time)`
   log for the firing step from the console below.

**Expected**: alert fires when cursor reaches exactly `11:00` — i.e. on
the step *into* the candle whose open time is `11:00` (the first 1h
candle where `_currentTime >= 11:00`).

**Console logs to capture**:

```
[tto] alert-check (time) {
  "alertId": "432b613f",
  "alertTime": 1776150000000,
  "alertTimeIso": "2026-04-14T07:00:00.000Z",
  "currentTime": 1776150000000,
  "currentTimeIso": "2026-04-14T07:00:00.000Z",
  "fired": true
}
```

**Pass criteria**:
- The `currentTime` in the log equals `11:00:00.000` (unix ms).
- The `alertTime` equals `11:00:00.000`.
- `fired: true`.
- The visible cursor in the UI at that moment is `11:00`.

---

## T2 — Scenario B: order time-trigger fires on target candle

**Type**: scenario + logs

**Setup**: same session. Refresh if needed.

**Steps**:
1. Place a smart entry order with a time trigger at e.g. `15:00`.
2. Before stepping, copy the `[tto] position-sent` log from the console
   below (captures the `candle.time` going to the backend at position
   creation).
3. Step forward one candle at a time until the order fires.
4. Copy the `[tto] trigger-sent` log from the firing step.
5. Copy the backend's returned backtest `[tto] backtest-received` log
   with the created position's `open_time`.

**Expected**:
- `candle.time` on position creation = **unix seconds of the hour
  boundary at cursor** (e.g. if cursor is `13:00` at placement,
  `candle.time` = `1776258000` i.e. `13:00:00`, NOT `13:00:00 - 1s`).
- Order fires when cursor reaches `15:00`, not `16:00`.
- The position's `open_time` returned from the backend matches the
  `candle.time` sent (same unix seconds, no offset).

**Console logs to capture**:

```
[tto] position-sent {
  "candleTime": 1776153600,
  "candleTimeIso": "2026-04-14T08:00:00.000Z",
  "currentTime": 1776153600000,
  "currentTimeIso": "2026-04-14T08:00:00.000Z"
}
[tto] backtest-received (post-position) {
  "lastCandleSeenAt": "2026-04-14T08:00:00.000Z",
  "positions": [
    {
      "id": 28642,
      "status": "open",
      "openTime": 1776153600,
      "closeTime": null,
      "openTimeIso": "2026-04-14T08:00:00.000Z",
      "closeTimeIso": null
    }
  ],
  "trades": []
}
```

```
[tto] trigger-hit (frontend pre-check) {
  "currentActualTime": 1776164400000,
  "currentActualTimeIso": "2026-04-14T11:00:00.000Z",
  "checkAt": "2026-04-14T11:00:00.000Z",
  "checkAtIso": "2026-04-14T11:00:00.000Z"
}
console.js:12 [tto] trigger-sent {
  "candleTime": 1776164400,
  "candleTimeIso": "2026-04-14T11:00:00.000Z",
  "currentTime": 1776164400000,
  "currentTimeIso": "2026-04-14T11:00:00.000Z"
}
```

```
[tto] backtest-received (post-trigger) {
  "lastCandleSeenAt": "2026-04-14T11:00:00.000Z",
  "positions": [
    {
      "id": 28642,
      "status": "open",
      "openTime": 1776164400,
      "closeTime": null,
      "openTimeIso": "2026-04-14T11:00:00.000Z",
      "closeTimeIso": null
    }
  ],
  "trades": [
    {
      "externalOrderId": "460224de-9782-4084-861a-de8807de3e0f",
      "time": 1776164400,
      "timeIso": "2026-04-14T11:00:00.000Z"
    }
  ]
}
```

**Pass criteria**:
- `[tto] position-sent` shows `candle.time` as a clean hour boundary
  (ends in `00`, not `99`).
- `[tto] backtest-received` shows the returned position's `openTime`
  matches the `candle.time` that was sent — if both are equal on the
  hour, the offset has been removed end-to-end.
- Trigger fires one candle earlier than the current bug (cursor `15:00`
  instead of `16:00`).

---

## T3 — Scenario C: 1h alert fires on 1h step, not only on 1m drop-down

**Type**: sight

**Setup**: same session.

**Steps**:
1. Set a **time alert** (alertType = `time`) at `18:00` on 1h resolution.
2. Step forward on 1h until cursor = `18:00`.
3. Confirm: **alert fires on that step** (new behavior). Under the old
   bug it only fired after switching to 1m and stepping once.

**Pass criteria**: alert fires on the `18:00` 1h step. No resolution
switch needed.

---

## T4 — Scenario D (corrected): first-candle trade undo via step-forward-then-back

**Type**: scenario + logs

**Setup**: fresh smart replay session. Session start at an hour
boundary.

**Steps**:
1. On the very first drawn candle (cursor = session `startTime`), place a
   smart order and let it fill. Copy the `[tto] position-sent` log.
2. Copy the `[tto] backtest-received` log showing the created position's
   `openTime`.
3. Click step-forward once. Cursor moves to `startTime + 1h`.
4. Click step-back once. Copy the `[tto] reset-sent` log and the
   resulting `[tto] backtest-received` log.
5. Visually confirm the trade has been removed from the chart and the
   positions list.

**Expected**:
- Position `openTime` post-creation = `startTime` (unix seconds),
  matching the session's hour boundary exactly.
- After step-back, `[tto] reset-sent` shows `resetTo = startTime` (unix
  seconds).
- Backend deletes the position (positions list becomes empty in the
  widget, chart overlay disappears).

**Console logs to capture**:

```
[tto] position-sent {
  "candleTime": 1776139200,
  "candleTimeIso": "2026-04-14T04:00:00.000Z",
  "currentTime": 1776139200000,
  "currentTimeIso": "2026-04-14T04:00:00.000Z"
}
```

```
[tto] backtest-received (post-position) {
  "lastCandleSeenAt": "2026-04-14T04:00:00.000Z",
  "positions": [
    {
      "id": 28643,
      "status": "open",
      "openTime": 1776139200,
      "closeTime": null,
      "openTimeIso": "2026-04-14T04:00:00.000Z",
      "closeTimeIso": null
    }
  ],
  "trades": [
    {
      "externalOrderId": "f9e34e59-8e94-4e90-ab06-031033aad47a",
      "time": 1776139200,
      "timeIso": "2026-04-14T04:00:00.000Z"
    }
  ]
}
```

```
[tto] reset-sent {
  "resetTo": 1776139200,
  "resetToIso": "2026-04-14T04:00:00.000Z",
  "currentTime": 1776142800000,
  "currentTimeIso": "2026-04-14T05:00:00.000Z",
  "resolutionMs": 3600000
}
```

```
[tto] backtest-received (post-reset) {
  "lastCandleSeenAt": "2026-04-14T04:00:00.000Z",
  "positions": [],
  "trades": []
}
```

**Pass criteria**:
- `position-sent.candle.time == backtest-received.position.openTime`
  (both on the hour boundary).
- `reset-sent.resetTo == openTime` (same value).
- Position is gone from the post-reset payload.

**Note**: This explicitly requires the step-forward-then-back flow. The
"step back immediately on first drawn candle" flow is still blocked by
`canStepBack` (this is structurally correct — see `fix-plan.md` §1.3).

---

## T5 — First-candle trade: visual anchor at session start

**Type**: sight

**Setup**: fresh smart replay session, step 0 (no forward steps yet).

**Steps**:
1. Place a trade on the first drawn candle.
2. Visually inspect where the trade marker appears on the chart
   **before** stepping forward.

**Expected (one of three)**:
- **A**: Marker sits cleanly at the right edge of the last drawn candle
  (acceptable — the "in the air" timestamp renders on the boundary and
  visually attaches to the previous candle). **PASS.**
- **B**: Marker appears floating slightly to the right, past the last
  drawn candle, in otherwise-empty space. **ACCEPTABLE** if the trade
  snaps back into place on the next forward step. **CHECK**: step
  forward once, confirm the marker lands on the newly-drawn candle.
- **C**: Marker does not render at all, or klinecharts logs a warning.
  **BLOCKER** — needs a follow-up cosmetic fix in the trade overlay
  layer.

Record which outcome was observed:

```
B. marker has the price-height of the close of the last drawn candle (07:00), at the timestamp of the current time (08:00)
This is correct
```

---

## T6 — Step back past a multi-candle closed position

**Type**: scenario + logs

**Setup**: fresh smart replay session, 1h resolution.

**Steps**:
1. Open a position with MARKET on the first drawn candle.
2. Step forward twice (cursor = `startTime + 2h`).
3. Close the position with MARKET. `openTime` and `closeTime` are now
   two candles apart (e.g. `07:00` and `09:00`).
4. Step forward twice more (cursor = `closeTime + 2h`).
5. Step back once (cursor = `closeTime + 1h`). Capture
   `[tto] reset-sent` if any.
6. Step back once more (target = `closeTime` exactly). Capture
   `[tto] reset-sent` and `[tto] backtest-received`.
7. Step back once more (target = `closeTime - 1h`, mid-lifetime).

**Expected**:
- Step 5: cursor moves; reset may or may not fire depending on
  `_hasChangesSince`.
- Step 6: **cursor moves**, no warning. A `[tto] reset-sent` likely
  fires (close trade is at `target`), backend returns the position
  unchanged (still closed at `closeTime`). The trade marker sits at
  the cursor boundary.
- Step 7: **"positions partially closed" warning toast**, cursor does
  NOT move, no `[tto] reset-sent`.

**Pass criteria**: only mid-lifetime step-backs (target strictly
between `openTime` and `closeTime`) are blocked. Boundary targets
(`target == closeTime` or `target == openTime`) are allowed.

**Variant — expired LIMIT (no trades)**: place a LIMIT entry with a
time expiration. Step until cursor crosses the expiry — position
auto-cancels. closeTime is the cursor at cancellation. From cursor
`closeTime + 1h`, step back once. Cursor should move to `closeTime`,
no warning. From `closeTime`, step back again (target = mid-lifetime)
— warning, no movement. This is the scenario that motivated the
strict `<` on `closeTime`.

**Separate flow** (sanity check): after the warning, jump back
directly to a time ≤ `openTime` (right-click chart → "Jump back to
here" on a candle before the open). That should succeed with no
warning — the entire position deletes cleanly.

---

## T7 — Resolution switch consistency

**Type**: sight

**Setup**: fresh smart replay session.

**Steps**:
1. Set a time alert (alertType = `time`) at a known hour boundary
   (e.g. `12:00`).
2. On 1h, step until cursor is one candle *before* target (`11:00`).
3. Switch to 1m resolution. The cursor stays at `11:00`.
4. Step forward on 1m until cursor reaches `12:00`.
5. Confirm the alert fires on the exact `12:00` step (not `12:01`).

**Pass criteria**: 1m cursor step to `12:00` fires the alert. Works
equivalently to the 1h case.

---

## T8 — Alert expiry — final-candle detection must still run

**Type**: scenario

**Setup**: fresh smart replay session, 1h resolution.

**Steps**:
1. Set a price alert with `expiresAt = 10:00` (hour boundary) and a
   price that would cross during the `09:00–10:00` candle
   (e.g. direction "up", price below the `09:00–10:00` candle's high).
2. Step forward until the cursor reaches `10:00` (the close of the
   `09:00–10:00` candle).
3. Observe: does the alert fire?

**Expected**: alert **fires** on the `10:00` step. The expiry
comparison is strict `>`, so `_currentTime > expiresAt` is false at
cursor `10:00` and the alert's detection pass runs against the
`09:00–10:00` candle's OHLC. "Expires at 10:00" means "valid for the
candle that closes at 10:00, pruned from the next step onward."

**Design note**: this is intentionally asymmetric with triggers
(which use `>=` and fire AT the cursor). Backend position expiry
uses the same strict `<` rule (`smart_positionable.rb:1430`), so
alerts and positions behave identically: triggers arm at the
boundary, expiries die after it. Kept consistent across alerts and
positions; symmetric inside each category, asymmetric between
trigger-vs-expiry by design.

**Pass criteria**:
- Alert fires on the cursor `10:00` step (not earlier, not later).
- The `[tto] alert-check` log (if this were a time alert, which it
  isn't for T8) / manual observation shows the alert in the
  "triggered" list after the `10:00` step.

**Expiry without firing**: if the alert's price does NOT cross during
the `09:00–10:00` candle, the alert is still "active" at cursor
`10:00` (strictly-greater check is false at the boundary), detection
runs and finds nothing, and on the `11:00` step the alert is pruned
by `_pruneExpiredAlertsNow` — removed from the chart and positions
list just as if the user cancelled it manually. Test this variant
too: set expiry at `09:00` with a price that would only cross *after*
expiry (on `09:00–10:00`), step to `10:00`, confirm the alert
disappears.

**Pass criteria**: observed matches expected under fix.

---

## T9 — Persisted pre-fix backtest resume

**Type**: scenario

**Setup**: a backtest created under the pre-fix build (any backtest
with `lastCandleSeenAt` set by the old code — i.e. created before this
fix commit lands).

**Steps**:
1. Open the Backtests widget, find a paused pre-fix backtest with at
   least one trade.
2. Click "Resume" and let the session load. Note the cursor position
   and which candle the trade renders on.
3. Step forward N candles (e.g. 2).
4. Step back N candles (back to the resume cursor). Observe: **no
   reset call** is sent — `_hasChangesSince` returns false because
   the pre-fix trade's stored `time = close_sec - 1` is one second
   *before* the boundary the step-back targets.
5. Step back **one more time** (cursor now N+1 candles before the
   trade). Now the reset fires. Copy the `[tto] reset-sent` log and
   the post-reset `[tto] backtest-received` log.

**Expected**:
- Resume renders the trade on the same candle it was placed on
  under the old code (the pre-fix `time = close_sec - 1` falls inside
  the previous candle's interval).
- Steps 3 and 4 are silent (no backend call, no orphan).
- Step 5 fires the reset and the position deletes cleanly: the
  backend's `where("open_time >= reset_to")` matches the pre-fix
  `open_time = close_sec - 1` against a target one full candle
  earlier.

**Pass criteria**: no orphans, no console errors. Pre-fix trades
require **one extra step-back** compared to post-fix trades — this
is expected mixed-semantics behavior, not a bug. Under post-fix
semantics, the trade's `time` would have been on the boundary and
the first step-back target would have hit it directly.

**Why this happens**: the reset target computation is unchanged by
the fix (`engine.getReplayCurrentTime() - resolution_ms`, always on
boundary). What shifts is *where the trade's stored time sits
relative to that boundary*: pre-fix is 1s below the boundary,
post-fix is on the boundary. `_hasChangesSince` uses `>=`, so a
pre-fix trade's time falls below the next-step's target by 1s and
is skipped on the first step-back attempt.



---

## T10 — Default (non-smart) replay: local step-back still works

**Type**: sight

**Setup**: fresh default (non-smart) replay session.

**Steps**:
1. Step forward a few candles.
2. Buy. Step forward. Sell. Step forward.
3. Step all the way back to session start.
4. Verify trades disappear as the cursor crosses them, matching the
   smart replay fix.

**Pass criteria**: trades are reverted by step-back. No trades remain
when cursor is at session start. The fix has been applied to the default
replay controller as well.

---

## T11 — Fast-play (20 cps) does not re-introduce lag

**Type**: sight

**Setup**: fresh smart replay session. Set a time alert 5-10 candles
ahead. Set replay speed to 20 cps (default).

**Steps**:
1. Press Play.
2. Observe the cursor position at which the alert fires (watch for the
   pause/toast).

**Expected**: alert fires on the candle whose open equals the alert
time. Under fast-play the engine fires multiple `onReplayStep`
callbacks per tick, but the sync pre-pause (`_anyAlertWouldFire`) should
still catch the fire candle on the correct step.

**Pass criteria**: alert fires on the correct candle (not one candle
late, not one candle early). No "debt accumulation" behavior.

---

## T12 — Held-step autorepeat

**Type**: sight

**Setup**: fresh smart replay session with a time alert
(alertType = `time`) 5+ candles ahead.

**Steps**:
1. Hold the step-forward hotkey down.
2. Release when the alert fires.

**Pass criteria**: alert fires on the exact target candle, not one step
before or after.

---

## T13 — `candle.time` consistency across all backend endpoints

**Type**: logs

**Setup**: fresh smart replay session.

**Steps**:
1. Place a position (entry).
2. Modify the position (click "Edit" or add a TP).
3. Cancel the position.
4. Collect all `[tto] position-sent`, `[tto] position-updated`,
   `[tto] position-cancelled`, `[tto] position-reduced`,
   `[tto] position-increased`, and `[tto] trigger-sent` logs.

**Expected**: every `candle.time` value is on the same hour boundary
(equal across all endpoints for the same step). No `...999`/`...59`
artefacts.

**Console logs to capture**:

```
[tto] position-sent {
  "candleTime": 1776153600,
  "candleTimeIso": "2026-04-14T08:00:00.000Z",
  "currentTime": 1776153600000,
  "currentTimeIso": "2026-04-14T08:00:00.000Z"
}
console.js:12 [tto] backtest-received (post-position) {
  "lastCandleSeenAt": "2026-04-14T08:00:00.000Z",
  "positions": [
    {
      "id": 28669,
      "status": "open",
      "openTime": 1776153600,
      "closeTime": null,
      "openTimeIso": "2026-04-14T08:00:00.000Z",
      "closeTimeIso": null
    }
  ],
  "trades": [
    {
      "externalOrderId": "e911ac95-6530-4136-a9d0-0b2a52fb3468",
      "time": 1776153600,
      "timeIso": "2026-04-14T08:00:00.000Z"
    }
  ]
}
console.js:12 [tto] position-updated {
  "candleTime": 1776193200,
  "candleTimeIso": "2026-04-14T19:00:00.000Z",
  "currentTime": 1776193200000,
  "currentTimeIso": "2026-04-14T19:00:00.000Z"
}
console.js:12 [tto] backtest-received (post-position) {
  "lastCandleSeenAt": "2026-04-14T19:00:00.000Z",
  "positions": [
    {
      "id": 28669,
      "status": "open",
      "openTime": 1776153600,
      "closeTime": null,
      "openTimeIso": "2026-04-14T08:00:00.000Z",
      "closeTimeIso": null
    }
  ],
  "trades": [
    {
      "externalOrderId": "e911ac95-6530-4136-a9d0-0b2a52fb3468",
      "time": 1776153600,
      "timeIso": "2026-04-14T08:00:00.000Z"
    }
  ]
}
console.js:12 [tto] position-cancelled {
  "candleTime": 1776200400,
  "currentTime": 1776200400000
}
```

**Pass criteria**: every `candle.time` value ends in `00`
(hour boundary in unix seconds), never `59` or `99`.

---

## T14 — Trend-line alert still triggers correctly

**Type**: sight

**Setup**: fresh smart replay session.

**Steps**:
1. Draw a trend-line alert with clear direction.
2. Step forward and confirm the trend-line alert fires on the right
   candle (the first candle where price crosses the interpolated line).

**Pass criteria**: trend-line alerts behave as before — the 1-second
shift in the x-coordinate is imperceptible for typical slopes.

---

## T15 — Grid bot backtests unaffected

**Type**: sight

**Setup**: go to the Grid Bot section, run a quick backtest of an
existing grid bot configuration.

**Pass criteria**: grid bot backtest runs and completes normally. No
regression in grid bot flows — they use a separate code path
(`MockBacktestingService`) and should be untouched by this fix.

---

## T16 — `[tto]` log cleanup

**Type**: sight

**After all other tests pass**, confirm the user is happy with the
results. Then **remove all `[tto]` console logs** from the code before
the fix is merged. These are instrumentation only — not for production.

**Pass criteria**: `grep -r "\[tto\]" src/` returns no matches.

---

## Summary

- Tests T1–T4 cover the primary bug fix and its reproducer scenarios.
- T5, T6, T7 cover specific side effects called out in the fix plan.
- T8 is a deliberate behavior change, documented for user awareness.
- T9 covers pre-fix backtest resume compatibility.
- T10 covers the default replay code path.
- T11, T12 cover fast-play and held-step paths.
- T13 is a log-only sanity check that every endpoint ships the same
  corrected timestamp.
- T14, T15 are regression checks.
- T16 is final cleanup.
