# Backtest presets — Design

PRD: [`prd.md`](prd.md) (`pc-presets`).

Frontend-only — presets are persisted config snapshots in localStorage, mirroring
`useSavedCandles` / `usePivotOptions`. No backend changes.

## Preset shape

```ts
interface Preset {
  name: string
  market: Market            // { symbol, baseAsset, quoteAsset }
  interval: Interval
  rangeStart: number        // unix seconds — absolute, for determinism
  rangeEnd: number
  config: PanelConfig       // mode, algo, all algo settings, balance, fees
  pivotOptions: PivotOptions // enabled, lookback, alternation
}
```

Everything the engine needs to reproduce a run is here. `market` is stored whole
(3 strings) so loading needs no markets-list lookup. The range is **absolute**,
never relative — the same historical klines every time.

## Files

### `src/util/presets.ts` (new)

`usePresets()` — localStorage hook (key `putcafe.presets`), same pattern as
`useSavedCandles`:

```ts
{ presets: Preset[],
  save(p: Preset): void,     // upsert by name (re-saving a name overwrites)
  remove(name: string): void }
```

`PRESETS_KEY`, load/parse with a try/catch fallback to `[]`.

### `src/App.tsx`

- `const presets = usePresets()`.
- `loadPreset(p: Preset)` — sets all the relevant state at once:
  `setMarket(p.market)`, `setInterval(p.interval)`, `setConfig(p.config)`,
  `setRangeStart(p.rangeStart)`, `setRangeEnd(p.rangeEnd)`,
  `pivotOptions.set(p.pivotOptions)`, `setPanelOpen(true)`. Does **not** start a
  session.
  - Guard: if a session is active, ignore/stop first (loading mid-session would
    be inconsistent) — simplest is to no-op when `snap.status` is running and let
    the existing market/interval-change effect handle teardown; in practice
    loading is done from the idle/finished state. We additionally call
    `engine.stop()`-equivalent only if needed. (Keep it: only allow load when not
    actively running; the panel hides the list while running anyway.)
- Pass `presets={presets.presets}`, `onSavePreset`, `onLoadPreset`,
  `onRemovePreset` to `BacktestPanel`.

### `src/components/BacktestPanel.tsx`

- **"Save as preset"** button (near the Start button / pickers). On click,
  `window.prompt("Preset name")`; if non-empty, build a `Preset` from the panel's
  current props (`market`, `interval`, `rangeStart`, `rangeEnd`, `config`,
  `pivotOptions`) and call `onSavePreset`. Disabled when range is unset.
- **Presets** section (like Saved candles / Sessions): each row shows
  `name · market · interval · range`, click → `onLoadPreset(p)`; a × removes it.
  Shown when not actively running (same gate as Sessions).
- **Determinism warning**: when a preset's `rangeEnd` is within ~2 intervals of
  `now`, show a small "⚠ ends near now — last candle may still form" note on that
  row (and/or when saving). Interval→seconds via a small map.

## Determinism

- Candles: Binance `/klines` history is immutable for closed candles →
  market+interval+absolute range fully determines the candle set (session range +
  the 500-candle pre-history seed are both historical).
- Pivot algo: stateless `POST /api/bot/simulate`, a pure function of
  (candles, options, params) → identical trades each run.
- DCA algo: deterministic decisions; each run persists a *new* positions session
  (side effect), but the computed result is the same.
- The only non-determinism is an unclosed final candle when `rangeEnd ≈ now` —
  hence the warning. Recommend picking ranges fully in the past.

## Open questions (resolve while implementing)

- Naming collisions: re-saving an existing name **overwrites** (upsert) — simpler
  than dedup suffixes; the row makes the overwrite visible.
- Whether to offer a one-click "load & run"; v1 is load-then-Start per the PRD.
