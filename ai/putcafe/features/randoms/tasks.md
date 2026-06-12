# Random backtest range — tasks

Implements [`design.md`](./design.md). One branch `feature/randoms`, one commit.

- [x] **T1 — `fetchKlineBounds`** in `frontend/src/binance/api.ts`: fetch
  earliest (`startTime=0&limit=1`) + last-closed (`fetchKlines`, `len-2`) candle
  open-times (unix seconds); throw on empty/short history.
- [x] **T2 — `rollRandomRange`** in new `frontend/src/util/randomRange.ts`: pure
  roll with injectable `rand`, `DEFAULT_MIN_BARS`/`DEFAULT_MAX_BARS`, clamped to
  available history, candle-aligned `{start, end}`.
- [x] **T3 — `App.randomizeRange`**: orchestrate fetch→roll→set range; guard the
  write against market/interval drift via `uiRef`; return the pair. Pass as
  `onRandomize` to `BacktestPanel`.
- [x] **T4 — `BacktestPanel` button**: `🎲 Random range` `tool-button` in
  `.pickers`; local `rolling`/`rollErr` state; disabled while `active`/in-flight.
- [x] **T5 — Bridge**: `AppHandle.randomRange`, register it in App's bridge
  effect, add `pc.backtest.randomRange` + `COMMANDS`/`pc.help()` entry.
- [x] **T6 — e2e**: extend `e2e/bridge.spec.ts` — roll, assert bounds/alignment/
  `start<end`, config mirrors it, headless run on it finishes.
- [x] **T7 — Verify**: `yarn build` (tsc) clean; `yarn e2e` green; manual roll
  via UI button + `pc.backtest.randomRange()`.
