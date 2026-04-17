---
id: sc-pnl-handle
---

# PRD: PnL Handle — SuperChart Integration

## Overview

Reimplement the PnL (break-even) handle overlay for SuperChart using the new `createOrderLine()` options-object API. The current implementation uses the old chainable-setter API (`createOrderLine(chart).setPrice().setText()...`). The new implementation passes all properties upfront via `createOrderLine(chart, options)`, matching the pattern established in `$SUPERCHART_DIR/.storybook/overlay-stories/overlays/order-line.ts`.

This is the first overlay to use the new API pattern. Orders, alerts, and other order-line-based overlays will follow the same pattern.

## Current Behavior (TradingView — `break-even.js`)

The PnL handle is a **left-aligned** order line at the position's `openPrice`:

- **Body text**: PnL in selected currency (e.g. `+12.50 USD` or `****` when masked)
- **Quantity text**: PnL percentage (e.g. `+2.50%`)
- **Cancel button**: Visible when user has an active API key, `positionsShowPnl` is on, and `positionsEnableCanceling` is on. Clicking closes/deletes the position.
- **Line**: Not shown (transparent)
- **Editable**: No — not draggable
- **Color**: Green (`openBuyOrder`) when profit >= 0, red (`openSellOrder`) when profit < 0
- **Body background**: `chartColors.grid`
- **Alignment**: Left-aligned with `marginLeft`

## Data Sources

### Position
- `currentPosition` from `CurrentPositionContext`
- Fields used: `unrealizedProfit`, `unrealizedProfitPercentage`, `investmentToUsd`, `openPrice`, `status`, `id`, `smartSettings`
- Only drawn when `status === "open"` and `id !== -1`

### Chart settings (Redux: `state.chartSettings`)
| Setting | Description |
|---|---|
| `positionsShowPnl` | Master toggle for PnL handle visibility |
| `positionsEnableCanceling` | Whether cancel button is shown |

### Colors (from `chartColors`)
| Key | Description |
|---|---|
| `openBuyOrder` | Green — used when profit >= 0 |
| `openSellOrder` | Red — used when profit < 0 |
| `grid` | Body background color |

### Other state
| Source | Description |
|---|---|
| `state.balances.hideAmounts` | When `BALANCES_MASKING.ALL`, body text shows `****` |
| `state.currencies.selectedCurrency` | Currency for PnL display (rate, key) |
| `mainChartSelectedExchangeApiKeyActive` | Whether cancel is allowed |

## Requirements

### R1 — Use options-object API

The chart-controller method must use `createOrderLine(chart, { ...options })` instead of chained setters. All visual properties are passed in the options object.

### R2 — Visual parity with TradingView

The handle must look and behave the same as the TradingView version:

- Left-aligned
- Body text = PnL value in currency
- Quantity text = PnL percentage
- Not draggable (`editable: false`)
- PnL color based on profit sign: green (`openBuyOrder`) when >= 0, red (`openSellOrder`) when < 0
- Line color = PnL color
- Body: background = grid, border = PnL color, text = PnL color
- Quantity: background = PnL color, border = PnL color, text = white
- Cancel button: background = white, border = PnL color, icon = PnL color
- Y-axis label: background = PnL color, border = PnL color, text = white

### R3 — Cancel behavior

- Cancel button visible only when `canClose` is true
- `onCancel` callback dispatches `closeOrDeletePosition` or `onDeleteSmartPosition` (with 200ms delay, same as current)
- No `onModify`, `onMove`, or `onMoveEnd` for now

### R4 — Follow overlay component patterns

The component (`pnl-handle.js`) must follow the same patterns as other SC overlay components (`trades.js`, `bid-ask.js`, `bases.js`):

- Get `readyToDraw`, `chartController`, `chartColors` from `useSuperChart()`
- Use `chartController.clearOverlays("pnl")` for cleanup
- Use `useSymbolChangeCleanup` hook for symbol change cleanup
- Use `util.useImmutableCallback` for stable callback refs where appropriate

### R5 — Chart-controller owns text building

The `createPnlHandle` method builds display text internally (`_buildPnlText`, `_buildPnlQuantityText`) from raw data (profit, percentage, currency). The component passes raw position data and flags — no text formatting in the component. This keeps rendering logic in the controller, consistent with how `_buildTradeText` works for trades.

## Non-Requirements

- No `onModify` callback (will be added later)
- No `onMove` / `onMoveEnd` (PnL handle is not draggable)
- No break-even point line (that's a separate overlay, already implemented as `break-even.js`)
- No changes to Redux state shape or chart settings
