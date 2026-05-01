# Phase 7: Quiz System — Tasks

Tasks for `prd.md` (`id: sc-quiz`) + `design.md`.

Order matters: each task assumes the previous ones have landed.

---

## 1. TT decoupling — remove TT-side quiz remnants

### 1.1 Delete `EditQuizQuestionWidget` + grid registration

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

### 1.2 Remove `EditQuizQuestion` translations

**Files:**
- `src/locales/en/translation.yaml`, `nl/translation.yaml`,
  `es/translation.yaml` — remove the `widgets.EditQuizQuestion` keys.

**Verify:** grep `EditQuizQuestion` returns zero matches across `src/locales/`.

### 1.3 Drop quiz reads from TT chart code

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

### 1.4 Drop quiz gates from SC TT chart context-menu controller

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/controllers/context-menu-controller.js`

- Remove the `inQuizzes = Selectors.inQuizzes(state)` line.
- Remove the `&& !inQuizzes && !showQuizControls` predicates from the
  `showAlertOptions` and `showTradingOptions` checks.
- If `showQuizControls` is the only remaining false constant, remove its
  declaration too.

**Verify:** open `/trade`, right-click chart background — the menu still
shows trading / alert / replay entries unaffected.

### 1.5 Drop `inQuizzes` selector if unused

**File:** `src/util/selectors.js`
- After tasks 1.3 and 1.4, grep `Selectors.inQuizzes` and `pathIsInQuizzes`.
  If no consumer remains, delete both the selector entry and the
  `util.pathIsInQuizzes` helper.

**Verify:** grep returns zero matches; webpack still compiles.

---

## 2. Move quiz module out of TT folder

### 2.1 Move quiz-context + use-quiz

**Files:**
- Move `src/containers/trade/trading-terminal/quiz/quiz-context.js`
  → `src/containers/quizzes/quiz-context.js`.
- Move `src/containers/trade/trading-terminal/quiz/use-quiz.js`
  → `src/containers/quizzes/use-quiz.js`.
- Delete the (now-empty) `src/containers/trade/trading-terminal/quiz/` folder.

### 2.2 Drop `editQuestionWidgetActive`

**File:** `src/containers/quizzes/quiz-context.js`
- Remove `editQuestionWidgetActive: false` from `QUIZZES_CONTEXT_SHAPE`.

**File:** `src/containers/quizzes/use-quiz.js`
- Remove the `editQuestionWidgetActive` selector + memo + return value.
- Remove `import {TradingLayoutSelectors} from ...` (no longer needed).

### 2.3 Update import paths

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

### 2.4 Move `QuizContextProvider` mount down to `/quizzes`

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

### 2.5 Replace mobile-menu QuizContext read with Redux selector

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

## 3. `DrawController` refactor

### 3.1 Strip TV-coupled surface

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

### 3.2 Add SC-driven candle reveal

Per `design.md` section 3:

- Add `chartController` getter via `ChartRegistry`.
- Add `drawUntil(targetTime, totalCandles)` using
  `chartController.replay.playUntil` + `_waitUntilPaused()`.
- Refactor `overrideSpeed` to call `chartController.replay.play(newSpeed)`.
- Refactor `stopDrawing` to call `chartController.replay?.pause()`.
- Refactor `reset` to `await chartController.replay?.setCurrentTime(null)`.
- Refactor `setVisibleRange` to delegate to `chartController.setVisibleRange`
  (unix seconds).

### 3.3 Stub drawings/indicators methods as noops

Per `design.md` section 3 + 7. Add `// deferred (sc-quiz):` comment to each.

**Verify:** unit-grep that `draw-controller.js` has no `tv.` accesses, no
`onRealtimeCallback`, no `chart.createShape`, no `chart.removeEntity`.
Open `/quizzes/play/<some-quiz>`, animation triggers progressive reveal.

---

## 4. `QuestionController` base refactor

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

## 5. `PlayController` refactor

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

## 6. `EditController` refactor

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

## 7. `PreviewController` refactor

**File:** `src/models/quiz/preview-controller.js`

- Remove `chartComponents` override (`PreviewDrawings` import drops).
- Remove `saveLoadAdapter = new QuestionSaveLoadAdapter(...)` line.
- Replace `drawQuestion` body per `design.md` section 4.

**Verify:** open `/quizzes/edit/preview/<quizId>/<questionId>`, candles
animate to `questionStartTime`, no answer recorded.

---

## 8. Storage adapter no-ops

**File:** `src/models/quiz/question-save-load-adapters.js`

Replace both classes with the no-op shells from `design.md` section 7.
Drop the `LocalSaveLoadAdapter` import. Keep the same export names so
nothing else has to change.

**Verify:** open edit mode, attempt to save a layout → no error, no save
happens silently. Documented in `deferred.md`.

---

## 9. Quiz SC widget (`QuizSuperChartWidget`)

### 9.1 Create the widget

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

### 9.2 Rewire `QuizQuestionChart`

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

## 10. Port chart-bound quiz overlays

### 10.1 `questions-timelines.js` (solution start/end vertical lines)

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

### 10.2 `decision-point-arrow.js`

**File (new):** `src/containers/trade/trading-terminal/widgets/super-chart/quiz/decision-point-arrow.js`

- Time-anchored arrow at `question.solutionStart` (or wherever the
  decision-point is in the original).
- Use `simpleAnnotation` or a custom registered figure if needed.
- Single overlay group, redraws on `solutionStart` change.

### 10.3 Per-mode wrapper components

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

## 11. Quiz controls (Set Solution Start/End)

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

## 12. Bg context-menu — Set Solution Start/End

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/controllers/context-menu-controller.js`

Add the registration path (or extend its provider model) so that
`QuizSuperChartWidget` can supply per-mount entries when in `edit` /
`new` mode. The entries call the same handlers that the sidebar buttons
use.

**Verify:** in edit mode, right-click chart → "Set Solution Start" /
"Set Solution End" entries appear; clicking enters price-time-select
mode just like the sidebar button.

---

## 13. Question model cleanup

**File:** `src/models/quiz/question.js`

### 13.1 Drawings/studies hooks → no-ops

- `loadStudies`, `loadDrawings`, `refreshStudies`, `updateDrawingsTrigger`,
  `allDrawings` — these are read by the no-op adapter methods. Trim or
  no-op them so they never reach a TV API. Don't delete the methods if
  other code still imports them; just make them resolve to empty/undefined.
- `subtractTimeInCandles` (referenced in `Question.questionStartTime`
  computation) — keep, but inline the logic or import from a shared util
  rather than `DrawController` (which no longer exposes it).

### 13.2 Drop per-question candle storage

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

## 14. Cleanup pass

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
