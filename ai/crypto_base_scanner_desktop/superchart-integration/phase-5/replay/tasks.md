# Phase 5: Default Replay — Tasks

## Task 1: Shared constants + move UI components

### 1a: Create shared constants

**New file:** `src/models/replay/constants.js`

Extract and consolidate:
- `REPLAY_MODE` from `tradingview/controllers/replay/replay-controller.js`
- `REPLAY_STATUS` from same
- `intervalToFrequencyString` from same (as standalone function)
- State shapes from `tradingview/context/replay-context.js`: `REPLAY_TRADING_STATE_SHAPE`, `REPLAY_SMART_TRADING_SHAPE`, `REPLAY_STATE_SHAPE`, `REPLAY_CONTEXT_SHAPE`
- `ReplayContext = React.createContext(REPLAY_CONTEXT_SHAPE)`
- New: `SC_SPEED_OPTIONS = [1, 2, 5, 10, 20, 100, 200, 400]`
- New: `SC_REPLAY_STATE_SHAPE` (same as REPLAY_STATE_SHAPE + `speed: 20`)

**Edit:** `tradingview/controllers/replay/replay-controller.js`
- Remove local `REPLAY_MODE`, `REPLAY_STATUS` definitions
- Re-export from `~/models/replay/constants`
- Keep `intervalToFrequencyString` as static method but delegate to shared function

**Edit:** `tradingview/context/replay-context.js`
- Remove local shape definitions
- Re-export from `~/models/replay/constants`

**Edit:** `tradingview/context/use-replay.js`
- Import `ReplayContext` from `~/models/replay/constants` instead of defining locally

### 1b: Move shared UI components to `widgets/replay/`

Move chart-agnostic replay UI components from `tradingview/replay/` to a shared
location at `widgets/replay/` (sibling to `center-view/` and `super-chart/`):

**Move:** `tradingview/replay/replay-controls.js` → `widgets/replay/replay-controls.js`
**Move:** `tradingview/replay/pick-replay-start-button.js` → `widgets/replay/pick-replay-start-button.js`
**Move:** `tradingview/replay/toggle-replay-mode-button.js` → `widgets/replay/toggle-replay-mode-button.js`

**Update TV imports after move:**
- `tradingview/tradingview-component.js` — update `ReplayControls` import
- `tradingview/action-buttons.js` — update `PickReplayStartButton` import
- `tradingview/replay/replay-controls.js` (now at `widgets/replay/`) — update relative
  imports (ChartContext, ReplayContext, etc.) to use absolute paths or adjusted relative paths

Note: The components keep their existing behavior at this point. The chart-agnostic
adaptations (MarketTabContext, shared constants imports, speed handling) happen in
Task 7 after the move.

### Verification:
- TV replay still works — controls render, play/pause works, speed dropdown works
- No import errors in TV replay code

---

## Task 2: Redux replay reducer + selectors

**New file:** `src/models/replay/selectors.js`

Create keyed selectors:
- `selectReplaySession(chartId)` — full session state
- `selectReplayStatus(chartId)` — status string
- `selectReplayMode(chartId)` — REPLAY_MODE.DEFAULT or false
- `selectReplayIsLoading(chartId)`, `selectReplayIsPlaying(chartId)`
- `selectReplayTrading(chartId)` — { amount, trades, currentPosition, pnl }
- `selectIsAnyReplayActive` — any session has startTime

**Edit:** existing replay reducer (or create new)

Add `sessions` key to `state.replay`:
- `setReplaySession(chartId, patch)` — shallow merge into `sessions[chartId]`
- `clearReplaySession(chartId)` — delete `sessions[chartId]`
- Keep existing `replayContextGlobal` for TV backward compat during coexistence

**Verification:**
- Redux devtools: `state.replay.sessions` exists
- Selectors return correct values

---

## Task 3: ScReplayController

**New file:** `src/models/replay/sc-replay-controller.js`

Create `ScReplayController` as a sub-controller of ChartController:

1. Constructor: accepts `chartController` (parent), stores ref
2. Creates `ScReplayTradingController` as `this.trading`
3. Polls for `_chartController._superchart.replay` (50ms interval)
4. `_wireCallbacks()` — subscribes to:
   - `onReplayStatusChange` → dispatch(setReplaySession(chartId, {status}))
   - `onReplayStep(candle, direction)` → dispatch(setReplaySession(chartId, {time, price}))
   - `onReplayError` → handleError
5. Handler methods (see design.md for full list):
   - `handleSelectReplayStartTimeClick(isMobile)`
   - `handleRandomReplayStartTime()` — wrapped with `conditionalCallback`
   - `_getRandomStartTime()` — async, uses getFirstCandleTime from datafeed
   - `_startSession(time)` — async
   - `handlePlayPause()`
   - `handleStep()`
   - `handleBackToStartClick(autoPlay)`
   - `handleStop(callback)`
   - `_stop()` — async
   - `setSpeed(speed)`
   - `setSelectingStartTime(v)`
6. Properties read from Redux via `this.getState()` + selectors
7. `replaySafeCallback(callback)` — shows confirmation modal if trades exist
8. `destroy()` — cleanup

**Verification:**
- Unit: controller can be instantiated with a mock ChartController
- Manual: will be tested after wiring (Task 7)

---

## Task 4: ScReplayTradingController

**New file:** `src/models/replay/sc-replay-trading-controller.js`

Port from `tradingview/controllers/replay/replay-trading-controller.js`:

1. Constructor: accepts `replayController` (parent ScReplayController)
2. Same methods: `setAmount`, `resetTo`, `reset`, `updateCurrentState`, `createTrade`, `addTrade`, `buy`, `sell`, `handleBuy`, `handleSell`
3. Writes state to Redux via `dispatch(setReplaySession(chartId, {amount, trades, currentPosition, pnl}))`
4. `getCurrentMarket` from parent: `this._replayController.currentMarket`
5. Trade validation reads status from Redux via selectors

**Key difference from TV version:**
- No `resolution` getter (not needed)
- `currentTime` and `currentPrice` read from Redux via selectors
- State written to Redux, not via Controller base class onSaveState
- Import Position and Trade from same location as TV version

**Verification:**
- Unit: can create trades, position calculation works
- Manual: will be tested after wiring (Task 7)

---

## Task 5: SC replay context provider

**New file:** `super-chart/replay/sc-replay-context.js`

Create minimal `ScReplayContextProvider` component:

1. Read `chartController` from `useSuperChart()`
2. Build context value (useMemo) with controller ref only:
   ```js
   {replayController: chartController?.replay || null}
   ```
3. Provide `ReplayContext.Provider value={contextValue}`

No state management here — controllers are created in ChartController (Task 7),
state lives in Redux (Task 2).

4. Outside-click handler for selectingStartTime:
   - Read `selectingStartTime` from Redux via selector
   - Document mousedown listener when true
   - Clear via `chartController.replay.setSelectingStartTime(false)`

**Verification:**
- Context renders without error
- `useContext(ReplayContext).replayController` returns the controller

---

## Task 6: CoinrayDatafeed getFirstCandleTime

**Edit:** `super-chart/coinray-datafeed.js`

Add method:
```js
getFirstCandleTime = (ticker, resolution, callback) => {
  // Fetch earliest candles and return the first candle's timestamp
  // callback(timestampMs) or callback(null) on error
}
```

Implementation:
- Call `getCoinrayCache().fetchCandles({coinraySymbol: ticker, resolution, start: 0, end: now})`
- Return `new Date(candles[0].time).getTime()` if candles exist
- Catch errors → `callback(null)`

**Verification:**
- Call `getFirstCandleTime("BINA_USDT_BTC", "60", console.log)` in console
- Should return a timestamp for the earliest available candle

---

## Task 7: Wire into SC widget tree

**Edit:** `super-chart/chart-controller.js`

1. Import `ScReplayController` from `~/models/replay/sc-replay-controller`
2. In constructor, create sub-controller:
   ```js
   this.replay = new ScReplayController(this)
   ```
3. In `dispose()`, destroy it:
   ```js
   this.replay?.destroy()
   ```

**Edit:** `super-chart/super-chart.js`

1. Import `ScReplayContextProvider` from `./replay/sc-replay-context`
2. Import `ReplayControls` from `widgets/replay/replay-controls` (shared location from Task 1b)
3. Import `ScReplayHotkeys` from `./replay/sc-replay-hotkeys`
4. Import `selectReplayMode` from `~/models/replay/selectors`

5. Wrap widget tree in `ScReplayContextProvider`:
   ```jsx
   <SuperChartContextProvider>
     <ScReplayContextProvider>
       {/* existing content */}
     </ScReplayContextProvider>
   </SuperChartContextProvider>
   ```

6. Modify `SuperChartControls`:
   - Read `replayMode` from Redux via `useSelector(selectReplayMode(chartId))`
   - Remove hardcoded `const replayMode = false`
   - Add `showReplayControls = !!replayMode`
   - Render `<ReplayControls/>` when active

7. Add `<ScReplayHotkeys/>` to widget tree

**Verification:**
- SC chart loads without errors
- No visible changes when replay is inactive
- Console: `ChartRegistry.get("main").replay` — should be the ScReplayController

---

## Task 8: Make shared replay components chart-agnostic

**Edit:** `widgets/replay/replay-controls.js` (already moved in Task 1b)

1. Change imports:
   ```js
   import {REPLAY_MODE, REPLAY_STATUS, ReplayContext, SC_SPEED_OPTIONS, intervalToFrequencyString} from "~/models/replay/constants"
   import {selectReplayStatus, selectReplayMode, selectReplayIsLoading, selectReplayIsPlaying, selectReplayTrading, selectReplaySession} from "~/models/replay/selectors"
   ```
   Remove imports from TV-specific paths.

2. Controller from ReplayContext (thin, controller-only):
   ```js
   const {replayController} = useContext(ReplayContext)
   ```

3. State from Redux via selectors:
   ```js
   const {id: chartId, currentMarket} = useContext(MarketTabContext)
   const status = useSelector(selectReplayStatus(chartId))
   const replayMode = useSelector(selectReplayMode(chartId))
   const isLoading = useSelector(selectReplayIsLoading(chartId))
   const isPlaying = useSelector(selectReplayIsPlaying(chartId))
   const {amount, currentPosition} = useSelector(selectReplayTrading(chartId))
   ```
   Remove `ChartContext` import entirely.

4. Speed handling:
   - Read `speed` from Redux session state
   - If `speed` exists → use SC_SPEED_OPTIONS, display as `${opt}x`, call `setSpeed(opt)`
   - If `speed` undefined → use TV_INTERVAL_OPTIONS, existing display, call `setIntervalMs(opt)`

**Edit:** `widgets/replay/pick-replay-start-button.js` (already moved in Task 1b)

- Controller from `useContext(ReplayContext)`, state from Redux selectors
- Replace any `ChartContext` reads with `MarketTabContext`

**Edit:** `widgets/replay/toggle-replay-mode-button.js` (already moved in Task 1b)

- Same pattern: controller from context, state from Redux

**Verification:**
- TV replay controls still work (speed dropdown, play/pause, etc.)
- SC replay controls render (after Task 7 wiring)

---

## Task 9: Wire header button

**Edit:** `super-chart/header-buttons.js`

1. Import selectors from `~/models/replay/selectors`
2. Import `ScreenContext, SCREENS` from screen context

3. Read state from Redux, controller from chartController:
   ```js
   const {id: chartId} = useContext(MarketTabContext)
   const replayMode = useSelector(selectReplayMode(chartId))
   const selectingStartTime = useSelector(state => selectReplaySession(chartId)(state)?.selectingStartTime)
   const screen = useContext(ScreenContext)
   ```

4. Wire onReplay callback:
   ```js
   onReplay: () => chartController?.replay?.handleSelectReplayStartTimeClick(screen === SCREENS.MOBILE),
   ```

5. Add replay highlight effect:
   ```js
   useEffect(() => {
     if (!readyToDraw || !chartController) return
     chartController.header.setReplayButtonHighlight(!!selectingStartTime)
   }, [readyToDraw, selectingStartTime])
   ```

6. Add enable/disable effect:
   ```js
   useEffect(() => {
     if (!readyToDraw || !chartController) return
     chartController.header.setHeaderButtonsEnabled(!replayMode)
   }, [readyToDraw, replayMode])
   ```

**Verification:**
- Click Replay button on mobile → random start → replay begins
- Click Replay button on desktop → button highlights
- Click outside chart on desktop → highlight clears
- Buy/Sell/Alert buttons disabled during replay

---

## Task 10: Create SC replay hotkeys

**New file:** `super-chart/replay/sc-replay-hotkeys.js`

Create `ScReplayHotkeys` component:
- Read `replayMode` from Redux via `useSelector(selectReplayMode(chartId))`
- Get controller via `useSuperChart().chartController.replay`
- Only renders when `replayMode` is truthy
- Reads hotkey map from Redux `state.hotkeys`
- Binds via `bindHotkey` (mousetrap global) — no TV chart binding
- Commands: playPause, step, backToStart, stop, buy, sell
- Uses `util.useImmutableCallback` for stable handler refs
- Unbinds via `unbindHotkey` on cleanup

**Verification:**
- Start replay → shift+right steps → shift+down plays/pauses
- shift+q stops replay
- shift+b / shift+s executes buy/sell
- Hotkeys inactive when not in replay

---

## Task 11: Verify ActionButtons + trade form reset

PickReplayStartButton was already moved and adapted in Tasks 1b and 8.
ActionButtons imports were updated in Task 1b.

**Verify:** `tradingview/action-buttons.js`
- PickReplayStartButton import points to `widgets/replay/pick-replay-start-button`
- Works correctly in both TV and SC widget trees

**Add trade form reset** in ScReplayContextProvider or a dedicated effect:
```js
const startTime = useSelector(state => selectReplaySession(chartId)(state)?.startTime)
useEffect(() => {
  if (startTime) dispatch(resetTradeForm())
}, [startTime])
```

**Verification:**
- Mobile: PickReplayStartButton visible in ActionButtons
- Click "Pick Start" on mobile → random replay start
- Trade form resets when replay starts

---

## Implementation Order

1. **Task 1** (shared constants + move UI) — foundation, must be first
2. **Task 2** (Redux reducer + selectors) — foundation
3. **Task 6** (getFirstCandleTime) — independent, can parallel with 3-4
4. **Task 3** (ScReplayController) — depends on Tasks 1, 2
5. **Task 4** (ScReplayTradingController) — depends on Tasks 1, 2
6. **Task 5** (SC replay context provider) — depends on Task 1
7. **Task 7** (widget wiring + ChartController) — depends on Tasks 3, 4, 5
8. **Task 8** (ReplayControls adaptation) — depends on Tasks 1, 2
9. **Task 9** (header button) — depends on Task 7
10. **Task 10** (hotkeys) — depends on Task 7
11. **Task 11** (ActionButtons + trade form reset) — depends on Tasks 7, 8

After all tasks: test full flow on mobile screen size.
