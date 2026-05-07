# Storage Attempt 1 — Notes Before Revert

Reference notes for the storage work being reverted (commit `eec76020` "WIP - storage - implementation" + uncommitted changes on top). Restart will rebuild storage from scratch; this captures the architectural lessons and fixes to re-apply later.

## What was in the commit (`eec76020`)

Initial Phase 7 storage wiring:

- `QuizStorageAdapter` (`src/models/quiz/quiz-storage-adapter.js`) — first cut of `save()`/`load()`/`delete()` against question state. Indicators written via `setQuestionStudies`; overlays routed by `question.drawingMode` to question/hint/solution drawings.
- `DrawController` (`src/models/quiz/draw-controller.js`) — added SC-shaped `createStudies` / `removeStudies` / `removeAllStudies` / `removeAllDrawings` / `drawPlayDrawings` / `clearPlayDrawings` / `switchEditDrawingMode` / `reloadEditState` / `_restoreDrawings`. TV-shaped methods kept as stubs.
- `quiz-super-chart.js` — adapter wired to chart options (`storageAdapter`, `storageKey: "quiz:edit"`, `autoSaveDelay: 300`). Effects added for `question?.id` (full reload) and `question?.drawingMode` (drawing swap). Monkey-patch on `chart.createIndicator`/`removeIndicator` to mirror live state into question (workaround — modal bypassed adapter at the time).
- `play-drawings.js` / `preview-drawings.js` — rewritten to merge `questionDrawings + hint + solution` and render via `draw.drawPlayDrawings(...)` as transient overlays under `OverlayGroups.quizUserDrawings`.
- `question.js` — `clearDrawings` now calls `draw.removeAllDrawings()` for the active mode.

## Uncommitted refinements on top (today)

- `QuizStorageAdapter` — `withSuppressedSave(fn)` async-friendly suppress counter; `load()` returns indicators ALWAYS (global to question), drawings only when `drawingMode` is set; `touch()` before writes so modal-driven saves mark the form touched.
- `DrawController` — dropped `createStudies` / `removeAllStudies` entirely. `removeStudies(names)` now uses public `superchart.removeIndicator(name)` (modal stays in sync). `reloadEditState` rewritten to: per-name `sc.removeIndicator` + `chart.removeOverlay({})` + `sc.loadState()`, all wrapped in `withSuppressedSave`.
- `quiz-super-chart.js` — monkey-patch removed (SC commit `84cac1c` fixed modal → adapter sync upstream). `mountedRef` gate restored on `[question?.id]` effect so SC's auto-`restoreChartState` handles first mount (avoids 2x BOLL duplicate). `controller.storageAdapter` reference exposed for `DrawController`.
- `question.js` — `refreshStudies` delegates to `draw.reloadEditState()`; `createStudies` removed; `removeStudies(names)` simplified (no more id lookup, names go straight to `draw.removeStudies`).
- `edit-question.js` — auto-switch to edit mode whenever `currentQuestion.touched` flips true (overview → edit on first chart-driven mutation).
- `question-edit-form/question-fields.js` — `await question.touch()` before form-X removal so the form marks touched.
- `multi-select.js` — `disabled={disabled || !hasOptions}` so an empty MultiSelect doesn't spawn an empty popup on click.

## Key architectural lessons (carry forward)

1. **Don't monkey-patch `chart.createIndicator/removeIndicator`.** Modal-driven adds/removes already fire `adapter.save` natively as of SC `84cac1c`. Just wire the adapter and consume `save()` calls.
2. **Use the public Superchart API for indicator removal**: `superchart.removeIndicator(name: string)` — routes through `popIndicator` → updates `chartStore.mainIndicators`/`subIndicators` → modal stays in sync. The klinecharts primitive `chart.removeIndicator({id})` only updates the canvas.
3. **No public `superchart.createIndicator`** exists. For restore, **don't call `chart.createIndicator(...)` directly** (it doesn't update modal signals). Instead let SC's own `restoreChartState` do it via `sc.loadState()` (or via auto-mount restore) — that path writes both canvas and signals.
4. **`sc.loadState()` doesn't clear** existing chart state (only adds). For "switch to a different saved state" (question navigation): per-name `sc.removeIndicator(name)` + `chart.removeOverlay({})` first, then `sc.loadState()`.
5. **First-mount restore is automatic** (SC's `ChartWidget` mount effect calls `restoreChartState` after a 500ms `setTimeout`). Manual reload on first mount races/duplicates with this — gate with `mountedRef`.
6. **Indicators are global to the question**, not per-`drawingMode`. `load()` must return them regardless of `drawingMode`; only overlays vary by mode.
7. **`adapter.save` writes back** `state.indicators`/`state.overlays` to question state; programmatic batches that clear-then-restore must wrap in a suppress mechanism so transient empty states don't clobber the source.
8. **Modal-driven adapter writes should `touch()` the question** so Save/Reset enable and the overview auto-switches to edit mode.
9. **Don't double-restore on first mount.** SC's auto-restore + our `[question?.id]` effect both firing → 2x indicators (`sc.loadState()` is additive, not idempotent).
10. **Form-driven removal should `touch()` first** (matches how `importQuestionStudiesCallback` already touches before bulk study replace).

## Non-storage fixes folded in (re-apply later separately)

- `multi-select.js` empty-popup fix — independent UX bug.
- `edit-question.js` auto-switch to edit mode on `touched` — independent UX behavior.
- `question-fields.js` form-X `touch()` — touch hygiene for the existing form path.

## Open SC API gaps filed during this work (`phase-7/sc/`)

- `bug-removeIndicator-modal-desync.md` — fixed upstream by SC commit `84cac1c`.
- `feature-setDrawingBarVisible.md` — runtime drawing-bar expand/collapse setter (still pending).
- Implicit gap: no public `superchart.createIndicator(name, isStack?, paneOptions?)`. For host-driven creation that keeps the modal in sync, the only current path is to write into `adapter` then `sc.loadState()`. Consider filing a feature request if needed.
