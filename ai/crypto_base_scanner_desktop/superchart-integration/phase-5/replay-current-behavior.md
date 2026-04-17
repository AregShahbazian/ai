# Replay & Quiz: Current TradingView Integration

How replay (default + smart/backtest) and quiz currently use/hack TradingView to control candle painting and chart behavior. Pure Altrady-side logic (playback speed UI, API call delays, position management) is excluded — this focuses on what SC needs to support.

---

## 1. Datafeed Hijacking (DataProvider)

**File:** `src/containers/trade/trading-terminal/widgets/center-view/tradingview/controllers/data-provider.js`

The custom `DataProvider` class implements TV's `IBasicDataFeed` interface. Both replay and quiz override its two critical methods:

### `getBars()` — History Loading

```js
getBars = async (symbolInfo, resolution, range, onResult) => {
  if (this.replayMode) {
    barsResult = await this.replayController.fetchCandles(...)
  } else if (this.quizController.questionController?.active) {
    barsResult = await this.quizController.questionController.getInitialCandles(...)
  } else {
    barsResult = await this.fetchCandles(...)  // normal path
  }

  // Replay post-processing: split candles into history vs future
  if (this.replayMode) {
    tvCandles = await this.replayController.takeCandles(tvCandles)
  }

  onResult(tvCandles, {noData})
}
```

**Replay:** Fetches a larger-than-requested range (to avoid TV's "No Data" on many empty `getBars` calls), then `takeCandles()` splits candles at the replay cursor time — history goes to TV, future candles are held in `replayCandles[]`.

**Quiz:** `getInitialCandles()` fetches candles but filters them to `maxCandleTime` (typically `questionStartTime`), so TV only sees candles up to a certain point.

### `subscribeBars()` — Realtime Updates

```js
subscribeBars = (symbolInfo, resolution, onRealtimeCallback, listenerGuid, onResetCacheNeededCallback) => {
  this.setDrawCandleCallback(onRealtimeCallback)

  if (this.replayMode) {
    this.onRealtimeCallback = onRealtimeCallback  // stored for manual invocation
    this.replayController.setReady()
    return  // NO WebSocket subscription
  }

  if (this.quizController.questionController?.active) {
    return  // NO WebSocket subscription, NO callback storage
  }

  // Normal: subscribe to live WebSocket candles via coinrayjs
  getCoinrayCache().subscribeCandles(...)
}
```

**Key hack:** Both replay and quiz prevent live candle data from reaching TV. Instead, they store the `onRealtimeCallback` and invoke it manually to push individual candles.

---

## 2. Draw Candle Callback Promise

**File:** `data-provider.js:57-68`

A promise-based mechanism decouples when candles are fetched from when they're drawn:

```js
drawCandleCallbackPromise = new Promise((resolve) => this.drawCandleCallbackResolve = resolve)

getDrawCandleCallback = async () => await this.drawCandleCallbackPromise
setDrawCandleCallback = (callback) => {
  if (callback) {
    this.drawCandleCallbackResolve(callback)  // resolve the promise
  } else {
    // reset: create new unresolved promise
    this.drawCandleCallbackPromise = new Promise(...)
  }
}
```

This is consumed by:
- **Replay:** `drawCandle()` calls `this.datafeed.onRealtimeCallback(candle)` directly (stored ref)
- **Quiz:** `DrawController.drawCandles()` awaits `getDrawCandleCallback()` then calls it per-candle
- **Layout changes:** TV layout events clear and re-await the callback to synchronize redraws

```js
// use-trading-view.js
tvWidget.subscribe("layout_about_to_be_changed", () => {
  datafeed.setDrawCandleCallback(undefined)  // clear
})
tvWidget.subscribe("layout_changed", async () => {
  await datafeed.getDrawCandleCallback()     // wait for new subscription
})
```

---

## 3. Replay: Candle Partitioning & Partial Candles

**File:** `src/containers/trade/trading-terminal/widgets/center-view/tradingview/controllers/replay/replay-controller.js`

### `takeCandles(candles)` — The Core Splitting Logic

When TV calls `getBars`, the returned candles are split at the replay cursor:

```js
takeCandles = async (candles) => {
  const currentTime = Math.max(this.time, this.firstCandleTime)
  let [history, replay] = partition(candles, ({time}) => this.sessionEnded || time < currentTime)
  
  // Future candles go to the queue
  this.replayCandles = sortBy(this.replayCandles.concat(replayCandles), "time")
  
  return history  // only history goes to TV
}
```

### Partial Candle — Preventing Price Spoilers

When the replay cursor falls mid-candle (e.g., 2:30pm in a 4h candle), showing the full candle would spoil the price. The system:

1. Detects when `this.time` is between a history candle's start and the next replay candle
2. Fetches sub-resolution candles (60m and 1m) covering only the elapsed portion
3. Merges them via `util.mergeCandles()` into a single partial candle with accurate OHLCV up to cursor time
4. Removes the full candle from history, keeps partial candle separately
5. Draws the partial candle via `drawCandle()` after TV is ready (in `handleReady`)
6. The full candle (with `time` set to replay cursor) is prepended to `replayCandles` so it gets completed during playback

```js
getPartialCandle = async (candle, candleCutoff) => {
  // Fetch 60m candles for the hours portion
  // Fetch 1m candles for the minutes portion
  // Merge into one candle with OHLC only up to candleCutoff
  return util.mergeCandles(innerCandles.map(util.parseTvCandle))
}
```

### `fetchCandles()` — Over-Fetching Workaround

**Problem:** TV calls `getBars` in chunks going backwards in time. If replay starts far
in the past, most chunks fall entirely after `startTime` — all candles get held for
replay, TV receives nothing, and after ~50 empty responses TV gives up and shows "No Data".

**What the code actually does:**

```js
fetchCandles = async ({coinraySymbol, resolution, range}) => {
  const replayLength = range.to * 1000 - this.startTime
  const replayStart = Math.max(
    Math.min(range.from, (this.startTime - replayLength) / 1000),
    this.firstCandleTime / 1000
  )
  return await this.datafeed.fetchCandles({..., range: {from: replayStart, to: range.to}})
}
```

The code extends `from` backwards by mirroring the distance from `startTime` to `range.to`.
The comment says "2x the needed range" but in practice:

- **Recent replay** (startTime close to now): `replayLength` is small, `from` shifts back
  modestly — roughly 2x as described.
- **Replay far in the past** (startTime far from `range.to`): `replayLength` is huge,
  `startTime - replayLength` goes negative or before `firstCandleTime`, gets clamped to
  `firstCandleTime`. Result: **fetches ALL available candles** from the market's first
  candle to `range.to`.

So for any replay that isn't very recent, this effectively fetches the entire candle
history in one request. The `takeCandles()` filter then splits this into history (shown)
and replay (queued). Wasteful but avoids the TV "No Data" bug.

---

## 4. Replay: Playback Loop

**File:** `replay-controller.js`

### `step()` — Draw One Candle

```js
async step(singleStep = false) {
  const candle = this.replayCandles.shift()
  await this.drawCandle(candle)        // push to TV via onRealtimeCallback
  this.setState({
    time: this.firstReplayCandle?.time || this.endTime,
    price: util.toSafeBigNumber(candle.close),
  })
}
```

### `drawCandle()` — Push to TV

```js
drawCandle = async (candle) => {
  await this.datafeed.onRealtimeCallback(candle)  // direct TV callback
  this.lastDrawnCandle = candle
}
```

### `play()` — Continuous Playback

```js
play = async () => {
  do {
    lastDrawnCandle = await this.step()
    await util.wait(this.intervalMs)  // user-configurable speed (10ms-10000ms)
  } while (lastDrawnCandle && this.status === REPLAY_STATUS.PLAYING)
}
```

### State Machine

```
LOADING → READY → PLAYING ⇄ PAUSED → FINISHED
                     ↓
                  STOPPED
```

---

## 5. Replay: Chart Reset & Reload

There are multiple levels of "reset" that serve different purposes. From lowest to
highest level:

### `resetCandles()` — Clear the replay queue

Clears the internal candle buffer only. No chart or datafeed interaction.

```js
resetCandles = () => {
  this.replayCandles = []
  delete this.lastDrawnCandle
}
```

**When used:** As a building block in all higher-level resets. Never called alone externally.

### `resetPlayback()` — Prepare for re-fetch

Clears the replay queue, wipes TV's candle cache, and puts the controller in LOADING
state so TV will call `getBars` again with fresh data. Does NOT touch trading state
(positions, trades) unless `resetSession=true` clears the time cursor.

```js
resetPlayback = async (resetSession = true) => {
  this.resetCandles()              // clear replay queue
  this.datafeed.resetAllData()     // clear TV's internal candle cache + reset draw callback promise
  this.setState({status: REPLAY_STATUS.LOADING})
}
```

**When used:** Resolution change during replay (with `resetSession=false` to keep the
session alive but re-fetch candles at the new resolution). Also called internally by
`setStartTime` when starting/restarting a replay.

### `reset()` — Full controller reset

Clears candles, optionally clears trading state (positions/trades), then triggers the
chart-level reset via `onReset` callback. This is the "start over" action.

```js
reset = ({keepSession} = {}) => {
  this.resetCandles()
  if (!keepSession) this.replayTradingController.reset()  // clear positions/trades
  this.onReset()  // → resetChartData() in use-trading-view
}
```

**When used:** After `setStartTime` — once the controller state is set, `reset` triggers
the chart to re-fetch and redraw. `keepSession=true` preserves trades when jumping back
in time within the same session.

### Chart-level resets (use-trading-view.js)

Two separate operations at the TV API level:

```js
resetChartData = (resetAllData = false) => {
  if (resetAllData) datafeed.resetAllData()  // clear ALL listener caches + draw callback
  else datafeed.resetData()                  // clear only the CURRENT listener's cache
  chart.resetData()                          // TV API: triggers fresh getBars calls
}
```

**`resetChartData`** is the `onReset` callback wired to `reset()` above. It forces TV to
discard its cached candles and re-invoke `getBars`, which flows back through
`fetchCandles` → `takeCandles` with the updated replay cursor position. The
`resetAllData` variant also resets the draw callback promise, which is needed when the
subscription state changes (e.g., layout changes, replay start/stop).

```js
resetChart = () => {
  chart.executeActionById("chartReset")  // TV API: reset zoom/scroll to default
}
```

**`resetChart`** only resets the viewport (zoom level, scroll position) — no data
changes. Called after replay reaches READY state (`handleReady`) so the chart
auto-fits the visible candles.

### Resolution Change During Replay

```js
// use-trading-view.js
handleIntervalChanged = async (interval) => {
  if (replayMode) {
    replayController.resetPlayback(false)  // keep session, re-fetch at new resolution
  }
}
```

`resetPlayback(false)` keeps the session (start time, trading state) but clears
the candle queue and TV cache. TV then calls `getBars` at the new resolution,
`fetchCandles` re-fetches, `takeCandles` re-splits at the same cursor position.

### Reset call chain summary

```
User clicks "Back to Start"
  → handleGoBackInTime(startTime)
    → resetTo(time)  // reset trading state to that point
    → setStartTime(startTime, {jumpTime, keepSession: true})
      → resetPlayback()        // clear queue + TV cache
        → resetCandles()
        → datafeed.resetAllData()
      → reset({keepSession})   // trigger chart re-fetch
        → resetCandles()
        → onReset()
          → resetChartData()   // TV re-fetches via getBars
      → handleReady()          // after TV loads
        → resetChart()         // fit viewport
```

---

## 6. Replay: TV Drawing Overlays

### Timeline Markers

**File:** `src/containers/trade/trading-terminal/widgets/center-view/tradingview/replay/replay-timelines.js`

Three vertical lines drawn via `chartFunctions.drawTimeLine()` (which uses `chart.createShape("vertical_line", ...)`):

| Line | Color key | When drawn |
|------|-----------|------------|
| Start time | `chartColors.replayStartTime` | Always (when replay active) |
| End time | `chartColors.replayEndTime` | When session has end time |
| Current time | `chartColors.replayCurrentTime` | During playback (not at start/finish) |

Each line is conditionally drawn only when `timeIsInVisibleRange(time)` is true, with labels showing formatted timestamps in the user's timezone.

Lines are managed with refs — cleared and redrawn on every state change.

### Position Overlay (Default Replay Only)

**File:** `src/containers/trade/trading-terminal/widgets/center-view/tradingview/replay/replay-position.js`

When the user has an open position during default replay:

- **P&L line:** `chartFunctions.createPositionLine()` → `chart.createOrderLine()` at entry price, showing unrealized P&L
- **Break-even line:** `chartFunctions.drawPriceLine()` → `chart.createShape("horizontal_line", ...)` at break-even price

---

## 7. Smart Replay (Backtest) Differences

**File:** `src/containers/trade/trading-terminal/widgets/center-view/tradingview/controllers/replay/smart-replay-controller.js`

SmartReplayController extends ReplayController. TV interaction differences:

| Aspect | Default Replay | Smart Replay |
|--------|---------------|--------------|
| Mode constant | `REPLAY_MODE.DEFAULT` | `REPLAY_MODE.SMART` |
| Start flow | Immediate `setStartTime` | Goes through backtest creation (`goToReplayBacktest`) or `quickStartBacktest` |
| Position overlay | P&L line + break-even (drawn on chart) | Managed by `ReplaySmartTradingController` (not drawn via chart shapes) |
| On stop | Clears trades | Clears backtest, refreshes market trading info |
| `isLoading` | Status-based only | Also true when `updatingPosition` |
| Jump back | Allowed | Blocked if backtest is finished |

TV datafeed behavior is identical — both use the same `DataProvider` instance, same `takeCandles`/`drawCandle` mechanism.

### Mode Switching

```js
// use-replay.js
toggleReplayController = (replayMode) => {
  const newController = isSmart ? smartReplayController : defaultReplayController
  if (replayController.datafeed) replayController.datafeed.setReplayController(newController)
  setReplayController(newController)
}

toggleSmartReplay = async (callback, replayMode) => {
  await replayController.handleStop(async () => {
    const controller = toggleReplayController(replayMode)
    if (callback) await callback(controller)
  })
}
```

Swapping controllers re-wires the `DataProvider` to the new controller. Both controllers are instantiated at mount and persist for the component lifetime.

---

## 8. Quiz: Candle Gating & Progressive Reveal

### Initial Candle Gating

**File:** `src/models/quiz/question-controller.js:82-97`

Base implementation filters candles by a `maxCandleTime`:

```js
async getInitialCandles({coinraySymbol, resolution, range, maxCandleTime}) {
  let candles = await this.quizController.api.fetchCandles({...})
  if (maxCandleTime) {
    candles = candles.filter(({time}) => valueOfDate(time) < valueOfDate(maxCandleTime))
  }
  return {candles, noData: !candles.length}
}
```

### Play Mode: Dynamic `maxCandleTime`

**File:** `src/models/quiz/play-controller.js:215-224`

```js
async getInitialCandles({coinraySymbol, resolution, range}) {
  const initialCandlesEnd =
    this.quizController.draw.lastDrawnCandleTime ||
    (this.reduxController.enableAnimation
      ? this.question?.questionStartTime
      : (!this.question.hideAnswer && this.question?.answer)
        ? this.question.solutionEnd
        : this.question?.solutionStartNextCandleTime)

  return await super.getInitialCandles({..., maxCandleTime: initialCandlesEnd})
}
```

This means:
- **Animation enabled:** Show candles up to `questionStartTime`, then animate the rest
- **Animation disabled, answered:** Show candles up to `solutionEnd`
- **Animation disabled, not answered:** Show candles up to `solutionStartNextCandleTime`

### Edit Mode: Static Gating

**File:** `src/models/quiz/edit-controller.js:99-106`

```js
async getInitialCandles({coinraySymbol, resolution, range}) {
  // No maxCandleTime — shows all candles up to current time
  // But adjusts `from` to center around questionStartTime
  if (this.question.questionStartTime) {
    const length = to * 1000 - this.question.questionStartTime
    from = Math.min(from, (this.question.questionStartTime - length) / 1000)
  }
  return await super.getInitialCandles({coinraySymbol, resolution, range: {from, to}})
}
```

### Progressive Candle Drawing

**File:** `src/models/quiz/draw-controller.js:223-271`

```js
drawCandles = async (candles, {visiblePriceRange, visibleTimeRange} = {}) => {
  const drawingCandlesId = UUID()  // abort token
  this.drawingCandlesId = drawingCandlesId

  const drawCandlesCallback = await this.getDrawCandleCallback()

  const animationSpeed = this.getAnimationSpeed(candlesToDraw.length, {
    maxDuration: this.questionGapDrawTimeLimit,  // default 2000ms
    minSpeed: this.reduxController.animationSpeed,  // default 30 candles/sec
    maxSpeed: DrawController.MAX_DRAWING_SPEED,  // 80 candles/sec
  })

  const waitMs = 1000 / animationSpeed

  for (let i in candlesToDraw) {
    if (this.drawingCandlesId !== drawingCandlesId) break  // abort check
    tvCandle = util.parseTvCandle(candlesToDraw[i])
    drawCandlesCallback(tvCandle)  // push one candle to TV
    this.lastDrawnCandle = tvCandle
    await util.wait(waitMs)

    // Lock visible range during drawing
    if (visiblePriceRange && Number(i) < 2) this.setVisiblePriceRange(visiblePriceRange)
    if (visibleTimeRange) this.setVisibleRange(visibleTimeRange)
  }
}
```

The `drawCandlesCallback` is TV's `onRealtimeCallback` obtained through the promise pattern.

### Question Transition Flow

**File:** `src/models/quiz/play-controller.js:247-285`

```js
drawQuestion = async (prevQuestion, question) => {
  const canTransition = await this.questionsCanTransition(prevQuestion, question)

  if (!canTransition || !enableAnimation) {
    // Hard reset: clear datafeed cache, force TV to re-fetch getBars
    await this.quizController.draw.reset(sameMarket && sameResolution)
  } else {
    // Smooth transition: fetch gap candles between questions
    const gapCandles = await this.getGapCandles(prevQuestion, question)
    candlesToDraw.push(...gapCandles)
  }

  if (enableAnimation) {
    const questionCandles = await question.fetchCandlesToDraw()
    candlesToDraw.push(...questionCandles)
    // Filter to only candles after last drawn candle
    candlesToDraw = util.filterCandlesByTime(candlesToDraw, {from: lastDrawnCandleTime})
    await this.quizController.draw.drawCandles(candlesToDraw)
  }
}
```

### Transition Eligibility

**File:** `src/models/quiz/question-controller.js:112-143`

Two questions can transition smoothly if:
- Same `coinraySymbol` and `resolution`
- Previous question was answered (in play mode)
- Solution times don't overlap
- Questions are in correct order
- Gap between them can be animated within `MAX_DRAWING_SPEED` (80 candles/sec)

Otherwise, a hard chart reset occurs.

### Gap Candles

```js
getGapCandles = async (question1, question2) => {
  return await this.quizController.api.fetchCandles({
    coinraySymbol: question2.coinraySymbol,
    resolution: question2.resolution,
    range: {
      from: (lastDrawnCandleTime || question1.solutionEnd) / 1000,
      to: question2.questionStartTime / 1000,
    },
  })
}
```

---

## 9. Quiz: TV Widget Configuration

### Base Quiz Setup (All Modes)

**File:** `src/models/quiz/question-controller.js:47-61`

```js
get tvSetup() {
  return {
    load_last_chart: !this.active,  // don't restore saved layout when active
    enabled_features: ["hide_resolution_in_legend"],
    disabled_features: [
      "header_resolutions",          // can't change timeframe
      "symbol_search_hot_key",       // can't search markets
      "symbol_info",                 // can't view symbol details
      "create_volume_indicator_by_default",
      "header_widget",               // entire header hidden
      "timeframes_toolbar",          // bottom timeframe bar hidden
    ],
    saveLoadAdapter: this.saveLoadAdapter,  // custom save/load for chart layouts
  }
}
```

### Edit Mode Override

**File:** `src/models/quiz/edit-controller.js:46-52`

```js
get tvSetup() {
  return {
    ...super.tvSetup,
    enabled_features: [],  // remove hide_resolution_in_legend
    disabled_features: ["create_volume_indicator_by_default"],  // re-enable everything else
  }
}
```

Edit mode enables full TV functionality (header, resolution changes, symbol search) since the quiz creator needs full control.

### TV Setup Application

**File:** `src/containers/trade/trading-terminal/widgets/center-view/tradingview/context/use-trading-view.js:298-319`

```js
const quizTvSetup = (inQuizzes || editQuestionWidgetActive) ? questionController?.tvSetup : {}
saveLoadAdapter = quizTvSetup?.saveLoadAdapter || dispatch(setupSaveLoadAdapter(...))

tvWidget = setupTradingview({
  ...tvSetup,           // base config
  ...quizTvSetup,       // quiz overrides applied last
  datafeed: datafeed,
  saveLoadAdapter,
})
```

---

## 10. Quiz: Chart Drawing API Usage

### DrawController Chart Access

**File:** `src/models/quiz/draw-controller.js`

The `DrawController` wraps TV chart APIs used by quiz:

| Method | TV API | Purpose |
|--------|--------|---------|
| `setVisibleRange(range)` | `chart.setVisibleRange()` | Lock viewport during animation |
| `setVisiblePriceRange(range)` | `pane.getMainSourcePriceScale().setVisiblePriceRange()` | Lock Y-axis during animation |
| `getAllShapes()` | `chart.getAllShapes()` | Get all drawings on chart |
| `deleteShape(id)` | `chart.removeEntity(id, {disableUndo: true})` | Remove a drawing |
| `createStudy(study)` | `chart.createStudy(name, forceOverlay, lock, inputs)` | Add indicators |
| `removeStudies(ids)` | `chart.removeEntity(id)` | Remove indicators |
| `saveChartToServer()` | `tvWidget.saveChartToServer()` | Persist chart layout |
| `currentLayoutName()` | `tvWidget.layoutName()` | Get current layout name |
| `reloadTradingView()` | Full widget destroy + recreate | Force complete reload |

### TV Initialization Wiring

```js
// use-trading-view.js — onChartReady
quizController.draw.setTradingView({
  chart: chart.current,
  tvWidget: tvWidget.current,
  datafeed: datafeed.current,
  reloadTradingView,
}, inQuizzes || editQuestionWidgetActive)
```

The `DrawController` stores these refs and uses a promise pattern (`tradingViewPromise`) so quiz operations can `await loadTv()` until the chart is ready.

---

## 11. Shared Patterns: What SC Must Support

### Mandatory Capabilities

1. **Datafeed control:** Ability to intercept/replace the standard data fetch and realtime subscription, or equivalent mechanism to control what candles the chart displays.

2. **Manual candle push:** A callback or method to push individual candles to the chart one at a time, making them appear as realtime updates (equivalent to TV's `onRealtimeCallback`).

3. **Data reset:** Clear all cached candle data and force re-fetch (equivalent to `resetData()` / `resetAllData()`).

4. **Partial candles:** Ability to show an "open" candle that gets updated over time — the candle drawn via the realtime callback must merge with the existing open candle rather than creating a new one.

5. **Visible range control:** Programmatic control of both time (X) and price (Y) visible ranges during animation.

6. **Drawing API:** Vertical lines (timelines), horizontal lines (price lines), and order/position lines that can be created, updated, and removed programmatically.

7. **Feature toggling:** Ability to disable chart UI elements (header, resolution selector, symbol search, timeframe toolbar) for quiz mode.

8. **Chart layout persistence:** Custom save/load adapter for quiz-specific chart layouts.

### Quiz-Specific Requirements

9. **Animation speed control:** The candle push mechanism must handle rates from 30 to 80 candles/sec without visual glitches or performance degradation.

10. **Abort mechanism:** Drawing loops must be cancellable mid-animation (when user skips to next question or changes question).

11. **Smooth transitions:** When transitioning between quiz questions on the same market/resolution, the chart should accept additional candles via the realtime callback without needing a full data reset.

12. **Study/indicator management:** Programmatic add/remove of studies with specific input values (quiz questions can have custom indicator setups).

13. **Shape management:** Programmatic access to all shapes (drawings) on the chart for export (quiz question creation) and selective deletion.

---

## 12. File Reference

```
Replay:
  controllers/data-provider.js          — Datafeed hijacking (getBars, subscribeBars)
  controllers/replay/replay-controller.js  — Core replay: takeCandles, partial candles, playback loop
  controllers/replay/smart-replay-controller.js  — Backtest extensions
  context/use-replay.js                 — React state, controller switching
  context/use-trading-view.js           — TV init, datafeed creation, chart reset
  context/replay-context.js             — State shapes
  replay/replay-timelines.js            — Timeline vertical lines
  replay/replay-position.js             — Position/PnL overlays

Quiz:
  models/quiz/question-controller.js    — Base: TV setup, candle gating, transition logic
  models/quiz/play-controller.js        — Play: dynamic gating, progressive drawing, transitions
  models/quiz/edit-controller.js        — Edit: full TV features, static candle view
  models/quiz/draw-controller.js        — Drawing loop, visible range, TV shape/study APIs
  models/quiz/quiz-redux-controller.js  — Animation settings (speed, gap limit, candle count)
```

All paths relative to `src/containers/trade/trading-terminal/widgets/center-view/tradingview/` unless prefixed with `src/`.
