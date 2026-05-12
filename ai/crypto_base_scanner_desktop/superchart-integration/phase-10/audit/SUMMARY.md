# Phase 1 Audit Summary

## Anchor
- **BASE** (merge-base of `release-5.3.x` and HEAD): `2ba1b825f8` — "bump version 5.3.11" (2026-04-26)
- All diffs anchor here. 5.3.x commits after BASE are NOT in scope (separate porting).

## Totals (vs BASE)
- **80 deletions** (1 of which is `.claude/settings.local.json` — config we just created; ignore)
- **178 modifications**
- **109 additions** (all SC code — leave untouched)
- **8 renames** (TV → SC paths, partial edits)

## Files
All lists at `audit/`:
- `all-changes.txt` — full name-status
- `deleted.txt` — to restore
- `modified.txt` → split into buckets below
- `added.txt` — SC-only, leave alone
- `renamed.txt` — see "Renames" below
- `modified-classified.tsv` — per-file TV/SC mention counts + line stats

## Modified-file buckets

### Bucket A — TV removed (50 files) → `bucket-A-tv-removed.tsv`
TV refs at BASE, zero at HEAD. Bulk of work. Top hitters:
- `charts-grid-item.js` (66/26)
- `models/quiz/question.js` (56/131)
- `models/quiz/play-controller.js` (39/72)
- `notes-form.js`, `grid-bot-settings.js`, `grid-item-settings.js`
- `actions/trading.js`, `reducers/replay.js`

Approach: re-add TV chunks behind flag, or split to `.tv.js` if behavior diverges.

### Bucket B — TV residual (5 files) → `bucket-B-tv-residual.tsv`
TV refs at BASE AND HEAD. Mostly i18n YAML (en/es/nl/ru translation + guide). Likely safe — keys may have moved namespaces. Verify keys exist on both branches.

### Bucket C — SC took over without TV trace (11 files) → `bucket-C-sc-only.tsv`
No TV refs at BASE, SC refs at HEAD. Mostly lockfile/CI/configs:
- `yarn.lock`, `package.json` (deps)
- `.github/workflows/*.yml`
- `charts.js`, `quiz-controller.js`, `layout.js`, a few quiz form files

Most are config — leave alone. The 3-4 JS files need inspection.

### Bucket D — Unrelated (112 files) → `bucket-D-unrelated.tsv`
No TV or SC refs at either side. Genuinely orthogonal changes:
i18n key reshuffles, design-system tweaks, eslint config, etc.
**Leave alone.**

## Renames (8 files) → `renamed.txt`
Critical — TV files renamed into SC paths with edits. For each:
- Restore the **original TV path** with BASE content (TV-side)
- Keep the **new SC path** with current content (SC-side)
- This yields the `.tv.js`/`.sc.js` split naturally (at different paths)

Affected pairs:
1. `tradingview/action-buttons.js` ↔ `super-chart/action-buttons.js`
2. `tradingview/settings/chart-color-picker.js` ↔ `super-chart/chart-settings/chart-color-picker.js`
3. `tradingview/settings/general-settings.js` ↔ `super-chart/chart-settings/general-settings.js`
4. `tradingview/controllers/replay/backtest.js` ↔ `super-chart/replay/backtest.js`
5. `tradingview/replay/pick-replay-start-button.js` ↔ `super-chart/replay/pick-replay-start-button.js`
6. `tradingview/replay/replay-controls.js` ↔ `super-chart/replay/replay-controls.js`
7. `trade/trading-terminal/quiz/quiz-context.js` ↔ `containers/quizzes/quiz-context.js` (non-TV?)
8. `trade/trading-terminal/quiz/use-quiz.js` ↔ `containers/quizzes/use-quiz.js` (non-TV?)

(Pairs 7-8 are inside quizzes restructure — verify if TV-related before restoring.)

## Work estimate
- **Restoration scope:** ~80 deletions + ~50 bucket-A files + 6 renames = **~136 TV touchpoints**
- **Already orthogonal:** ~112 bucket-D files (no action)
- **Mostly safe:** Bucket C (11) — only ~4 JS files to inspect

## Open questions before Phase 2
1. The two quiz renames (pairs 7-8) — are they TV-coupled or pure restructure?
2. i18n YAML residual — should TV-era keys be re-added alongside SC keys, or do they already coexist?
