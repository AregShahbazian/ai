# Discussion — Add 3+ proven trading algos (2026-06-13)

## Summary
Areg wants more proven, common trading algorithms added to putcafe's backtest
engine to find which generate **long-term consistent profits (even if small)**.
Started at "3 more", grew to **5 algos**, each built in its **own git worktree**
as an independent comparison branch. Each algo must reuse the existing `pivot`
strategy's structure: a stateless server-side `simulate()` returning the shared
`PivotSimResult` shape (trades + TP/SL bracket + close-and-reverse + order ledger
+ equity/liquidation), so the existing frontend rendering (BacktestPanel results,
chart order lines, replay-by-cursor) works unchanged. Each algo gets its own
**parameter tuning / optimization (pruning) pass**. Deliverable: select an algo
in the UI, run a backtest with tuned defaults, and get good results — verified by
me via build + Playwright (`window.pc` bridge / `yarn e2e` on :5183) per worktree.

Areg wants this to run unattended overnight; permission prompts to be minimized
(bypass mode / Shift+Tab auto-accept / settings allow-list — added a broad
allow-list to `.claude/settings.json`, push still excluded).

## The 5 algos
1. **MA crossover** (golden/death cross) — trend.
2. **RSI mean-reversion** — counter-trend.
3. **Bollinger-band breakout**.
4. **Donchian channel** (trend-following).
5. **MACD** (trend-following).

## Key conclusions
- Architecture: each algo = an **entry-signal generator** plugged into the shared
  bracket/exit/liquidation/close-reverse/order-ledger machinery from
  `pivot_strategy.py`. The signal differs; the position management is shared.
- Reuse `PivotSimResult` so no new frontend rendering is needed; only a new
  algo option in `BacktestPanel` + per-algo param controls.
- **Per-algo tuning**, not a shared optimizer.
- Worktrees are parallel experiments under `~/git/worktrees/putcafe/<branch>`;
  not necessarily all merged — the point is to compare profitability.

## Open questions
- Exact tuning method: param grid-sweep across multiple historical ranges,
  scored by aggregate (median ROI / positive expectancy / win-rate). To be
  designed per algo.
- Whether/which algos ultimately get merged to `main`.

## Ideas to realize
- Add a generic **signal-driven simulator core** (extract the bracket/exit/order
  machinery from `pivot_strategy.py` into a reusable engine taking a signal fn).
- Implement **MA-crossover** algo (backend sim + UI option + params + tuner + e2e).
- Implement **RSI mean-reversion** algo (full stack + tuner + e2e).
- Implement **Bollinger-breakout** algo (full stack + tuner + e2e).
- Implement **Donchian-channel** algo (full stack + tuner + e2e).
- Implement **MACD** algo (full stack + tuner + e2e).
- Per-algo **parameter-sweep / pruning tuner** — sweep params over several
  historical ranges, pick params with consistent positive expectancy; surface
  the tuned values as the algo's UI defaults.
- A **multi-range / multi-market backtest harness** to measure "long-term
  consistent profit" (run an algo over many windows, report median/worst-case
  ROI, % profitable windows) — the real selection criterion.
- Extend `window.pc` bridge for each new algo's state/params so scripted
  verification stays complete.
- Possible **algo comparison view** — run all algos on the same range and rank
  by consistency.
