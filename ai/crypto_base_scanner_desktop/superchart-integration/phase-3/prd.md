# Phase 3 — Overlays — ✅ Done

**Status:** All overlays under 3a–3e ported and verified. 3f (custom shapes — callouts, custom-indicator shapes, multipoint drawings) is deferred; none of those shapes are required by shipped features and will be picked up if/when a feature needs them. The overlay-optimization subtask landed organically as the shared overlay hooks (`use-chart-colors`, `use-symbol-change-cleanup`, `use-draw-overlay-effect`) were built. Price/time select shipped as `[sc-price-time-select]`.

## Goal

Migrate all chart overlay components from TradingView APIs to SuperChart.
Each overlay is first proved in Storybook (`$SUPERCHART_DIR/.storybook/overlay-stories/`),
then ported to Altrady (`super-chart/overlays/`).

## Workflow

1. **Storybook** — create/update a story that exercises the overlay API in isolation
2. **Altrady** — port the working story into `super-chart/overlays/*.js`

## Status

### 3a. Order & position overlays (trading core)

#### TradingView handle primitives (`chart-functions.js`)

Two core methods build all order/position handles on the TV chart:

| Method | Draggable | Line style | Callbacks | Primary use |
|---|---|---|---|---|
| `createPositionLine` | No | Dashed | onModify, onCancel | Display-only: open orders, alerts, PnL |
| `createOrderLine` | Yes (onMove) | Solid | onModify, onMove, onCancel | Editable: trade-form handles, grid bot limits |
| `createTriggerPriceHandle` (wrapper) | Yes | Solid | onMove, onCancel | Entry conditions & expirations (delegates to `createOrderLine`) |

#### Complete handle inventory

**Orders — display-only** (`orders.js` → `createPositionLine`)

| Handle | Color | Label example | Actions |
|---|---|---|---|
| Regular open order (buy/sell) | `openBuyOrder` / `openSellOrder` | `"BUY 0.5 BTC"` | onModify, onCancel |
| Stop order | `stopBuyPrice` / `stopSellPrice` | `"STOP SELL 0.5 BTC"` | onModify, onCancel |
| Trailing stop — entry | `openBuyPrice` / `openSellPrice` | `"TS #1: BUY 0.5 BTC"` | onModify, onCancel |
| Trailing stop — stop loss | darkened buy/sell | `"TS #1: Stop at 42000"` | — |
| Take profit — start | `openBuyPrice` / `openSellPrice` | `"Start TP #1: SELL 0.5 BTC"` | onModify, onCancel |
| Take profit — target | darkened opposite side | `"Target TP #1: 5%"` | — |
| Take profit order | buy/sell color | `"TP 1: 0.5 BTC %5"` | onModify, onCancel |
| Emergency stop loss | darkened stop color | `"Emergency SL"` | onModify, onCancel |
| Stop loss order (with type) | darkened stop color | `"Stop loss for 42000"` | onModify, onCancel |
| Stop loss order (no type) | darkened stop color | `"Stop for 42000"` | onModify, onCancel |
| Creating order (transient) | buy/sell color | `"Creating"` | — |

**Edit orders — draggable** (`edit-orders.js` → `createOrderLine`)

| Handle | Color | Draggable | Notes |
|---|---|---|---|
| Entry price | buy/sell order color | Yes | onMove updates price field |
| Trigger price (trailing) | stop buy/sell color | Yes | via `createTriggerPriceHandle` |
| Stop price (stop order) | stop buy/sell color | Yes | optional onModify |
| Stop trailing price | stop buy/sell color | Yes | |
| Stop distance | stop buy/sell color | Yes | |
| Stop loss price | stop buy/sell color | Yes | validity-based opacity |
| Cool-down cancel price | stop buy/sell color | Yes | displays exact price |
| Take profit price | buy/sell order color | Yes | shows position % |
| Trailing take profit price | buy/sell order color | Yes | nested within TP handle |
| Stop limit price (OCO) | buy/sell color | Yes | OCO limit price |

**Alerts — display-only** (`alerts.js`)

| Handle | Type | Method | Color | Label example | Actions |
|---|---|---|---|---|---|
| Price alert | `price` | `createPositionLine` | `chartColors.alert` | alert note (max 20 chars) | onModify, onCancel (delete) |
| Time alert | `time` | `drawTimeLine` | `chartColors.alert` | "Trigger At {date}" + note | onSelect → edit, onDelete → confirm modal |
| Trendline alert | `trend_line` | `drawTrendLine` | `chartColors.alert` | note + 🔔 (pending) / 🏁 (triggered) | onSelect → edit, onDelete → confirm modal |

**Edit alerts — mixed** (`edit-alerts.js`)

| Handle | Type | Method | Color | Draggable | Notes |
|---|---|---|---|---|---|
| Price alert (saving) | `price` | `createPositionLine` | `chartColors.alert` | No | text: "Saving" |
| Price alert (editing) | `price` | `createOrderLine` | `chartColors.alert` | Yes | text: "Alert me when", onMove updates price |
| Time alert (editing) | `time` | `drawTimeLine` | `chartColors.alert` | Yes | Movable vertical line, mouse_up updates time |
| Trendline alert (editing) | `trend_line` | `drawTrendLine` | `chartColors.alert` | Yes | Both endpoints movable, mouse_up updates points |

**PnL / break-even handle** (`break-even.js` → `createPositionLine`)

| Handle | Color | Label example | Actions |
|---|---|---|---|
| PnL handle | `openSellOrder` (loss) / `openBuyOrder` (profit) | PnL amount + PnL % | onCancel → close position (if allowed) |

**Grid bot prices — draggable** (`grid-bot-prices.js` → `createOrderLine`)

| Handle | Color | Draggable | Notes |
|---|---|---|---|
| Stop loss limit | `openSellOrder` | Yes | |
| Take profit limit | `openBuyOrder` | Yes | |
| Upper price limit | `alert` | Yes | showLine: false |
| Lower price limit | `alert` | Yes | showLine: false |

**Entry conditions — draggable** (`edit-entry-conditions.js` → `createTriggerPriceHandle`)

| Handle | Color | Draggable | Notes |
|---|---|---|---|
| Entry condition price | `triggerPrice` | Yes | label: condition operator, right text: "Condition" |
| Entry condition time | `triggerPrice` | — | Time line (uses `drawTimeLine`, not order line) |

**Entry expirations — draggable** (`edit-entry-expirations.js` → `createTriggerPriceHandle`)

| Handle | Color | Draggable | Notes |
|---|---|---|---|
| Expiration price | `triggerPrice` | Yes | right text: "Expires at" |
| Expiration time | `triggerPrice` | — | Time line (uses `drawTimeLine`, not order line) |

**Replay mode PnL** (`replay/replay-position.js` → `createPositionLine`)

| Handle | Color | Label example | Actions |
|---|---|---|---|
| Replay PnL handle | `openSellOrder` (loss) / `openBuyOrder` (profit) | PnL amount + PnL % | None (fully display-only) |

#### Migration table

| Overlay | Status | PRD | Altrady | Notes |
|---|---|---|---|---|
| Orders (submitted) | DONE | `sc-orders` | `overlays/orders/` | All display-only order handles — entry, exit/TP, stop loss, smart, standalone, saving |
| Orders (editing) | DONE | `sc-orders` | `overlays/orders/edit-*.js` | All draggable trade-form handles — entry, exit/TP, stop loss, conditions, expirations |
| Entry Conditions | DONE | `sc-orders` | `overlays/orders/entry-conditions.js`, `edit-entry-conditions.js` | Submitted price/time lines + editing draggable handles (SC improvement: draggable time lines) |
| Entry Expirations | DONE | `sc-orders` | `overlays/orders/entry-expirations.js`, `edit-entry-expirations.js` | Same pattern as conditions |

### 3b. Alert overlays

| Overlay | Status | PRD | Altrady | Notes |
|---|---|---|---|---|
| Price Alerts | DONE | `sc-price-alerts` | `overlays/alerts/price-alerts/` | Submitted + editing + triggered. Horizontal handles via `createOrderLine` |
| Time Alerts | DONE | `sc-time-alerts` | `overlays/alerts/time-alerts/` | Submitted + editing + triggered. Vertical lines via `verticalStraightLine` |
| Trendline Alerts | DONE | `sc-trendline-alerts` | `overlays/alerts/trendline-alerts/` | Submitted + editing + triggered. Line segments via `segment` |

### 3c. Market data overlays

| Overlay | Status | Altrady | Notes |
|---|---|---|---|
| Bid/Ask | DONE | `bid-ask.js` | Live bid/ask price lines via `createPriceLine` |
| Break-even | DONE | `break-even.js` | Break-even line via `createBreakEven`/`updateBreakEven` |
| PnL Handle | DONE | `pnl-handle.js` | Position PnL overlay with close button (`createOrderLine`) |
| Price/Time Select | DONE | `InteractionController` + `ChartRegistry` | Form eye-dropper inputs (`PriceField`, `PriceTimeField`, `DatePickerInput`) call `ChartRegistry.getActive()?.interaction.start({once:true, onSelect})`. See `phase-3/price-time-select/prd.md` (`sc-price-time-select`) |
| Trades | DONE | `trades.js` | Trade markers via `createTradeLine` (buy/sell arrows at trade prices) |

### 3d. Grid bot overlays

| Overlay | Status | PRD | Altrady | Notes |
|---|---|---|---|---|
| Grid Bot Orders | DONE | `sc-grid-bot` | `overlays/grid-bot/grid-bot-orders.js` | Read-only order lines for grid levels |
| Grid Bot Prices | DONE | `sc-grid-bot` | `overlays/grid-bot/grid-bot-prices.js` | Draggable handles for upper/lower bounds, stop-loss, take-profit |
| Grid Bot SC Widget | DONE | `sc-grid-bot` | `grid-bot-super-chart.js` | Standalone SC widget for grid bot pages (replaces TV) |
| Backtest Times | DONE | `sc-grid-bot-backtest` | `overlays/grid-bot/backtest-times.js` | Draggable start/end vertical time markers |
| Backtest SC Widget | DONE | `sc-grid-bot-backtest` | `grid-bot-super-chart.js` | SC in backtest modal (replaces TV) |

### 3e. Scanner overlays

| Overlay | Status | Altrady | Notes |
|---|---|---|---|
| Bases | DONE | `bases.js` | `createBaseSegment`, `createBaseBox`, multi-style (respected/cracked/not cracked), selected base box with median drop |

### 3f. Custom shapes

| Overlay | Status | Storybook | Altrady | Notes |
|---|---|---|---|---|
| Callouts | TODO | — | — | Text annotations on chart |
| Custom indicator shapes | TODO | — | — | Shapes drawn by custom indicator logic |
| Multipoint drawings | TODO | — | — | Multi-point shape support |

## Constraints

- Each overlay must gate rendering on `readyToDraw` from `useSuperChart()`
- Overlays call SuperChart/klinecharts APIs through `chartController` — no direct
  klinecharts imports
- TV chart overlays must remain fully functional throughout
- Do NOT add convenience methods to `ChartController` upfront — add them as each
  overlay needs them during implementation
- Overlay files go in `super-chart/overlays/`, one file per overlay type

## Known Issues / TODO

- **No tooltips on order handles** — TV sets `cancelTooltip` ("Cancel editing") on editing handles and body hover tooltips. SC's `createOrderLine` supports tooltips (`tooltip`, `modifyTooltip`, `cancelTooltip`) but they're not wired yet. Affects all editing order handles.
- **No `wsOrderUpdates.closedOrders` filtering** — TV uses WebSocket closed-order tracking to immediately hide just-closed orders before the Redux state update arrives. SC relies solely on order status from Redux, which can cause a brief flash where a just-closed order remains visible. Implement when wiring order WebSocket updates to SC.
- **Font styling on overlay text** — TV uses Trebuchet MS bold 11px on all chart handle text. SC's `createOrderLine` accepts font properties (`bodyFont`, `quantityFont`, etc.) but they have no visible effect — the library likely doesn't support font customization yet. Once SC adds support, apply a consistent font across ALL overlay text labels (orders, alerts, PnL, etc.).
- ~~**All handle labels must be uppercase**~~ — RESOLVED: all `createOrderLine` text labels use `.toUpperCase()` across all SC instances.
- ~~**PriceLine is draggable — no way to disable**~~ — RESOLVED: replaced all `createPriceLine` calls with custom `priceLevelLine` overlay which is inherently non-draggable.

## Out of Scope

- Context menu (Phase 4)
- Hotkeys (Phase 4)
- Replay mode overlays (Phase 5)
- Quiz mode overlays (Phase 7)
- Custom indicators (Phase 8)
- Secondary chart instances (Phase 9)
