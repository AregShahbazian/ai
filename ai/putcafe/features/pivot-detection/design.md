# Pivot detection — Design

PRD: [`prd.md`](prd.md) (`pc-pivots`).

## Pivot format

```json
{ "time": 1780869600, "type": "high", "price": 64234.68, "confirmedAt": 1780880400 }
```

`confirmedAt` = time of the candle `lookback` positions later — the moment the
pivot became knowable. Drives honest replay clipping on the frontend.

Options object (one shape everywhere — seed, live update, analyze, localStorage):

```json
{ "enabled": true, "lookback": 3, "alternation": true }
```

## Bot-backend (Python)

New `app/pivots.py`:

- `detect(candles, lookback, alternation) -> list[pivot]` — single pass over
  indices `[lookback, len-lookback)`; high if `high >= max` of window highs
  (checked first), elif low if `low <= min` of window lows. Alternation:
  walk raw pivots in time order, collapse consecutive same-type runs to the
  strongest (max high / min low; first wins ties).
- Recompute-from-scratch each call — O(n·lookback) on ≤ a few thousand candles,
  no incremental state to corrupt.

`app/main.py` changes:

- Session store gains `"pivots": options_dict` (from seed; default
  `{enabled: false, lookback: 3, alternation: true}`).
- `PivotOptions` pydantic model (`enabled: bool`, `lookback: int ge=1`,
  `alternation: bool`); `SeedBody.options: PivotOptions | None`.
- Responses gain pivots (full recomputed list, `null`/absent when disabled —
  the lists are tiny):
  - `seed` → `{ok, historySize, pivots}` (pivots over seeded history)
  - `step` → `{decisions, pivots}`
  - `run` → `{steps, trades, pivots}`
- `PUT /api/bot/sessions/{id}/options` `{pivots: PivotOptions}` → `{ok, pivots}`
  — the replay live-control: store new options, recompute over candles-so-far.
  409 `not_seeded` when unknown (frontend re-seeds like `step`).
- `POST /api/bot/analyze` `{candles, pivots: PivotOptions}` → `{pivots}` —
  stateless; serves loaded finished sessions (bot memory is gone by then) and
  option toggles on a finished/loaded view.

## Frontend

- `util/pivotOptions.ts` — `PivotOptions` type + localStorage-backed
  `usePivotOptions()` (key `putcafe.pivotOptions`, pattern of
  `useSavedCandles`). Defaults: `{enabled: true, lookback: 3, alternation: true}`.
- `api/backend.ts` — `Pivot`/`PivotOptions` types; `bot.seed` body gains
  `options`; `bot.step`/`bot.run` response types gain `pivots`;
  `bot.setOptions(id, opts)`; `bot.analyze(candles, opts)`.
- `backtest/engine.ts`:
  - `EngineSnapshot.pivots: Pivot[]`; engine holds current `PivotOptions`
    (passed via `start(config, pivotOptions)` and kept for re-seeds).
  - `stepOnce`/seed/`runHeadless` fold returned `pivots` into the snapshot.
  - `setPivotOptions(opts)` — store; when a replay session is active, call
    `bot.setOptions` (one re-seed retry on 409, like `botStep`) and emit new
    pivots; disabled → emit `pivots: []`. On a loaded/finished view, use
    `bot.analyze` over `preCandles + candles` instead.
  - `loadSession` — when enabled, `bot.analyze(pre + candles, opts)`.
- `App.tsx` — `usePivotOptions()`; pass options into `engine.start` /
  `engine.setPivotOptions`; thread `pivots` into `SessionView`.
- `components/BacktestPanel.tsx` — "Pivots" block: Show-pivots checkbox,
  Lookback number input, Alternation checkbox. **Not** disabled while a replay
  session is active (live control); disabled only while headless is `playing`.
- `chart/ChartView.tsx` — `SessionView.pivots`; the markers effect merges
  pivots (clipped by `confirmedAt <= cursor time`) with trades, sorted by time:
  high → `aboveBar`/`arrowDown`/`#f0a431`, low → `belowBar`/`arrowUp`/`#42a5f5`
  (trade markers stay green + text, so lows remain distinguishable).

## Dev/test plumbing

Bot must be testable pre-merge (CI deploys `api` from `main` only). The bot ran
locally before (pycache present): `uvicorn app.main:app --port 8102` with
`POSITIONS_URL` pointed at the deployed API. `vite.config.ts` gains an opt-in
dev proxy — when `VITE_LOCAL_BOT=1`: `/api/bot/*` → `http://localhost:8102`,
`/api/positions/*` → the deployed host, and `VITE_API_BASE` is forced to `""`
via `define` so the app routes through the proxy. Default behavior unchanged.

## Open questions (resolve while implementing)

- Whether `seed`'s pivots are worth rendering before the first step (they are
  returned regardless; render path should just take them).
- Marker colors may need a contrast tweak against the dark theme.
