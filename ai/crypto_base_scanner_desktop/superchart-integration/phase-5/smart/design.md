# SC Smart Replay — Design

## Controller Architecture

### Hierarchy

```
ChartController
  └─ ScReplayController              (existing, handles SC engine)
       ├─ ScReplayTradingController   (existing, simple buy/sell)
       └─ ScSmartReplayController     (NEW, backtest + smart trading)
```

`ScSmartReplayController` extends `ReduxController`. Created in `ScReplayController`
constructor alongside `ScReplayTradingController`.

```js
// sc-replay-controller.js constructor
this.trading = new ScReplayTradingController(this)
this.smart = new ScSmartReplayController(this)
```

### Mode Delegation

`ScReplayController` already calls `this.trading.updateCurrentState()` on each candle
step. In smart mode, it should delegate to the smart controller instead:

```js
// sc-replay-controller.js — onReplayStep callback
this._unsubStep = engine.onReplayStep((candle, direction) => {
  this._setSession({
    time: engine.getReplayCurrentTime(),
    price: util.toSafeBigNumber(candle.close),
  })

  if (this.replayMode === REPLAY_MODE.SMART) {
    this.smart.updateCurrentState(candle)
  } else {
    this.trading.updateCurrentState()
  }
})
```

The `replayMode` getter changes from checking `startTime` to checking the session's
`replayMode` field:

```js
get replayMode() { return this.state.replayMode }
```

And `_startSession` accepts a mode parameter:

```js
_startSession = async (startTime, mode = REPLAY_MODE.DEFAULT) => {
  // ...existing logic...
  this._setSession({startTime, replayMode: mode, selectingStartTime: false})
  this.dispatch(setReplayMode(mode))
  // ...
}
```

### ScSmartReplayController

Extends `ReduxController`. Receives `replayController` in constructor (same pattern as
`ScReplayTradingController`).

```js
class ScSmartReplayController extends ReduxController {
  _replayController = null

  constructor(replayController) {
    super({dispatch: replayController.dispatch, getState: replayController.getState})
    this._replayController = replayController
  }

  get _chartId() { return this._replayController._chartId }

  get state() {
    return selectReplaySession(this._chartId)(this.getState()) || {}
  }

  _setSession(patch) {
    this.dispatch(setReplaySession(this._chartId, patch))
  }
}
```

### Method Groups

**Backtest CRUD** — API calls, dispatch results to Redux:
- `fetchBacktests()`, `fetchBacktest(id)`, `createBacktest(config)`,
  `editBacktest(id, patch)`, `deleteBacktest(id)`

**Backtest Session** — load/resume/finish:
- `loadBacktest({backtestId, backtest})` — sets up replay with backtest data
- `handleNewBacktest()` — opens edit modal, stops current session if needed
- `setBacktestFinished()` — marks finished, cancels alerts
- `refreshBacktest()` — re-fetches active backtest
- `goToReplayBacktest(backtestId, isEdit)` — navigates widget to detail view

**Position Management** — all go through backend:
- `submitBacktestPosition(tradeForm)` — POST/PATCH position
- `cancelBacktestPosition(positionId)` — cancel
- `increaseBacktestPosition(positionId, params)` — add to position
- `reduceBacktestPosition(positionId, params)` — reduce/close position
- `triggerBacktest(backtestId)` — execute pending trigger

**Alert Management** — local state:
- `submitBacktestAlert(alert)` — add/update alert
- `cancelBacktestAlert(alertId)` — remove alert
- `checkAlerts()` — run each step, trigger if hit

**Trading Info Sync:**
- `loadBacktestTradingInfo({backtest})` — builds market trading info from backtest
  data, dispatches `storeMarketTradingInfo()` to Redux. This is how existing Trading
  Terminal widgets (order form, positions panel) display backtest data.

**Step Update:**
- `updateCurrentState(candle)` — called each step by ScReplayController. Checks
  alerts via `checkAlerts()`, checks backtest triggers, pauses + executes if hit,
  auto-resumes if enabled.

**List Management:**
- `setBacktestsStatus(status)`, `setBacktestsQuery(query)`, `refreshBacktests()`,
  `reloadBacktests()`

**Reset-To:**
- `checkResetToPossible(time)` — validates no partially-closed positions in range
- `resetTo(time)` — PATCH `/backtests/{id}/reset`, restart replay at new time

## State Management

### Session State — `state.replay.sessions[chartId]`

Existing default replay fields plus smart-specific fields:

```js
sessions[chartId]: {
  // Existing (sc-replay)
  startTime, endTime, time, price, status, selectingStartTime,
  trades, currentPosition,       // used by default replay trading

  // New (sc-smart-replay)
  replayMode,                    // REPLAY_MODE.DEFAULT or .SMART
  backtestId,                    // server ID of active backtest
  alerts,                        // active local alerts []
  triggeredAlerts,               // fired alerts []
  updatingPosition,              // true during trigger execution
}
```

Note: `backtest` (full object) is NOT in session state. It's a class instance stored in
`replayBacktestsWidget.backtest` (the widget's detail view state). The session only
stores `backtestId`. The smart controller holds a reference to the active backtest
instance in-memory (`this._backtest`).

### Widget State — existing slices (no changes to reducer)

```js
state.replay.backtests           // {data: ReplayBacktest[], loading, total}
state.replay.backtestsFilters    // {status, page, per, query}
state.replay.replayBacktestsWidget // {loading, editModal, backtest}
```

These are global (not per-chart), already exist in the reducer, and use existing action
types (`SET_REPLAY_BACKTESTS`, `SET_BACKTESTS_FILTERS`, `SET_REPLAY_BACKTEST_WIDGET`).

### ReplayBacktest Model

The existing `ReplayBacktest` class stays in its current TV location
(`tradingview/controllers/replay/backtest.js`). Both TV and SC need it during
coexistence.

The class currently gets its controller references via
`Selectors.selectReplayContextGlobal(this.getState())`. This works for TV. For SC,
the controller references need to come from a different source.

**Approach:** Make the backtest model controller-agnostic. Instead of reading from
`selectReplayContextGlobal`, accept controller references in the constructor or via
a setter. The `_parseBacktest` method on each smart controller passes its own refs:

```js
// ScSmartReplayController._parseBacktest
_parseBacktest = (state) => {
  const backtest = this.dispatch(ReplayBacktest.newController({state}))
  backtest._smartController = this
  backtest._replayController = this._replayController
  return backtest
}

// TV's parseReplayBacktest stays as-is (uses selectReplayContextGlobal)
```

The `ReplayBacktest` class adds a fallback:

```js
get replaySmartTradingController() {
  // SC path: injected directly
  if (this._smartController) return this._smartController
  // TV path: from Redux (existing)
  const {replaySmartTradingController} = Selectors.selectReplayContextGlobal(this.getState())
  return replaySmartTradingController
}
```

This keeps TV working exactly as before while allowing SC to inject its own controllers.

### Selectors

New selectors in `src/models/replay/selectors.js`:

```js
// Smart replay session fields
export const selectSmartReplayState = (chartId) => (state) => {
  const session = state.replay.sessions?.[chartId || "main"]
  return {
    backtestId: session?.backtestId,
    alerts: session?.alerts || [],
    triggeredAlerts: session?.triggeredAlerts || [],
    updatingPosition: session?.updatingPosition || false,
  }
}
```

Update `selectReplayMode` to use the stored mode:

```js
export const selectReplayMode = (chartId) => (state) => {
  const session = state.replay.sessions?.[chartId || "main"]
  return session?.replayMode || false
}
```

## Widget Access Pattern

### Problem

The backtest widget components are in the Trading Terminal layout, outside the SC chart
component tree. They can't use `ReplayContext`. TV solves this by mirroring controller
state to `replayContextGlobal` in Redux. SC doesn't mirror.

### Solution: Dual-source hook

During coexistence, the widget needs to work with both TV and SC charts. A custom hook
resolves the active smart replay controller from both sources:

```js
// src/containers/trade/trading-terminal/widgets/replay-backtests/use-active-smart-replay.js

export function useActiveSmartReplay() {
  const activeTabId = useSelector(MarketTabsSelectors.selectActiveTradingTabId)
  const session = useSelector(selectReplaySession(activeTabId))
  const tvContext = useSelector(Selectors.selectReplayContextGlobal)

  // SC controller from ChartRegistry (non-reactive lookup, stable ref)
  const chartController = ChartRegistry.get(activeTabId)
  const scReplayController = chartController?.replay || null
  const scSmartController = chartController?.replay?.smart || null

  // TV controller from Redux global context (existing path)
  const tvReplayController = tvContext?.replayController || null
  const tvSmartController = tvContext?.replaySmartTradingController || null

  // Active controller: prefer whichever has an active session
  const isScActive = !!session?.replayMode
  const isTvActive = !!tvContext?.backtest

  return {
    // SC controllers
    scReplayController,
    scSmartController,
    // TV controllers
    tvReplayController,
    tvSmartController,
    // Resolved active controller (for operations that don't care about chart type)
    replayController: isScActive ? scReplayController : tvReplayController,
    smartController: isScActive ? scSmartController : tvSmartController,
    // Availability (for edit modal chart type selector)
    hasSc: !!scReplayController,
    hasTv: !!tvReplayController,
    // Reactive state
    backtestId: session?.backtestId,
    updatingPosition: isScActive ? (session?.updatingPosition || false) : (tvContext?.updatingPosition || false),
    time: isScActive ? session?.time : tvContext?.time,
  }
}
```

Widget components use `smartController` / `replayController` for operations. These
resolve to whichever chart type has an active session (or SC by default).

The hook is reactive because:
- `activeTabId` from Redux → re-renders on tab switch
- `session` from Redux → re-renders on SC state changes
- `tvContext` from Redux → re-renders on TV state changes
- `ChartRegistry.get()` is a lookup — controller ref is stable during chart lifetime

### Chart Type Selector

Backtest sessions are chart-agnostic on the backend — a session created on TV can be
resumed on SC and vice versa. The chart type is only a client-side choice of which
replay engine renders the session.

When both `hasSc` and `hasTv` are true and the action is initiated from the widget
(not from the chart), a simple select "TradingView" / "SuperChart" is shown in:

- **Edit modal** — for new backtest creation. The selected type determines which
  controller pair handles `handleSubmit` and `loadBacktest`.
- **Resume confirmation dialog** — `backtest.handleResumeClick()` shows a confirm
  dialog. When both chart types are available, add a chart type select to the dialog.
  The selected type determines which controller loads the session.
- **View on Chart action** — `backtest.handleViewOnChart()` loads a finished backtest.
  Same selector logic.

When initiated from the chart (mode switch button), the chart type is implicit — no
selector shown.

Implementation: the `ReplayBacktest` action methods (`handleResumeClick`,
`handleViewOnChart`, `handleSubmit`) check `hasSc`/`hasTv` availability. When both
are available and not chart-initiated, they include the selector in the dialog/modal.
The selected chart type resolves to the corresponding controller pair via the hook.

### currentTimezone

TV reads `currentTimezone` from `replayContextGlobal`. For SC, read from the existing
`selectTimezone` selector directly in the components that need it (BacktestStats).

### Active Backtest Detection

Widget components that highlight the active backtest (list rows, detail header) compare
`backtest.id === activeBacktestId`. Use `backtestId` from the hook (which checks both
SC session and TV context).

## Mode Switching

### Flow

1. User clicks ToggleReplayModeButton
2. `replayController.handleSwitchReplayMode()` is called
3. If switching TO smart: opens backtest creation flow (edit modal)
4. If switching FROM smart: confirms data loss, stops, starts default replay

### No Controller Swapping

TV swaps between two separate controller instances (DefaultReplayController vs
SmartReplayController). SC does NOT swap — `ScReplayController` is always the replay
controller. The `replayMode` field in session state determines which sub-controller
handles step updates.

### handleSwitchReplayMode

```js
// sc-replay-controller.js
handleSwitchReplayMode = () => {
  if (this.replayMode === REPLAY_MODE.SMART) {
    // Smart → Default: stop smart session, keep replay going
    this.smart.exitSmartMode()
  } else {
    // Default → Smart: open backtest creation
    this.smart.handleNewBacktest()
  }
}
```

## loadBacktestTradingInfo

Same pattern as TV. After any position/trigger/alert change, rebuild and dispatch
market trading info so existing Trading Terminal widgets display backtest data:

```js
loadBacktestTradingInfo = async ({backtest}) => {
  const marketTradingInfo = {
    ...EMPTY_MARKET_TRADING_INFO,
    coinraySymbol,
    exchangeApiKeyId,
    openOrders: backtest.orders.filter(active),
    trades: backtest.trades,
    positions: backtest.backtestPositions.map(p => ({...p, exchangeApiKeyId})),
    alerts: this.state.alerts,
    triggeredAlerts: this.state.triggeredAlerts,
    alertCounts: computeAlertCounts(this.state.alerts),
    balances: {
      base: {available: backtest.baseBalance, total: backtest.baseBalance},
      quote: {available: backtest.quoteBalance, total: backtest.quoteBalance},
    },
  }

  await this.dispatch(storeMarketTradingInfo(coinraySymbol, marketTradingInfo, {
    exchangeApiKeyId, marketTabId
  }))
}
```

## Context Provider Updates

`ScReplayContextProvider` needs to populate the `smartTrading` field:

```js
smartTrading: {
  replaySmartTradingController: replay?.smart || null,
  backtest: session?.backtest,
  currentPosition: session?.smartCurrentPosition,
  updatingPosition: session?.updatingPosition || false,
  trades: session?.smartTrades || [],
  alerts: session?.alerts || [],
  triggeredAlerts: session?.triggeredAlerts || [],
},
```

And `replayMode` reads from session state instead of deriving from `startTime`:

```js
replayMode: session?.replayMode || false,
```

## File Organization

```
src/models/replay/
  constants.js                     # existing
  selectors.js                     # existing
  sc-replay-controller.js          # existing
  sc-replay-trading-controller.js  # existing
  sc-smart-replay-controller.js    # NEW (Group 1, done)

src/containers/trade/trading-terminal/widgets/
  replay-backtests/                # stays in place, rewired
    use-active-smart-replay.js     # NEW — dual-source hook
    backtest-edit-modal.js         # EDIT — add chart type selector
    ...                            # EDIT — replace selectReplayContextGlobal

  center-view/tradingview/controllers/replay/
    backtest.js                    # STAYS — shared by TV and SC
                                   # EDIT — add injected controller fallback
```

The `ReplayBacktest` model stays in its TV location. Both TV and SC import from
the same path. The model is made controller-agnostic (injected refs with TV fallback).

The widget files stay in their current location. `selectReplayContextGlobal` is
replaced with `useActiveSmartReplay()` which resolves to TV or SC controllers.
