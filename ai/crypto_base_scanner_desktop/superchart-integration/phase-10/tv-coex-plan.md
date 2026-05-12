# TV/SC Coexistence Plan

## Goal
Restore TradingView functionality alongside SuperChart, gated by a global flag. TV must look like it was never removed (history preserved). SC's post-fork history can be discarded.

## Strategy
Move SC out of TV's way on the current branch so restored TV files sit at their original paths byte-identical to 5.3.x. Squash is the **final** step — purely additive vs 5.3.x.

## Phases

### 1. Audit
- Enumerate deleted TV files: `git log --diff-filter=D --name-only 5.3.x..HEAD`
- Enumerate edited shared files: `git log --diff-filter=M --name-only 5.3.x..HEAD`
- Classify edited files into:
  - **TV-only chunks removed** → restore chunk in-place
  - **SC took over file** → split into `.sc.js` + restore `.tv.js` (original path) + router
  - **Pure TV import/wiring removed** → re-add behind flag

### 2. Global flag
- Add `useTradingView` (or similar) to Redux/settings
- UI toggle lives in chart settings modal `general-settings.js`, under the "Chart" tab
- Define routing helper / hook
- **Switching provider must NOT reload the app** — hot swap via React unmount/remount of the chart subtree (different `key` per provider already handles this)
- **Switching MUST terminate active replay sessions** — treat provider switch like a symbol/market-tab change (reuse existing teardown path)

### 3. Move SC aside (per shared file) — SKIPPED
After audit: zero path collisions (all deleted/renamed TV paths empty at HEAD).
No file requires `.sc.js`/`.tv.js` splitting. Conflict candidates fall into:
- **Wrapper consumers** that swap chart-widget imports → in-file `useChartProvider()` branching in Phase 5
- **Behavioral consumers** (e.g. `notes-form.js` `takeScreenshot` signature change) → in-file branching in Phase 5
- **Shared infra** (`actions/replay.js`, `reducers/replay.js`) → union TV+SC exports/cases in canonical file; Phase 6 reconciles state shape if needed

### 4. Restore deleted TV files
- `git checkout 5.3.x -- <path>` for each
- Re-wire imports/callsites behind flag

### 5. Restore TV chunks in shared files
- For each file with TV-only edits removed, re-add the chunks behind flag branches or extract to a TV-only module

### 6. State / datafeed reconciliation
- Namespace divergent Redux state (`chartSettings.sc` / `.tv`) if shapes differ
- Wire TV's coinray datafeed back; keep SC datafeed untouched

### 7. Verify
- Both libs load and function with flag toggled
- Smoke-test: charts render, overlays (orders, alerts, bases), market switch, replay, drawing tools
- TV `git blame` on restored files shows 5.3.x history unbroken

### 8. Squash (final)
- Squash all post-fork commits into one on top of 5.3.x
- Verify squashed diff vs 5.3.x is **additive only** — no TV file modified or deleted
- Confirm `git log -- <TV file>` reads: 5.3.x history → squash commit (untouched) → future

## Rules
- TV files at canonical paths must be byte-identical to 5.3.x (= BASE)
- Prefer separate files (`.sc.js` / `.tv.js`) over in-file branching
- Share only pure utils / data — split when behavior diverges
- No commits/squash until explicitly requested
- **Restructure decision rule:** if a move/rename was SC-driven → undo, restore TV's BASE path. If it was a sensible cleanup that would have happened without SC → keep new path, repoint TV imports.
- **i18n:** restore TV-era keys to their BASE shape/namespace; SC keys are additive and coexist.
