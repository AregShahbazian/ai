# Phase 7: Deferred Items

Items excluded from `prd.md` (the `sc-quiz` core port). Each becomes its own
follow-up PRD when the blocker resolves.

> **Status update.** Several items originally listed here as deferred are
> now **delivered** in the working branch (commit `ff0c14e0` "wire quiz
> storage, persistence, and gating"). The persistence-side gap that this
> file was written to track is closed; what remains here are the items
> still genuinely out of scope. See `design.md §13 (Storage & persistence)`
> for the as-built design.

---

## ✅ DELIVERED — User drawings capture in edit mode

Captured live via SC's autosave → `QuizStorageAdapter.save` → bucketed into
`questionDrawings` / `hintDrawings` / `solutionDrawings` per the active
`drawingMode` (or kept in the existing bucket when mode is unset, matched
by id). Drawings made in `new` / `edit` mode persist to the question. SC's
drawing-tools API was sufficient — no `getAllShapes` / `deleteShape`
equivalents needed because the chart-engine state is the source of truth
and `adapter.save` is fed the full overlay list on every mutation.

---

## ✅ DELIVERED — User indicators capture in edit mode

Captured via the same `adapter.save` path. Indicators are global to the
question (not per-bucket) and live on `question.questionStudies`.
`QuizPersistenceController` does a surgical diff (`removed` / `changed` /
`added`) on question-id change so kept indicators don't flash. Indicator
creation goes through SC's indicator-picker modal, which writes through
`adapter.save`; programmatic restore on question switch goes through
`sc.loadState()` (the only public path that updates both canvas and modal
signals).

> The 4 custom Altrady indicators (`rsiStoch`, `previousCandleOutliers`,
> `smartMoney`, `Willams21EMA13`) port is still Phase 8 — orthogonal to the
> capture/restore pipeline.

---

## ✅ DELIVERED — Auto-load saved drawings / indicators on enter edit / play / preview

Auto-loaded via `adapter.load` — SC calls it on chart mount and on
`storageKey` change. `load()` returns the gated overlay set (edit: full
buckets; preview/play: `questionDrawings + (showHint? hint : []) + (answer
&& !hideAnswer? solution : [])`) plus indicators. On question-id change the
`quizPersistence.reload()` controller path drops the chart and re-hydrates
from the adapter (drawings imperatively, indicators via `sc.loadState`).

---

## ✅ DELIVERED — Storage adapter

`QuestionSaveLoadAdapter` / `EditQuestionSaveLoadAdapter` are gone (file
deleted in commit `ba984246`). Replaced by `QuizStorageAdapter` at
`src/models/quiz/quiz-storage-adapter.js` which implements SC's
`StorageAdapter` shape (`load` / `save` / `delete`). The `storageKey` is
unused — the adapter resolves the active question and mode from
`quizController` at call time, so a single chart instance handles
edit/preview/play without re-keying.

---

## Per-question chart layout naming

**What it is.** TV stored each question's saved chart layout under a
human-readable name (`tvWidget.saveChartToServer` /
`tvWidget.layoutName()`), defaulted to the quiz name when missing. Used in
the quiz-edit UI for displaying the layout association.

**Why deferred.** Direct dependency of the StorageAdapter port — neither the
naming convention nor the mapping survives a 1:1 transfer to SC's storage
key model.

**Blockers.** Phase 6.

**Placeholder.** `DrawController.saveChartToServer` and `currentLayoutName`
are no-ops.

---

## `tradingview-enhancements.js` floating-toolbar drawing buttons

Already tracked on `SUPERCHART_BACKLOG.md` (Backlog section, "Drawing
selection toolbar"). Mentioned here only to record that the quiz
edit-mode UX in TV-prod relied on the bell-icon trendline-to-alert path on
the floating drawing toolbar. Not used by quiz directly — listed for
context only.
