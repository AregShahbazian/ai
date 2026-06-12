# Putcafe — workflow overview

Crypto trading-bot **simulation & backtesting** web app. Binance spot/real
historical data, fictional balances (no API keys), replay + headless sessions,
pivot-based strategies. This file indexes the workflow docs under `~/ai/putcafe/`
— see [`workflow.md`](workflow.md) for repo-specific rules (yarn-only, CI-only
deploys, branch-per-feature).

## Canonical docs

| Doc | What |
|---|---|
| [bare/prd.md](bare/prd.md) | Bare slice — chart + market selector (`pc-bare`) |
| [mvp/prd.md](mvp/prd.md) | MVP — backtesting & replay, sessions, two backends (`pc-mvp`) |
| [devops/prd.md](devops/prd.md) | Build/release pipeline + VPS docker edge (`pc-devops`) |
| [backlog.md](backlog.md) | Unplanned idea holding-pen |

## Features

Each feature dir holds `prd.md` (+ `design.md` / `tasks.md` / `review.md`).
Status = state on `main` unless noted.

| Feature | id | Docs | Status |
|---|---|---|---|
| [Bare slice](bare/prd.md) | `pc-bare` | prd·design·tasks·review | ✅ shipped |
| [MVP backtest/replay](mvp/prd.md) | `pc-mvp` | prd·design·tasks·review | ✅ shipped |
| [DevOps pipeline](devops/prd.md) | `pc-devops` | prd·design·tasks·review | ✅ shipped |
| [VPS docker UI](devops/docker-ui/prd.md) | `pc-docker-ui` | prd·design·tasks·review | ✅ shipped |
| [Candle tools](features/candle-tools/prd.md) | `pc-candle-tools` | prd·design·tasks·review | ✅ shipped |
| [Pivot detection](features/pivot-detection/prd.md) | `pc-pivots` | prd·design·tasks·review | ✅ shipped |
| [Pivot trading](features/pivot-trading/prd.md) | `pc-pivot-trading` | prd·design·tasks·review | ✅ shipped |
| [Backtest presets](features/presets/prd.md) | `pc-presets` | prd·design·tasks·review | ✅ shipped |
| [Overview widgets](features/overview-widgets/prd.md) | `pc-overview-widgets` | prd·design·tasks·review | ✅ shipped |
| [Console bridge](features/console-bridge/prd.md) | `pc-console-bridge` | prd·design·tasks·review | ✅ shipped |
| [Leverage](features/leverage/prd.md) | `pc-leverage` | prd·design·tasks·review | 🔨 in progress (branch `feature/leverage`) |
| [Futures order protocol](features/futures-orders/prd.md) | `pc-futures-orders` | prd only | 📋 planned |

## Discussions

| Date | Topic | Doc | Ideas to realize |
|---|---|---|---|
| 2026-06-12 | Pivot (swing high/low) detection | [doc](discussions/2026-06-12-pivot-detection.md) | mostly shipped |
| 2026-06-12 | Pivot detection — visualization (part 2) | [doc](discussions/2026-06-12-pivot-detection-part2.md) | shipped |
| 2026-06-12 | Pivot-breakout trading strategy | [doc](discussions/2026-06-12-pivot-trading-strategy.md) | partly shipped |
| 2026-06-12 | Hedge-mode futures order protocol | [doc](discussions/2026-06-12-futures-order-protocol.md) | yes (drives `pc-futures-orders`) |

## Backlog — ideas to realize

Aggregated from discussion `## Ideas to realize` sections + [backlog.md](backlog.md).

- [x] Pivot detection in bot backend (symmetric-window swing detector) → pivot-detection
- [x] Alternation enforcement option (persisted, togglable) → pivot-detection
- [x] Pre-session + live-replay bot-option editing → pivot-detection
- [x] Frontend pivot visualization / triangle markers → pivot-detection (part 2)
- [x] `pivot` breakout trading algo (stateless bot-side sim) → pivot-trading-strategy
- [x] Order/position visualization (working orders as lines, fills as markers) → futures-order-protocol
- [ ] Pivot `strength` field + ZigZag-style refinement → pivot-detection
- [ ] Smart TP/SL via pivot recency / time-distance weighting → pivot-trading-strategy
- [ ] Equity-curve subchart for backtest PnL → pivot-trading-strategy
- [ ] Futures order protocol + matching engine (`pc-futures-orders`) → futures-order-protocol
- [ ] Pivot-based futures strategy emitting protocol orders → futures-order-protocol
- [ ] Persisted futures sessions for the pivot algo (after `pc-futures-orders`) → pivot-trading-strategy
- [ ] Separate prod/staging API + DB (per-env isolation) → backlog.md
- [ ] Rename positions-backend → session-backend → backlog.md

## Key decisions

- **Identity:** web-only crypto backtest/replay app; Binance spot, real klines, fictional balances, no API keys.
- **Stack:** React/TS frontend (lightweight-charts) · Python FastAPI **bot** backend · **positions** backend + Postgres · GitHub-CI-only deploys to a VPS docker edge, preview slot per `feature/<slug>`, staging on `main`.
- **Strategy sim:** the `pivot` algo is a **stateless** server-side simulation (`/api/bot/simulate`) — single source of truth; replay reveals pre-computed trades/orders by cursor, no per-candle backend calls.
- **Orders:** sim emits a full **orders ledger** (armed entry stops, TP/SL bracket, reverse exits) rendered in the overview widget + as chart price lines (Altrady-style labels).
- **Futures:** real resting/bracket orders, shorts, leverage & liquidation are the in-flight `pc-leverage` / planned `pc-futures-orders` line — spot positions-backend can't model them.
