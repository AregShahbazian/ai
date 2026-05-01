# Phase 7: Quiz System — Design & Implementation

Design choices for `prd.md` (`id: sc-quiz`).

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
  const resolutionOrSymbolChanged =
    question.coinraySymbol !== prevQuestion?.coinraySymbol ||
    question.resolution !== prevQuestion?.resolution
  const questionChanged = question.id !== prevQuestion?.id

  if (!questionChanged || resolutionOrSymbolChanged) {
    this.refreshRanges(false)
  }
}

refreshRanges = (single = true) => {
  const setRanges = () =>
    this.quizController.draw.setVisibleRange(this.question.visibleTimeRange)
  setRanges()
  if (!single) util.wait(500).then(setRanges)
}
```

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

## 11. Open questions (resolve during implementation)

1. **Where does `QuizSuperChartWidget` actually live?** Under
   `super-chart/quiz/` next to other SC variants, or under a new
   `super-chart/variants/` umbrella? Lean toward `super-chart/quiz/` for
   consistency — `super-chart/charts/`, `super-chart/preview/` already
   set the precedent.

2. **`Question.animationLengthCandles` exposure.** The candle count for
   `drawUntil` calls is already encoded in `question.questionStartTime`
   (which is `solutionStart - animationLengthCandles * resolutionMs`). The
   `drawUntil` helper computes count internally from `(target - now) /
   resolutionMs`. Confirm during implementation that no quiz UX cares
   about the exact computed count beyond the speed-ceiling check.

3. **`isResetting` state.** Old code had `isResetting` in the draw state
   shape. The new path uses `chartController.replay`'s status. Likely
   removable — verify no consumer reads it.

4. **Mobile-only price-time-select toast.** `useQuizHandlers` shows a
   "use long press" toast on mobile when starting price-time-select. The
   new `InteractionController` may need an equivalent hook, or the toast
   can stay on the quiz handler side. Verify.

5. **`refreshStudies` / `updateDrawingsTrigger` callsites in
   `Question.js`.** They become no-ops; double-check no quiz flow
   structurally breaks when they resolve immediately. (E.g. ordering
   between `refreshStudies` and `drawQuestion`.)

6. ~~**`QuizContextProvider` location.**~~ **Resolved** — provider moves
   to `containers/quizzes.js`, scoped to the `/quizzes` route only. The
   two cross-route consumers (`logged-in.js`'s dev-only `storeGlobal`
   call and `main-menu-mobile.js`'s play/preview hide check) are replaced
   per §1a (Redux flag) and the description in "Quiz module relocation
   + provider scoping". No regression on server-persisted quiz state
   (`openQuizResult`, answers, timings) — those reload from the backend
   on `/quizzes` re-entry. Ephemeral context state is recreated per
   mount, which is fine.
