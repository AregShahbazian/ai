---
id: sc-quiz
---

# Phase 7: Quiz System (SuperChart port)

Port the quiz/training system from TradingView to SuperChart, replacing the
TV-specific candle-gating + drawing-loop hacks with a thin layer on top of the
already-shipped Phase 5 replay engine. All current functionality is preserved.
Persistence-side hacks (drawings/indicators capture/restore, per-question chart
layouts) are out of scope for this PRD — see `deferred.md`.

## Quiz lives only at `/quizzes`

The original quiz design briefly considered a Trading-Terminal widget for
creating / playing / previewing questions. That direction was dropped, but
remnants of it still sit in TT-side code. As part of this PRD, those remnants
are removed: quiz only mounts under the `/quizzes` route, never inside TT.

## Why now

Phase 5 shipped `chartController.replay` (wrapping `sc.replay`). Its public
surface (`setCurrentTime`, `playUntil`, `step`, `pause`,
`getReplayCurrentTime`, `getReplayBufferLength`) is exactly the candle gating +
progressive reveal that quiz needs. With Phase 5 in place, quiz can drop:

- the `DataProvider` `getInitialCandles` `maxCandleTime` filter,
- the `DataProvider` `subscribeBars` no-op-during-quiz hack,
- the `DrawController.drawCandles` manual `onRealtimeCallback` loop with
  `wait(1000/speed)` between candles,
- the `tradingViewPromise` / `loadTv()` ready-gate plumbing inside
  `DrawController`.

Quiz logic, UX, sidebar layout, multiple-choice answer flow, transition
eligibility rules, agree/disagree feedback, and quiz-result persistence all
stay identical to prod.

---

## Scope

### In scope

- **Remove TT-side quiz remnants** (see "TT decoupling" section below).
- Drive candle gating + progressive reveal for **play** and **preview** modes
  via `chartController.replay` (`sc.replay`).
- **Edit mode**: live SuperChart with the existing live-tick subscription
  (no replay session). Sidebar buttons + bg context-menu entries to set
  `solutionStart` / `solutionEnd` via SC `InteractionController` price-time
  selection.
- Port all chart-bound quiz overlays: `questions-timelines` (solutionStart /
  solutionEnd vertical lines), `decision-point-arrow`,
  `edit-drawings` / `play-drawings` / `preview-drawings` wrapper components.
- Replace `DefaultTradingWidget` in `containers/quizzes/edit/quiz-question-chart.js`
  with a SC equivalent patterned after `ChartsPageChartWidget` /
  `GridBotSuperChartWidget`.
- Hide period-bar in play/preview via `superchart.setPeriodBarVisible(false)`.
- Header policy on the quiz SC widget, built into the widget config (not
  toggled at runtime via path selectors), analogous to
  `ChartsPageChartWidget` / `GridBotSuperChartWidget` /
  `PreviewSuperChartWidget`:
  - **Edit / New mode** — header visible. Only **Settings** is shown.
    Alert / Buy / Sell are not present at all. Replay is also hidden for
    now and will appear once the deferred "default replay session in edit
    mode" lands.
  - **Play / Preview mode** — header is entirely hidden (no header bar,
    no buttons of any kind).
- Period-bar policy on the quiz SC widget:
  - **Edit / New** — period bar visible.
  - **Play / Preview** — period bar hidden via
    `superchart.setPeriodBarVisible(false)` (or `periodBarVisible: false`
    constructor option, since the policy is static per mode).
- Bg chart context-menu: add `setSolutionStart` / `setSolutionEnd` entries
  (Phase 4a explicitly deferred these to Phase 7).
- Question transitions (same / different symbol/resolution) reusing the same
  symbol/period/reset call ordering Trading Terminal and Phase 5 already use
  — quiz controllers do not introduce a parallel orchestration.

### Out of scope (see `deferred.md`)

- Default replay session enabled in quiz edit mode (live chart without
  latest-candle live-tick subscription).
- Capturing user drawings / indicators in edit mode.
- Auto-loading saved drawings / indicators on enter edit / play / preview.
- `QuestionSaveLoadAdapter` / `EditQuestionSaveLoadAdapter` real
  implementation (StorageAdapter port — Phase 6).
- Per-question chart layout naming (`saveChartToServer` / `currentLayoutName`).
- `tradingview-enhancements.js` floating-toolbar drawing buttons (already on
  `SUPERCHART_BACKLOG.md`).

### Non-requirements

- The y-axis is **not** locked during animated reveal. SC will auto-fit. This
  is a deliberate behaviour deviation from TV (which used
  `setVisiblePriceRange`) — accepted to keep the port small. Re-evaluate
  during the review round if it visibly degrades the experience.
- Quiz controllers do not own symbol / resolution change orchestration —
  they push intent through the same `MarketTab` / `chartController` pipeline
  TT uses. Sequencing across `setCurrentTime(null) → setSymbol/setPeriod →
  setCurrentTime(newStart)` reuses the Phase 5 pattern verbatim.

---

## TT decoupling — remnants to remove

These exist because of the dropped "edit a quiz question inside TT" idea.
They must be deleted as part of the port. After this PRD ships, no TT code
reads `QuizContext`, `inQuizzes`, `editQuestionWidgetActive`, or
`questionController?.tvSetup`.

### Files to delete

| Path | Reason |
|---|---|
| `containers/trade/trading-terminal/widgets/edit-quiz-question-widget.js` | The TT-FlexLayout widget that was supposed to host the quiz-question editor inside TT. Mounts `QuizQuestionEditLoader` with `withChart={false}` and forces a TV reload via `quizController.draw.reloadTradingView()`. |

### Files to edit

| Path | Edit |
|---|---|
| `containers/trade/trading-terminal/grid-layout/grid-content.js` | Remove the `EditQuizQuestion` case + `EditQuizQuestionWidget` import. |
| `actions/constants/layout.js` | Remove the commented-out `EditQuizQuestion: { ... }` widget block (line 71). |
| `locales/en/translation.yaml`, `locales/nl/translation.yaml`, `locales/es/translation.yaml` | Remove `widgets.EditQuizQuestion.*` entries. |
| `containers/trade/trading-terminal/quiz/quiz-context.js`, `use-quiz.js` | **Move** to `containers/quizzes/` (location-only — no TT-coupling justifies their current placement). Drop the `editQuestionWidgetActive` field from `QUIZZES_CONTEXT_SHAPE` and stop reading `TradingLayoutSelectors.selectWidgetIsActive(state, "EditQuizQuestion")` in `useQuiz`. |
| `containers/trade/trading-terminal/widgets/center-view/tradingview.js` | Drop `useContext(QuizContext)`, `useSelector(Selectors.inQuizzes)`, `(inQuizzes \|\| editQuestionWidgetActive) ? questionController?.chartComponents : chartComponents` branch. |
| `containers/trade/trading-terminal/widgets/center-view/tradingview/header.js` | Drop `useContext(QuizContext)` reads; quiz-mode header-button gating moves to the quiz SC widget itself. |
| `containers/trade/trading-terminal/widgets/center-view/tradingview/tradingview-component.js` | Drop `QuizContext` reads + `inQuizzes` selector; the chart-frame gating that branched on quiz mode is dead in TT. |
| `containers/trade/trading-terminal/widgets/center-view/tradingview/context/use-on-context-menu.js` | Drop `QuizContext` reads + the `setSolutionStart` / `setSolutionEnd` TV-chart entries. Those entries live only on the quiz SC widget's bg context menu now. |
| `containers/trade/trading-terminal/widgets/center-view/tradingview/context/use-trading-view.js` | Drop `quizTvSetup` merging. TV widget never receives quiz-mode disabled features. |
| `containers/trade/trading-terminal/widgets/super-chart/controllers/context-menu-controller.js` | Drop the `inQuizzes` and `showQuizControls` gates (lines ~285, 304-305). Quiz-mode trading/alert hiding moves into the quiz SC widget config (analogous to grid-bot / charts-page / settings-preview variants), not into a path-based feature flag. |
| `util/selectors.js` | Drop the `inQuizzes` path-based selector if no remaining consumer exists after the edits above. (`util.pathIsInQuizzes` may still be used elsewhere — check before removing.) |
| `containers/quizzes/edit/quiz-question-chart.js` | The handlers `handleTVSymbolChanged` / `handleTVIntervalChanged` are renamed and re-wired to the SC widget's symbol/period change callbacks (already exposed by `chartController` via `onSymbolChange` / `onPeriodChange`). |

### Files that stay (quiz lives at `/quizzes` — these are quiz-route consumers, NOT TT)

- `containers/logged-in.js` — keeps `QuizContextProvider` as a top-level wrapper so `/quizzes` routes have it.
- `containers/quizzes.js` — `useContext(QuizContext)` here is fine (it's the quiz route entry).
- `containers/main-menu/main-menu-mobile.js` — reads `questionController` to alter mobile menu while a quiz is being played; this is a /quizzes-aware concern but the menu itself isn't TT-coupled. Keep.

---

## Replay-engine mapping (TV → SC)

| TV mechanism | SC replacement |
|---|---|
| `getInitialCandles({maxCandleTime})` filter to T | `chartController.replay.setCurrentTime(T)` — engine fetches history up to T, builds buffer T..now, isolates live data |
| `DataProvider.subscribeBars` skips WebSocket during quiz | Engine isolates live data automatically while session active |
| `DrawController.drawCandles` manual `onRealtimeCallback` loop | `chartController.replay.playUntil(targetTime, candlesPerSec)` — auto-pauses at target |
| `setVisibleRange` to lock x-axis | `superchart.setVisibleRange({from, to})` (unix seconds) |
| `setVisiblePriceRange` to lock y-axis | **Dropped.** |
| `datafeed.resetAllData()` + `chart.resetData()` between questions | `setCurrentTime(null)` then `setSymbol`/`setPeriod` then `setCurrentTime(newQuestionStart)` |
| `lastDrawnCandleTime` for resume / gap calculation | `chartController.replay.getReplayCurrentTime()` |
| `MAX_DRAWING_SPEED = 80 cps` cap on transition feasibility | Same cap — feeds into `playUntil(_, speed)` |
| `tvWidget.disabled_features: ["header_widget","timeframes_toolbar"]` for play/preview | `superchart.setPeriodBarVisible(false)` |
| `tvSetup.load_last_chart: !active` to skip layout restore | Storage wiring (deferred) |
| `getAllShapes` / `deleteShape` / `createStudy` / `removeStudies` | Noop placeholders on `DrawController` (deferred) |
| `tvWidget.saveChartToServer` / `tvWidget.layoutName` | Noop placeholders on `DrawController` (deferred) |
| `QuestionSaveLoadAdapter` / `EditQuestionSaveLoadAdapter` | Noop placeholders (deferred) |

**Animation speed mid-flight.** `setSpeed(s)` calls
`chartController.replay.play(s)` if the engine status is `playing`. SC's
engine treats `play(newSpeed)` while already playing as an in-place speed
update — the status callback does not re-fire. The TV-era `waitMsOverride`
indirection in `DrawController` is removed.

---

## Question-mode flows

### Play / Preview, animation ON, first question

1. `setCurrentTime(questionStartTime)` — chart shows candles up to
   `questionStartTime`; SC builds the replay buffer for `[questionStartTime,
   now]`.
2. `playUntil(solutionStart, computedSpeed)` — animate gap candles up to the
   decision point. Engine auto-pauses at target.
3. Wait for the user to submit an answer.
4. On submit: `playUntil(solutionEnd, computedSpeed)` — animate the solution
   reveal. Engine auto-pauses at target.

### Play / Preview, animation OFF

1. If unanswered → `setCurrentTime(solutionStartNextCandleTime)`.
2. If answered & solution shown → `setCurrentTime(solutionEnd)`.
3. No `playUntil` calls.

### Question transition (same symbol/resolution, transitionable)

The "transitionable" predicate is unchanged from TV
(`question-controller.js: questionsCanTransition`): same `coinraySymbol`,
same `resolution`, prev question answered (play mode), `solutionEnd <
nextSolutionStart`, correct order, gap animatable within `MAX_DRAWING_SPEED`.

1. After prev question's `solutionEnd` is drawn,
   `playUntil(nextQuestionStart, gapSpeed)`.
2. Then continue per the first-question flow above for the new question, but
   without the initial `setCurrentTime` (already in a session).

### Question transition (different symbol/resolution OR not transitionable)

Reuses the Phase-5 reset sequence used by replay restart on resolution
change:

1. `setCurrentTime(null)` — exit replay session.
2. `setSymbol(newSymbol)` and/or `setPeriod(newPeriod)` — pushed through the
   same `MarketTab` / `chartController` pipeline TT uses on tab switch.
3. `setCurrentTime(newQuestionStart)` — open a new session.
4. Per the first-question flow above.

### Edit mode

- Chart fully LIVE. No replay session.
- `chartController.setVisibleRange` to focus on `questionStartTime` /
  `solutionEnd` when the user edits those fields (the existing
  `EditController.refreshRanges` logic carries over, calling SC's
  `setVisibleRange` instead of `chart.setVisibleRange`).

---

## Component-level changes

| Current file | Phase 7 change |
|---|---|
| `models/quiz/draw-controller.js` | Refactor: candle drawing delegates to `chartController.replay`. Drawings/indicators/saveChart/layoutName methods become noops with `// deferred:` markers. Drop `tradingViewPromise` / `loadTv()` / `setTradingView`. Drop `setVisiblePriceRange`. Drop `waitMsOverride`. |
| `models/quiz/question-controller.js` | Drop `tvSetup`, `chartComponents`, `saveLoadAdapter`. Replace `getInitialCandles` (TV-datafeed contract) with the controller-level `setCurrentTime`/`playUntil` calls invoked from PlayController/EditController/PreviewController. |
| `models/quiz/play-controller.js` | Refactor `drawQuestion`: replace `getGapCandles` + `drawCandles` loop with `playUntil`. Replace `getInitialCandles` with `setCurrentTime` call. Keep `questionsCanTransition` logic verbatim. |
| `models/quiz/edit-controller.js` | Refactor `refreshTv`: drop `saveChartToServer` / `currentLayoutName` (deferred). Keep `refreshRanges` using `chartController.setVisibleRange`. Drop `getInitialCandles` override. |
| `models/quiz/preview-controller.js` | Refactor `drawQuestion`: replace draw-loop with `setCurrentTime(questionStartTime)`. |
| `models/quiz/question-save-load-adapters.js` | Adapter classes become noop placeholders (real impl deferred to Phase 6). |
| New `super-chart/quiz/questions-timelines.js` | Port from TV — `verticalStraightLine` overlays via `chartController.createOverlay` for solutionStart / solutionEnd lines. Reuse `useDrawOverlayEffect` per overlay-architecture docs. |
| New `super-chart/quiz/decision-point-arrow.js` | Port from TV — time-anchored overlay at decision point. |
| New `super-chart/quiz/quiz-controls.js` | Port from TV — Set Solution Start/End sidebar buttons. Re-wire `startPriceTimeSelect` / `stopPriceTimeSelect` (currently called from `containers/trade/trading-terminal/quiz/use-quiz.js`) to the SC `InteractionController` consumer pattern (same one Phase 5 uses for replay-start picking). |
| New `super-chart/quiz/edit-drawings.js`, `play-drawings.js`, `preview-drawings.js` | Port the per-mode wrapper components that compose chart-mode-specific overlays. The drawings-capture / auto-load logic inside them becomes noops with `// deferred:` markers. |
| `containers/quizzes/edit/quiz-question-chart.js` | Replace `DefaultTradingWidget` with a SC equivalent patterned after `ChartsPageChartWidget` / `GridBotSuperChartWidget`. |
| `containers/quizzes/play/play-question.js`, `preview/preview-question.js` | No structural change — still mount `QuizQuestionChart`. |
| New `super-chart/quiz/quiz-super-chart.js` (or whatever the variant is named) | The quiz SC widget. Mirrors `ChartsPageChartWidget` / `PreviewSuperChartWidget` in shape. Per-mode policy: **edit / new** — header visible with **Settings only** (no Alert / Buy / Sell; Replay added later when the deferred edit-mode replay session lands), period bar visible, bg context-menu shows `setSolutionStart` / `setSolutionEnd`; **play / preview** — header entirely hidden, period bar hidden, no quiz bg-menu entries. No path-based gating — the widget config IS the gate. Used by `QuizQuestionChart`. |

`QuizContext` shape, `useQuiz`, `QuizContextProvider`, the full sidebar layout
in `containers/quizzes/play/`, quiz-result persistence, agree/disagree
feedback, hint reveal, skip handling, and quiz-categories/random-quiz logic
are all unchanged.

---

## Verification

> **Review-round flag.** The SC replay engine has its own time-travel
> semantics (`getReplayCurrentTime()` returns the close time of the last
> visible candle, not its start; partial-candle exception when the cursor
> lands mid-period; one-candle trigger-timing offset documented in
> `phase-5/deferred.md → trigger-timing-offset/`). Whether these line up
> with what TV-prod quiz did at every quiz timestamp boundary
> (`questionStart`, `solutionStart`, `solutionEnd`, gap-candle `from/to`,
> `lastDrawnCandleTime` reads, `solutionStartNextCandleTime`) is a
> **review-phase evaluation**, not a design assumption — the review must
> walk every comparison and document any divergence. Diverging semantics
> are not blockers for the port itself, but must be enumerated.

### Functional checklist

1. **Edit mode** — open a question, scrub start/solution times via sidebar
   buttons + bg context menu; confirm chart focuses correctly via
   `setVisibleRange`; confirm no replay session is active and live ticks
   update the latest candle.
2. **Play mode, animation ON, single question** — candles reveal up to
   `questionStart`, animate to `solutionStart`, pause; submit answer,
   animate to `solutionEnd`.
3. **Play mode, animation OFF** — candles cut to `solutionStartNextCandle`
   (or `solutionEnd` if answered), no animation.
4. **Question transition (same symbol/resolution, gap < 80 cps)** — smooth
   `playUntil` from prev `solutionEnd` → next `questionStart`; no chart
   reset, no flicker.
5. **Question transition (diff symbol/resolution OR gap > 80 cps)** — hard
   reset via `setCurrentTime(null)` + `setSymbol`/`setPeriod` + new session;
   chart catches up correctly.
6. **Preview mode** — mirrors play mode but is non-persistent (no answer
   recording, no quiz-result mutations).
7. **Header (edit / new)** — header bar visible; the **only** button is
   Settings. No Alert, no Buy, no Sell; no Replay yet (added once the
   deferred edit-mode replay session lands).
8. **Header (play / preview)** — header bar entirely hidden. No buttons of
   any kind.
9. **Period bar** — visible in edit/new, hidden in play/preview. Configured
   statically on the widget, not toggled at runtime by a path selector. The
   TT chart is unchanged because TT no longer reads `QuizContext`.
10. **Drawings / indicators noop verification** — confirm edit mode does not
    crash when toolbar drawings are enabled; user can draw locally but
    drawings vanish on reload (documented in `deferred.md`); no exception
    thrown by `getAllShapes`/`createStudy`/`saveChartToServer` calls.
11. **Speed control** — change speed via sidebar mid-animation; engine
    speed updates in place without re-firing the status callback.
12. **Hint reveal** — toggle hint while a solution is in progress / drawn;
    chart overlays update without disrupting the replay session.
13. **Skip / answer-back** — skip a question, then return; chart re-enters
    correct mode (cut vs. animate) based on `answer` / `hideAnswer` flags.

### TT-decoupling regression checks

Quiz now lives only at `/quizzes`. TT must keep working with no quiz code
path. Verify:

14. **TT renders with no `QuizContext` reads in its tree** — grep
    `tradingview/` and `super-chart/` after the port; no `QuizContext`,
    `inQuizzes`, `editQuestionWidgetActive`, or `questionController?.tvSetup`
    references remain in TT-side code.
15. **`EditQuizQuestion` widget is gone** — `grid-content.js` no longer
    references it, the i18n entries are removed, and the widget file is
    deleted; layouts that previously referenced it (if any) fall through to
    `UnknownWidget` with no crash.
16. **TT chart background context menu in `/trade`** — no
    `setSolutionStart` / `setSolutionEnd` entries; the bg menu only shows
    trading / alerts / replay options as before.
17. **/quizzes route in isolation** — open `/quizzes` directly without
    visiting `/trade` first; the quiz SC widget mounts cleanly, header /
    period-bar / bg-menu policies all match the widget config.

### Quiz mode + symbol/resolution changes (per `~/ai/workflow.md`)

18. **Changing the question's coinraySymbol mid-edit** — in edit mode,
    change the question's symbol; quiz controllers push the change through
    the same MarketTab/chartController pipeline TT uses (no parallel
    orchestration).
19. **Changing the question's resolution mid-edit** — same pipeline; the
    Phase-5 `setCurrentTime(null) → setPeriod → setCurrentTime(newStart)`
    ordering applies (this is moot in edit mode since no replay session is
    active here, but the in-pipeline order should still hold).
20. **Two consecutive play questions on the same TradingTab-equivalent
    tab** — the SC quiz widget instance reuses cleanly across questions
    without re-mounting the chart.
