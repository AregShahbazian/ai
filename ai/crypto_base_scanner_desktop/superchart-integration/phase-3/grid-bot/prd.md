---
id: sc-grid-bot
---

# PRD: Grid Bot Overlays — SuperChart Integration

## Overview

Reimplement grid bot chart overlays for SuperChart and add a dual-chart comparison layout to the grid bot details page. The grid bot uses its own chart widget (`GridBotTradingWidget`) separate from the trading terminal's main chart. This widget appears in two places: the grid bot **overview** tab and the **settings** tab, each with different interactivity levels.

This PRD covers three scopes:
1. **Dual-chart layout** — render SC below TV in the grid bot details page for side-by-side comparison
2. **Grid bot prices overlay** — upper/lower price + stop loss / take profit handles
3. **Grid bot orders overlay** — horizontal price lines for each grid level

## Current Behavior (TradingView)

### Grid bot prices (`grid-bot-prices.js`)

Rendered only when `edited` is true. Four handles via `createOrderLine`:

| Handle | Color | Line visible | Draggable | Label text | Condition |
|---|---|---|---|---|---|
| Upper price | `chartColors.alert` | No (`showLine: false`) | When `updateUpperPrice` provided | i18n "Upper price" | Always (when edited) |
| Lower price | `chartColors.alert` | No (`showLine: false`) | When `updateLowerPrice` provided | i18n "Lower price" | Always (when edited) |
| Stop loss | `chartColors.openSellOrder` | Yes | When `updateStopLoss` provided | i18n "Stop loss" | `stopLoss.enabled` |
| Take profit | `chartColors.openBuyOrder` | Yes | When `updateTakeProfit` provided | i18n "Take profit" | `takeProfit.enabled` |

All handles have empty quantity text. Draggability is controlled by whether the parent passes an `updateXxx` callback — overview passes none (read-only), settings passes all four.

### Grid bot orders (`grid-bot-orders.js`)

Rendered when `orders` array is provided. Each order becomes a horizontal line via `drawPriceLine`:

| Element | Color | Line style | Line width | Y-axis price label | Text label | Interactive |
|---|---|---|---|---|---|---|
| Buy order level | `chartColors.openBuyOrder` | Solid | 1 | Yes (TV default) | No | No |
| Sell order level | `chartColors.openSellOrder` | Solid | 1 | Yes (TV default) | No | No |

Lines are plain `horizontal_line` shapes with no body, no handle, no interaction. The y-axis shows the price label for each line (TradingView default for `horizontal_line`).

### Usage by tab

**Overview tab** (`grid-bot-overview.js`):
- `GridBotTradingWidget` with `orders`, `trades`, `upperPrice`, `lowerPrice`, `edited`, `takeProfit`, `stopLoss`
- **No update callbacks** — all handles are display-only (not draggable)
- Shows order lines + price handles (read-only) + trade markers

**Settings tab** (`grid-bot-settings.js`):
- `GridBotTradingWidget` with all of the above **plus** `updateLowerPrice`, `updateUpperPrice`, `updateStopLoss`, `updateTakeProfit`, `orders`, `edited`
- All four price handles are draggable
- Shows order lines + interactive price handles
- No `trades` prop (settings uses form state, not historical data)

**Other usages:**
- `shared-grid-bot-overview.js` — same as overview (read-only)

### Chart widget types

The codebase has two categories of chart usage with different data/context patterns:

**Market-tab charts** (trading terminal, multi-charts):
- Live inside a `MarketTabContext` provider
- Get `coinraySymbol`, `resolution`, `currentMarket`, `exchangeApiKey` from the market tab system
- Symbol/resolution/VR changes sync bidirectionally with `TradingTabsController` (chart UI change → persist to tab state, tab state change → push to chart)
- TV: `MainChartTradingWidget` / `DefaultTradingWidget`
- SC: `SuperChartWidgetWithProvider`

**Standalone charts** (grid bot details, backtest, shared bot overview):
- No `MarketTabContext` — receive `coinraySymbol` directly as a prop from the parent page
- No `TradingTabsController` sync — symbol/resolution/VR changes stay local to the chart instance
- No `exchangeApiKey` or `currentMarket` from context — data comes from the bot/form state
- TV: `GridBotTradingWidget`
- SC: needs a new standalone widget (this PRD)

Both TV widget types share the same low-level chart init (`TradingViewChart` → `ChartContextProvider`) and the same overlay components. The wrappers differ only in where data comes from and what callbacks are wired. The SC architecture should follow the same pattern: shared `ChartController`, `CoinrayDatafeed`, `SuperChartContextProvider`, and overlay components — with a separate wrapper for standalone usage.

### Chart location

In the trading terminal, TV and SC run side by side in a flex layout for comparison during integration. In the grid bot details page (both overview and settings), there is currently only **one chart** (TV). SC needs to be added here.

## Requirements

### R1 — Dual-chart layout in grid bot details page

Add SuperChart below TradingView in both overview and settings tabs. The vertical space currently used by TV alone is split equally between TV (top) and SC (bottom). This is a **temporary comparison layout** — once overlays are verified, TV will be removed.

- Both charts receive the same `coinraySymbol` and display the same market
- Both charts render independently (separate instances, separate contexts)
- The split applies to both desktop and mobile (collapsed) layouts
- No shared state between TV and SC beyond the same props

### R2 — Grid bot prices overlay (SuperChart)

Render upper/lower price and stop loss / take profit handles on SuperChart using `createOrderLine`.

| Handle | Color | Body text | Quantity | Line visible | Editable | Y-axis label |
|---|---|---|---|---|---|---|
| Upper price | `chartColors.alert` | i18n "Upper price" | (empty) | No | When `onMoveEnd` wired | Yes, alert color |
| Lower price | `chartColors.alert` | i18n "Lower price" | (empty) | No | When `onMoveEnd` wired | Yes, alert color |
| Stop loss | `chartColors.openSellOrder` | i18n "Stop loss" | (empty) | Yes | When `onMoveEnd` wired | Yes, sell color |
| Take profit | `chartColors.openBuyOrder` | i18n "Take profit" | (empty) | Yes | When `onMoveEnd` wired | Yes, buy color |

- Only drawn when `edited` is true
- Stop loss only drawn when `stopLoss.enabled`
- Take profit only drawn when `takeProfit.enabled`
- Draggability is determined by the parent: overview passes no callbacks (read-only), settings passes all four
- `onMoveEnd` calls the parent's `updateXxx` callback with the new price
- Controller methods receive the raw data objects and resolve colors/text/callbacks internally

### R3 — Grid bot orders overlay (SuperChart)

Render horizontal price lines for each grid bot order using `createPriceLine`.

| Element | Color | Y-axis label | Line width |
|---|---|---|---|
| Buy order level | `chartColors.openBuyOrder` | Yes — buy color | 1 |
| Sell order level | `chartColors.openSellOrder` | Yes — sell color | 1 |

- Lines are fully non-interactive — no body, no handle, no drag, no callbacks
- Y-axis price label must be visible (matching TV behavior)
- Only drawn when `orders` array is provided and non-empty
- Cleared and redrawn when orders change

### R4 — Trades overlay (SuperChart)

Render trade markers (buy/sell arrows) on the grid bot chart. The trading terminal's `Trades` overlay already exists and uses `chartController.createTrade()`. The grid bot widget reuses this same component, passing `trades` as a prop.

- Trades are an array of `{price, side, time, amount, externalId}` objects from `bot.lastSession.trades`
- Buy trades render as upward arrows, sell as downward — colors from `chartColors.closedBuyOrder` / `chartColors.closedSellOrder`
- Fully non-interactive — display only
- Only shown in overview tab (settings has no trade history)

### R5 — Tab-specific rendering

**Overview tab:**
- Grid bot orders: shown (from `bot.lastSession.orders` filtered to OPEN)
- Grid bot prices: displayed but **not interactive** (no update callbacks)
- Trades: shown (passed as `trades` prop)

**Settings tab:**
- Grid bot orders: shown
- Grid bot prices: **fully interactive** (all update callbacks passed)
- Trades: not shown

### R6 — Overlay component patterns

Follow the standard SC overlay pattern from `context.md`:

- Use `useDrawOverlayEffect(group, draw, deps)` for both overlays
- Components pass raw data to controller — controller owns colors, text, callbacks
- Add overlay groups to `OverlayGroups` in `overlay-helpers.js`
- Both are singleton components (one instance per chart) — use plain `OverlayGroups.xxx`
- Respect `visible` prop for clearing/skipping draw

### R7 — GridBotSuperChartWidget

Create a SuperChart widget for the grid bot pages. This widget:

- Initializes its own `Superchart` instance, `CoinrayDatafeed`, `ChartController`
- Wraps overlay components in `SuperChartContextProvider`
- Accepts the same props as `GridBotTradingWidget` (coinraySymbol, orders, trades, prices, callbacks, edited, visible)
- Does **not** depend on `MarketTabContext` or `WidgetContext` — the grid bot page provides `coinraySymbol` directly, not through the trading terminal's tab system
- Renders only grid-bot-relevant overlays: grid bot prices, grid bot orders, trades
- Does **not** render trading-terminal-specific overlays: bid/ask, break-even, PnL handle, orders (regular), edit-orders, bases, alerts
- PriceTimeSelect: SC component exists but wiring to grid bot charts is pending

**Shared logic note:** The trading terminal's `SuperChartWidget` has significant init logic (Superchart construction, datafeed, controller, ready check, symbol/resolution/theme sync, resize). After implementing the grid bot widget, evaluate how much code is duplicated and whether it's worth extracting shared logic (e.g., a `useSuperChartInit` hook). This is a follow-up refactor, not a blocker — get the grid bot widget working first, then assess.

### R8 — Visibility gating

- Both overlays gate on `readyToDraw` from `useSuperChart()` (handled by `useDrawOverlayEffect`)
- Both overlays respect the `visible` prop — when false, overlays are cleared
- Grid bot prices additionally gates on `edited` — when false, no handles are drawn

## Data Sources

### Grid bot prices
| Prop | Type | Source |
|---|---|---|
| `upperPrice` | string/number | `bot.upperPrice` (overview) or `botForm.upperPrice` (settings) |
| `lowerPrice` | string/number | `bot.lowerPrice` (overview) or `botForm.lowerPrice` (settings) |
| `stopLoss` | `{enabled, price}` | `bot.lastSession.settings.stopLoss` or `botForm.stopLoss` |
| `takeProfit` | `{enabled, price}` | `bot.lastSession.settings.takeProfit` or `botForm.takeProfit` |
| `updateUpperPrice` | `fn(price)` | `botForm.updateUpperPrice` (settings only) |
| `updateLowerPrice` | `fn(price)` | `botForm.updateLowerPrice` (settings only) |
| `updateStopLoss` | `fn({...stopLoss, price})` | `botForm.updateStopLoss` (settings only) |
| `updateTakeProfit` | `fn({...takeProfit, price})` | `botForm.updateTakeProfit` (settings only) |
| `edited` | boolean | `true` (overview) or `botForm.edited` (settings) |

### Grid bot orders
| Prop | Type | Source |
|---|---|---|
| `orders` | `[{price, side}]` | `bot.lastSession.orders` filtered to OPEN (overview) or `botForm.orders` (settings) |

### Colors
| Key | Used for |
|---|---|
| `chartColors.alert` | Upper/lower price handles |
| `chartColors.openBuyOrder` | Take profit handle, buy order lines |
| `chartColors.openSellOrder` | Stop loss handle, sell order lines |
| `chartColors.closedBuyOrder` / `closedBuyOrderPosition` | Buy trade markers |
| `chartColors.closedSellOrder` / `closedSellOrderPosition` | Sell trade markers |

## File Structure

```
super-chart/
  grid-bot-super-chart.js             # GridBotSuperChartWidget — self-contained SC widget for grid bot pages
  overlays/
    grid-bot/
      grid-bot-prices.js              # Upper/lower + SL/TP handles overlay component
      grid-bot-orders.js              # Horizontal order level lines overlay component
```

## Incremental Implementation Plan

### Step 1: Dual-chart layout

Add `GridBotSuperChartWidget` (initially with no overlays — just the chart) below TV in `grid-bot-overview.js` and `grid-bot-settings.js`. Split the chart area height 50/50. Verify both charts load the same market and render candles independently.

**Files:** `grid-bot-super-chart.js`, `grid-bot-overview.js`, `grid-bot-settings.js`

### Step 2: Grid bot prices overlay

Implement the four price handles (upper, lower, SL, TP) on SuperChart. Verify display-only mode in overview and interactive mode in settings.

**Files:** `overlays/grid-bot/grid-bot-prices.js`, `chart-controller.js`, `overlay-helpers.js`

### Step 3: Grid bot orders overlay

Implement horizontal price lines for grid levels on SuperChart. Verify y-axis labels are visible and colors match buy/sell side.

**Files:** `overlays/grid-bot/grid-bot-orders.js`, `chart-controller.js`, `overlay-helpers.js`

### Step 4: Trades overlay

Wire the existing `Trades` overlay component into `GridBotSuperChartWidget`. Pass `trades` prop from overview tab. No new overlay code needed — reuses the trading terminal's `Trades` component and `chartController.createTrade()`.

**Files:** `grid-bot-super-chart.js`, `grid-bot-overview.js`

### Step 5: Remove TV (future — not part of this PRD)

Once overlays are verified correct, remove TV from grid bot pages and give SC the full chart area. This is a separate task after review.

## Non-Requirements

- No changes to Redux state, grid bot form, or grid bot actions
- No backtest overlay support (separate PRD — `sc-grid-bot-backtest`)
- No replay mode (Phase 5)
- No shared-grid-bot-overview changes (can be migrated after grid bot details is done)
- No storybook stories — `createOrderLine` and `createPriceLine` are already proved
- No trading-terminal overlays (orders, PnL, break-even, alerts, etc.) on the grid bot chart — TV currently renders `<Alerts noEdit>` but this is unintended; it will be removed when TV is removed
- No removal of TV from grid bot pages — that happens after review confirms parity
