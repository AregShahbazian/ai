# Phase 7: Deferred Items

Items excluded from `prd.md` (the `sc-quiz` core port). Each becomes its own
follow-up PRD when the blocker resolves.

---

## User drawings capture in edit mode

**What it is.** When a quiz creator draws on the chart (trendlines, rays,
text annotations, arrows) in edit mode, those drawings should be captured
and persisted on the question. Loaded back on play / preview / re-edit.

**Why deferred.** SC's drawings-tools layer does not yet expose:

- "list all drawings on the chart" (TV: `chart.getAllShapes()`)
- "delete a drawing by ID" (TV: `chart.removeEntity(id, {disableUndo:true})`)
- programmatic creation of typed drawings the user could otherwise create
  via the toolbar.

See `INTEGRATION.md → Phase 7` for the dependency note and
`SUPERCHART_BACKLOG.md` row #6 (drawings tools audit).

**Blockers.** SC drawings-tools API + Phase 6 StorageAdapter.

**Placeholder.** `DrawController.getAllDrawings`, `getAllShapes`,
`deleteShape`, `deleteShapes`, `removeAllDrawings` return empty arrays or
no-op. `EditQuestionSaveLoadAdapter.saveLineToolsAndGroups` is a no-op.

---

## User indicators capture in edit mode

**What it is.** Same as drawings, but for indicators (RSI, MACD, custom
studies). Creator adds an indicator, the question records its name + input
values; replayed on play / preview.

**Why deferred.** klinecharts' indicator API needs an audit for: list
attached indicators, read input values, attach a typed indicator with custom
inputs, remove by ID. The 4 custom Altrady indicators (`rsiStoch`,
`previousCandleOutliers`, `smartMoney`, `Willams21EMA13`) also need to be
ported to klinecharts (Phase 8).

**Blockers.** SC drawings/indicators API audit + Phase 6 StorageAdapter +
Phase 8 custom-indicator port (`SUPERCHART_BACKLOG.md` row #8).

**Placeholder.** `DrawController.getAllStudies`, `getStudyInputValues`,
`createStudy`, `createStudies`, `removeStudies`, `removeAllStudies` return
empty arrays or no-op. `EditQuestionSaveLoadAdapter.saveChart` is a no-op.

---

## Auto-load saved drawings / indicators on enter edit / play / preview

**What it is.** When entering a question, restore the drawings + indicators
that were saved on it. Currently routed through `QuestionSaveLoadAdapter` /
`EditQuestionSaveLoadAdapter`.

**Why deferred.** Depends on capture-side being implemented first
(previous two items) and on the StorageAdapter port (Phase 6).

**Blockers.** Same as the two items above.

**Placeholder.** `Question.refreshStudies()` and `Question.updateDrawingsTrigger()`
remain no-ops on the SC path.

---

## `QuestionSaveLoadAdapter` / `EditQuestionSaveLoadAdapter` real implementation

**What it is.** The current adapters extend `LocalSaveLoadAdapter` (TV-shaped
contract). Need rewriting to implement SC's `StorageAdapter` interface so the
SC instance can save/restore per-question chart state.

**Why deferred.** Phase 6 (Persistence) has not landed yet. The
`StorageAdapter` shape, the `storageKey` strategy (per question vs. per
market), and migration of existing TV-format saved data all happen there.

**Blockers.** Phase 6 (`SUPERCHART_BACKLOG.md` row #7).

**Placeholder.** Adapter classes exist as no-op shells — no save calls go
through, load calls return empty state.

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
