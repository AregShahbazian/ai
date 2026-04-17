# Phase 5: Replay Overlays — Review

## Round 1: Implementation (2026-04-07)

### Verification

**Conditional rendering:**
1. Start replay → BidAsk, alerts, orders, context menu overlays disappear
2. Stop replay → all overlays reappear
3. Trades, Bases, BreakEven, PnlHandle remain visible during replay
4. No console errors on replay start/stop

**ReplayTimelines:**
5. Start replay → green "Start At" vertical line at start time
6. Step/play → orange "Now At" line moves with each candle
7. At ready state (before first step) → no "Now At" line shown
8. At finished state → "Now At" line disappears, red "End At" line shows
9. Stop replay → all timeline lines gone
10. Lines have timestamp labels

**Trades data switching:**
11. Live mode → shows regular trades as before
12. Replay mode → only shows replay trades (from buy/sell during session)
13. Execute buy during replay → trade marker appears on chart
14. Stop replay → regular trades shown again

**BreakEven data switching:**
15. Live with open position → break-even line at position entry
16. Replay with open replay position → break-even line at replay entry price
17. Replay without position → no break-even line
18. Stop replay → live break-even returns

**PnlHandle data switching:**
19. Live with open position → PnL handle shown, interactive
20. Replay with open replay position → PnL handle shown, non-interactive (no close/refresh)
21. Replay without position → no PnL handle
22. Stop replay → live PnL handle returns with interactivity

**Bases (no changes, verify still works):**
23. Live → bases filtered by visible range
24. Replay → bases filtered by replay time (appear as user time-travels)

---

## Round 2: Fixes (2026-04-07)

### Bug 1: PnlHandle shows close button during replay
**Root cause:** `createPnlHandle` determined cancel visibility internally without
knowing about replay mode.
**Fix:** Pass `{replayMode}` option to `createPnlHandle`. Cancel visibility forced
false when `replayMode`.
**Files:** `pnl-handle.js`, `positions-controller.js`

### Bug 2: Timeline labels use 12hr format
**Root cause:** `toLocaleString()` uses browser default which may be 12hr.
**Fix:** Added `_formatTimelineLabel()` helper with explicit 24hr format
(`hour12: false`).
**Files:** `chart-controller.js`

### Bug 3: Replay controls overlap chart x-axis
**Root cause:** Chart canvas didn't resize when controls panel appeared. The resize
effect only triggered on `containerWidth`/`containerHeight` from WidgetContext, not
on internal layout changes.
**Fix:** Added `replayMode` to the resize effect dependencies so the chart resizes
when controls appear/disappear.
**Files:** `super-chart.js`

### Verification
25. PnlHandle during replay has no close button
26. Timeline labels show 24hr format (e.g. "07 Apr 2026, 14:30")
27. Replay controls don't overlap chart — x-axis and timestamps visible
28. Chart resizes when entering/exiting replay

---

## Round 3: Timeline visibility + PnL calculation + stale chartId (2026-04-08)

### Bug 4: Current time line not shown after stepping (only after play)
**Root cause:** `createReplayTimelines` excluded "ready" status from showing the
current time line. After stepping, status is "paused" or "ready" — both were blocked.
**Fix:** Matched TV logic: show current time line when not idle/loading/finished,
not same as start time. Hidden when finished (if start/end lines shown).
**Files:** `chart-controller.js`

### Bug 5: Missing timeline settings checks
**Root cause:** SC implementation didn't check `replayShowStartEnd`,
`replayShowCurrentTime`, `replayShowLineLabels` chart settings. TV checks all three.
**Fix:** Pass settings from `ReplayTimelines` component to controller method.
Controller respects `replayShowStartEnd` (hides start/end during loading),
`replayShowCurrentTime`, `replayShowLineLabels` (hides labels when off).
**Files:** `replay-timelines.js`, `chart-controller.js`

### Bug 6: PnL handle uses wrong profit calculation during replay
**Root cause:** SC PnlHandle used the live profit formula
(`unrealizedProfit * investmentToUsd * selectedCurrency.rate`) during replay. TV's
replay-position.js uses `unrealizedQuoteProfit` directly in quote currency.
**Fix:** `createPnlHandle` switches formula based on `replayMode`: uses
`unrealizedQuoteProfit` with `quoteCurrency` label in replay, USD-converted in live.
Color based on position side in replay (not profit sign).
**Files:** `positions-controller.js`

### Bug 7: Stale `_chartId` after tab/symbol switch
**Root cause:** `ScReplayController._chartId` was set once in constructor and captured
in `onSaveState` closure. When `marketTabId` changed (tab switch), the controller
dispatched to the old key, but components read from the new key.
**Fix:** Changed `_chartId` from a stored field to a getter reading
`this._chartController._marketTabId`. Removed the field declaration.
**Files:** `sc-replay-controller.js`

### Verification

**Round 1 (re-verify):**
1. ✅ Start replay → hidden overlays disappear
2. ✅ Stop replay → all overlays reappear
3. ✅ Trades, Bases, BreakEven, PnlHandle remain visible during replay
4. ✅ No console errors on replay start/stop
5. ✅ Start replay → green "Start At" line
6. ✅ Step/play → orange "Now At" line moves
7. ✅ At ready state (before first step) → no "Now At" line
8. ✅ At finished state → "Now At" disappears, "End At" shows
9. ✅ Stop replay → all timeline lines gone
10. ✅ Lines have 24hr timestamp labels
11. ✅ Live mode → regular trades shown
12. ✅ Replay mode → only replay trades shown
13. ✅ Execute buy during replay → trade marker appears
14. ✅ Stop replay → regular trades return
15. ✅ Live with open position → break-even line
16. ✅ Replay with open position → break-even at replay entry price
17. ✅ Replay without position → no break-even
18. ✅ Stop replay → live break-even returns
19. ✅ Live with open position → PnL handle interactive
20. ✅ Replay with open position → PnL handle non-interactive, no close button
21. ✅ Replay without position → no PnL handle
22. ✅ Stop replay → live PnL handle returns
23. ✅ Live → bases filtered by visible range
24. ✅ Replay → bases filtered by replay time

**Round 2 (re-verify):**
25. ✅ PnlHandle no close button during replay
26. ✅ Timeline labels 24hr format
27. ✅ Controls don't overlap chart
28. ✅ Chart resizes on enter/exit replay

**Round 3 (new):**
29. ✅ Step forward multiple times → "Now At" line visible and moves
30. ✅ "Now At" hidden when time equals start time
31. ✅ Timeline settings (show start/end, show current, show labels) respected
32. ✅ PnL handle shows quote currency profit during replay
33. ✅ PnL handle color based on position side during replay

**TT context tests:**
34. ✅ Start replay → switch TradingTab → replay controls/overlays follow correctly
35. ✅ Start replay → switch coinraySymbol → session aborts cleanly, overlays reset
36. ✅ Start replay → switch resolution → partial candle handling
37. ✅ Switch TradingTab → start replay on new tab → works correctly
38. ✅ Switch coinraySymbol → start replay → works correctly
