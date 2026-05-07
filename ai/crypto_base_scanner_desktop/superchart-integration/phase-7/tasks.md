# Phase 7: Quiz System — Tasks

Tasks for `prd.md` (`id: sc-quiz`) + `design.md`.

Order matters: each task assumes the previous ones have landed.

✅ = done and merged into the working branch.

> **Status note.** Tasks 1–17 below are the original port. The persistence
> work (originally deferred — see initial `deferred.md`) was folded back in
> during implementation; tasks 18–22 below cover what was actually built
> for storage/persistence/prev-question drawings. See `design.md §13` for
> the full architecture.

---

## 1. TT decoupling — remove TT-side quiz remnants ✅

### 1.1 Delete `EditQuizQuestionWidget` + grid registration ✅

**Files:**
- Delete: `src/containers/trade/trading-terminal/widgets/edit-quiz-question-widget.js`
- Edit: `src/containers/trade/trading-terminal/grid-layout/grid-content.js`
  — remove `import EditQuizQuestionWidget from "../widgets/edit-quiz-question-widget"`
  and the `case "EditQuizQuestion"` branch.
- Edit: `src/actions/constants/layout.js` — remove the commented-out
  `// EditQuizQuestion: {...}` block (line 71 area).

**Verify:** no remaining reference to `EditQuizQuestion` /
`edit-quiz-question-widget` in `src/`. Open `/trade`, the widget picker no
longer shows "Edit Quiz Question".

### 1.2 Remove `EditQuizQuestion` translations ✅

**Files:**
- `src/locales/en/translation.yaml`, `nl/translation.yaml`,
  `es/translation.yaml` — remove the `widgets.EditQuizQuestion` keys.

**Verify:** grep `EditQuizQuestion` returns zero matches across `src/locales/`.

### 1.3 Drop quiz reads from TT chart code ✅

**Files:**
- `src/containers/trade/trading-terminal/widgets/center-view/tradingview.js`
  — drop `useContext(QuizContext)`, `useSelector(Selectors.inQuizzes)`,
  and the `(inQuizzes || editQuestionWidgetActive) ? questionController?.chartComponents : chartComponents`
  branch (use `chartComponents` directly).
- `src/containers/trade/trading-terminal/widgets/center-view/tradingview/header.js`
  — drop `useContext(QuizContext)` reads. `questionController.active` /
  `questionMode` checks for hide-Replay / hide-Alert in TV header are dead
  in TT — remove.
- `src/containers/trade/trading-terminal/widgets/center-view/tradingview/tradingview-component.js`
  — drop QuizContext + `inQuizzes` reads + the action-buttons gating that
  references quiz mode.
- `src/containers/trade/trading-terminal/widgets/center-view/tradingview/context/use-on-context-menu.js`
  — drop QuizContext reads + the "Set Solution Start/End" entries
  (block branched on `inQuizzes || editQuestionWidgetActive`).
- `src/containers/trade/trading-terminal/widgets/center-view/tradingview/context/use-trading-view.js`
  — drop `quizTvSetup`, `questionController?.tvSetup`, and the merge into
  the TV widget setup. The TV widget always starts with the standard
  configuration.

**Verify:** grep `tradingview/` and `tradingview-component` for
`QuizContext`, `inQuizzes`, `questionController`, `editQuestionWidgetActive`
returns zero matches. Open `/trade`, TT chart loads, Buy/Sell/Alert/Replay
header buttons all behave as before.

### 1.4 Drop quiz gates from SC TT chart context-menu controller ✅

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/controllers/context-menu-controller.js`

- Remove the `inQuizzes = Selectors.inQuizzes(state)` line.
- Remove the `&& !inQuizzes && !showQuizControls` predicates from the
  `showAlertOptions` and `showTradingOptions` checks.
- If `showQuizControls` is the only remaining false constant, remove its
  declaration too.

**Verify:** open `/trade`, right-click chart background — the menu still
shows trading / alert / replay entries unaffected.

### 1.5 Drop `inQuizzes` selector if unused ✅ (kept — still used inside /quizzes route for layout widths)

**File:** `src/util/selectors.js`
- After tasks 1.3 and 1.4, grep `Selectors.inQuizzes` and `pathIsInQuizzes`.
  If no consumer remains, delete both the selector entry and the
  `util.pathIsInQuizzes` helper.

**Verify:** grep returns zero matches; webpack still compiles.

---

## 2. Move quiz module out of TT folder ✅

### 2.1 Move quiz-context + use-quiz ✅

**Files:**
- Move `src/containers/trade/trading-terminal/quiz/quiz-context.js`
  → `src/containers/quizzes/quiz-context.js`.
- Move `src/containers/trade/trading-terminal/quiz/use-quiz.js`
  → `src/containers/quizzes/use-quiz.js`.
- Delete the (now-empty) `src/containers/trade/trading-terminal/quiz/` folder.

### 2.2 Drop `editQuestionWidgetActive` ✅

**File:** `src/containers/quizzes/quiz-context.js`
- Remove `editQuestionWidgetActive: false` from `QUIZZES_CONTEXT_SHAPE`.

**File:** `src/containers/quizzes/use-quiz.js`
- Remove the `editQuestionWidgetActive` selector + memo + return value.
- Remove `import {TradingLayoutSelectors} from ...` (no longer needed).

### 2.3 Update import paths ✅

**Files (anything that imports `QuizContext`, `QUESTION_MODES`,
`QUIZZES_*_STATE_SHAPE`, `QuizContextProvider`, or `useQuiz`):**
- `src/containers/logged-in.js` (will lose its imports entirely in 2.4 —
  but path-update only is the safe interim)
- `src/containers/quizzes.js`
- `src/containers/main-menu/main-menu-mobile.js` (will lose its import
  entirely in 2.5 — but path-update is the safe interim)
- All quiz-specific containers: `src/containers/quizzes/edit/*`,
  `src/containers/quizzes/play/*`, `src/containers/quizzes/preview/*`,
  `src/containers/quizzes/common/*`
- All quiz-specific models: `src/models/quiz/*`

Update the import paths from `~/containers/trade/trading-terminal/quiz/quiz-context`
to `~/containers/quizzes/quiz-context`. Same for `use-quiz`.

**Verify:** grep `trading-terminal/quiz/` returns zero matches in `src/`.
Open `/quizzes` — pages mount and `quizController` is reachable.

### 2.4 Move `QuizContextProvider` mount down to `/quizzes` ✅

Per `design.md` "Quiz module relocation + provider scoping". The provider
currently mounts in `logged-in.js`; both cross-route consumers
(`useAppGlobals` in `logged-in.js`, and `main-menu-mobile.js`) get
replaced (this task + 2.5), so the provider can scope to `/quizzes` only.

**File:** `src/containers/logged-in.js`
- Remove the `<QuizContextProvider>` wrapper (line 276 area) from the
  composition stack.
- Remove the `useContext(QuizContext)` call at line 79 inside
  `useAppGlobals`.
- Drop the `quizController` field from the `storeGlobal({...})` call at
  line 82 — `storeGlobal` is dev-only debug, no runtime consumer.
- Remove the `import {QuizContext, QuizContextProvider} from
  "./quizzes/quiz-context"` line entirely.

**File:** `src/containers/quizzes.js`
- Add `import {QuizContextProvider} from "./quizzes/quiz-context"` (or
  the relative import as appropriate).
- Wrap the rendered `/quizzes/*` umbrella in
  `<QuizContextProvider>...</QuizContextProvider>`. The exact placement:
  the outermost JSX returned from the route component. Anything inside
  `useContext(QuizContext)` (the existing reads in `containers/quizzes.js`
  itself) must be moved into a child component since hooks can't read a
  provider mounted by their own component — easiest: split the existing
  `Quizzes` body into a `<QuizContextProvider><QuizzesContent/>` pair.

**(Optional)** Re-register `quizController` on `window` for dev console
access by adding to `useQuiz`:
```js
useEffect(() => {
  if (process.env.NODE_ENV === "development") {
    window.quizController = quizController.current
  }
}, [])
```
or via the existing `storeGlobal({quizController: quizController.current})`
call. Skip this if dev console access isn't needed.

**Verify:** open `/trade` — no console errors about missing
`QuizContext`; `window.quizController` is `undefined` in dev (expected,
unless re-registered inside `useQuiz`). Open `/quizzes` — quiz works,
controller initialises, route navigation between quiz sub-routes works.

### 2.5 Replace mobile-menu QuizContext read with Redux selector ✅

Per `design.md` §1a. New Redux flag `state.quiz.activeQuestionMode`
maintained by `PlayController` / `PreviewController`, read by the mobile
menu via `QuizSelectors.selectIsInPlayOrPreview`.

**File:** `src/models/quiz/quiz-redux-controller.js`
- Add `activeQuestionMode: null` to `QuizReduxController.defaultState`.
- Add `static SET_ACTIVE_QUESTION_MODE = "SET_ACTIVE_QUESTION_MODE"`.
- Add `setActiveQuestionMode = async (activeQuestionMode) =>
  this.dispatchAction(QuizReduxController.SET_ACTIVE_QUESTION_MODE,
  {activeQuestionMode})`.
- Add to `QuizSelectors`:
  - `selectActiveQuestionMode: (state) => state.quiz.activeQuestionMode`
  - `selectIsInPlayOrPreview: (state) =>
    ["play", "preview"].includes(state.quiz.activeQuestionMode)`

**File:** `src/reducers/quiz.js` (or wherever the quiz reducer lives —
search for the reducer matching `state.quiz.userSettingsEnabled`)
- Add a case for `SET_ACTIVE_QUESTION_MODE` that writes
  `activeQuestionMode` from the action payload.

**File:** `src/models/quiz/play-controller.js`
- Inside `setQuestion` (or `loadQuestion`), after the state write, call
  `await this.reduxController.setActiveQuestionMode(question ? "play" : null)`.

**File:** `src/models/quiz/preview-controller.js`
- Same as Play, but with `"preview"`.

**File:** `src/models/quiz/quiz-controller.js` (or wherever
`destroy`/teardown lives)
- On controller teardown, call `setActiveQuestionMode(null)` so a stale
  value doesn't survive into unrelated routes.

**File:** `src/containers/main-menu/main-menu-mobile.js`
- Remove `import {QUESTION_MODES, QuizContext} from
  "../trade/trading-terminal/quiz/quiz-context"` (or the post-2.1 path).
- Remove `const {questionController} = useContext(QuizContext)`.
- Add `import {QuizSelectors} from "~/models/quiz/quiz-redux-controller"`.
- Replace the play/preview-mode check with:
  ```js
  const isInPlayOrPreview = useSelector(QuizSelectors.selectIsInPlayOrPreview)
  if (isInPlayOrPreview) return null
  ```

**Verify:** on mobile, navigate to `/quizzes/play/<id>` → bottom nav
hides as soon as a question loads. Navigate away (back button or quit) →
bottom nav reappears. Same for `/quizzes/preview/<id>`. On `/trade`,
`/dashboard`, `/markets` etc., bottom nav is always visible.

---

## 3. `DrawController` → `AnimationController` refactor ✅

> **As-built rename.** `DrawController` was renamed to `AnimationController`
> (`src/models/quiz/animation-controller.js`) and the `chartController`
> getter moved to `QuizController`. Reference field renamed from
> `quizController.draw` → `quizController.animation`. State shape and
> reducer keys (`draw`, `QUIZZES_DRAW_STATE_SHAPE`, `onSaveDrawState`)
> kept their names. The drawings/indicators no-op stubs originally listed
> in 3.3 below are gone — that work moved to the new persistence layer
> (tasks 18–22).

### 3.1 Strip TV-coupled surface ✅

**File:** `src/models/quiz/draw-controller.js`

Per `design.md` section 3:

- Remove fields: `tv`, `tradingViewPromise`, `tradingViewResolve`,
  `firstDrawnCandle`, `lastDrawnCandle`, `drawingCandlesId`, `waitMsOverride`.
- Remove methods: `loadTv`, `setTradingView`, `getDrawCandleCallback`,
  `firstDrawnCandleTime`, `lastDrawnCandleTime`, `drawCandles`,
  `setVisiblePriceRange`, `getCandlesVisiblePriceRange`,
  `getPaddedVisiblePriceRange`, `loadFirstCandleTime`, `lastCandle`,
  `firstCandleTime`, `getCandlesVisibleRange`, `getPaddedVisibleRange`,
  `subtractTimeInCandles` (move to `Question` if needed),
  `reloadTradingView`.

### 3.2 Add SC-driven candle reveal ✅

Per `design.md` section 3:

- Add `chartController` getter via `ChartRegistry`.
- Add `drawUntil(targetTime, totalCandles)` using
  `chartController.replay.playUntil` + `_waitUntilPaused()`.
- Refactor `overrideSpeed` to call `chartController.replay.play(newSpeed)`.
- Refactor `stopDrawing` to call `chartController.replay?.pause()`.
- Refactor `reset` to `await chartController.replay?.setCurrentTime(null)`.
- Refactor `setVisibleRange` to delegate to `chartController.setVisibleRange`
  (unix seconds).

### 3.3 Stub drawings/indicators methods as noops ✅ (later removed entirely)

Originally per `design.md` section 3 + 7 — added `// deferred (sc-quiz):`
no-op stubs to `DrawController`. **Later removed** during the persistence
work (tasks 18–22) since the real storage path replaced them. Cleaned up
in commit `ba984246` ("Quiz-TV code cleanup").

**Verify:** unit-grep that `animation-controller.js` has no `tv.` accesses,
no `onRealtimeCallback`, no `chart.createShape`, no `chart.removeEntity`.
Open `/quizzes/play/<some-quiz>`, animation triggers progressive reveal.

---

## 4. `QuestionController` base refactor ✅

**File:** `src/models/quiz/question-controller.js`

- Remove `tvSetup`, `chartComponents`, `saveLoadAdapter`,
  `loadFirstCandleTime`, `getInitialCandles`, `adjustCandleTime` getters /
  methods.
- Remove imports: `PriceTimeSelect`, `TradingViewEnhancements`.
- Keep: `questionMode`, `active`, `question`, `setQuestion`, `goTo`,
  `reloadQuiz`, `reloadQuestion`, `loadQuestion`, `questionsCanTransition`.

**Verify:** grep `tvSetup` / `chartComponents` returns zero matches in
quiz models. Quiz controllers still construct without errors.

---

## 5. `PlayController` refactor ✅

**File:** `src/models/quiz/play-controller.js`

- Remove `getInitialCandles` override.
- Remove `getGapCandles`.
- Replace `drawQuestion` body per `design.md` section 4 — drives
  `chartController.replay` directly.
- Remove imports: `PlayDrawings` (the chart-component reference), since
  `chartComponents` is gone from base.
- Remove the `saveLoadAdapter = new QuestionSaveLoadAdapter(...)` line —
  the adapter is no longer wired into the chart.

**Verify:** play a quiz with animation ON — candles reveal up to
`questionStart`, animate to `solutionStart`, pause; submit answer, animate
to `solutionEnd`. With animation OFF — candles cut to
`solutionStartNextCandle`.

---

## 6. `EditController` refactor ✅

**File:** `src/models/quiz/edit-controller.js`

- Remove `getInitialCandles` override.
- Remove `tvSetup` override.
- Remove `EditDrawings` import.
- Remove `saveLoadAdapter = new EditQuestionSaveLoadAdapter(...)` line.
- Rename `refreshTv` → `focusOnQuestion`. Drop `saveChartToServer` /
  `currentLayoutName` calls (the methods are no-ops anyway). Keep
  `refreshRanges` calling `chartController.setVisibleRange`.

**Verify:** open `/quizzes/edit/<id>`, change `questionStartTime` /
`solutionEnd` via sidebar buttons or bg context-menu; chart focuses on
the new range.

---

## 7. `PreviewController` refactor ✅

**File:** `src/models/quiz/preview-controller.js`

- Remove `chartComponents` override (`PreviewDrawings` import drops).
- Remove `saveLoadAdapter = new QuestionSaveLoadAdapter(...)` line.
- Replace `drawQuestion` body per `design.md` section 4.

**Verify:** open `/quizzes/edit/preview/<quizId>/<questionId>`, candles
animate to `questionStartTime`, no answer recorded.

---

## 8. Storage adapter no-ops ✅ (later replaced by real implementation)

Originally per `design.md` section 7 — replaced both classes with no-op
shells. **Superseded** by tasks 18–22 (real `QuizStorageAdapter`). The
`question-save-load-adapters.js` file was deleted in commit `ba984246`.

---

## 9. Quiz SC widget (`QuizSuperChartWidget`) ✅

### 9.1 Create the widget ✅

**File (new):** `src/containers/trade/trading-terminal/widgets/super-chart/quiz/quiz-super-chart.js`

Per `design.md` section 2:

- Mirror `ChartsPageChartWidget` / `PreviewSuperChartWidget` setup.
- Read `questionMode` from `QuizContext` (or take it as a prop).
- Pick `periodBarVisible` from mode (`true` for `new` / `edit`, `false`
  for `play` / `preview`).
- For `edit` / `new`: hide period-bar buttons we don't want via CSS
  (Indicators, Symbol search, Timezone, Screenshot, Fullscreen — leave
  Settings, Period picker stays for resolution change ability — confirm
  during impl whether this is desired).
- Add only the **Settings** custom button via
  `chartController.header.createButton`.
- Bg context-menu provider:
  - `edit` / `new` → `setSolutionStart`, `setSolutionEnd` entries.
  - `play` / `preview` → no quiz entries.
- Mount the per-mode overlay wrappers (edit-drawings / play-drawings /
  preview-drawings).

### 9.2 Rewire `QuizQuestionChart` ✅

**File:** `src/containers/quizzes/edit/quiz-question-chart.js`

Replace `<DefaultTradingWidget {...}/>` with `<QuizSuperChartWidget
{...}/>`. Remove `import {DefaultTradingWidget}`.

The handlers `handleTVSymbolChanged` / `handleTVIntervalChanged` are
renamed to `handleSymbolChanged` / `handleResolutionChanged` and wired
through SC's `onSymbolChange` / `onPeriodChange` exposed by
`chartController` (already shipped in Phase 1). Drop the `chartComponents`
prop (gone from controllers); drop `tvSetup` prop. Drop the
`MarketTabContext`-equivalent wiring from `QuizQuestionChart` to whatever
the SC variant expects (likely `marketTabId` + symbol/resolution props).

**Verify:** `/quizzes/edit/<id>` mounts the SC chart, period bar visible,
Settings button visible, no Alert/Buy/Sell, live ticks update latest
candle.

---

## 10. Port chart-bound quiz overlays ✅

### 10.1 `questions-timelines.js` (solution start/end vertical lines) ✅

**File (new):** `src/containers/trade/trading-terminal/widgets/super-chart/quiz/questions-timelines.js`

- Use `useDrawOverlayEffect` per overlay-architecture docs.
- Per-item overlay groups (`OverlayGroups.questionsTimelines-${id}-start`
  and `-end`) since multiple lines can coexist.
- Use `verticalStraightLine` overlay type via
  `chartController.createOverlay`.
- Source the time + colour from
  `question.solutionStart`/`solutionEnd` and `chartColors.quizSolutionStart`/
  `quizSolutionEnd` (color keys already exist for TV — reuse the keys,
  resolved through `chartController.colors`).

### 10.2 `decision-point-arrow.js` ✅

**File (new):** `src/containers/trade/trading-terminal/widgets/super-chart/quiz/decision-point-arrow.js`

- Time-anchored arrow at `question.solutionStart` (or wherever the
  decision-point is in the original).
- Use `simpleAnnotation` or a custom registered figure if needed.
- Single overlay group, redraws on `solutionStart` change.

### 10.3 Per-mode wrapper components ✅

**Files (new):**
- `src/containers/trade/trading-terminal/widgets/super-chart/quiz/edit-drawings.js`
- `src/containers/trade/trading-terminal/widgets/super-chart/quiz/play-drawings.js`
- `src/containers/trade/trading-terminal/widgets/super-chart/quiz/preview-drawings.js`

Pure JSX. Read `QuizContext` for question + mode, mount the relevant
overlay set:

- `edit` / `new` → `<QuestionsTimelines question/>` + `<DecisionPointArrow question/>`
- `play` → `<QuestionsTimelines question/>` + `<DecisionPointArrow question/>`
  (only when answered / showHint to match TV-prod behaviour)
- `preview` → `<QuestionsTimelines question/>` + `<DecisionPointArrow question/>`
  (when relevant)

The "auto-load saved drawings" / "save user drawings" logic that lived in
the TV equivalents is dropped — the methods on `DrawController` it called
are no-ops.

**Verify:** lines + arrow appear at correct time positions in edit/new/
play/preview modes.

---

## 11. Quiz controls (Set Solution Start/End) ✅

**File (new):** `src/containers/trade/trading-terminal/widgets/super-chart/quiz/quiz-controls.js`

Port from `tradingview/quiz/quiz-controls.js`:

- Two buttons: Set Solution Start, Set Solution End.
- "Refresh ranges" button.
- Uses `QuizContext.handlers.handleSelectQuestionTimeClick`.

The `useQuizHandlers` shims `startPriceTimeSelect` / `stopPriceTimeSelect`
(currently imported from `.../tradingview/price-time-select`) get
re-pointed to a new SC equivalent that registers with
`chartController.interactionController.consumePriceTime(...)` (the same
API Phase 5 wires for replay-start picking). The shims in
`use-quiz.js` may be replaced with direct `InteractionController` calls
or kept as a thin abstraction.

**Verify:** in edit mode, click "Set Solution Start" → click on chart →
solution start updates and timeline overlay redraws. Same for End.

---

## 12. Bg context-menu — Set Solution Start/End ✅

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/controllers/context-menu-controller.js`

Add the registration path (or extend its provider model) so that
`QuizSuperChartWidget` can supply per-mount entries when in `edit` /
`new` mode. The entries call the same handlers that the sidebar buttons
use.

**Verify:** in edit mode, right-click chart → "Set Solution Start" /
"Set Solution End" entries appear; clicking enters price-time-select
mode just like the sidebar button.

---

## 13. Question model cleanup ✅

**File:** `src/models/quiz/question.js`

### 13.1 Drawings/studies hooks → no-ops ✅

- `loadStudies`, `loadDrawings`, `refreshStudies`, `updateDrawingsTrigger`,
  `allDrawings` — these are read by the no-op adapter methods. Trim or
  no-op them so they never reach a TV API. Don't delete the methods if
  other code still imports them; just make them resolve to empty/undefined.
- `subtractTimeInCandles` (referenced in `Question.questionStartTime`
  computation) — keep, but inline the logic or import from a shared util
  rather than `DrawController` (which no longer exposes it).

### 13.2 Drop per-question candle storage ✅

Per `design.md` section 10. Backend still requires the `candles` field on
the create/update payload — we satisfy it by leaving `candles: []` in
`defaultMutableState` (which `Question.body` serialises). Frontend never
reads or fetches the stored candles.

- Delete `setCandles(candles)` setter (line ~383).
- Delete `candles` getter (line ~198).
- Delete `loadQuestionCandles()` method (lines ~640-648) including the
  `toast.warn(i18n.t("containers.quizzes.validation.noDataCouldBeFound"))`
  call. If that i18n key has no remaining consumer, drop it from all three
  YAML files.
- Remove the `if (!this.id) { await this.loadQuestionCandles(); if
  (!this.candles.length) return }` guard at the top of `submit()` (line
  ~606). `submit()` proceeds unconditionally after standard validation.
- Keep the `candles: []` entry in `defaultMutableState` so the body
  serialiser still sends `[]` to the backend.

**Verify:** edit-mode form fields that depend on `questionStartTime` show
correct values. Creating a brand-new question saves successfully without
the candle-load step (and the network payload contains `candles: []`).
Editing an existing question still saves cleanly.

---

## 14. Cleanup pass ✅

- Search for `MainChartTradingWidget`, `DefaultTradingWidget`,
  `GridBotTradingWidget`, `useTradingView`, `useTradingViewMarket`,
  `useReplay` references inside quiz-related files. None should remain
  after this phase.
- Search for `chart-functions`, `data-provider` imports inside quiz files.
  None should remain.
- Search for `LocalSaveLoadAdapter` imports in quiz files. None should
  remain.

**Verify:** webpack compiles. `/trade` and `/quizzes` both load. Quiz
edit, preview, and play modes all work end-to-end (full review-doc
checklist).

---

## 15. `ReplayController` quiz-facing engine delegates ✅

`quiz/play/preview/draw` controllers call engine methods directly on
`cc.replay` (bypassing the full `_startSession` flow). These were missing
from `ReplayController`'s public surface.

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js`

Added five thin delegates:
- `setCurrentTime(time, endTime)` → `_replayEngine.setCurrentTime`
- `getReplayCurrentTime()` → `_replayEngine.getReplayCurrentTime()`
- `getReplayStatus()` → `_replayEngine.getReplayStatus()`
- `onReplayStatusChange(cb)` → `_replayEngine.onReplayStatusChange(cb)`
- `playUntil(targetTime, speed)` → `_replayEngine.playUntil(targetTime, speed)`

These do NOT go through Redux session state — they're the raw engine
control surface that the quiz animation loop needs.

**Verify:** preview mode loads a question into replay at `questionStartTime`
without crashing on `setCurrentTime is not a function`. Play mode animation
runs and stops at the correct candle.

---

## 16. `QuestionSyncController` — quiz chart symbol/period sync ✅

**File (new):** `src/containers/trade/trading-terminal/widgets/super-chart/controllers/question-sync-controller.js`

Handles the two-way sync between the quiz question's `coinraySymbol`/`resolution`
state and what's loaded in SC. Also manages edit-mode VR focus after
symbol/period/question changes.

Key behaviours:

- `syncSymbolToChart(coinraySymbol, resolution)` — pushes state→chart (echo-guarded).
- `syncResolutionToChart(resolution)` — same for period-only changes.
- `_scheduleEditFocusAfterLoad()` — called from `_onChartSymbolChange` and
  `_onChartPeriodChange` (before the echo check, so it fires for both
  user-initiated and state-driven changes). Subscribes one-shot to
  `onVisibleRangeChange`; when SC resets the VR to latest candles after the
  load completes, intercepts that reset and re-applies `editFocusRange`.
- `focusEditQuestion()` — direct `setVisibleRange` for when the question
  identity changes but symbol/resolution is unchanged (chart already loaded,
  no VR change event needed).

Wired in `QuizChart` (`quiz-super-chart.js`):
- `useEffect([coinraySymbol])` → `syncSymbolToChart`
- `useEffect([resolution])` → `syncResolutionToChart`
- `useEffect([question?.id])` → `focusEditQuestion`

**Verify:** edit mode — change symbol or resolution → chart loads new data
and VR re-focuses on `editFocusRange` (not latest candle). Navigate between
questions with same symbol/resolution → VR re-focuses on new question's
`editFocusRange`. Editing timestamps on same question → no spurious VR reset.

---

## 17. `Question.editFocusRange` getter + Alt+R hotkey in edit mode ✅

**`Question.editFocusRange`** — handles partial timestamp state:
- Both set → delegates to `visibleTimeRange` (100% pad each side).
- Only one set → 50-candle window around the set timestamp.
- Neither set → `undefined` (falls through to SC's `resetView()`).

**`chart-reset-hotkey.js`** — module-level `alt+R` binding (ref-counted,
single binding across all chart instances). In quiz edit mode resolves via
`c.quizOverlays._quizController` and uses `editFocusRange` for the focus
target. Everywhere else delegates to `c._superchart.resetView()`.

**Verify:** alt+R in edit mode with both timestamps set → chart focuses on
the solution window. alt+R with only one timestamp set → 50-candle window
around it. alt+R with no timestamps → `resetView()` (latest candle). alt+R
in TT/CS/GridBot/charts → `resetView()` unaffected.

---

## 18. `QuizStorageAdapter` ✅

**File (new):** `src/models/quiz/quiz-storage-adapter.js`

See `design.md §13.2` for the full spec. Implements SC's `StorageAdapter`
shape (`load(key)` / `save(key, state)` / `delete(key)`); the `key`
argument is ignored — active question and mode are read from
`quizController` at call time.

Highlights:
- Mode-aware `load`: edit returns full bucket(s) by `drawingMode`;
  preview/play returns the gated subset (`questionDrawings + (showHint?
  hint : []) + (answer && !hideAnswer? solution : [])`).
- `save` is a no-op outside edit mode and during `_loading`. Drops
  `save: false` overlays defensively. Routes overlays to buckets matched
  by id; new ones default to `"question"`.
- Deep equality via `sameOverlays` (catches drag) and `sameIndicators`
  (ignores id, since SC reissues ids on every load).
- `setLoadIndicatorsOverride` / `setLoadOverlaysOverride` hooks let
  `quizPersistence.reload` feed `sc.loadState()` with only the new/
  changed indicators.
- Touches the question via `q.touch()` (dontSave) before `setQuestionStudies`
  so the form auto-switches to edit mode.

**Verify:** in edit mode, draw a trendline → stays after reload. Add an
indicator via the picker modal → `questionStudies` is set on the question
state. Switch question via the question switcher → previous question's
drawings/indicators replaced. Form auto-switches to edit mode after the
first chart-driven mutation.

---

## 19. `QuizPersistenceController` ✅

**File (new):** `src/containers/trade/trading-terminal/widgets/super-chart/controllers/quiz-persistence-controller.js`

See `design.md §13.3` for the full spec. Owns chart-side imperative
drawing/indicator application — the things `adapter.load` + autosave
cannot express on their own.

Methods:
- `swapDrawings()` — fires on `question.drawingMode` change. Reads chart's
  current overlays via `chart.getOverlays()` (NOT `adapter.current`),
  excludes prev-transient ids, removes everything else, recreates from the
  new bucket(s) with fresh UUIDs. Silent bucket writeback.
- `reload()` — full path used on question-id change and on Reset.
  Imperative drawing recreate (with fresh UUIDs to dodge the klinecharts
  tombstone bug) + surgical indicator diff via `sc.removeIndicator(name)`
  for removed/changed ones, plus `sc.loadState()` with override hooks
  feeding only `[...changed, ...added]`. Calls `_applyPrevDrawings()` at
  the end.
- `applyPrev()` / `_applyPrevDrawings()` — renders the previous question's
  drawings as transient overlays (`save: false, lock: true`). Mode gating:
  edit (sameMarketResolution), play (questionsCanTransition), preview
  (never). Skips work when sig unchanged → no flash on revisits.
- `clearBucket(mode)` — exposed for the form X-chip on
  `DrawingModePicker`.
- `removeIndicator(name)` / `removeOverlay(id)` — passthroughs for
  form-side actions.

**Verify:** switch buckets via picker → only drawings change, indicators
and prev overlays untouched. Reset → chart drawings rehydrate without
tombstoned ids; form NOT marked touched. Toggle "Keep prev question
drawings" → prev set appears/disappears live. Question switch in play
mode where transition rules pass → prev overlays linger; non-transitionable
switch → they don't.

---

## 20. `QuizChartController` ✅

**File (new):** `src/containers/trade/trading-terminal/widgets/super-chart/quiz-chart-controller.js`

`ChartController` subclass that holds `questionSync`, `quizOverlays`, and
`quizPersistence` references and disposes them in `dispose()`. The setup
callback in `quiz-super-chart.js` constructs each sub-controller (they
need `quizController`, which only the consumer has).

**Verify:** open `/quizzes`, `controllerRef.current.quizPersistence` is
defined; navigate away, no leaked subscriptions in dev tools.

---

## 21. Wire adapter + persistence in `QuizSuperChartWidget` ✅

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/quiz/quiz-super-chart.js`

Per `design.md §13.4`:

- `useMemo` the `QuizStorageAdapter` (one per mount).
- Pass it via `useChartLifecycle({superchartOptions: {storageAdapter,
  storageKey: "quiz", ...}})`.
- In `setup`, instantiate `QuestionSyncController`, `QuizOverlaysController`,
  `QuizPersistenceController`. Wire `superchart.onApiReady` →
  `replay.init()` and `subscribeBarsLoaded` → `quizPersistence.applyPrev()`.
- Effects (with `mountedRef` gate):
  - `[question?.drawingMode]` → `swapDrawings()`
  - `[question?.id]` → `reload()`
  - `[question?.showHint, question?.answer, preview?.answer, mode]` →
    `reload()` (preview/play only)
  - `[keepPrevQuestionDrawings]` → `applyPrev()`
  - `[mode]` → `setFeatureEnabled` for period_bar / symbol_search /
    period_picker / indicator_picker
- Replace CSS-based button hiding with SC `disabledFeatures` constructor
  option + `setFeatureEnabled` runtime calls. Period bar visibility,
  symbol/period lock, indicator-picker visibility, drawing-bar
  visibility all flow from `MODE_POLICY[mode]`.

**Verify:** edit existing question — period bar visible but symbol/period
disabled. New question — symbol/period editable. Play/preview — no header
or period bar. Drawing bar visible only in new/edit. Indicator picker
visible only in new/edit.

---

## 22. Form-side touch hygiene & UX polish ✅

Folded in alongside the storage work. Each item independently completes a
piece that storage relied on or surfaced.

- **`edit-question.js`** — `useEffect([currentQuestion.touched])` flips
  the edit-mode UI on automatically when the chart mutates the question
  (overview → edit form without an explicit click).
- **`question-fields.js`** — `await question.touch()` before form-X
  removal so the form marks touched.
- **`drawing-mode-picker.js`** — `onClear={!drawings.length ? undefined :
  ...}` to disable the X chip when the bucket is empty. Routes through
  `question.quizController.chartController?.quizPersistence.clearBucket`.
- **`multi-select.js`** — `disabled` derived as `disabled || !hasOptions`
  so an empty MultiSelect doesn't spawn an empty popup on click.
- **`edit-quiz-modal.js`** — `QuizPublished` takes `quizController` as a
  prop (modal renders outside `QuizContextProvider`); add `onToggle` to
  the publish-success modal.
- **`fa-marker-overlay.js`** — extended `createPointFigures` to render a
  second text figure when `extendData.label` is provided, positioned
  above the glyph. `decision-point-arrow.js` uses this to show "Decision
  point" above the FA arrow-down glyph anchored at `bar.high`.
- **`decision-point-arrow.js`** — subscribes to `subscribeBarsLoaded` and
  bumps a `barsTick` state in the `useDrawOverlayEffect` deps so the
  arrow re-fires after data lands (fixes initial-mount race where
  `getDataList()` was empty).
- **`play-controller.drawQuestion`** — both `drawUntil` calls now target
  `animEnd = (!hideAnswer && answer) ? solutionEnd : solutionStart`, so
  loading an already-answered question animates to `solutionEnd` instead
  of stopping at `solutionStart`. (Fixed in commit `7cfd01da`.)
- **`edit-controller.reload({noFocus})`** — threads through `loadQuestion`
  → `focusOnQuestion` so the Reset path doesn't retrigger a VR jump on
  the still-active question.
