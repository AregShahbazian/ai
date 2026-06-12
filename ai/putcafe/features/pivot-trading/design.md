# Pivot trading — Design

PRD: [`prd.md`](prd.md) (`pc-pivot-trading`).

## Where the simulation lives

The strategy is **bot-side** and **stateless**, mirroring the existing
`POST /api/bot/analyze` pivot endpoint. One call simulates the whole candle range
and returns the trade list + per-position brackets; the frontend renders it and
replay reveals events by cursor. Rationale:

- The positions-backend is spot/buy-only — it can't hold shorts, resting orders,
  or brackets. "Simulate in backtest for now" ⇒ don't touch it.
- Keeping the detector **and** the strategy in the bot keeps a single source of
  truth (no TS re-port), consistent with `pc-pivots`.
- The sim is deterministic and cheap, so replay needs no per-candle backend
  calls — it pre-computes once and clips by the cursor, exactly like pivot
  `confirmedAt` clipping.

When `pc-futures-orders` lands, this strategy emits real order intents instead;
the state machine here is the reference.

## Bot-backend (Python)

### `app/pivot_strategy.py` (new)

`simulate(candles, pivot_options, params) -> dict`:

1. Detect pivots via `pivots.detect(candles, lookback, alternation)` (alternation
   forced on for a clean structure — strategy needs alternating support/
   resistance). Each pivot has `confirmedAt`.
2. Walk candles in time order, maintaining a small state machine:
   - `position`: `None | {side, entryTime, entryPrice, qty, slPrice, tpPrice, feePaid}`
   - `last_exit_time`: gates re-arm.
   - `last_high` / `last_low`: the most recent confirmed pivot of each type
     **as of the current candle** (`confirmedAt <= candle.time`).
3. **Confirm pivots up to `candle.time`** first, updating `last_high`/`last_low`.
4. **Intra-candle path** (OHLC heuristic): green (`close >= open`) ⇒ O→L→H→C,
   red ⇒ O→H→L→C. Evaluate level crossings in path order so the first-touched
   level wins; a single candle resolves at most one entry and one exit (the
   reverse's fresh position is evaluated from the **next** candle).
5. **When flat**: arm buy-stop = `last_high.price`, sell-stop = `last_low.price`,
   but only for pivots with `confirmedAt > last_exit_time` (re-arm gate). Along
   the path, the first stop breached fills:
   - buy-stop (`high >= stop`) → open **long**; sell-stop (`low <= stop`) → **short**.
   - fill price = gap-aware (`max(stop, open)` for buy, `min(stop, open)` for
     sell) + slippage if `feesEnabled`.
   - bracket: opposite pivot = `last_low` for a long / `last_high` for a short.
     `sl% = min(|entry - opp|/entry, slCapPct/100)` (fallback `slCapPct/100`);
     `slPrice` on the loss side, `tpPrice = entry × (1 ± sl%·ratio)`.
6. **When in a position**, along the path:
   - **long** downside levels = `{slPrice, last_low.price}` (only the current
     `last_low`, if below entry); the **higher** one is hit first on a down-move:
     - `slPrice` first → **SL** exit, go flat, set `last_exit_time` (re-arm).
     - `last_low` first → **reverse**: close long, open short at that level.
   - **long** upside = `tpPrice` → **TP** exit, flat, re-arm. (mirror for short)
7. Fees: `fee = notional × TAKER_FEE` on entry and exit; slippage `SLIPPAGE` on
   the adverse side — same constants as the positions-backend (0.001 / 0.0005).
8. Realized `pnl` per closed trade: `qty·(exit-entry)` long, negated for short,
   minus both fees. Running `equity = startingBalance + Σ realized pnl`.

Returns:

```json
{
  "pivots": [ {time,type,price,confirmedAt}, ... ] | null,
  "trades": [
    { "side":"long|short", "entryTime":..., "entryPrice":...,
      "exitTime":...|null, "exitPrice":...|null,
      "exitReason":"tp|sl|reverse|open", "qty":...,
      "slPrice":..., "tpPrice":..., "pnl":...|null, "feePaid":... }
  ],
  "equity": <final>, "realizedPnl": <sum>,
  "wins": <int>, "losses": <int>
}
```

A still-open position at range end is a trade with `exitReason:"open"`,
`exitTime/exitPrice/pnl = null`.

### `app/main.py`

- `StrategyParams` model: `tpSlRatio: float ge 0`, `slCapPct: float gt 0`,
  `quoteAmount: float gt 0`, `feesEnabled: bool`, `startingBalance: float`.
- `SimulateBody { candles, pivots: PivotOptions, params: StrategyParams }`.
- `POST /api/bot/simulate` → `pivot_strategy.simulate(...)`. Stateless, like
  `/analyze`. `lookback` comes from `pivots`; alternation forced on internally.

## Frontend

### `api/backend.ts`

- `SessionConfig.algo: "dca" | "pivot"`; `algoConfig` stays the DCA shape, add a
  separate `PivotParams { tpSlRatio, slCapPct, quoteAmount }` carried on the
  pivot config.
- Types: `PivotTrade`, `PivotSimResult`, `PivotParams`.
- `bot.simulate(candles, pivots, params) -> PivotSimResult`.

### `backtest/engine.ts`

- `EngineSnapshot.pivotSim: PivotSimResult | null`.
- Branch on `config.algo`:
  - **dca** — unchanged (positions session + bot seed/step/run).
  - **pivot** — `start()` fetches candles + seed history, calls
    `bot.simulate([...seed, ...candles] or candles, pivotOptions, params)` once,
    stores `pivotSim` and the detected `pivots`. **No** positions session, **no**
    bot seed. Status → `ready` (replay) or jump to `finished` (headless).
- Replay for pivot: `stepOnce` just advances `upTo` (no backend); `significant`
  = a trade entry/exit occurs at `candle.time` (so playback pauses on trades when
  auto-resume is off). `stepBack`/`play`/`stepForward` already drive off `upTo`.
- `setPivotOptions` / new `setPivotParams`: while a pivot session is active,
  re-run `bot.simulate` and replace `pivotSim` (re-clipped by cursor downstream).
- `loadSession` unaffected (pivot sims aren't persisted).

### `App.tsx`

- `algo` state (`"dca" | "pivot"`) + pivot params state (ratio, slCap, size).
  Build the right `SessionConfig`; pass `pivotSim`/algo into `SessionView`.

### `components/BacktestPanel.tsx`

- Algorithm `<select>` gains **Pivot**. When `pivot`: show **TP/SL ratio**, **SL
  cap %**, **Position size (USDT)** inputs (the existing Buy-amount/Frequency
  DCA fields hide). Pivot lookback stays in the pivot-options block (reused).
- Params are editable mid-replay (live control), locked only during a running
  headless batch — same rule as pivot options.
- Results block (pivot): realized PnL, ROI, win rate, trades, open position
  (side/entry/unrealized at the cursor).

### `chart/ChartView.tsx`

- `SessionView` gains `pivotSim` + `algo`. When `algo==="pivot"`:
  - Markers: entries (long ▲ below / short ▼ above, labelled) + exits
    (TP/SL/reverse, coloured), clipped to `time <= cursor`. Pivot triangles
    still render (clipped by `confirmedAt`).
  - Bracket **price lines** (entry / SL / TP) for the trade open at the cursor
    (entryTime ≤ cursor < exitTime|∞), via `series.createPriceLine`, cleared and
    redrawn as the cursor moves.

## Intra-candle resolution (the honest part)

We can't see the true tick path, so we assume the **color heuristic**: a green
candle traded O→L→H→C, a red one O→H→L→C. Walk that ordered path; the first
strategy level the path crosses fires. At most one entry + one exit per candle;
a reverse's new position starts being evaluated next candle. This is the same
assumption the futures discussion settled on and keeps SL pessimistic relative
to TP on red candles.

## Dev/test

Bot is testable pre-merge via the existing `VITE_LOCAL_BOT=1` proxy +
`uvicorn app.main:app --port 8102`. Verify `/api/bot/simulate` by curl over an
exported candle file before wiring the UI.

## Open questions (resolve while implementing)

- Marker shapes/colors for short entries vs pivot triangles — keep distinct
  (pivots are thin arrows at the bar; trades carry text labels).
- Whether to draw the pending (armed, unfilled) stop levels too — deferred; the
  pivot triangles already show where stops arm.
- Recency/time-distance weighting of SL — deferred (v1 = capped distance).
