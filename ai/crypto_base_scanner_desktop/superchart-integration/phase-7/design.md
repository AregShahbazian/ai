# Phase 7: Quiz System — Design & Implementation

Design choices for `prd.md` (`id: sc-quiz`).

---

## 0. Status preamble — drift between design and as-built

Most sections below describe the implementation accurately. A few items
drifted during implementation; this preamble lists the renames and moved
ownership in one place so the rest of the doc reads correctly:

| Original (in design below) | As-built |
|---|---|
| `DrawController` | `AnimationController` (`src/models/quiz/animation-controller.js`). Same shape — replay-engine driver: `drawUntil` / `overrideSpeed` / `stopDrawing` / `reset` / `setVisibleRange`. The drawings/indicators no-op stubs originally listed on `DrawController` are gone — that work moved to the new persistence layer (see §13). |
| `DrawController.chartController` getter | Moved to `QuizController.chartController` (`src/models/quiz/quiz-controller.js`). Resolves via `ChartRegistry.get("quiz")` (the quiz route mounts a single chart with the fixed id `"quiz"`); falls back to any registered controller. The animation controller and the persistence path both reach the chart through `quizController.chartController`. |
| `quizController.draw` | `quizController.animation`. Same instance, renamed reference. The reducer / state shape still uses `draw` (`onSaveDrawState`, `QUIZZES_DRAW_STATE_SHAPE`) — only the controller field name changed. |
| `_withChart` polling fallback | Uses `ChartRegistry.subscribe(tick)` plus `cc.replay.whenReady()`. The `whenReady` step waits for `superchart.onApiReady` → `ReplayController.init()`; without it, `setCurrentTime` calls fired between `ChartRegistry.register` and `onApiReady` were silent no-ops because `_replayEngine` was still null. |
| `EditController.refreshTv` | `EditController.focusOnQuestion(question, prevQuestion, {noFocus})`. The `noFocus` flag threads through `loadQuestion` so Reset / delete-question paths can avoid retriggering a VR jump on the still-active question. |
| `QuestionSyncController.focusEditQuestion` | Removed. The `[question?.id]` effect in `quiz-super-chart.js` no longer focuses VR — `quizPersistence.reload()` runs there instead. VR re-focus on identity change is handled by `editFocusRange` via the alt+R hotkey or by `focusOnQuestion`'s symbol/resolution branch. |
| `QuestionSaveLoadAdapter` / `EditQuestionSaveLoadAdapter` | **Files deleted.** Replaced by `QuizStorageAdapter` — see §13. |
| Drawings/indicators no-op stubs on `DrawController` | Gone. Capture and restore are real — see §13. |
| Header CSS hacks for hiding period-bar buttons | Replaced by SC feature flags (`disabledFeatures` constructor option + `setFeatureEnabled` runtime). See §2. |
| MODE_POLICY in `quiz-super-chart.js` | Per-mode policy expanded to `{periodBarVisible, lockSymbolPeriod, showSettings, showIndicatorPicker, showQuizContextMenu, drawingBarVisible}`. The `lockSymbolPeriod` flag distinguishes `edit` (locked — existing question) from `new` (unlocked — symbol/resolution still editable). |

The rest of this doc reads against the original names where it improves
historical readability (this is a design record, not a code reference);
when in doubt, the as-built names in the table above win.

---

## 1. Architecture overview

```
/quizzes route (containers/quizzes.js)
    │
    └─ QuizContextProvider  ← mounted here (NOT at logged-in.js anymore)
          │
          ├─ QuizController + Play/Edit/Preview/QuestionController + DrawController
          │      │
          │      └─ chartController.replay  (sc.replay engine)
          │
          └─ QuizQuestionChart
                │
                └─ QuizSuperChartWidget  ← new SC variant
                      │
                      └─ Superchart instance (independent ChartController per mount)

Outside /quizzes
    │
    └─ main-menu-mobile reads `state.quiz.activeQuestionMode` via Redux
       (no QuizContext dependency)
```

### Single source of candle gating

`chartController.replay` is the **only** thing that controls which candles are
visible during play / preview. No datafeed mutation. No `onRealtimeCallback`
hijacking. No parallel candle buffer.

The Play / Preview controllers' job becomes orchestration:

```
opening a question (animation ON) →
  await chartController.replay.setCurrentTime(question.questionStartTime)
  chartController.replay.playUntil(question.solutionStart, speed)

submitting an answer (animation ON) →
  chartController.replay.playUntil(question.solutionEnd, speed)

opening a question (animation OFF) →
  await chartController.replay.setCurrentTime(
    question.answer ? question.solutionEnd : question.solutionStartNextCandleTime
  )
```

Edit mode does **not** open a replay session — it stays in live mode (the
"freeze latest candle via default replay session at now" follow-up is
deferred — see `deferred.md`).

### Quiz module relocation + provider scoping

The folder `src/containers/trade/trading-terminal/quiz/` is a relic of the
dropped TT-integrated quiz idea. It moves to `src/containers/quizzes/` —
`quiz-context.js` and `use-quiz.js` end up alongside the other quiz route
files. `QUIZZES_CONTEXT_SHAPE` drops the `editQuestionWidgetActive` field;
`useQuiz` stops calling `TradingLayoutSelectors.selectWidgetIsActive(state,
"EditQuizQuestion")`.

`QuizContextProvider` also moves down — it leaves `logged-in.js` and
mounts inside `containers/quizzes.js` instead, wrapping the `/quizzes/*`
umbrella. Two cross-route consumers get replaced first:

- **`logged-in.js:79` (`useAppGlobals`)** — reads `quizController` only to
  put it on `window` via `storeGlobal` (a dev-only debug helper that
  early-returns in production). The `quizController` field gets dropped
  from that `storeGlobal({...})` call. If dev console access is wanted,
  it gets re-registered inside `useQuiz` so `window.quizController` is
  populated while the user is on `/quizzes`.

- **`containers/main-menu/main-menu-mobile.js:46`** — reads
  `questionController?.question?.questionMode` to hide the mobile
  bottom-nav while in play / preview. Replaced by a Redux flag — see §1a
  below.

### §1a Redux-driven mobile-menu hiding

`QuizReduxController` (already exists at
`src/models/quiz/quiz-redux-controller.js`) gets one new field and one
new selector. The mobile menu reads via Redux, with no `QuizContext`
dependency.

```js
// QuizReduxController.defaultState
{
  ...,
  activeQuestionMode: null,  // "play" | "preview" | null
}

// new action
static SET_ACTIVE_QUESTION_MODE = "SET_ACTIVE_QUESTION_MODE"

// new dispatcher
setActiveQuestionMode = async (activeQuestionMode) =>
  this.dispatchAction(QuizReduxController.SET_ACTIVE_QUESTION_MODE,
    {activeQuestionMode})

// QuizSelectors
selectActiveQuestionMode: (state) => state.quiz.activeQuestionMode,
selectIsInPlayOrPreview: (state) =>
  ["play", "preview"].includes(state.quiz.activeQuestionMode),
```

Wiring (in `PlayController` / `PreviewController`):

- `setQuestion(question)` → after the state write, call
  `this.reduxController.setActiveQuestionMode(question ? this.questionMode : null)`.
- `EditController` does **not** touch this flag — edit / new modes don't
  hide the bottom nav.
- `quizController.destroy()` (or any teardown path) clears the flag via
  `setActiveQuestionMode(null)` so a stale value doesn't survive into
  unrelated routes.

Mobile menu becomes:

```js
import {QuizSelectors} from "~/models/quiz/quiz-redux-controller"
const isInPlayOrPreview = useSelector(QuizSelectors.selectIsInPlayOrPreview)
if (isInPlayOrPreview) return null
```

No `QuizContext` import, no path coupling, no provider dependency.

`logged-in.js` updates its import path. `containers/quizzes.js`,
all code under `containers/quizzes/`, and any other `/quizzes`-route
file that reads `QuizContext` updates its import path. The mobile menu
loses its `QuizContext` import entirely. No other changes.

---

## 2. New SC variant: `QuizSuperChartWidget`

Location: `src/containers/trade/trading-terminal/widgets/super-chart/quiz/quiz-super-chart.js`
(or `src/components/quiz/quiz-super-chart.js` — kept under super-chart for
consistency with `ChartsPageChartWidget`, `GridBotSuperChartWidget`,
`PreviewSuperChartWidget`).

### Per-mode policy

The widget receives the active `questionMode` (`new`, `edit`, `play`,
`preview`) as a prop or via `QuizContext`. The mode drives all chrome:

| Mode | Header bar | Header buttons | Period bar | Bg context-menu |
|---|---|---|---|---|
| `new` | visible | Settings only | visible | `setSolutionStart`, `setSolutionEnd` |
| `edit` | visible | Settings only | visible | `setSolutionStart`, `setSolutionEnd` |
| `play` | hidden | — | hidden | (no quiz-specific entries) |
| `preview` | hidden | — | hidden | (no quiz-specific entries) |

> Replay button in edit / new — **not** wired in this PRD. Will be added when
> the deferred default-replay-session-in-edit-mode lands.

Header-bar visibility mechanism:
- SC has `setPeriodBarVisible(boolean)` for the **whole period bar** (the
  toolbar above the chart). Per the SC backlog and Phase 4 design, that's
  also the lever used to hide the entire chart "header" because there is
  no separate header construct in SC.
- For play / preview the widget mounts with `periodBarVisible: false` (the
  static constructor option, since the policy never changes for the lifetime
  of a play / preview chart instance).
- For edit / new the widget mounts with `periodBarVisible: true` and uses
  CSS to hide the buttons we don't want (Indicators, Symbol search,
  Timezone, Screenshot, Fullscreen) — same approach the
  `_applyTemporaryHacks` global rule uses, except scoped to this widget.
  Buy / Sell / Alert are not added in the first place since they are custom
  buttons via `chartController.header.createButton`. Only Settings is added.

### TradingTab/MarketTab wiring

Widget reads symbol + resolution from `MarketTabContext` like other SC
variants (Phase 9 charts-page pattern). Symbol/resolution changes flow back
through the same `TradingTabsController.setCoinraySymbol` /
`setResolution` pathways that TT and `/charts` use. The **EditController**
proxies `question.setCoinraySymbol` / `question.setResolution` to those
pathways instead of calling `chartController.setSymbol` / `setPeriod`
directly. Same pattern Phase 5 used for resolution change during replay.

### `ChartRegistry` registration

`super-chart.js` already auto-registers / auto-unregisters via
`ChartRegistry`. The quiz widget reuses that. The registry id is the
`marketTabId || "main"` if a tab exists, or a synthetic `quiz-question-{id}`
key when the widget is mounted outside a tab context. This matches the
phase-2 multi-chart contract.

---

## 3. `DrawController` refactor

Old shape: 400-line file holding `tv = {chart, tvWidget, datafeed,
reloadTradingView}`, a `loadTv()` promise, and a `drawCandles(...)` loop
that pushes candles via `datafeed.onRealtimeCallback`.

New shape:

```js
class DrawController extends Controller {
  constructor({redux, state, onSaveState, quizController}) {
    super({redux, state, onSaveState})
    this.quizController = quizController
    this.reduxController = new QuizReduxController({...})
  }

  // resolves the active SC chart controller via ChartRegistry
  get chartController() {
    return ChartRegistry.get(this.quizController.chartId) || ChartRegistry.getActive()
  }

  get isDrawing() { return this.state.isDrawing }
  get drawingSpeed() { return this.state.drawingSpeed }

  setIsDrawing = async (isDrawing) => {...}
  setDrawingSpeed = async (drawingSpeed) => {...}

  // Computed animation speed (cps), capped at MAX_DRAWING_SPEED = 80
  getAnimationSpeed = (totalCandles, {maxDuration, minSpeed, maxSpeed}) => {
    return Math.min(maxSpeed, Math.max(minSpeed, totalCandles / (maxDuration / 1000)))
  }

  // Drives sc.replay for animated reveal. Returns when target time reached.
  drawUntil = async (targetTime, totalCandles) => {
    const speed = this.getAnimationSpeed(totalCandles, {
      maxDuration: this.questionGapDrawTimeLimit,
      minSpeed: this.reduxController.animationSpeed,
      maxSpeed: DrawController.MAX_DRAWING_SPEED,
    })
    await this.setIsDrawing(true)
    await this.setDrawingSpeed(speed)
    this.chartController.replay.playUntil(targetTime, speed)
    // Resolve when the engine status auto-pauses at target
    await this._waitUntilPaused()
    await this.setIsDrawing(false)
  }

  // Mid-flight speed change → just call play() with the new speed
  overrideSpeed = (speed) => {
    if (this.chartController.replay.getReplayStatus() === "playing") {
      this.chartController.replay.play(speed)
      this.setDrawingSpeed(speed).catch(console.error)
    }
  }

  stopDrawing = async () => {
    this.chartController.replay?.pause()
    await this.setIsDrawing(false)
  }

  // Hard reset (called when transitioning to a non-transitionable question)
  reset = async () => {
    await this.stopDrawing()
    await this.chartController.replay?.setCurrentTime(null)
  }

  // ========================================================================
  // Drawings & indicators — NOOPS (deferred — see deferred.md)
  // ========================================================================
  saveChartToServer = async () => undefined
  currentLayoutName = async () => undefined
  getShapeById = async () => undefined
  getAllShapes = async () => []
  getAllDrawings = async () => []
  deleteShape = async () => undefined
  deleteShapes = async () => undefined
  removeAllDrawings = async () => undefined
  getAllStudies = async () => []
  getStudyInputValues = async () => undefined
  createStudy = async () => undefined
  createStudies = async () => undefined
  removeStudies = async () => undefined
  removeAllStudies = async () => undefined

  // setVisibleRange → delegate to chartController.setVisibleRange (unix s).
  setVisibleRange = (range) => {
    if (!range) return
    const {from, to} = range
    this.chartController?.setVisibleRange?.({from: from / 1000, to: to / 1000})
  }

  // setVisiblePriceRange — DROPPED (per PRD)
}
```

### `_waitUntilPaused` helper

`sc.replay.playUntil(target, speed)` doesn't return a promise. The engine
auto-transitions to `paused` when `getReplayCurrentTime() >= target`. We
listen via `onReplayStatusChange` once and resolve when status hits
`paused`:

```js
_waitUntilPaused() {
  return new Promise((resolve) => {
    const unsub = this.chartController.replay.onReplayStatusChange((status) => {
      if (status === "paused" || status === "finished") {
        unsub()
        resolve()
      }
    })
  })
}
```

### Readiness gating — replacing TV's two-promise dance

TV's `DrawController` had two hand-rolled gates: `tradingViewPromise`
(awaiting `onChartReady`) and `drawCandleCallbackPromise` (awaiting
TV's `subscribeBars` to hand over the realtime callback, with re-creation
on `layout_about_to_be_changed` / `layout_changed`). Quiz operations
awaited both in sequence. Stale references and re-subscription ordering
were the source of most quiz flakiness.

SC replaces all of this with **three** library-native gates and zero
manual promise plumbing:

| Gate | SC mechanism | Where it's used |
|---|---|---|
| **Chart mount** (DOM mounted, klinecharts ready, `getChart()` non-null, `sc.replay` non-null) | `superchart.onReady(cb)` — fires immediately if already ready, returns unsubscribe | `super-chart.js` (Phase 1) gates `ChartRegistry` registration on this. By the time `ChartRegistry.get(id)` returns a controller, the chart is mounted. |
| **Replay buffer ready** (history fetched, partial constructed, `status === "ready"`) | `setCurrentTime(t)` returns a `Promise<void>` that resolves only after the buffer is built | `await chartController.replay.setCurrentTime(t)` — single await, no parallel "callback ready" promise. |
| **Animation done** (`playUntil` reached its target and the engine auto-paused) | `onReplayStatusChange(cb)` for `paused` / `finished` | `_waitUntilPaused()` above. |

**Quiz operations always run after `QuizQuestionChart` mounts the SC widget**,
so by the time `PlayController.drawQuestion` / `EditController.focusOnQuestion`
/ `PreviewController.drawQuestion` execute, the registry already has the
controller. To make this contract explicit and prevent any silent-no-op if
a quiz operation ever races the mount, `DrawController` defers via
`onReady` when the controller isn't yet registered:

```js
async _withChart() {
  // Fast path — controller already registered (typical case).
  let cc = this.chartController  // ChartRegistry.get(...)
  if (cc?.replay) return cc

  // Slow path — wait for the SC widget to register a controller.
  await new Promise((resolve) => {
    const tick = () => {
      const c = this.chartController
      if (c?.replay) { unsub(); resolve() }
    }
    const unsub = ChartRegistry.onRegister(tick)  // or polling fallback
    tick()
  })
  return this.chartController
}

drawUntil = async (targetTime, totalCandles) => {
  const {replay} = await this._withChart()
  ...
}
```

If `ChartRegistry` doesn't yet expose an `onRegister` callback, the
fallback is a one-time `superchart.onReady` subscription on the active
widget instance (the `QuizSuperChartWidget` exposes its `superchart`
through context for this purpose). Either way, **no quiz call ever
silently fails because the chart wasn't ready** — it queues, then
runs.

**No layout-change re-gating.** SC has no equivalent of TV's
`layout_about_to_be_changed` / `layout_changed` events. The replay
engine survives indicator add/remove, theme switches, and theme styles
without reset. The whole `setDrawCandleCallback(undefined)` /
re-await dance from TV is gone.

**No abort-token (UUID) bookkeeping.** TV's `drawingCandlesId` UUID
existed because manual `await wait(ms)` loops can't be cancelled. SC's
engine has an internal `_generation` counter — calling
`setCurrentTime(null)` or starting a new session invalidates in-flight
fetches automatically. The `_waitUntilPaused()` listener simply detects
the status transition and unsubscribes.

### Removed surfaces

- `tv = {chart, tvWidget, datafeed, reloadTradingView}` ref.
- `tradingViewPromise` / `tradingViewResolve` / `loadTv()` / `setTradingView`.
- `getDrawCandleCallback`, `firstDrawnCandle`, `lastDrawnCandle`,
  `firstDrawnCandleTime`, `lastDrawnCandleTime`, `drawingCandlesId`,
  `waitMsOverride`, `drawCandles`, `setVisiblePriceRange`,
  `getCandlesVisiblePriceRange`, `getPaddedVisiblePriceRange`,
  `loadFirstCandleTime`, `lastCandle`, `firstCandleTime`,
  `getCandlesVisibleRange`, `getPaddedVisibleRange`, `subtractTimeInCandles`
  (the latter moves to `Question` since only `Question.questionStartTime`
  uses it).
- `reloadTradingView`.

The state shape `QUIZZES_DRAW_STATE_SHAPE` keeps `isDrawing` and
`drawingSpeed`. `isResetting` may be removable too — verify after the
refactor.

---

## 4. `QuestionController` / `PlayController` / `EditController` /
   `PreviewController` refactors

### `QuestionController` (base)

- Drop `tvSetup`, `chartComponents`, `saveLoadAdapter`,
  `getInitialCandles`, `loadFirstCandleTime`, `adjustCandleTime`.
- Keep `questionMode`, `active`, `question`, `setQuestion`, `goTo`,
  `reloadQuiz`, `reloadQuestion`, `loadQuestion`, `questionsCanTransition`.

### `PlayController.drawQuestion` (the heart of the port)

```js
drawQuestion = async (prevQuestion, question) => {
  const canTransition = await this.questionsCanTransition(prevQuestion, question)
  await this.question?.refreshStudies()  // NOOP (deferred), kept as a hook

  const {replay} = this.quizController.draw.chartController
  const enableAnim = this.reduxController.enableAnimation

  // Hard reset path — different symbol/resolution OR not transitionable
  if (!canTransition) {
    await replay.setCurrentTime(null)
    // symbol/resolution change flows through the MarketTab pipeline
    // (handled by the EditController/PlayController/PreviewController
    // via question.setCoinraySymbol / setResolution, not here)
    if (enableAnim) {
      await replay.setCurrentTime(question.questionStartTime)
      await this.setIsDrawingTransition(false)
      await this.quizController.draw.drawUntil(
        question.solutionStart,
        question.animationLengthCandles
      )
    } else {
      const target = !question.hideAnswer && question.answer
        ? question.solutionEnd
        : question.solutionStartNextCandleTime
      await replay.setCurrentTime(target)
    }
    return
  }

  // Smooth-transition path — same session, just play forward
  if (enableAnim) {
    const gapCandles = (question.questionStartTime -
      replay.getReplayCurrentTime()) / resolutionMs(question.resolution)
    await this.setIsDrawingTransition(true)
    await this.quizController.draw.drawUntil(
      question.questionStartTime, gapCandles)
    await this.setIsDrawingTransition(false)
    await this.quizController.draw.drawUntil(
      question.solutionStart, question.animationLengthCandles)
  } else {
    const target = !question.hideAnswer && question.answer
      ? question.solutionEnd
      : question.solutionStartNextCandleTime
    await replay.setCurrentTime(target)
  }
}
```

The `getGapCandles` API call disappears entirely — the engine fetches gap
candles itself when we `playUntil(questionStartTime)`.

### `PlayController` post-answer

When `answerResultQuestion` resolves, kick `playUntil(solutionEnd, speed)`
if animation is enabled. The existing `handleAnswer` callback in
`play-question.js` already triggers `question.drawSolutionCandles` — that
method gets retargeted to `chartController.replay.playUntil`.

### `EditController.refreshTv` → `EditController.focusOnQuestion`

```js
focusOnQuestion = async (question, prevQuestion) => {
  const resolutionOrMarketChanged =
    question.coinraySymbol !== prevQuestion?.coinraySymbol ||
    question.resolution !== prevQuestion?.resolution
  const questionHasChanged = question.id !== prevQuestion?.id

  if (!questionHasChanged || resolutionOrMarketChanged) {
    this.refreshRanges()
  }
}

refreshRanges = async () => {
  await this.quizController.draw.setVisibleRange(this.question?.visibleTimeRange)
}
```

> **Implementation note:** the design originally had a `refreshRanges(false)` double-call (immediate + 500ms retry). The actual implementation is a single call — the retry was found unnecessary once `QuestionSyncController` handled VR focus for symbol/resolution changes (see §12a).

`saveChartToServer` and `currentLayoutName` calls are removed (the methods
on `DrawController` are no-ops now anyway).

### `PreviewController.drawQuestion`

```js
drawQuestion = async ({question}) => {
  const {replay} = this.quizController.draw.chartController
  await this.quizController.draw.stopDrawing()
  await replay.setCurrentTime(null)
  // refreshStudies — NOOP (deferred)
  await replay.setCurrentTime(question.questionStartTime)
  await this.quizController.draw.drawUntil(
    question.solutionStart, question.animationLengthCandles)
}
```

Preview always animates. If the user toggles animation OFF in preview,
`drawUntil` gets a speed of `MAX_DRAWING_SPEED` (effectively a fast cut).

---

## 4a. `Question.editFocusRange` getter

Used by the alt+R hotkey and `QuestionSyncController` to compute the edit-mode
VR target, handling partial timestamp state:

```js
get editFocusRange() {
  const start = this.solutionStart
  const end   = this.solutionEnd
  if (!start && !end) return undefined          // nothing set → resetView()
  if (start && end)   return this.visibleTimeRange  // both set → full window
  const anchor = start || end
  const padMs  = resolutionToDuration(this.resolution) * 1000 * 50
  return {from: anchor - padMs, to: anchor + padMs}  // one set → 50-candle pad
}
```

`visibleTimeRange` pads 100% on each side of the `solutionStart`–`solutionEnd`
spread (unchanged from TV-prod). `editFocusRange` delegates to it when both
are set, so the two are identical in the normal case.

---

## 4b. `ReplayController` quiz-facing engine delegates

Quiz draw/play/preview controllers call engine methods directly on `cc.replay`
to control the SC replay engine without going through the full `_startSession`
Redux session flow. These are thin delegates in `ReplayController`:

```js
setCurrentTime = async (time, endTime) => { ... }   // null → reset engine
getReplayCurrentTime = () => { ... }
getReplayStatus = () => { ... }
onReplayStatusChange = (cb) => { ... }               // returns unsubscribe
playUntil = (targetTime, speed) => { ... }
```

They deliberately bypass Redux state (`setReplayMode`, `_setSession`) — the
quiz animation loop is not a user-visible replay session.

---

## 4c. `QuestionSyncController` — quiz chart symbol/period sync ✅

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/controllers/question-sync-controller.js`

Quiz analog of `MarketTabSyncController`. Manages:

1. **State→chart sync** (`syncSymbolToChart`, `syncResolutionToChart`) — echo-guarded
   to prevent SC's change events from writing back to the question.

2. **VR re-focus after load** (`_scheduleEditFocusAfterLoad`) — called from
   `_onChartSymbolChange` / `_onChartPeriodChange` before the echo guard. SC
   fires these events after it finishes loading the new data and resets VR to
   latest candles. The method subscribes one-shot to `onVisibleRangeChange`:
   when SC's own reset fires it, the callback immediately calls `setVisibleRange`
   with `editFocusRange`. This handles both user-initiated and
   state-driven symbol/resolution changes.

3. **VR re-focus on question identity change** (`focusEditQuestion`) — called
   directly from `QuizChart`'s `useEffect([question?.id])`. Fires when navigating
   between questions that share the same symbol/resolution (no chart reload,
   no VR event). Calls `setVisibleRange` directly.

The `QuizChart` component in `quiz-super-chart.js` wires three effects:
```js
useEffect([coinraySymbol]) → questionSync.syncSymbolToChart(coinraySymbol, resolution)
useEffect([resolution])    → questionSync.syncResolutionToChart(resolution)
useEffect([question?.id])  → questionSync.focusEditQuestion()
```
The `question?.id` dep prevents timestamp edits on the same question from
triggering a VR jump (only identity change triggers it).

---

## 5. New chart overlays

| Overlay | TV file | New SC file | Pattern |
|---|---|---|---|
| Solution-start / Solution-end vertical lines | `tradingview/quiz/questions-timelines.js` | `super-chart/quiz/questions-timelines.js` | `verticalStraightLine` overlay via `chartController.createOverlay`, one per timeline marker, per-item overlay groups (`OverlayGroups.questionsTimelines-${id}-start`). Standard `useDrawOverlayEffect`. |
| Decision-point arrow | `tradingview/quiz/decision-point-arrow.js` | `super-chart/quiz/decision-point-arrow.js` | Time-anchored overlay (`simpleAnnotation` or custom figure registered for the arrow shape). Single overlay group, redrawn on `question?.solutionStart` change. |
| Per-mode wrappers (compose mode-specific overlays) | `tradingview/quiz/{edit,play,preview}-drawings.js` | `super-chart/quiz/{edit,play,preview}-drawings.js` | Pure JSX composition. Reads `QuizContext` for question + mode, mounts the relevant overlay components. No chart API calls inside. |

The "user drawings auto-load" / "user drawings capture" inside `edit-drawings.js` are stubbed
(the methods they would call on `DrawController` are no-ops — see deferred.md).

---

## 6. Bg context-menu entries

The SC bg context menu lives in
`super-chart/controllers/context-menu-controller.js`. The quiz widget
declares its entries through the same builder pattern Phase 4
established. Pseudocode:

```js
// Quiz widget mount
chartController.contextMenu.registerProvider(() => {
  if (mode === "edit" || mode === "new") {
    return [
      {label: i18n.t("..setSolutionStart"), onClick: handleSetSolutionStart},
      {label: i18n.t("..setSolutionEnd"),   onClick: handleSetSolutionEnd},
    ]
  }
  return []
})
```

`handleSetSolutionStart` / `handleSetSolutionEnd` reuse the existing
`InteractionController` price-time-select pattern Phase 5 wired for the
replay-start picker. Quiz already uses this via `startPriceTimeSelect` /
`stopPriceTimeSelect` in `use-quiz.js` — those shims are removed and the
widget consumes `InteractionController` directly.

The TT chart's `context-menu-controller.js` drops the `inQuizzes` /
`showQuizControls` gates entirely — there's nothing to gate against
anymore.

---

## 7. Storage adapter no-ops

`QuestionSaveLoadAdapter` and `EditQuestionSaveLoadAdapter` keep the same
class shape so existing imports don't break, but every method becomes a
no-op:

```js
export class QuestionSaveLoadAdapter {
  constructor({questionController}) {
    this.getQuestionController = () => questionController
  }
  // All methods return resolved promises with empty data
  loadChart()                  { return Promise.resolve(null) }
  saveChart()                  { return Promise.resolve() }
  loadLineToolsAndGroups()     { return Promise.resolve(null) }
  saveLineToolsAndGroups()     { return Promise.resolve() }
  // ... rest of LocalSaveLoadAdapter surface
}

export class EditQuestionSaveLoadAdapter extends QuestionSaveLoadAdapter {}
```

The `LocalSaveLoadAdapter` parent (`controllers/local-save-load-adapter.js`)
is TV-shaped — these subclasses no longer extend it. They become
freestanding stubs. The TV file stays untouched (still used by TV elsewhere
during coexistence).

---

## 8. Animation speed dynamics

`reduxController.animationSpeed` (cps) drives the **floor** of computed
speed. `MAX_DRAWING_SPEED = 80` is the **ceiling**. The middle term is
"draw all gap candles within `questionGapDrawTimeLimit` ms (default
2000ms)".

Mid-flight speed changes from the sidebar settings panel call
`drawController.overrideSpeed(newSpeed)`. With SC's `play(newSpeed)` while
already playing, only the speed changes — no status-callback re-fire. The
PR drops `waitMsOverride` since it has no equivalent need.

---

## 9. State machine guards

The replay engine enforces strict transitions (idle → loading → ready →
playing ⇄ paused → finished, plus `any → idle` on `setCurrentTime(null)` /
`setSymbol`). Quiz has to respect these:

- `setCurrentTime(time)` can be called from any state — engine internally
  handles `loading`. Always `await` it before `playUntil`.
- `playUntil(target)` requires `paused` or `ready`. If we just finished
  a previous `playUntil` and the engine is `paused`, we can chain.
- A second `setCurrentTime(time)` while the previous is in flight is safe —
  the engine increments `_generation` and old fetches no-op.

The `drawingCandlesId` UUID abort token is dropped — the engine's
generation counter is the abort mechanism.

---

## 10. Drop per-question candle storage

TV-prod saved the candles for a question on the backend as a "we might lose
provider data later" fallback. Our provider is now reliable; the fallback
is removed.

**Backend contract.** The create/update payload still requires a `candles`
field. The `Question.body` builder reads it from
`defaultMutableState.candles` which stays `[]`. So every payload sends
`candles: []`, satisfying the contract without any frontend logic
populating it.

**Removed surface (in `Question.js`):**

- `setCandles(candles)` setter.
- `candles` getter.
- `loadQuestionCandles()` method (and its `noDataCouldBeFound` toast).
- The `if (!this.id) { await loadQuestionCandles(); if (!this.candles.length) return }`
  guard in `submit()`. Submission proceeds unconditionally after standard
  validation.

**Kept:**

- `candles: []` in `defaultMutableState` — purely so `Question.body`
  serialises it as `[]` for the backend. Nothing reads it on the frontend.

**Not introduced:**

- No fallback "if backend has saved candles, use them" code path. Play /
  preview / edit always fetch from `chartController.replay` (which goes
  through the SC datafeed → CoinrayCache). If the provider is unavailable
  for a market, the question simply fails to render its candles — same
  failure mode as any live chart.

## 11. Open questions

All resolved during implementation:

1. ~~**Where does `QuizSuperChartWidget` actually live?**~~ Resolved — under
   `super-chart/quiz/` next to other SC variants
   (`super-chart/quiz/quiz-super-chart.js`).

2. ~~**`Question.animationLengthCandles` exposure.**~~ Resolved — the count
   stays encoded in `question.questionStartTime`. `AnimationController.drawUntil`
   computes it internally and only uses the count for the speed-ceiling
   check. No quiz UX reads the exact value.

3. ~~**`isResetting` state.**~~ Resolved — removed. Engine status is
   authoritative.

4. ~~**Mobile-only price-time-select toast.**~~ Resolved — kept on the
   quiz-handler side (`useQuizHandlers`), no `InteractionController` hook
   needed.

5. ~~**`refreshStudies` / `updateDrawingsTrigger` callsites.**~~ Resolved —
   `refreshStudies` is gone (the persistence layer handles indicator
   restore on question switch via `quizPersistence.reload()`).
   `updateDrawingsTrigger` is gone too.

6. ~~**`QuizContextProvider` location.**~~ **Resolved** — provider moves
   to `containers/quizzes.js`, scoped to the `/quizzes` route only. The
   two cross-route consumers (`logged-in.js`'s dev-only `storeGlobal`
   call and `main-menu-mobile.js`'s play/preview hide check) are replaced
   per §1a (Redux flag) and the description in "Quiz module relocation
   + provider scoping". No regression on server-persisted quiz state
   (`openQuizResult`, answers, timings) — those reload from the backend
   on `/quizzes` re-entry. Ephemeral context state is recreated per
   mount, which is fine.

---

## 12. `QuestionSyncController` — quiz chart symbol/period sync (as-built)

The earlier §4c described a `focusEditQuestion()` method called from the
`[question?.id]` effect. That method was removed during implementation
because it caused a spurious VR re-sync when navigating between questions
on the same symbol/resolution (the chart was already loaded; nothing to
re-focus). The remaining responsibilities:

1. **State→chart sync** (`syncSymbolToChart`, `syncResolutionToChart`),
   echo-guarded.
2. **VR re-focus after load** (`_scheduleEditFocusAfterLoad`) — called
   from `_onChartSymbolChange` / `_onChartPeriodChange`. Subscribes
   one-shot to `onVisibleRangeChange`; when SC's own reset fires after
   the load completes, the callback calls `setVisibleRange` with
   `editFocusRange`. This handles both user-initiated and state-driven
   symbol/resolution changes.

Wiring in `QuizChart`:
- `useEffect([coinraySymbol])` → `syncSymbolToChart`
- `useEffect([resolution])`    → `syncResolutionToChart`
- `useEffect([question?.id])`  → `quizPersistence.reload()` (no VR call)

Same-question timestamp edits do not trigger VR jumps — `editFocusRange`
is only consumed by alt+R and by `_scheduleEditFocusAfterLoad` (which only
fires on load completion). The `EditController.focusOnQuestion` path
applies `setVisibleRange` only when symbol/resolution changed or on the
initial load of a new question identity.

---

## 13. Storage & persistence (added during implementation)

The original PRD scoped storage out (see initial `deferred.md`), then
folded it back in during implementation. The architecture below is what
shipped — see commit `ff0c14e0` "wire quiz storage, persistence, and
gating".

### 13.1 Data model (existing on `Question`, used by adapter)

The `Question` model already held the storage shape — three drawing
buckets and one global indicator list. The adapter just bridges SC's
StorageAdapter contract to these:

```
question.questionDrawings    ← the always-shown drawings
question.hintDrawings        ← shown when showHint is on
question.solutionDrawings    ← shown after the user answers
question.questionStudies     ← indicators (global to the question, not bucketed)
question.drawingMode         ← edit-mode UI state: which bucket the user
                               is currently editing ("question" | "hint" |
                               "solution" | undefined for "show all")
question.allDrawings         ← computed: concat of the three buckets
question.getDrawingsForMode  ← computed: bucket lookup by name
```

The buckets are persisted server-side as part of the question payload.
Drawings come back from the API with whatever ids they were saved with;
the chart-side path (§13.3) regenerates fresh UUIDs on every render to
avoid klinecharts' id-collision tombstone bug.

### 13.2 `QuizStorageAdapter` (model layer)

`src/models/quiz/quiz-storage-adapter.js`. Implements SC's `StorageAdapter`
shape (`load(key) → {state, revision}`, `save(key, state) → {revision}`,
`delete(key)`). The `key` argument is unused — the adapter resolves the
active question and mode from `quizController` at call time, so the same
chart instance handles edit/preview/play without re-keying.

**Mode resolution.** `isEditMode` is `quizController.questionController ===
quizController.edit`. Anything else (preview, play) is read-only.

**Load.** Returns:
```
{state: {version: 1, indicators, overlays, styles, paneLayout, preferences}, revision}
```

- `indicators`: `_loadIndicatorsOverride ?? question.questionStudies`.
- `overlays`: in edit mode, `_editOverlays(question)` →
  `question.drawingMode ? getDrawingsForMode(mode) : allDrawings`. In
  preview/play, `_playOverlays(question, qc)` →
  `questionDrawings + (showHint? hint : []) + (answer && !hideAnswer?
  solution : [])`. `_loadOverlaysOverride` short-circuits this.

The override hooks (`setLoadIndicatorsOverride`, `setLoadOverlaysOverride`)
let `quizPersistence.reload` feed `sc.loadState()` only the new/changed
indicators — kept indicators would otherwise duplicate, since `loadState`
is additive.

**Save.** SC autosaves on every overlay/indicator mutation. The adapter:
- No-ops in preview/play (the gated load returns only some buckets — letting
  save echo those would wipe the omitted ones).
- No-ops while `_loading` is true (suppress autosave during reload-driven
  bulk mutations).
- Drops any overlay with `save: false` (transient prev-question drawings
  must never enter the buckets).
- Routes overlays to buckets: if `drawingMode` is set, the whole list goes
  to that bucket; otherwise each overlay stays in its existing bucket
  (matched by id), with new overlays defaulting to `"question"`.
- Compares against `question.questionStudies` via deep equality that
  ignores `id` (SC reassigns ids on every save) and writes only on real
  change. `touch()` (dontSave) fires before `setQuestionStudies` so the
  subsequent respawn captures `touched=true` in the cloned state.

**Delete.** Clears the active bucket if `drawingMode` is set, else all
buckets, plus indicators.

**Defensive equality helpers.** `sameOverlays` is a JSON deep-equal —
catches drag/coord changes (ids stable, points differ). `sameIndicators`
strips `id` because SC issues fresh ids on every load.

### 13.3 `QuizPersistenceController` (chart-side)

`src/containers/trade/trading-terminal/widgets/super-chart/controllers/quiz-persistence-controller.js`.
Sub-controller on `QuizChartController` (which extends `ChartController`).
Owns chart-side imperative drawing/indicator application — the things SC's
`adapter.load` + autosave cannot express on its own.

**`reload()`** — full path used on question-id change and on Reset:

1. Drop chart state imperatively. Walk `adapter.current.overlays` and call
   `sc.removeOverlay(id)` for each. Then walk `_viewTransientIds` (preview/
   play UUIDs that weren't in `adapter.current` because they're not in
   question state).
2. In **edit mode**: render the full bucket(s) with fresh UUIDs (avoiding
   the klinecharts tombstone bug — re-creating an overlay with a
   just-removed id silently fails). Write the fresh ids back via
   `adapter.setBucketDrawings(bucket, list, {silent: true})` so the form
   doesn't get touched.
3. In **preview/play**: render the gated subset (`adapter.viewOverlays()`)
   with fresh UUIDs into `_viewTransientIds`. No bucket writes.
4. Diff indicators (`{removed, changed, added}`). Remove the old/changed
   ones via `sc.removeIndicator(name)`. Set `_loadIndicatorsOverride` to
   `[...changed, ...added]` and `_loadOverlaysOverride` to `[]`, then call
   `sc.loadState()` — this restores the new indicators through SC's
   modal-aware path (the only public API that updates both canvas and
   `chartStore.mainIndicators`/`subIndicators`). The `[]` overlays
   override prevents `loadState` from re-creating drawings (we already
   handled them above; without the override, `loadState`'s additive
   behaviour would either fight us or duplicate).
5. Apply prev-question drawings via `_applyPrevDrawings()`.

**`swapDrawings()`** — fires on `question.drawingMode` change. Lighter
than `reload`: keeps indicators and transient prev overlays in place,
reads the chart's current overlays via `chart.getOverlays()` (NOT
`adapter.current` — adapter state lags during rapid mutations), excludes
prev-transient ids, removes everything else, recreates from the new
bucket(s) with fresh UUIDs, writes back silently.

**`_applyPrevDrawings()`** — renders the previous question's drawings as
**transient** overlays (`save: false, lock: true`, fresh UUIDs). Mode
gating mirrors TV-prod:

| Mode | Predicate | Source |
|---|---|---|
| edit    | `question.isSameMarketResolution(prevQuestion)`   | `editController.prevQuestionDrawings` (already gated by sameMarketResolution) |
| play    | `await questionsCanTransition(prev, current)`     | `prevQuestion.allDrawings` |
| preview | never                                              | — |

A signature string (`mode|prevId|symbol|resolution|count`) lets repeat
calls with unchanged input no-op — prevents flash on question switches
that share the same prev set. Public `applyPrev()` is fired from
`subscribeBarsLoaded` so prev drawings appear after the first dataset
lands (initial mount restore doesn't include them).

**`clearBucket(mode)`** — exposed for the form-side X-chip on
`DrawingModePicker`. Removes the bucket's drawings from chart and writes
the empty bucket via the adapter. Same call regardless of whether the
bucket is currently visible.

**`removeIndicator(name)` / `removeOverlay(id)`** — passthroughs for
form-side actions that need the chart as the single source of truth.

### 13.4 Wiring (`quiz-super-chart.js`)

Mounted once via the chart-lifecycle setup callback:

```js
const adapter = useMemo(() => new QuizStorageAdapter({quizController}), [...])

useChartLifecycle({
  superchartOptions: {storageAdapter: adapter, storageKey: "quiz", ...},
  ControllerClass: QuizChartController,
  setup: ({superchart, controller}) => {
    controller.replay        = new ReplayController(controller, {forceDefaultMode: true})
    controller.questionSync  = new QuestionSyncController(controller, {quizController})
    controller.quizOverlays  = new QuizOverlaysController(controller, {quizController})
    controller.quizPersistence = new QuizPersistenceController(controller, {adapter})
    superchart.onApiReady(() => controller.replay?.init())
    controller.subscribeBarsLoaded(() => controller.quizPersistence?.applyPrev())
  },
})
```

React effects:

| Dep | Action |
|---|---|
| `coinraySymbol`             | `questionSync.syncSymbolToChart(coinraySymbol, resolution)` |
| `resolution`                | `questionSync.syncResolutionToChart(resolution)` |
| `question?.drawingMode`     | `quizPersistence.swapDrawings()` |
| `question?.id`              | `quizPersistence.reload()` |
| `[showHint, answer, preview.answer, mode]` | `quizPersistence.reload()` (preview/play only) |
| `keepPrevQuestionDrawings`  | `quizPersistence.applyPrev()` |
| `mode`                      | `setFeatureEnabled` for period_bar / symbol_search / period_picker / indicator_picker |

The `mountedRef` gate on every effect is critical — SC's own
`restoreChartState` runs on first mount via the storage adapter, so a
manually-fired `reload` on first mount would race/duplicate with it.

### 13.5 Touch hygiene

Two paths can mark a question touched:

1. **Adapter writes** — `adapter.save` calls `q.touch()` before
   `setQuestionStudies` (only when indicators actually changed by deep
   equality). Drawing setters (`setQuestionDrawings` etc.) handle their
   own touch internally and accept `{silent: true}` to skip it for
   adapter-driven bucket rewrites.
2. **Form actions** — direct user actions that bypass the adapter (e.g.
   removing a question's option from the form X-chip, the
   drawing-mode-picker clear button). These call `await question.touch()`
   before mutating.

The `[currentQuestion.touched]` effect in `edit-question.js` flips the
edit-mode UI on automatically when the first chart-driven mutation lands
(takes the user from overview → edit form without an explicit click).

### 13.6 Why imperative drawings (and not just `loadState`)

Three problems force the imperative path on `reload`:

1. **`sc.loadState` is additive** — does not clear existing drawings.
   Calling it repeatedly on question switch would accumulate.
2. **klinecharts tombstone bug** — `chart.createOverlay({id: justRemovedId})`
   silently fails for one tick after the remove. Reusing question-state
   ids on Reset (which removes-then-restores the same set) would lose
   half the overlays. Fresh UUIDs sidestep this entirely.
3. **No public `superchart.createIndicator(name, isStack?, paneOptions?)`**
   exists (only the modal-driven path). For host-driven indicator restore
   we still rely on `sc.loadState()` — which is fine because indicators
   don't suffer the tombstone bug and the load-override mechanism prevents
   duplication.

### 13.7 Open SC API gaps that influenced this design

Filed under `phase-7/sc/`:

- `bug-removeIndicator-modal-desync.md` — fixed upstream by SC commit
  `84cac1c` (modal now fires through the adapter natively; no monkey-patch
  needed in the consumer).
- `feature-setDrawingBarVisible.md` — runtime drawing-bar toggle (still
  pending; the consumer uses `drawingBarVisible` constructor option).
- Implicit: no public `superchart.createIndicator(...)` API. Mentioned
  above; not yet filed as a feature request because `loadState` covers
  the host-driven restore use case.
