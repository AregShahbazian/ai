# Backtest presets — Tasks

Design: [`design.md`](design.md). Built on branch `feature/pivot-trading`
(presets must capture the pivot algo settings that live there); commits tagged
`[pc-presets]`.

## 1. Presets store

- `frontend/src/util/presets.ts` — `Preset` type + `usePresets()` localStorage
  hook (`putcafe.presets`), `save` (upsert by name) / `remove`.
- Verify: `tsc -b` clean.

## 2. App wiring

- `frontend/src/App.tsx` — `usePresets()`, `loadPreset` (sets market / interval
  / range / config / pivotOptions, opens panel, no auto-start), thread props to
  the panel.
- Verify: `tsc -b` clean.

## 3. Panel UI

- `frontend/src/components/BacktestPanel.tsx` — "Save as preset" button (name
  prompt, build from props), Presets list (load on click, × to remove),
  near-now determinism warning.
- Verify: save a setup → reload → preset persists; load → market/interval/range/
  algo/settings restored; run twice → identical pivot result.

## 4. Build + review

- `tsc -b && vite build` clean; write `review.md`; commit + push (frontend-only
  → redeploys the `pivot-trading` preview slot).
