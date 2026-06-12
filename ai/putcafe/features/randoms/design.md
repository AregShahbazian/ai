# Random backtest range — design

Implements [`prd.md`](./prd.md) (`pc-randoms`). Frontend-only; no backend change.

## Where it plugs in

The Backtest range is two pieces of `App` state — `rangeStart` / `rangeEnd`
(unix seconds) — set today by chart-click picking or presets, and read verbatim
by Start (`App.startSession`) and the bridge (`pc.session.start`). The feature
adds a third way to fill them: a dice roll bounded to the current market's
history. Because it writes the same two values, it round-trips through presets,
the bridge, and Start unchanged (PRD R4) — nothing downstream needs to know.

## Pieces

### 1. Bounds — `binance/api.ts: fetchKlineBounds(symbol, interval)`

Returns `{ earliest, latest }` in unix seconds for the current market+interval:

- **earliest** — `GET /klines?startTime=0&limit=1`; Binance returns the first
  listed candle, so its `openTime` is the start of available history.
- **latest** — reuse `fetchKlines()` (most-recent page). Binance's last element
  is the *still-forming* candle; we take the one before it (`data[len-2].time`),
  i.e. the last **closed** candle — satisfies PRD R2's reproducibility clause
  (never the forming candle) and matches the panel's existing `endsNearNow`
  guard intent.
- Throws a clear error if a symbol has no/too-little history.

Two small fetches, called on demand per click — no caching (history bounds
barely move; a fresh roll wanting the freshest `latest` is cheap and correct).

### 2. Roll — `util/randomRange.ts: rollRandomRange(bounds, intervalSec, opts, rand)`

Pure (PRD R3). `rand: () => number = Math.random` is injectable so it's unit-
/e2e-assertable. Logic:

- `totalBars = floor((latest - earliest) / intervalSec)`.
- `maxBars = min(opts.maxBars ?? DEFAULT_MAX_BARS, totalBars)`,
  `minBars = min(opts.minBars ?? DEFAULT_MIN_BARS, maxBars)` — clamps the window
  to what short histories allow (a freshly-listed coin on `1w` won't overflow).
- `windowBars = minBars + floor(rand()·(maxBars−minBars+1))`, ≥ 1.
- Place at a random whole-bar offset: `start = earliest + offsetBars·intervalSec`
  where `offsetBars ∈ [0, totalBars−windowBars]`; `end = start + windowBars·intervalSec`.
- `start` stays candle-aligned (earliest is an open-time, offsets are whole
  bars), so the result lands on real klines.

Defaults: `DEFAULT_MIN_BARS = 200`, `DEFAULT_MAX_BARS = 1000` — a usable
backtest span at any resolution (1h → ~8–42 days; 1d → ~200–1000 days), and
≤ `KLINE_LIMIT` keeps headless runs to roughly one klines page. Adjustable via
`opts` (the bridge open question — defaults stand unless a knob earns its keep).

### 3. Orchestrator — `App.randomizeRange(opts?)`

`async (opts?) => { start, end }`. Reads current `market.symbol` + `interval`,
`fetchKlineBounds`, `rollRandomRange`, then `setRangeStart/​setRangeEnd` and
`setPanelOpen(true)`. Guards the write behind a re-read of `uiRef.current`
(market/interval may have changed during the await — don't stamp a stale range
onto a switched market, which the change-effect just cleared). Returns the
chosen pair so the bridge can report it. Disabled while a session is active
(same rule as the pickers).

### 4. UI — `BacktestPanel`

A `🎲 Random range` `tool-button` in the existing `.pickers` block (top, above
the start/end pickers). Local `rolling` + `rollErr` state mirror the existing
`exporting` pattern: button shows `Rolling…` and is `disabled` while in flight
or when `active`; a failed fetch shows a small inline error. Calls a new
`onRandomize` prop wired to `App.randomizeRange`.

### 5. Bridge — `pc.backtest.randomRange(opts?)`

New `backtest` namespace. `AppHandle` gains
`randomRange(opts?): Promise<{start, end}>`, registered in App's bridge effect
to call `randomizeRange`. The command returns `{ start, end, ...state.config }`
so a caller sees the rolled range and the synced UI. Added to `COMMANDS` for
`pc.help()`, per the repo bridge rule (PRD R5).

## Determinism & honesty

The dice are deliberately non-reproducible (re-roll differs each click, PRD
non-req); reproducibility lives entirely in the resulting **absolute** range,
exactly like a hand-typed one. Capping `end` at the last closed candle keeps any
rolled range re-runnable.

## Testing

No unit runner in the repo (Playwright e2e only). Extend `e2e/bridge.spec.ts`:
roll via `pc.backtest.randomRange()`, assert the returned `{start,end}` is
within the market's bounds, candle-aligned, `start < end`, and that
`pc.state.config()` now mirrors it — then start a headless run on it to prove it
flows through unchanged.
