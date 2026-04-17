# Phase 5: Replay Overlays — Tasks

## Task 1: Conditional rendering in super-chart.js

**Edit:** `super-chart/super-chart.js`

1. Extract overlay section from `SuperChartWidgetWithProvider` into a new
   `SuperChartOverlays` component (inside the provider tree, can use hooks)
2. Read `replayMode` via `useSelector(selectReplayMode(chartId))`
3. Wrap hidden overlays in `{!replayMode && <> ... </>}`
4. Mount `<ReplayTimelines/>` in `{replayMode && <> ... </>}`
5. Keep always-mounted overlays outside the conditionals

**Verification:**
- Start replay → hidden overlays disappear (alerts, orders, bid/ask, etc.)
- Stop replay → overlays reappear
- Always-mounted overlays (Trades, Bases, BreakEven, PnlHandle) stay visible

---

## Task 2: Trades data source switching

**Edit:** `super-chart/overlays/trades.js`

1. Import `selectReplayMode`, `selectReplayTrading` from `~/models/replay/selectors`
2. Read `replayMode` and `replayTrading` from Redux
3. Switch `allTrades` data source:
   - `replayMode` → `replayTrading.trades`
   - Otherwise → existing live trades logic
4. Adjust time filtering: skip visible range filter when `replayMode`
   (replay trades are already bounded by replay time)

**Verification:**
- Live: trades render as before
- Replay: only replay trades (buy/sell during session) shown
- Execute buy/sell during replay → trade marker appears

---

## Task 3: BreakEven data source switching

**Edit:** `super-chart/overlays/break-even.js`

1. Import `selectReplayMode`, `selectReplayTrading` from `~/models/replay/selectors`
2. Read `replayMode` and `replayTrading` from Redux
3. Switch position source:
   - `replayMode` → `replayTrading.currentPosition`
   - Otherwise → `CurrentPositionContext.currentPosition`
4. Pass switched position to `chartController.positions.createBreakEven()`

**Verification:**
- Live: break-even renders as before
- Replay: break-even shows at replay position entry price
- No replay position → no break-even line

---

## Task 4: PnlHandle data source switching

**Edit:** `super-chart/overlays/pnl-handle.js`

1. Import `selectReplayMode`, `selectReplayTrading` from `~/models/replay/selectors`
2. Read `replayMode` and `replayTrading` from Redux
3. Switch position source (same as BreakEven)
4. Disable interactivity during replay:
   - Pass no close callback (or null) when `replayMode`
   - Skip position refresh when `replayMode`

**Verification:**
- Live: PnL handle renders and is interactive
- Replay: PnL handle shows replay position, no close button
- No replay position → no PnL handle

---

## Task 5: ReplayTimelines component + controller method

**New file:** `super-chart/overlays/replay-timelines.js`

Create `ReplayTimelines` component:
- Read `startTime`, `endTime`, `time`, `status` from Redux via `selectReplaySession`
- Use `useDrawOverlayEffect(OverlayGroups.replayTimelines, ...)`
- Call `chartController.createReplayTimelines({startTime, endTime, currentTime, status})`

**Edit:** `super-chart/overlay-helpers.js`
- Add `replayTimelines: "replayTimelines"` to `OverlayGroups`

**Edit:** `super-chart/chart-controller.js`
- Add `createReplayTimelines({startTime, endTime, currentTime, status})` method
- Creates up to 3 `timeLine` overlays using `this._createOverlay()`
- Uses `this.colors.replayStartTime`, `replayEndTime`, `replayCurrentTime`
- Labels: "Start At", "End At", "Now At" with formatted timestamps
- Current time line hidden at start/finish (only shown during playback)

**Edit:** `super-chart/hooks/use-chart-colors.js` (or equivalent color mapping)
- Add `replayStartTime`, `replayEndTime`, `replayCurrentTime` to chart colors
- Values from `src/themes/index.js` (already defined there)

**Verification:**
- Start replay → green "Start At" line appears
- Play → orange "Now At" line moves with each step
- Finish → "Now At" line disappears, red "End At" line shows
- Stop replay → all timeline overlays gone

---

## Implementation Order

1. **Task 5** first — ReplayTimelines needs overlay group + controller method + colors
2. **Task 1** — conditional rendering (mounts ReplayTimelines, hides others)
3. **Tasks 2-4** in parallel — data source switching (independent)

After all tasks: test full flow with replay start → play → buy/sell → stop.
