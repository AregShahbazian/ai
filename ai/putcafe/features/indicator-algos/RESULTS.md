# Indicator algos — implementation & profitability results (2026-06-13)

Five proven, common trading algos added to putcafe's backtest engine, each on the
shared **signal-driven bracket engine** (`backend/bot/app/bracket_sim.py`): an algo
emits a per-candle desired direction (−1/0/+1, no lookahead); the engine manages one
isolated-margin position with a TP/SL bracket + liquidation + close-and-reverse, and
returns the existing `PivotSimResult` shape (so the frontend renders it unchanged).

## Branches / worktrees
- `feature/algos` — **integration**: all 5 algos + tuner + e2e (the real work).
  `~/git/worktrees/putcafe/algo-ma`.
- `feature/algo-donchian | -bollinger | -ma-cross | -rsi | -macd` — per-algo
  worktrees, each defaulting to its algo with tuned params (same shared code).

All branched off the pre-futures-orders `main` (`cdc9144`). `main` has since advanced
to `afcb1a9` (futures-orders merge) — **a rebase/merge will be needed** before landing,
since that work also touched the bot strategy layer.

## How to run
- Local bot: `PORT=8102 ./scripts/dev/local/run-bot.sh` (stateless /simulate; no DB).
- Frontend: `frontend/.env.local → VITE_API_BASE=http://localhost:8102`, then `yarn dev`.
- e2e: `yarn e2e` (drives all 5 algos via `window.pc`, asserts sim invariants).
- Tuner: `cd backend/bot && python tuner.py [--quick]` → `tuned_defaults.json`.

## Tuning method
`tuner.py` fetches BTC/ETH/BNB/SOL 1h (~8 months each), splits into 24 non-overlapping
1000-candle windows, sweeps each algo's indicator grid × bracket grid (SL%, TP/SL ratio)
at leverage 1 with fees on. Scores by **consistency**: median per-window ROI gated by
% of windows green, discounted if too few trades. Best combo per algo → UI defaults.

## Verdict — which generate long-term consistent (small) profit
Ranked by best-combo consistency score over the 24 windows:

| # | Algo | Median ROI | % windows green | Worst window | Tuned defaults |
|---|------|-----------:|----------------:|-------------:|----------------|
| 1 | **Donchian breakout** | **+1.44%** | **67%** | −5.98% | period 30, SL 6%, TP/SL 1.5 |
| 2 | **Bollinger breakout** | **+1.15%** | **67%** | −3.34% | period 30, σ2.0, SL 4%, TP/SL 2 |
| 3 | RSI mean-reversion | −1.21% | 0% | −3.44% | p7, 20/80, SL 2%, TP/SL 1.5 |
| 4 | MACD | −3.69% | 0% | −6.97% | 8/21/9, SL 2%, TP/SL 1.5 |
| 5 | MA crossover | −0.24% | 50% | −4.26% | 10/200 EMA, SL 6%, TP/SL 1.5 |

**Donchian and Bollinger-breakout are the consistent small earners** — positive median
and profitable in two-thirds of independent windows. The trend-crossover pair (MA, MACD)
and RSI mean-reversion did **not** hold up on this sample/period at any swept params.
ROI magnitudes are muted because margin is 10% of balance at leverage 1 — leverage and
position size are user choices in the UI; the *sign and consistency* are what the sweep
measures.

## Caveats / next
- Sample = 4 large-cap USDT pairs, 1h, last ~8 months (mostly trending). Donchian's edge
  is trend-following; a ranging regime would compress it. Re-run the tuner on more
  symbols / a bear window before trusting it as "long-term".
- The mean-reversion algos may do better intraday (lower TF) or with a regime filter
  (only fade inside a range) — not yet explored.
- Bracket exits + re-entry can churn trend algos after a stop; a "no re-entry until a
  fresh cross" gate could cut whipsaw (future idea).
