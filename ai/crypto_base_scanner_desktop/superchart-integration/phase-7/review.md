# Phase 7: Quiz System — Review

User-visible verification for `prd.md` (`id: sc-quiz`) +
`design.md` + `tasks.md`. Only items observable in the UI.

---

## Round 1: Initial implementation

### Verification

#### Time-travel semantics (visual comparison vs. TV-prod)

The SC replay engine has its own current-time semantics:
`getReplayCurrentTime()` is the **close** time of the last visible candle
(not its start), partial candles appear when the cursor lands mid-period,
and there's a known one-candle trigger-timing offset. The quiz code feeds
quiz timestamps into `setCurrentTime` and `playUntil`. Walk every
boundary visually:

1. **Animated reveal stops at the right spot (play, animation ON).**
   Open a play question whose `solutionStart` is `2025-09-15 14:00` on a
   1H chart. After the animation pauses, hover the last visible candle —
   its open time should be `13:00` and close time `14:00`. The "current
   time" shown in any timeline overlay should read `14:00`. If the engine
   stops one candle early (last candle reads `12:00–13:00`) or one candle
   late (last reads `14:00–15:00`), flag it.
2. **Solution reveal stops at the right spot (play, post-answer).**
   Submit an answer; `playUntil(solutionEnd)` runs. Last drawn candle
   should be the one whose close time equals `solutionEnd`.
3. **Cut to solutionStartNextCandle (play, animation OFF, unanswered).**
   With animation toggled off, open an unanswered question. Last visible
   candle's close time should be `solutionStartNextCandleTime`.
4. **Cut to solutionEnd (play, animation OFF, answered).** Same question
   after answering. Last visible candle should be the one closing at
   `solutionEnd`.
5. **Partial candle behaviour.** Pick a question whose `solutionStart` is
   `2025-09-15 14:30` on a 1H chart (mid-period). Animation OFF. The
   chart should show the 14:00 candle as a **partial** with OHLCV up to
   14:30 only, not as a full closed candle.
6. **Question-transition target.** With animation ON, transition between
   two consecutive same-symbol/same-resolution questions. After the
   transition `playUntil` pauses, the last visible candle should be the
   one closing at the new question's `questionStartTime`. (Then the
   normal animation up to `solutionStart` continues.)

#### Edit / New mode

7. **Open `/quizzes/edit/<id>`.** Chart loads, period bar **visible** with
   the symbol-search and period-picker buttons **disabled** (existing
   question — symbol/resolution locked via `disabledFeatures`); no replay
   controls panel visible. (Earlier draft had the period bar fully hidden;
   the implementation kept it visible so other period-bar buttons remain
   usable.)
8. **Header in edit mode shows only Settings.** No Alert, no Buy, no
   Sell, no Replay.
9. **Live ticks update the latest candle.** Wait 1 minute on a 1m
   resolution and watch the last candle update — the in-progress candle's
   close should change as live ticks arrive.
10. **Click "Set Solution Start" sidebar button** → the button text
    turns brand-blue ("armed") → click on the chart at a target time →
    `solutionStart` updates in the form, the solution-start timeline
    overlay appears at that time on the chart, button returns to normal.
11. **Click "Set Solution End" sidebar button** → same armed highlight
    flow, solution-end overlay appears.
12. **Bg context-menu in edit mode.** Right-click chart background →
    "Set Solution Start" and "Set Solution End" entries appear → click
    "Set Solution Start" → click on chart → same effect as #10.
13. **Refresh ranges button** in the sidebar → chart re-centers on the
    current question's `visibleTimeRange`.
14. **New question.** From an existing quiz, click "Add Question" →
    routes to new-question form → chart mounts in `new` mode: period bar
    **visible** (symbol/resolution can be changed), Settings button shown.
15. **Change question's symbol** in the form (only available on new
    questions) → chart reloads on the new market **and VR re-focuses on
    `editFocusRange`** (not latest candle) when solution timestamps are
    set. If no timestamps set, chart shows latest candles (default SC
    behaviour).
16. **Change question's resolution** in the form (only available on new
    questions) → chart reloads at the new resolution **and VR re-focuses
    on `editFocusRange`** when timestamps are set.
16a. **Navigate between questions (same symbol/resolution).** Go from a
    question with no timestamps to one with timestamps — chart
    immediately re-focuses on that question's `editFocusRange`. Go the
    other direction (timestamps → no timestamps) — chart shows latest
    candles. Setting/changing timestamps on the active question does NOT
    trigger a VR jump (only question identity change does).

#### Play mode

17. **Open `/quizzes/play/<quiz-id>` or random.** Chart loads with no
    header bar at all and no period bar.
18. **First question, animation ON.** Candles animate from
    `questionStartTime` up to `solutionStart`, then pause. Sidebar shows
    question text + answer options.
19. **First question, animation OFF.** Toggle animation off in settings,
    open a question. Chart cuts directly to `solutionStartNextCandle`,
    no animation.
20. **Submit answer with animation ON.** Click an answer option →
    candles animate from `solutionStart` to `solutionEnd` → pause.
    Solution + correct-answer reveal in sidebar.
21. **Submit answer with animation OFF.** Click an answer option →
    candles cut to `solutionEnd`. Solution reveal in sidebar.
22. **Show hint.** Click hint button mid-question → hint drawing overlay
    appears on chart. Toggle off → drawing disappears.
23. **Skip a question** → next question loads, prev question marked as
    skipped in progress strip. Skipped questions can be revisited.
24. **Same-symbol/resolution transition (animation ON).** Move between
    two consecutive questions on the same market that pass the
    `questionsCanTransition` rules. The chart animates smoothly forward
    without a reset/flicker. Solution-start/solution-end timelines for
    the previous question fade off, the new question's overlays appear.
25. **Different-symbol/resolution transition.** Move between two
    questions on different markets. The chart resets, switches market,
    and starts a fresh animation from the new question's
    `questionStartTime`. No animation across the gap.
26. **Speed control mid-animation.** Start a question with animation ON,
    change the speed slider mid-flight in settings → the in-progress
    animation visibly speeds up or slows down without a stutter or
    re-start.
27. **Pause / resume the animation.** Some quiz controls let the user
    pause; the animation pauses on the current candle, resumes from
    there. (If quiz has no pause UI, skip this — confirm during impl.)
28. **Agree / disagree feedback.** After answer reveal, click agree or
    disagree → feedback persists across reload of the same question.
29. **Finish a quiz.** Answer all questions → results page renders,
    accuracy %, time, etc. all match the answers given.
30. **Resume a partially-answered quiz.** Quit mid-quiz, re-enter from
    `/quizzes` listing → the first unanswered question loads with the
    correct prior-state.

#### Preview mode

31. **Open `/quizzes/edit/preview/<quizId>/<questionId>`.** Chart loads
    with no header bar and no period bar.
32. **Animation runs in preview.** Candles animate from
    `questionStartTime` to `solutionStart` once, then pause. Sidebar
    shows the question.
33. **Submitting an answer in preview is non-persistent.** Click an
    answer option → solution reveal happens, but reloading the page
    starts the question fresh (no answer persisted).
34. **Hint toggle works** like in play.
35. **Bg context-menu in preview.** Right-click chart background → the
    "Set Solution Start" / "Set Solution End" entries are **NOT**
    present.
36. **No Alert/Buy/Sell/Replay/Settings buttons** anywhere on or above
    the chart in preview.

#### Quiz overlays

37. **Solution-start vertical line** appears at `solutionStart` time
    in **edit and new modes only**. Play and preview modes do **not**
    show timeline overlays (would spoil the question). Colour matches
    the pre-port `chartColors.quizSolutionStart`.
38. **Solution-end vertical line** appears at `solutionEnd` in edit/new
    only. Colour matches `chartColors.quizSolutionEnd`.
39. **Decision-point arrow** appears post-answer in play/preview (after
    the answer is revealed), and is not shown during the question phase
    (would reveal solutionStart).
40. **Overlays clear on question change.** Move from question A to
    question B (different solution times) → A's lines/arrow disappear,
    B's appear.
41. **Overlays clear on chart reset.** Trigger a hard transition
    (different symbol) → previous question's overlays gone after reset.

#### Drawings / indicators (storage now wired — see Round 2)

42. ~~**Edit mode does not crash when drawing.**~~ **Superseded by Round 2.**
    Drawings are now persisted; the original noop-verification
    expectations no longer apply.
43. ~~**No save/restore on question change.**~~ **Superseded by Round 2.**
    Drawings/indicators DO save and restore on question change; see Round
    2 §Persistence.

#### TT-decoupling regression

44. **`/trade` opens normally.** Chart loads, all overlays (orders,
    alerts, trades, bid/ask, break-even) render. Buy/Sell/Alert/Replay
    header buttons all visible and functional.
45. **TT chart bg context-menu.** Right-click chart background in
    `/trade` → trading / alert / replay entries present, **no**
    `setSolutionStart` / `setSolutionEnd` entries.
46. **`EditQuizQuestion` widget gone.** Open the FlexLayout widget
    picker / "Add Widget" → "Edit Quiz Question" is no longer an option.
    Layouts that previously had an `EditQuizQuestion` node load without
    crashing (the node falls through to `UnknownWidget` or is silently
    dropped).
47. **No `i18n` warning for `widgets.EditQuizQuestion`** in the console
    on `/trade`.

#### Cross-route navigation

48. **`/quizzes` → `/trade` → `/quizzes`.** Navigate quiz → trade →
    quiz. No console errors, both routes mount cleanly each time. SC
    chart instance disposes and reinitialises correctly.
49. **`/quizzes` (deep-link).** Open `/quizzes/play/<id>` directly in a
    fresh tab without visiting `/quizzes` listing first → mounts cleanly.
50. **Quiz progress survives `/quizzes` ↔ `/trade` round-trip.** Start
    a quiz, answer 2 questions, navigate to `/trade`, return to
    `/quizzes`, open the same quiz topic. The two answered questions
    are still marked answered (server-persisted). The current
    in-progress question can be resumed.

#### Provider scoping (mobile-menu Redux flag + provider mount)

51. **Mobile bottom-nav hides while playing a question.** On mobile,
    open `/quizzes/play/<id>` and wait for a question to load. Bottom
    nav disappears as soon as the question is active.
52. **Mobile bottom-nav hides during preview.** Same for
    `/quizzes/edit/preview/<quizId>/<questionId>`.
53. **Mobile bottom-nav stays visible everywhere else.** On
    `/dashboard`, `/markets`, `/trade`, `/quizzes` listing, and
    `/quizzes/edit/<id>` (edit / new mode) — bottom nav is visible.
54. **Mobile bottom-nav reappears after quitting a quiz.** While in
    play, click Quit → return to listing → bottom nav back.
55. **`/trade` does not read QuizContext.** Open `/trade` directly in a
    fresh tab without visiting `/quizzes` first. No console errors
    about a missing context provider; chart and trading panels load
    normally.

#### Per-question candle storage removed

56. **Create a brand-new question.** In edit mode, fill out a new
    question (symbol, resolution, solution start/end, answer options) and
    click Save. The save completes without the historical "fetching
    candles" toast / wait. The question shows up in the quiz immediately
    after.
57. **No "no data could be found" toast.** With the toast string gone,
    saving a new question never shows that toast — even if the chosen
    market has limited history.
58. **Play a freshly-created question.** Open the new question from `play`
    mode → candles load correctly via the live provider (no fallback to a
    stored array). Animation runs as expected.
59. **Edit and re-save an existing question.** No regression — saving an
    edit completes without the candle-fetch step.
60. **Open a pre-port question that has stored candles in the DB.**
    Frontend ignores any candles payload returned by the backend; chart
    candles come purely from the live provider. Behaviour is
    indistinguishable from a question with `candles: []`.

#### Internationalisation

61. **English / Dutch / Spanish quiz UI.** Switch language → all quiz
    UI strings (sidebar buttons, controls, modal text, header) appear
    correctly translated. No untranslated keys visible.

#### Alt+R reset hotkey

62. **Alt+R in edit mode, both timestamps set.** Press alt+R →
    chart VR jumps to `editFocusRange` (100% pad on each side of the
    `solutionStart`–`solutionEnd` window). Same result as the Refresh
    Ranges button.
63. **Alt+R in edit mode, only one timestamp set.** Press alt+R →
    chart VR shows a 50-candle window centred on the set timestamp.
64. **Alt+R in edit mode, no timestamps set.** Press alt+R →
    `resetView()` fires (latest candle, default zoom). No crash.
65. **Alt+R in TT / CS / GridBot / /charts.** Behaviour unchanged —
    `resetView()` always fires. Quiz edit-mode branch is not active
    outside `/quizzes`.
66. **Alt+R in replay mode (TT).** `resetView()` targets the replay
    buffer tail (latest drawn candle), not the live latest candle.

#### Preview mode engine delegates

67. **Open `/quizzes/edit/preview/<quizId>/<questionId>`.** Chart
    enters replay mode at `questionStartTime` and animates to
    `solutionStart` without a `setCurrentTime is not a function` crash.
68. **`drawUntil` completes in preview.** Animation pauses exactly at
    `solutionStart`; `_waitUntilPaused` resolves; no timeout or hang.
69. **Play mode `playUntil` post-answer.** After submitting, candles
    animate to `solutionEnd` and pause. `onReplayStatusChange` fires the
    `paused` status exactly once, resolving `_waitUntilPaused`.

---

## Round 2: Storage / persistence / prev-question drawings

Folded back in after Round 1 (originally deferred — see early
`deferred.md`). All items below verify behaviour delivered by commit
`ff0c14e0` and follow-ups.

### Persistence — drawings (edit)

70. **Add a drawing in edit mode** → reload page → drawing reappears.
71. **Drag an existing drawing** → reload → drawing is at the new
    coordinates (deep-equality `sameOverlays` catches coord changes even
    though ids stayed the same).
72. **Switch `drawingMode` to "hint"** → only hint drawings show; switch
    to "solution" → only solution drawings; switch to undefined ("show
    all") → all three buckets render.
73. **Add a drawing while `drawingMode = "hint"`** → reload → drawing is
    in `question.hintDrawings`, not `questionDrawings`.
74. **No-bucket save preserves bucket assignment.** With
    `drawingMode = undefined` (showing all), drag an existing solution
    drawing → reload in mode "solution" → drawing is still classified
    as solution (matched by id, not re-routed to "question").

### Persistence — indicators

75. **Add an indicator via the picker modal** → reload → indicator
    reappears.
76. **Modify indicator settings** (e.g. RSI length) → reload → settings
    persist.
77. **Hide an indicator via the modal** → reload → indicator stays
    hidden (settings property captured by `sameIndicators`'s deep
    equality, ignoring id).
78. **No flash on question switch.** Two questions sharing the same
    indicators: switching between them keeps the indicators on screen
    without a visible flash (surgical diff: removed/changed/added).
79. **Question-switch with different indicators.** A→B where B has a
    different RSI length: the old indicator is removed, the new one
    appears, no duplicate.

### Mode-aware gating (preview / play)

80. **Hint toggle in preview/play.** Toggle hint on → `hintDrawings`
    appear on the chart. Toggle off → they disappear. `questionDrawings`
    always shown.
81. **Solution gating in play.** Before submitting an answer, no
    `solutionDrawings` on the chart even if the question has them.
    After submitting, they appear (unless `hideAnswer` is set).
82. **Solution gating in preview.** Same as play: solutionDrawings
    only appear after the user picks an answer (`preview.answer`).
83. **`hideAnswer` suppresses solution drawings** in play mode even
    after the user has answered.
84. **Adapter.save is no-op in preview/play.** Try interacting with a
    drawing in play mode (if SC's input layer allows it) — no save
    fires; reload preserves question state untouched.
85. **Indicators always returned regardless of bucket gating.** Open a
    play-mode question whose `questionStudies` contain RSI → RSI
    appears on the chart (indicators are global to the question, not
    bucketed).

### Prev-question drawings (transient overlays)

86. **Edit mode, same-symbol/resolution prev question** with drawings →
    open the next question → prev-question drawings appear faded /
    locked. Try to drag → can't (lock: true).
87. **Edit mode, different-symbol prev question** → prev drawings do
    NOT render.
88. **Play mode, transitionable** (passes `questionsCanTransition`) →
    prev drawings render.
89. **Play mode, non-transitionable** → prev drawings do NOT render.
90. **Preview mode** → never renders prev drawings.
91. **No flash on question switch with same prev set** — sig check on
    `_resolvePrev` short-circuits when `mode|prevId|symbol|resolution|count`
    is unchanged.
92. **Toggle "Keep drawings of previous question"** in play settings
    while a question is active → prev drawings appear/disappear
    immediately (no need to navigate).
93. **Prev-question drawings do not save back.** Drag-of-transient is
    blocked by `lock: true`; even if a transient overlay appears in
    `state.overlays`, `adapter.save` filters `o.save !== false` before
    bucket routing.

### Decision-point arrow (delivered as part of overlay design)

94. **Arrow anchors at the candle's high.** Open an answered play
    question → arrow points down at the high of the
    `solutionStart`-aligned bar (FA `` glyph), with "Decision
    point" label above.
95. **Initial-load arrow visibility.** Cold-load directly into
    `/quizzes/play/<id>` for an answered question — arrow appears on
    first paint (subscribe-bars-loaded triggers the redraw once the
    candles arrive; previously it was invisible because `getDataList()`
    was empty at first mount).

### Reset path

96. **Reset in edit mode** → drawings rehydrate without disappearing
    (no klinecharts tombstone). Form is NOT marked touched (silent
    bucket writeback). Chart VR doesn't jump (reload is called with
    `noFocus`).
97. **Delete-question Reset** — when a question is deleted via the
    confirm modal, the surviving currentQuestion's drawings re-render
    correctly.

### Auto edit-mode switch

98. **Drawing in overview** auto-switches to edit form. Open a question
    in overview, draw a trendline → form transitions to edit mode (the
    `[currentQuestion.touched]` effect fires when the chart-driven
    autosave path calls `q.touch()`).
99. **Form X-chip touches first.** Removing a question option via the
    form X chip → form marks touched immediately (no race where the
    next input change overwrites it).

### Answered-question animation (commit `7cfd01da`)

100. **Cold-load an answered question with animation ON.** Candles
     animate up to `solutionEnd` (not `solutionStart`). Verifies the
     `animEnd = (!hideAnswer && answer) ? solutionEnd : solutionStart`
     branch in `play.drawQuestion`.

### MODE_POLICY runtime sync

101. **Switch from new-question form to edit of an existing one.** Period
     bar stays visible but symbol-search and period-picker buttons
     become disabled (mode-change effect calls
     `setFeatureEnabled("symbol_search", false)` etc.). No need to
     re-mount the chart.
102. **Drawing bar visibility.** Drawing bar shows in new/edit, hides in
     play/preview (`drawingBarVisible` constructor option + per-mode
     policy).
