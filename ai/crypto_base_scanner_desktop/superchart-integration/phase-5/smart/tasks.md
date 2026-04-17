# SC Smart Replay — Tasks

## Group 1: Controller + Redux Foundation

### Task 1.1: ScSmartReplayController

**File:** `src/models/replay/sc-smart-replay-controller.js` (NEW)

Create `ScSmartReplayController extends ReduxController`:

- Constructor: receives `replayController`, same pattern as `ScReplayTradingController`
- Redux access: `get _chartId()`, `get state()`, `_setSession(patch)` — same as trading
- In-memory: `_backtest` (active ReplayBacktest instance), `_replayController` ref
- **Backtest CRUD methods:**
  - `fetchBacktests()` — GET `/backtests` with filters from `selectBacktestsFilters`
  - `fetchBacktest(backtestId)` — GET single backtest
  - `createBacktest(config)` — POST `/backtests`
  - `editBacktest(backtestId, patch)` — PATCH `/backtests/{id}`
  - `deleteBacktest(backtestId)` — DELETE `/backtests/{id}`
- **Session methods:**
  - `loadBacktest({backtestId, backtest})` — set up replay with backtest, compute
    jumpTime from `lastCandleSeenAt`, call `_replayController._startSession(startTime, REPLAY_MODE.SMART)`, dispatch trading info
  - `handleNewBacktest()` — if in smart mode: stop first, then open edit modal;
    if not: open edit modal directly
  - `setBacktestFinished()` — PATCH status=finished, cancel alerts, stop replay
  - `refreshBacktest()` — re-fetch + update active backtest
  - `goToReplayBacktest(backtestId, isEdit)` — dispatch `setReplayBacktestsWidget`
    to show detail view
  - `exitSmartMode()` — clear smart state, switch replayMode to DEFAULT
- **Position management:**
  - `submitBacktestPosition(tradeForm)` — POST/PATCH position with candle + resolution
  - `cancelBacktestPosition(positionId)` — PATCH cancel
  - `increaseBacktestPosition(positionId, params)` — PATCH increase
  - `reduceBacktestPosition(positionId, params)` — PATCH reduce
  - `triggerBacktest(backtestId)` — POST trigger
  - `cancelBacktestOrder(openOrder)` — confirm dialog + cancel
- **Alert management:**
  - `submitBacktestAlert(alert)` — add/update in session state
  - `cancelBacktestAlert(alertId, opts)` — remove from session state
  - `checkAlerts()` — check price/time/trendline alerts against current candle
  - `notifyAlert(alert)` — toast notification
- **Step update:**
  - `updateCurrentState(candle)` — check alerts, check triggers (up/down/time),
    if hit: pause, set updatingPosition, call triggerBacktest, refresh trading info,
    auto-resume if enabled
- **Trading info:**
  - `loadBacktestTradingInfo({backtest})` — build `EMPTY_MARKET_TRADING_INFO` +
    backtest data, dispatch `storeMarketTradingInfo()`
- **List management:**
  - `setBacktestsStatus(status)` — dispatch filter, reload
  - `setBacktestsQuery(query)` — dispatch filter, reload
  - `refreshBacktests()` — re-fetch current page
  - `reloadBacktests()` — clear + reload
- **Reset-to:**
  - `checkResetToPossible(time)` — validate no partial positions in range
  - `resetTo(time)` — PATCH `/backtests/{id}/reset`, restart replay
- **Cleanup:**
  - `destroy()` — clear references

Port logic from TV's `ReplaySmartTradingController`. Replace:
- `this.setState(...)` → `this._setSession(...)`
- `this.state.xxx` → `this.state.xxx` (same, but reads from Redux via selector)
- `this.replayController` → `this._replayController`
- `this.dispatch(setReplayContextGlobal(...))` → remove (not needed)

**Verify:** Controller can be instantiated in ScReplayController constructor.

### Task 1.2: Wire ScSmartReplayController into ScReplayController

**File:** `src/models/replay/sc-replay-controller.js` (EDIT)

- Import `ScSmartReplayController`
- Constructor: `this.smart = new ScSmartReplayController(this)`
- Change `replayMode` getter: `return this.state.replayMode` (instead of deriving
  from startTime)
- Change `_startSession`: accept `mode` parameter, store `replayMode` in session
- Change `onReplayStep` callback: delegate to `this.smart.updateCurrentState(candle)`
  when `replayMode === REPLAY_MODE.SMART`, else `this.trading.updateCurrentState()`
- Add `handleSwitchReplayMode()`: smart→default or default→smart flow
- Change `willLoseDataIfStopped`: in smart mode, always false (backtests are resumable)
- Change `_stop()`: in smart mode, clear smart state + refresh trading info
- Change `destroy()`: call `this.smart = null`

**Verify:** Mode delegation works — step updates go to correct sub-controller.

### Task 1.3: Selectors + Constants

**File:** `src/models/replay/selectors.js` (EDIT)

- Update `selectReplayMode`: read `session.replayMode` instead of deriving from
  `startTime`
- Add `selectSmartReplayState(chartId)`: returns `{backtestId, alerts, triggeredAlerts, updatingPosition}`
- Add `selectIsSmartReplay(chartId)`: returns `session.replayMode === REPLAY_MODE.SMART`

**File:** `src/models/replay/constants.js` (EDIT)

- No changes needed — `REPLAY_MODE.SMART`, `REPLAY_SMART_TRADING_STATE_SHAPE` already
  exist

**Verify:** Selectors return correct values from session state.

## Group 2: Backtest Model

### Task 2.1: Make ReplayBacktest Controller-Agnostic

**File:** `tradingview/controllers/replay/backtest.js` (EDIT — stays in place)

The model stays in its TV location. Both TV and SC import from the same path.

Changes:
- Add `_smartController` and `_replayController` instance fields (default `null`)
- Update `replaySmartTradingController` getter to check injected ref first:
  ```js
  get replaySmartTradingController() {
    if (this._smartController) return this._smartController
    const {replaySmartTradingController} = Selectors.selectReplayContextGlobal(this.getState())
    return replaySmartTradingController
  }
  ```
- TV path continues to work via `selectReplayContextGlobal` (no change)
- SC path injects refs via `_parseBacktest` on `ScSmartReplayController`

### Task 2.2: Update ScSmartReplayController._parseBacktest

**File:** `src/models/replay/sc-smart-replay-controller.js` (EDIT)

Update `_parseBacktest` to inject SC controller refs into the backtest instance:
```js
_parseBacktest = (state) => {
  const backtest = this.dispatch(ReplayBacktest.newController({state}))
  backtest._smartController = this
  backtest._replayController = this._replayController
  return backtest
}
```

**Verify:** ReplayBacktest created via SC controller uses SC refs. ReplayBacktest
created via TV controller still uses `selectReplayContextGlobal`. Validation works.

## Group 3: Widget Rewiring

### Task 3.1: useActiveSmartReplay Hook

**File:** `src/containers/trade/trading-terminal/widgets/replay-backtests/use-active-smart-replay.js` (NEW)

Dual-source hook that resolves controllers from both TV (Redux global) and SC
(ChartRegistry):

```js
export function useActiveSmartReplay() {
  const activeTabId = useSelector(MarketTabsSelectors.selectActiveTradingTabId)
  const session = useSelector(selectReplaySession(activeTabId))
  const tvContext = useSelector(Selectors.selectReplayContextGlobal)

  const chartController = ChartRegistry.get(activeTabId)
  const scReplayController = chartController?.replay || null
  const scSmartController = chartController?.replay?.smart || null

  const tvReplayController = tvContext?.replayController || null
  const tvSmartController = tvContext?.replaySmartTradingController || null

  const isScActive = !!session?.replayMode
  const isTvActive = !!tvContext?.backtest

  return {
    scReplayController, scSmartController,
    tvReplayController, tvSmartController,
    replayController: isScActive ? scReplayController : tvReplayController,
    smartController: isScActive ? scSmartController : tvSmartController,
    hasSc: !!scReplayController,
    hasTv: !!tvReplayController,
    backtestId: session?.backtestId,
    updatingPosition: isScActive ? (session?.updatingPosition || false) : (tvContext?.updatingPosition || false),
    time: isScActive ? session?.time : tvContext?.time,
  }
}
```

**Verify:** Hook returns SC controllers when SC chart is active, TV controllers when
TV chart is active. Both `hasSc` and `hasTv` reflect availability.

### Task 3.2: Rewire Widget Components

Replace `useSelector(Selectors.selectReplayContextGlobal)` with `useActiveSmartReplay()`
in all backtest widget files. Use `smartController` / `replayController` from the hook
(these resolve to the active chart type's controllers).

**Files to update (13 files):**

1. `backtests-overview.js` — `smartController` (was `replaySmartTradingController`)
2. `backtest-overview.js` — `smartController`
3. `backtest-edit-modal.js` — `replayController` + chart type selector (Task 3.4)
4. `backtest-overview-header.js` — `replayController, smartController, updatingPosition` + active backtest detection via `backtestId`
5. `backtests-header.js` — `smartController`
6. `backtests-pagination.js` — `smartController`
7. `backtests-settings.js` — `replayController`
8. `backtests-list.js` — active backtest detection: `backtest.id === backtestId`
9. `backtests-table.js` — same
10. `backtest-row.js` — active backtest detection
11. `backtest-stats.js` — `time` from hook, `currentTimezone` from `Selectors.selectTimezone`
12. `backtest-position-row.js` — `time` from hook
13. `backtest-positions-list.js` — `time` from hook
14. `backtest-positions-table.js` — active backtest detection

For each file:
- Replace `useSelector(Selectors.selectReplayContextGlobal)` with `useActiveSmartReplay()`
- Map old destructured names to hook values:
  - `replaySmartTradingController` → `smartController`
  - `replayController` → `replayController`
  - `backtest: currentBacktest` → detect via `backtestId`
  - `updatingPosition` → `updatingPosition`
  - `time` → `time`
  - `currentTimezone` → use `Selectors.selectTimezone` directly

**Verify:** Each component renders without errors. List loads, detail view shows.
Both TV and SC backtests appear in the list and can be interacted with.

### Task 3.3: Backtest Action Methods

Backtest instances created by SC's `_parseBacktest` have injected controller refs
(Task 2.2). Backtest instances created by TV's `parseReplayBacktest` continue using
`selectReplayContextGlobal`.

Widget components call action methods on the backtest object as before
(`backtest.handleResumeClick()`, etc.). The backtest model resolves to the correct
controller via the injected ref or Redux fallback.

**Verify:** Backtest action buttons work for both TV-created and SC-created backtests.

### Task 3.4: Chart Type Selector

Backtest sessions are chart-agnostic on the backend. A session created on TV can be
resumed on SC and vice versa. When both chart types are available and the action is
widget-initiated (not from chart mode switch), show a chart type selector.

**File:** `backtest-edit-modal.js` (EDIT)

- Get `hasSc`, `hasTv`, `scSmartController`, `tvSmartController` from hook
- When both available AND not chart-initiated: add a simple select "TradingView" /
  "SuperChart" (default to whichever is currently active, or SC)
- On submit, use selected controller pair for `createBacktest` + `loadBacktest`
- Pass `initiatedFromChart` flag through edit modal open action to distinguish
  widget-initiated vs chart-initiated

**File:** `tradingview/controllers/replay/backtest.js` (EDIT)

Update `handleResumeClick` and `handleViewOnChart`:
- These methods show confirmation dialogs. When both chart types are available, add
  the chart type select to the dialog content
- The selected type determines which controller pair loads the session:
  - SC: `scSmartController.loadBacktest({backtest})`
  - TV: `tvSmartController.loadBacktest({backtest})`
- The backtest model needs access to `hasSc`/`hasTv` — pass via the hook result
  stored on the controller, or check availability in the method itself via
  `ChartRegistry.getActive()` and `Selectors.selectReplayContextGlobal`

**Verify:**
- Edit modal shows chart type selector when both TV+SC available, widget-initiated
- Resume dialog shows chart type selector when both available
- View on Chart shows chart type selector when both available
- All selectors hidden when chart-initiated or only one type available
- A backtest created on TV can be resumed on SC and vice versa

## Group 4: Context + Mode Switching

### Task 4.1: Update ScReplayContextProvider

**File:** `src/containers/.../super-chart/replay/sc-replay-context.js` (EDIT)

- Populate `smartTrading` field from session state:
  ```js
  smartTrading: {
    replaySmartTradingController: replay?.smart || null,
    backtest: undefined,  // read from widget state if needed
    currentPosition: session?.smartCurrentPosition,
    updatingPosition: session?.updatingPosition || false,
    trades: session?.smartTrades || [],
    alerts: session?.alerts || [],
    triggeredAlerts: session?.triggeredAlerts || [],
  }
  ```
- `replayMode`: read from `session?.replayMode || false`

**Verify:** Smart trading data available via ReplayContext in SC components.

### Task 4.2: Mode Switching Wiring

**File:** `src/containers/.../widgets/replay/toggle-replay-mode-button.js` (EDIT)

Currently reads `replayController` from `Selectors.selectReplayContextGlobal`.
Update to:
- Use `useContext(ReplayContext)` if inside SC tree
- Or `useActiveSmartReplay()` if outside SC tree

The button calls `replayController.handleSwitchReplayMode()` — this method is
added in Task 1.2.

Check `isSmartReplay`: derive from `replayMode === REPLAY_MODE.SMART` instead of
reading from `replaySettings.isSmartReplay`.

**Verify:** Toggle button switches between modes. Smart mode opens edit modal.
Default mode restarts as default replay.

### Task 4.3: Replay Controls — Smart Mode UI

**File:** `src/containers/.../widgets/replay/replay-controls.js` (EDIT)

- Show "Exit Backtesting" text when in smart mode (vs "Exit Replay" in default)
- Add auto-resume toggle when in smart mode
- Show backtest name/info in controls when active

**Verify:** Controls show correct text and options per mode.

## Group 5: Hotkeys

### Task 5.1: Smart Replay Hotkeys

**File:** `src/containers/.../super-chart/replay/sc-replay-hotkeys.js` (EDIT)

- In smart mode, buy/sell hotkeys should go through smart controller's position
  flow instead of simple trading
- Or: disable buy/sell hotkeys in smart mode (trades are done via order form)

**Verify:** Hotkeys behave correctly per mode.

## Verification Checklist

- [ ] Create new backtest → session starts at correct time
- [ ] Resume existing backtest → jumps to lastCandleSeenAt
- [ ] Position create/increase/reduce/cancel via API
- [ ] Trigger fires → replay pauses → trigger executes → auto-resumes
- [ ] Alerts fire notifications on step
- [ ] Backtest widget list: shows running/finished tabs, search, pagination
- [ ] Backtest widget detail: stats, positions, action buttons
- [ ] Edit modal: validation, submit, market picker
- [ ] Mode switch: default→smart opens creation, smart→default confirms
- [ ] Trading Terminal widgets (order form, positions) show backtest data
- [ ] Tab switch: smart replay controller survives
- [ ] Market change: smart replay stops (engine auto-exit)
- [ ] Reset-to: jumps backward, positions rolled back
- [ ] Finish: backtest marked finished, appears in finished tab
- [ ] Delete: confirmation, removes from list, stops if active
- [ ] **Coexistence:** TV backtesting still works exactly as before
- [ ] **Coexistence:** Edit modal shows chart type selector when both TV+SC available
- [ ] **Coexistence:** Resume dialog shows chart type selector when both available
- [ ] **Coexistence:** View on Chart shows chart type selector when both available
- [ ] **Coexistence:** All selectors hidden when initiated from chart mode switch
- [ ] **Coexistence:** Backtest created on TV can be resumed on SC
- [ ] **Coexistence:** Backtest created on SC can be resumed on TV
