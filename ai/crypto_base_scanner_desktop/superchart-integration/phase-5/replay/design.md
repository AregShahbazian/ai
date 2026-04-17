# Phase 5: Default Replay — Design

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ SuperChartWidgetWithProvider                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ SuperChartContextProvider                             │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │ ScReplayContextProvider                         │  │  │
│  │  │  (provides shared ReplayContext)                │  │  │
│  │  │                                                 │  │  │
│  │  │  ┌──────────────┐  ┌──────────────────────┐    │  │  │
│  │  │  │ SuperChart   │  │ SuperChartControls   │    │  │  │
│  │  │  │ Widget       │  │  ├ ReplayControls    │    │  │  │
│  │  │  │              │  │  └ ActionButtons      │    │  │  │
│  │  │  └──────────────┘  └──────────────────────┘    │  │  │
│  │  │  ┌──────────────┐  ┌──────────────────────┐    │  │  │
│  │  │  │ HeaderButtons│  │ ScReplayHotkeys      │    │  │  │
│  │  │  └──────────────┘  └──────────────────────┘    │  │  │
│  │  │  ┌──────────────────────────────────────────┐  │  │  │
│  │  │  │ Overlays (existing)                      │  │  │  │
│  │  │  └──────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Data flow:**
```
sc.replay (ReplayEngine)
    ↑ setCurrentTime / play / pause / step
    │
ScReplayController  (sub-controller of ChartController)
    │ dispatch(setReplaySession(chartId, state))
    ↓
Redux: state.replay.sessions[chartId]
    │ useSelector / getState
    ↓
ReplayControls / HeaderButtons / ScReplayHotkeys / Thunks

Controller access:
  Shared UI       → useContext(ReplayContext).replayController
  SC components   → useSuperChart().chartController.replay
  Thunks/external → ChartRegistry.get(chartId).replay
```

## New Files

| File | Purpose |
|------|---------|
| `src/models/replay/constants.js` | Shared constants, context shapes, ReplayContext, speed helpers |
| `src/models/replay/sc-replay-controller.js` | ScReplayController wrapping sc.replay |
| `src/models/replay/sc-replay-trading-controller.js` | ScReplayTradingController for simulated trades |
| `super-chart/replay/sc-replay-context.js` | ScReplayContextProvider + useScReplay hook |
| `super-chart/replay/sc-replay-hotkeys.js` | Mousetrap hotkey bindings for SC replay |

(`super-chart/` = `src/containers/trade/trading-terminal/widgets/super-chart/`)
(`widgets/` = `src/containers/trade/trading-terminal/widgets/`)

## Moved Files (TV → shared)

Replay UI components that are chart-agnostic move to a shared location at the
`widgets/` level, sibling to both `center-view/` and `super-chart/`:

| From (TV path) | To (shared path) |
|-----------------|-------------------|
| `tradingview/replay/replay-controls.js` | `widgets/replay/replay-controls.js` |
| `tradingview/replay/pick-replay-start-button.js` | `widgets/replay/pick-replay-start-button.js` |
| `tradingview/replay/toggle-replay-mode-button.js` | `widgets/replay/toggle-replay-mode-button.js` |

TV files that imported these update their imports to the new shared path.
SC files import from the same shared path.

## Modified Files

| File | Change |
|------|--------|
| `super-chart/super-chart.js` | Add ScReplayContextProvider, modify SuperChartControls |
| `super-chart/header-buttons.js` | Wire onReplay callback, add replay highlight/enable effects |
| `super-chart/coinray-datafeed.js` | Add getFirstCandleTime method |
| `tradingview/controllers/replay/replay-controller.js` | Re-export constants from shared |
| `tradingview/context/replay-context.js` | Re-export shapes from shared |
| `tradingview/context/use-replay.js` | Import ReplayContext from shared |
| `tradingview/tradingview-component.js` | Update ReplayControls import to shared path |
| `tradingview/action-buttons.js` | Update PickReplayStartButton import to shared path |

---

## Controller Design

### ScReplayController

Sub-controller of ChartController. Created in ChartController's constructor alongside
`header`, `alerts`, `positions`, etc. Writes state to Redux via `dispatch`.

```js
// src/models/replay/sc-replay-controller.js
import {REPLAY_MODE, REPLAY_STATUS} from "./constants"

export class ScReplayController {
  _chartController = null  // parent ChartController
  _replayEngine = null     // sc.replay
  _pollInterval = null
  _startTime = null        // original start time (for restart)
  _speed = 20              // candles/sec
  _chartId = null          // for keyed Redux state

  // Event unsubscribers
  _unsubStatus = null
  _unsubStep = null
  _unsubError = null

  trading = null           // ScReplayTradingController

  constructor(chartController) {
    this._chartController = chartController
    this._chartId = chartController._marketTabId || "main"
    this.trading = new ScReplayTradingController(this)
    this._pollForEngine()
  }

  get dispatch() { return this._chartController.dispatch }
  get getState() { return this._chartController.getState }
  get currentMarket() { return this._chartController._currentMarket }
```

**Key methods:**

| Method | Implementation |
|--------|---------------|
| `setSuperchart(sc)` | Store ref, poll for `sc.replay` every 50ms |
| `_wireCallbacks()` | Subscribe to onReplayStatusChange, onReplayStep, onReplayError |
| `handleSelectReplayStartTimeClick(isMobile)` | Mobile → randomStart, Desktop → toggle selectingStartTime |
| `handleRandomReplayStartTime()` | Wrapped with conditionalCallback. Gets random time, calls `_startSession` |
| `_getRandomStartTime()` | Use getFirstCandleTime, pick random in [first, now*0.95], round to candle boundary |
| `_startSession(time)` | Set _startTime, setState, call `engine.setCurrentTime(time)` |
| `handlePlayPause()` | playing→pause, ready/paused→play(speed), finished→restart |
| `handleStep()` | Guard loading/finished, call `engine.step()` |
| `handleBackToStartClick(autoPlay)` | `engine.setCurrentTime(_startTime)`, reset trading, optionally play |
| `handleStop(callback)` | If trades exist → confirmStop, else → _stop + callback |
| `_stop()` | `engine.setCurrentTime(null)`, reset trading, clear state |
| `setSpeed(speed)` | Store speed, if playing call `engine.play(speed)` |
| `setSelectingStartTime(v)` | setState({selectingStartTime: v}) |
| `destroy()` | Clear interval, unsub all, null refs |

**Properties matching ReplayControls interface:**

| Property | Source |
|----------|--------|
| `replayMode` | `state.startTime ? REPLAY_MODE.DEFAULT : undefined` |
| `startTime` | `state.startTime` |
| `status` | `state.status` |
| `time` | `state.time` (from engine.getReplayCurrentTime) |
| `price` / `currentPrice` | `state.price` (from last stepped candle close) |
| `isLoading` | `status === 'loading'` |
| `isFinished` | `status === 'finished'` |
| `isPlaying` | `status === 'playing'` |
| `selectingStartTime` | `state.selectingStartTime` |
| `speed` | `_speed` |
| `willLoseDataIfStopped` | `replayMode && trades.length > 0` |

**Error handling:**
- `resolution_change_failed` → sync period UI to engine's actual period via ChartController
- Other errors → toast notification

**Confirmation dialog:**
Use `replaySafeCallback` pattern: open modal with confirm/cancel, on confirm execute
callback. Same modal component as TV uses (`ReplayModeDialog` or a simpler confirm modal).

### ScReplayTradingController

Port from existing `ReplayTradingController`. Same logic, different wiring.

```js
// src/models/replay/sc-replay-trading-controller.js

export class ScReplayTradingController {
  _replayController = null  // parent ScReplayController

  constructor(replayController) {
    this._replayController = replayController
  }

  get dispatch() { return this._replayController.dispatch }
  get getState() { return this._replayController.getState }
  get currentMarket() { return this._replayController.currentMarket }
```

**Differences from TV version:**

| Concern | TV ReplayTradingController | ScReplayTradingController |
|---------|---------------------------|---------------------------|
| `currentTime` | `this.replayController.time` | Same — reads from Redux via selector |
| `currentPrice` | `this.replayController.currentPrice` | Same — reads from Redux via selector |
| `resolution` | `this.replayController.datafeed.resolution` | Not needed |
| `getCurrentMarket` | Passed via constructor | From parent: `this._replayController.currentMarket` |
| State storage | Controller base class + onSaveState | Dispatches to Redux replay slice |

The logic (buy, sell, createTrade, resetTo, updateCurrentState) is identical.
Port the class — do not import from TV path.

---

## State Design

### Redux as source of truth

All replay state lives in a Redux reducer, keyed by chart ID:

```js
// src/reducers/replay.js (new reducer, or extend existing)
state.replay.sessions = {
  "main": {
    status: "idle",
    startTime: null,
    time: null,
    price: null,
    speed: 20,
    selectingStartTime: false,
    // trading:
    amount: null,
    trades: [],
    currentPosition: null,
    pnl: null,
  },
  // "tab-2": { ... }  // future multi-chart
}
```

**Actions:** `setReplaySession(chartId, patch)` — shallow-merges patch into
`state.replay.sessions[chartId]`. Single action for all state updates.
`clearReplaySession(chartId)` — removes session on stop.

**Selectors** (in `src/models/replay/selectors.js`):
```js
export const selectReplaySession = (chartId) => (state) =>
  state.replay.sessions?.[chartId]

export const selectReplayStatus = (chartId) => (state) =>
  state.replay.sessions?.[chartId]?.status || "idle"

export const selectReplayMode = (chartId) => (state) => {
  const session = state.replay.sessions?.[chartId]
  return session?.startTime ? REPLAY_MODE.DEFAULT : false
}

export const selectReplayIsLoading = (chartId) => (state) =>
  state.replay.sessions?.[chartId]?.status === "loading"

export const selectReplayIsPlaying = (chartId) => (state) =>
  state.replay.sessions?.[chartId]?.status === "playing"

export const selectReplayTrading = (chartId) => (state) => ({
  amount: state.replay.sessions?.[chartId]?.amount,
  trades: state.replay.sessions?.[chartId]?.trades,
  currentPosition: state.replay.sessions?.[chartId]?.currentPosition,
  pnl: state.replay.sessions?.[chartId]?.pnl,
})

// Chart-agnostic selector for shared components — reads chartId from context
export const selectIsAnyReplayActive = (state) =>
  Object.values(state.replay.sessions || {}).some(s => s?.startTime)
```

Controllers write state by dispatching:
```js
this.dispatch(setReplaySession(this._chartId, {status: "playing"}))
```

Components read via selectors:
```js
const status = useSelector(selectReplayStatus(chartId))
```

### Controller access (no state in context)

**ReplayContext** is a thin React context holding only the controller instance ref.
No state. Both TV and SC provide the same `ReplayContext` object.

```js
// src/models/replay/constants.js
export const ReplayContext = React.createContext({replayController: null})
```

**ScReplayContextProvider** becomes minimal:

```js
// super-chart/replay/sc-replay-context.js
export const ScReplayContextProvider = ({children}) => {
  const {chartController} = useSuperChart()

  const contextValue = useMemo(() => ({
    replayController: chartController?.replay || null,
  }), [chartController?.replay])

  return <ReplayContext.Provider value={contextValue}>
    {children}
  </ReplayContext.Provider>
}
```

No controller creation here — the controller is created in ChartController's
constructor as a sub-controller. The context provider simply exposes it.

TV's provider does the same with its own controller.

### ChartController integration

```js
// chart-controller.js — in constructor
this.replay = new ScReplayController(this)

// In dispose:
this.replay.destroy()
```

The controller has access to everything via its parent:
- `this._chartController._superchart` → Superchart instance / sc.replay
- `this._chartController.dispatch` / `getState` → Redux
- `this._chartController._currentMarket` → market data
- `this._chartController._marketTabId` → chart ID for keyed Redux state

---

## Controls Adaptation

### File moves

Components move from `tradingview/replay/` to `widgets/replay/`:

- `replay-controls.js` — main controls panel
- `pick-replay-start-button.js` — start time picker + random bar dropdown
- `toggle-replay-mode-button.js` — default/smart mode toggle

After the move, TV files (`tradingview-component.js`, `action-buttons.js`) update
their imports to `../../replay/...` (relative to the shared `widgets/replay/` path).
SC files import from the same shared path.

### ReplayControls changes (during move)

1. **Imports** — from shared constants + selectors:
   ```js
   import {REPLAY_MODE, REPLAY_STATUS, ReplayContext} from "~/models/replay/constants"
   import {selectReplaySession, selectReplayMode, selectReplayIsLoading, selectReplayIsPlaying} from "~/models/replay/selectors"
   ```

2. **Controller** — from ReplayContext (thin, controller-only):
   ```js
   const {replayController} = useContext(ReplayContext)
   ```

3. **State** — from Redux via selectors:
   ```js
   const {id: chartId} = useContext(MarketTabContext)
   const status = useSelector(selectReplayStatus(chartId))
   const replayMode = useSelector(selectReplayMode(chartId))
   const isLoading = useSelector(selectReplayIsLoading(chartId))
   const {amount, currentPosition} = useSelector(selectReplayTrading(chartId))
   // etc.
   ```

4. **currentMarket** — from MarketTabContext instead of ChartContext:
   ```js
   const {currentMarket} = useContext(MarketTabContext)
   ```
   Remove `ChartContext` dependency entirely.

5. **Speed** — handle both TV (intervalMs) and SC (speed) modes.

### Speed handling

Add to shared constants:
```js
export const SC_SPEED_OPTIONS = [1, 2, 5, 10, 20, 100, 200, 400]
export const TV_INTERVAL_OPTIONS = [10, 100, 1000 / 3, 1000, 2000, 3000, 10000]
```

Context provides:
- TV: `intervalMs` (existing), `speed: undefined`
- SC: `speed` (new field), `intervalMs: undefined`

In ReplayControls:
```js
const {speed, intervalMs} = useContext(ReplayContext)
const isScSpeed = speed !== undefined

// Speed dropdown
const speedOptions = isScSpeed ? SC_SPEED_OPTIONS : TV_INTERVAL_OPTIONS
const currentSpeedValue = isScSpeed ? speed : intervalMs

// Display
const speedLabel = isScSpeed
  ? `${speed}x`
  : `${ReplayController.intervalToFrequencyString(intervalMs)}x`

// On change
const handleSpeedChange = isScSpeed
  ? (s) => replayController.setSpeed(s)
  : (interval) => replayController.setIntervalMs(interval)

// Dropdown items
{speedOptions.map((opt) => (
  <PopupItem active={opt === currentSpeedValue} onClick={() => handleSpeedChange(opt)}>
    {isScSpeed ? `${opt}x per second` : `${ReplayController.intervalToFrequencyString(opt)}x per second`}
  </PopupItem>
))}
```

Move `intervalToFrequencyString` to shared constants as a standalone function.

---

## Widget Integration

### SuperChartWidgetWithProvider tree

```jsx
const SuperChartWidgetWithProvider = () => {
  const {id: marketTabId} = useContext(MarketTabContext)
  return <SuperChartContextProvider chartId={marketTabId || "main"}>
    <ScReplayContextProvider>                              {/* NEW */}
      <div tw="flex flex-col flex-1 h-full">
        <SuperChartWidget/>
        <SuperChartControls/>
      </div>
      <HeaderButtons mainChart/>
      <ScReplayHotkeys/>                                   {/* NEW */}
      <Screenshot/>
      {/* ... existing overlays ... */}
    </ScReplayContextProvider>                             {/* NEW */}
  </SuperChartContextProvider>
}
```

### SuperChartControls

```jsx
const SuperChartControls = () => {
  const screen = useContext(ScreenContext)
  const {id: chartId} = useContext(MarketTabContext)
  const replayMode = useSelector(selectReplayMode(chartId))  // was: hardcoded false

  const showReplayControls = !!replayMode
  const showActionButtons = !replayMode && screen === SCREENS.MOBILE

  if (!showActionButtons && !showReplayControls) return null

  return <TradeFormContextProvider>
    <div tw="flex flex-row space-x-2 p-2 overflow-auto"
         css={[css`box-shadow: inset 0 1px 0 0 var(--general-divider);`]}
         className="no-scrollbar">
      {showActionButtons && <ActionButtons/>}
      {showReplayControls && <ReplayControls/>}
    </div>
  </TradeFormContextProvider>
}
```

---

## Header Button Wiring

```js
// header-buttons.js
const HeaderButtons = ({mainChart}) => {
  const {readyToDraw, chartController} = useSuperChart()
  const {id: chartId} = useContext(MarketTabContext)
  const replayMode = useSelector(selectReplayMode(chartId))
  const selectingStartTime = useSelector(state => selectReplaySession(chartId)(state)?.selectingStartTime)
  const screen = useContext(ScreenContext)

  useEffect(() => {
    if (!readyToDraw || !chartController) return
    chartController.header.createHeaderButtons({
      // ...existing...
      onReplay: () => chartController?.replay?.handleSelectReplayStartTimeClick(screen === SCREENS.MOBILE),
    })
  }, [readyToDraw])

  // Replay highlight effect
  useEffect(() => {
    if (!readyToDraw || !chartController) return
    chartController.header.setReplayButtonHighlight(!!selectingStartTime)
  }, [readyToDraw, selectingStartTime])

  // Disable Buy/Sell/Alert buttons during replay
  useEffect(() => {
    if (!readyToDraw || !chartController) return
    chartController.header.setHeaderButtonsEnabled(!replayMode)
  }, [readyToDraw, replayMode])

  return null
}
```

**Exit selectingStartTime on outside click:**
Add a document click listener in ScReplayContextProvider (or a dedicated effect
component) that clears selectingStartTime when clicking outside the chart container.

```js
useEffect(() => {
  if (!selectingStartTime) return
  const handler = (e) => {
    const container = chartController?.getContainer()
    if (container && !container.contains(e.target)) {
      chartController?.replay?.setSelectingStartTime(false)
    }
  }
  document.addEventListener("mousedown", handler)
  return () => document.removeEventListener("mousedown", handler)
}, [selectingStartTime, chartController])
```

---

## Hotkeys

```js
// super-chart/replay/sc-replay-hotkeys.js
import {useContext, useMemo} from "react"
import {useSelector} from "react-redux"
import {bindHotkey, unbindHotkey} from "~/actions/hotkeys"
import {HOTKEY_COMMANDS} from "~/actions/constants/hotkeys"
import {selectReplayMode} from "~/models/replay/selectors"
import {useSuperChart} from "../context"
import {MarketTabContext} from "~/containers/market-tabs/context"
import HotkeyMapper from "~/containers/hotkeys/hotkey-mapper"
import util from "~/util/util"

const ScReplayHotkeys = () => {
  const {chartController} = useSuperChart()
  const {id: chartId} = useContext(MarketTabContext)
  const replayMode = useSelector(selectReplayMode(chartId))
  const hotkeysMap = useSelector(state => state.hotkeys.hotkeys.serializedSettings.keyMap.replay)
  const replay = chartController?.replay

  const handlePlayPause = util.useImmutableCallback(() => replay?.handlePlayPause())
  const handleStep = util.useImmutableCallback(() => replay?.handleStep())
  const handleBackToStart = util.useImmutableCallback(() => replay?.handleBackToStartClick())
  const handleStop = util.useImmutableCallback(() => replay?.handleStop())
  const handleBuy = util.useImmutableCallback(() => replay?.trading?.handleBuy())
  const handleSell = util.useImmutableCallback(() => replay?.trading?.handleSell())

  const comboCallbackMap = useMemo(() => ({
    [hotkeysMap[HOTKEY_COMMANDS.replayPlayPause]]: handlePlayPause,
    [hotkeysMap[HOTKEY_COMMANDS.replayStep]]: handleStep,
    [hotkeysMap[HOTKEY_COMMANDS.replayBackToStart]]: handleBackToStart,
    [hotkeysMap[HOTKEY_COMMANDS.replayStop]]: handleStop,
    [hotkeysMap[HOTKEY_COMMANDS.replayBuy]]: handleBuy,
    [hotkeysMap[HOTKEY_COMMANDS.replaySell]]: handleSell,
  }), [hotkeysMap])

  if (!replayMode) return null

  return <HotkeyMapper comboCallbackMap={comboCallbackMap}
                       bindFunction={bindHotkey}
                       unbindFunction={unbindHotkey}/>
}
```

TV's `ReplayHotkeys` has two modes: in-chart (tvWidget.onShortcut) and global (mousetrap).
SC only needs global (mousetrap via `bindHotkey`). Buy/Sell hotkeys added (TV's
ReplayHotkeys omits them — they're handled elsewhere in TV but should be here for SC).

---

## Datafeed Changes

```js
// super-chart/coinray-datafeed.js — add method
getFirstCandleTime = (ticker, resolution, callback) => {
  getCoinrayCache().fetchCandles({
    coinraySymbol: ticker,
    resolution,
    start: 0,
    end: Math.floor(Date.now() / 1000),
    useWebSocket: false,
  }).then((candles) => {
    if (candles?.length) {
      callback(new Date(candles[0].time).getTime())
    } else {
      callback(null)
    }
  }).catch(() => callback(null))
}
```

Note: this fetches the earliest chunk. If `fetchCandles` with `start: 0` doesn't
return the absolute first candle (API may paginate), we may need a dedicated endpoint
or a binary-search approach. Verify during implementation.

---

## Open Questions

1. **getFirstCandleTime reliability**: Does `getCoinrayCache().fetchCandles({start: 0})`
   return the actual first candle, or just the first page? If paginated, we need a
   different approach.

2. **Random start time rounding**: `util.roundTimeToCandle(time, resolution)` — does
   this utility exist? TV's `getRandomReplayStartTime` uses it. If not, it needs to
   be created or the rounding logic inlined.

3. **Trade form reset**: TV resets the trade form when replay starts
   (`dispatch(resetTradeForm())`). Does SC need the same? SC's trade form may be in
   a different context.

4. **Existing replay reducer**: There's already `state.replay` in Redux (with
   `replayContextGlobal`). Extend the existing reducer with `sessions` key, or
   create a new one? Extending avoids breaking existing TV code during coexistence.
