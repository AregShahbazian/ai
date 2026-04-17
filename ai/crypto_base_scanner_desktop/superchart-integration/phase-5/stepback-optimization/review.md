# Phase 5: Replay Step Back Optimization — Review

PRD: `prd.md` (id `sc-replay-stepback-optimization`)
Design: `design.md`

---

## Round 1: Initial verification (2026-04-15)

### Implementation summary

- **`smart-replay-controller.js`:**
  - New field `_pendingResetTo = null` on `SmartReplayController`
  - New private methods `_clearPendingReset`, `_flush`, `_hasPositionsSince`,
    `_untriggerAlertsSince`, `_flushPendingReset`
  - `resetTo` rewritten to branch dirty/quiet via `_hasPositionsSince`
  - `_processTriggerAsync` clears pending as first line (forward-past-rewind)
  - `loadBacktest`, `reset`, `destroy` clear pending
  - `exitSmartMode` flushes at top
  - `submitBacktestPosition`, `cancelBacktestPosition`,
    `increaseBacktestPosition`, `reduceBacktestPosition` flush at top
- **`replay-controller.js`:**
  - `_stop` flushes at top (covers `handleStop`, `handleBackToStartClick`
    smart branch, `_startReplayInMode` cross-mode restart — all via `_stop`)
  - `_startSession` clears pending

### Design deviation from initial plan

Tasks 6, 7, and 10 collapsed into a single flush at the top of `_stop`
after discovering that `handleBackToStartClick`'s smart branch creates a
new backtest rather than issuing `/reset(startTime)`. See `design.md` →
"Implementation correction". PRD R4 list is unchanged — the flush points
are all hit, just via a single centralized hook.

### Alert un-trigger decision

Per user input: **drop-only, no restore**. `_untriggerAlertsSince` and
`_flushPendingReset` both filter `triggeredAlerts` without moving entries
back to `alerts`. Matches pre-optimization behaviour.

---

### A. Quiet step-back — no backend call

1. Smart replay, empty session (no positions, no triggered alerts), step
   back once on a quiet candle. Network tab shows **zero** `/reset` PUTs.
2. Same as 1 but step back 5 candles in sequence. Zero PUTs. Chart rewinds
   five candles visibly.
3. Smart replay with 1 position opened at candle C. Step back N candles
   where all N land after C. Zero PUTs.
4. During 1–3, `updatingPosition` never flips to true. No loading overlay
   flashes on the chart.
5. After a quiet step-back, `smart._pendingResetTo` holds the earliest
   target across the sequence (inspect via Redux devtools or a temporary
   console log).

### B. Dirty step-back — one backend call

6. Smart replay with 3 positions at candles C1 < C2 < C3. Step back past
   C3 but not C2: **one** PUT fires, position C3 destroyed, C1 and C2
   intact.
7. Continue stepping back past C2: **one** PUT fires, C2 destroyed.
8. Quiet prefix + dirty: place a position at C3, step back 5 quiet
   candles first, then one more step past C3. Expect **one** PUT with
   `resetTo` equal to the earliest quiet target (6 candles earlier than
   start of sequence), and C3 destroyed.
9. Dirty flush UI: `updatingPosition` flickers true→false exactly once
   per dirty PUT.

### C. Alert un-trigger — drop-only semantics

10. Smart replay, price alert on candle C. Play until it triggers
    (appears in `triggeredAlerts`). Step back past C. Alert disappears
    from `triggeredAlerts` AND does not reappear in `alerts` (active).
    Play forward past C again — alert does NOT re-trigger (it's gone).
    This matches pre-optimization behaviour.
11. Candle-boundary case: alert fires on candle C (close = T). Step back
    to engine time T exactly (same candle that triggered). Alert stays
    triggered (`updatedAt = T - 1000 < T` → filter keeps it). Step back
    one more candle (engine time T − resolutionMs). Alert is dropped.

### D. Flush points

12. **handleStop flush.** Step back 3 quiet, click Exit Replay, confirm →
    **one** `/reset` PUT with earliest target, session ends, backtest on
    server has `last_candle_seen_at` equal to stepped-back time.
13. **handleStop cancel.** Step back 3 quiet, click Exit → cancel dialog.
    **Zero** PUTs. `_pendingResetTo` still set. Next action batches from
    the preserved target.
14. **Back to Start (smart).** Step back 3 quiet, click Back to Start →
    **one** PUT fires (the flush), then a new backtest is created via
    `quickStartBacktest`. Old backtest persists in the widget with
    `last_candle_seen_at` equal to the flushed target.
15. **Cross-mode restart.** Start smart, step back 3 quiet, open pick
    mode and start a default session → **one** PUT fires (flush via
    `_stop` in `_startReplayInMode`), then default session begins.
16. **exitSmartMode (toggle).** Step back 3 quiet, click Toggle Replay
    Mode → **one** PUT, backtest persisted with stepped-back state,
    default session begins at engine's current time.
17. **Submit trade flush.** Step back 3 quiet, click Buy → **two** PUTs
    in order: `/reset` at the stepped-back time, then `/positions`
    create. New position's `openTime` on the server matches the current
    (stepped-back) engine time, NOT the stale pre-stepback time.
18. **Cancel trade flush.** Existing open position, step back 3 quiet,
    cancel → **two** PUTs in order.
19. **Increase position flush.** Same.
20. **Reduce position flush.** Same.
21. **Alert ops do NOT flush.** Step back 3 quiet, create a new alert
    (price / time / trendline) → **zero** PUTs. Alerts are local.

### E. Clear points (no flush)

22. **Forward past pending.** Step back 3 quiet, let the engine play
    forward past them until a trigger fires. The trigger's own
    `triggerBacktest` PUT fires normally; no extra flush PUT. Inspect:
    `_pendingResetTo` is null immediately at the top of
    `_processTriggerAsync`.
23. **Session start clear.** Exit session, start a new smart session →
    `_pendingResetTo` starts null. Verify via the first step-back: no
    unexpected old target leaks in.
24. **Resume from widget.** Flushed exit (test 12), then resume the
    backtest from the widget → loads at stepped-back time,
    `_pendingResetTo` starts null.

### F. R6 — behavioural equivalence to un-optimized

25. Place 3 positions across 5 candles with gaps. Step back across all
    of them one at a time, then Exit → `backtestPositions` on the
    server after the session is the same set that would result from
    the un-optimized per-step flushes.
26. `last_candle_seen_at` on the server after any flush point matches
    the earliest stepped-back engine time since the last flush.
27. Resume after a flushed exit: engine jumps to the stepped-back
    position, not the pre-stepback position.

### G. R7 — held-key performance

28. Hold `shift+left` across 30 quiet candles (empty session): **zero**
    `/reset` PUTs, **zero** `updatingPosition` flickers, ~30 rewinds
    rendered.
29. Network throttled to 1s/req + 30-candle held rewind: still zero
    PUTs until a flush point. Release point is smooth.
30. Mixed held rewind: 20 quiet + 5 dirty interleaved. Exactly one PUT
    per dirty candle crossed (5 total), plus zero for the quiet
    prefixes. `_stepInFlight` serializes properly — no overlapping
    PUTs in the waterfall.

### H. Trading Terminal context

31. **Change TradingTab during pending state.** Start smart replay tab A,
    step back 3 quiet, switch to tab B (no replay). Tab A's pending
    state is preserved (per-controller). Switch back, step back
    again → earliest target still correct.
32. **Change coinraySymbol.** Symbol change exits replay (engine
    auto-exit). `_startSession` on re-entry clears pending. Verify no
    stale leak.
33. **Change resolution mid-pending.** Step back 3 quiet at 1h, switch
    to 4h. Engine re-seeks at new resolution; `_pendingResetTo` stays
    valid (same backtest, same position `open_time` values, local
    state unchanged). Step back once more at 4h → batches correctly
    from the preserved target.
34. **Change exchangeApiKeyId.** Replay-side unaffected. Pending intact.

### I. Edge cases

35. **Partial-split validation.** Step back into a range where
    `checkResetToPossible` returns an error (partial position split).
    Toast fires, `_pendingResetTo` unchanged, engine does not move.
    Next valid step-back batches correctly from the preserved target.
36. **Backend failure on dirty flush.** Simulate 500 on `/reset`:
    `_flushPendingReset` clears `_pendingResetTo` **before** the await,
    so after the failure the controller state is clean. Error toast
    fires via `_revertAndSeek`'s catch. Next step-back starts fresh.
37. **`goBackTo` multi-candle (future entry point).** Not wired to UI
    yet, but calling `replay.goBackTo(time)` from the console applies
    the same branching. No regression vs single-step path.
38. **View mode (finished backtest).** `canStepBack` is false, the
    branch is never reached. No pending state possible.
39. **Natural session end (FINISHED transition).** Continuous playback
    reaches the last candle → pause-on-last (per base `sc-replay`).
    User steps back 2 quiet candles → then plays forward → first
    forward step triggers `_processTriggerAsync` which clears pending.
    Further forward play hits empty buffer → FINISHED. No flush
    happens at FINISHED time because pending is already null. Verify
    `setBacktestFinished` is called with the correct terminal state.
