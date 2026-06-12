# Backtest presets — Review

## Round 0: implementation verification (2026-06-12)

Implemented on branch `feature/pivot-trading` (worktree
`~/git/worktrees/putcafe/pivot-trading`), tag `[pc-presets]`. Frontend-only.

Files: `frontend/src/util/presets.ts` (new), `frontend/src/App.tsx`,
`frontend/src/components/BacktestPanel.tsx`, `frontend/src/app.css`.

### Design recap

A `Preset` snapshots `{ name, market, interval, rangeStart, rangeEnd, config,
pivotOptions }` in localStorage (`putcafe.presets`), upsert by name. The range is
**absolute**, so a preset always points at the same immutable historical klines;
the pivot algo is a pure stateless sim — together that makes a loaded preset's run
deterministic. `loadPreset` pre-syncs the market/interval ref so the
change-teardown effect doesn't wipe the range it sets.

### Verification

1. ✅ `tsc -b` clean; `vite build` clean (claude-verified).
2. Save: set up market/interval/range/algo/settings → "Save as preset" → name →
   row appears under **Presets**; survives a page reload.
3. Load: click a preset → market, interval, range, mode, algo + all settings, and
   pivot options restored; panel opens; no auto-start.
4. Determinism: load a past-dated preset, Start (pivot, headless) → note the
   result; reload the app, load the same preset, Start → identical trades/PnL.
5. Near-now warning: a preset whose end is within ~2 candles of now shows ⚠ with a
   "last candle may still be forming" tooltip.
6. Overwrite: re-saving with an existing name replaces that preset (no dup row).
7. Remove: × deletes the preset; persists across reload.

### Notes / deferred

- localStorage only — no server storage or export/import (possible later add).
- Presets reference candles by market/interval/range and re-fetch (history is
  immutable) — they don't snapshot candle data.
- DCA runs still persist a new positions session per run; the *result* is
  deterministic, the persistence is a side effect.
- Built on `feature/pivot-trading` (not its own branch) because a preset must
  capture the pivot algo settings that only exist there; merges to main with it.
