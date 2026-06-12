# Pivot-breakout trading strategy — 2026-06-12

## Summary

Designed a concrete bot trading algo that **consumes pivots** (swing highs/lows
from `pc-pivots`) to take directional positions. Entries are **stop-market
breakouts** of the most recent pivot in the breakout direction ("breaking
previous resistance/support"); exits are a **TP/SL bracket** sized off the
opposite pivot, plus a **close-and-reverse** when the opposite structure breaks.
Strictly **one netted position at a time**. For now this is **simulated entirely
in the backtest** — the spot, buy-only positions-backend can't model
shorts/resting orders/brackets (that's the separate `pc-futures-orders` effort
from `2026-06-12-futures-order-protocol.md`). New algo named **`pivot`**,
alongside `dca`.

## Decisions

- **Entry**: when flat, arm a buy-stop at the last confirmed **high** pivot and a
  sell-stop at the last confirmed **low** pivot. Price breaching a level (same
  direction) fills a stop-market entry → long on up-breakout, short on
  down-breakout. Single position only.
- **TP/SL bracket, set at entry**: `SL%` = distance from entry to the **opposite**
  pivot, **capped** at a configurable `SL cap %`. `TP%` = `SL% × ratio`
  (configurable ratio, e.g. 2:1 → 4% SL ⇒ 8% TP). Fixed ratio confirmed.
- **Close + reverse**: while long, price breaking below the **current** last low
  pivot (opposite structure break) closes the long *and* opens a short same
  candle (mirror for short). Distinct from SL because the latest opposite pivot
  can drift above the bracket stop.
- **Re-arm only on a fresh pivot**: after a **TP or SL** exit (leaves us flat),
  do **not** re-enter until a *new* pivot confirms (a pivot with
  `confirmedAt` after the exit). Prevents whipsaw re-entries in chop. A reverse
  is not a flat-exit, so it needs no re-arm.
- **Single full close** for now (no partial TP / scaling / pyramiding).
- **Params** (configurable): TP/SL **ratio**, **SL cap %**, pivot **lookback**
  (reuses the existing pivot lookback), plus position size (notional USDT).
- **Simulated in backtest** only; real bracket/resting orders deferred to
  `pc-futures-orders`.

## Open questions (resolve in design)

- Intra-candle fill ordering when multiple levels sit inside one candle — use the
  OHLC **path heuristic** from the futures discussion (green: O→L→H→C, red:
  O→H→L→C) to decide which level is touched first.
- "Smart" TP/SL beyond capped opposite-pivot distance: the user floated using
  **pivot time-distance to now** (recency weighting). Deferred — v1 is
  capped-distance only; recency weighting is a future refinement.
- Position sizing/leverage: v1 is fixed notional, 1×. Leverage/margin deferred to
  `pc-futures-orders`.
- Persistence: pivot sims are not written to the positions-backend, so they don't
  appear in the Sessions list or reload. Acceptable while "simulate in backtest".

## Ideas to realize

- **`pivot` trading algo (`pc-pivot-trading`)**: bot-side stateless simulator
  (`POST /api/bot/simulate`, mirroring `/analyze`) running the breakout state
  machine over a candle range; frontend renders entries/exits + bracket lines,
  replay reveals by cursor. *(This feature.)*
- **Smart TP/SL via pivot recency/time-distance** weighting — future refinement
  of the bracket sizing.
- **Persisted futures sessions** for the pivot algo once `pc-futures-orders`
  lands (real resting orders, hedge-mode model, reload/Sessions list parity).
- **Equity-curve subchart** for backtest PnL over time.
