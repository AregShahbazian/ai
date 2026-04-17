# Chart Overlay Mapping

Reference tables mapping every chart overlay to its SC creation method, color keys, and visibility toggles.

Source: `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`

## Color Mapping

Which `chartColors` keys each overlay uses. Color keys reference `themes/index.js` chart colors, overridable via `state.chartSettings.chartColors`.

| Overlay | Group | SC Method | Color Keys | Notes |
|---|---|---|---|---|
| **Alerts** | | | | |
| Price alert | `alerts` | `createOrderLine` | `alert` | Line, label bg, y-axis label |
| Editing price alert | `editAlert` | `createOrderLine` | `alert` | |
| Saving price alert | `editAlert` | `createOrderLine` | `alert` | |
| Triggered price alert | `triggeredPriceAlerts` | `createOverlay` (emojiMarker) | hardcoded `#00BFFF` | Not using chartColors |
| Time alert | `timeAlerts` | `createOverlay` (timeLine) | `alert` | |
| Editing time alert | `editTimeAlert` | `createOverlay` (timeLine) | `alert` | |
| Triggered time alert | `triggeredTimeAlerts` | `createOverlay` (timeLine) | `closedAlert` | |
| Trendline alert | `trendlineAlerts` | `createOverlay` (styledSegment) | `alert` | |
| Editing trendline alert | `editTrendlineAlert` | `createOverlay` (styledSegment) | `alert` | |
| Triggered trendline alert | `triggeredTrendlineAlerts` | `createOverlay` (styledSegment) | `closedAlert` | |
| **Trades** | | | | |
| Trade (buy, in position) | `trades` | `createTradeLine` | `closedBuyOrderPosition` | |
| Trade (buy, outside) | `trades` | `createTradeLine` | `closedBuyOrder` | |
| Trade (sell, in position) | `trades` | `createTradeLine` | `closedSellOrderPosition` | |
| Trade (sell, outside) | `trades` | `createTradeLine` | `closedSellOrder` | |
| **Position** | | | | |
| Break-even | `breakEven` | `createOverlay` (priceLevelLine) | `breakEvenPoint` | |
| PnL handle (profit) | `pnl` | `createOrderLine` | `openBuyOrder`, `background` | Green when profit >= 0 |
| PnL handle (loss) | `pnl` | `createOrderLine` | `openSellOrder`, `background` | Red when profit < 0 |
| **Bid/Ask** | | | | |
| Bid line | `bidAsk` | `createOverlay` (priceLevelLine) | `bidPrice` | |
| Ask line | `bidAsk` | `createOverlay` (priceLevelLine) | `askPrice` | |
| **Bases** | | | | |
| Base (not cracked) | `bases` | `createOverlay` (styledSegment) | `notCrackedLine2` | |
| Base (cracked) | `bases` | `createOverlay` (styledSegment) | `crackedLine2` | |
| Base (respected) | `bases` | `createOverlay` (styledSegment) | `respectedLine2` | |
| Base box | `bases` | `createOverlay` (box) | derived from base state + `"33"` alpha | |
| **Orders (submitted)** | | | | |
| Entry order | `submittedEntryOrders-{posId}` | `createOrderLine` | `openBuyOrder` / `openSellOrder` | Darkened on PENDING/ERROR |
| Exit order | `submittedExitOrders-{posId}` | `createOrderLine` | `openBuyOrder` / `openSellOrder` | |
| Stop loss | `submittedStopLossOrders-{posId}` | `createOrderLine` | `stopBuyPrice` / `stopSellPrice` | |
| Smart order (TP watch) | `submittedSmartOrders` | `createOrderLine` | `openBuyOrder` / `openSellOrder` | |
| Smart order (TP target) | `submittedSmartOrders` | `createOrderLine` | opposite side color, darkened | |
| Smart order (SL/stop) | `submittedSmartOrders` | `createOrderLine` | `stopBuyPrice` / `stopSellPrice` | |
| Smart order (trailing) | `submittedSmartOrders` | `createOrderLine` | `openBuyOrder` / `openSellOrder` | |
| Standalone order | `submittedStandaloneOrders` | `createOrderLine` | `openBuyOrder` / `openSellOrder` | |
| Saving order | `creatingOrders` | `createOrderLine` | `openBuyOrder` / `openSellOrder` | |
| Trigger price line | (various order groups) | `createOverlay` (priceLevelLine) | `triggerPrice` | |
| Trigger time line | (various order groups) | `createOverlay` (timeLine) | `triggerPrice` | |
| **Orders (editing)** | | | | |
| Editing entry order | `editEntryOrders` | `createOrderLine` | `openBuyOrder` / `openSellOrder` | |
| Editing exit order | `editExitOrders` | `createOrderLine` | `openBuyOrder` / `openSellOrder` | |
| Editing stop loss | `editStopLoss` | `createOrderLine` | `stopBuyPrice` / `stopSellPrice` | |
| Editing condition price | `editEntryConditions` | `createOrderLine` | `triggerPrice` | |
| Editing condition time | `editEntryConditions` | `createOverlay` (timeLine) | `triggerPrice` | |
| Editing expiration price | `editEntryExpirations` | `createOrderLine` | `triggerPrice` | |
| Editing expiration time | `editEntryExpirations` | `createOverlay` (timeLine) | `triggerPrice` | |
| **Entry conditions/expirations (submitted)** | | | | |
| Entry condition price | `submittedEntryConditions-{posId}` | `createOverlay` (priceLevelLine) | `triggerPrice` | |
| Entry condition time | `submittedEntryConditions-{posId}` | `createOverlay` (timeLine) | `triggerPrice` | |
| Entry expiration price | `submittedEntryExpirations-{posId}` | `createOverlay` (priceLevelLine) | `triggerPrice` | |
| Entry expiration time | `submittedEntryExpirations-{posId}` | `createOverlay` (timeLine) | `triggerPrice` | |
| **Grid Bot** | | | | |
| Upper/lower price | `gridBotPrices` | `createOrderLine` | `alert` | |
| Stop loss | `gridBotPrices` | `createOrderLine` | `openSellOrder` | |
| Take profit | `gridBotPrices` | `createOrderLine` | `openBuyOrder` | |
| Grid order line | `gridBotOrders` | `createOverlay` (priceLevelLine) | `openBuyOrder` / `openSellOrder` | |
| **Backtest** | | | | |
| Backtest time line | `backtestTimes` | `createOverlay` (timeLine) | `triggerPrice` | |

## Visibility Toggles

Which `state.chartSettings` toggles control whether each overlay is shown or hidden.

| Overlay | Group | Primary Toggle | Secondary Toggles | Notes |
|---|---|---|---|---|
| **Alerts** | | | | |
| Price alert | `alerts` | `alertsShow` | | |
| Triggered price alert | `triggeredPriceAlerts` | `alertsShow` | `alertsShowClosed` | Both must be true |
| Time alert | `timeAlerts` | `alertsShow` | | |
| Triggered time alert | `triggeredTimeAlerts` | `alertsShow` | `alertsShowClosed` | Both must be true |
| Trendline alert | `trendlineAlerts` | `alertsShow` | | |
| Triggered trendline alert | `triggeredTrendlineAlerts` | `alertsShow` | `alertsShowClosed` | Both must be true |
| **Trades** | | | | |
| Trade | `trades` | `closedOrdersShow` | `closedOrdersShowAll`, `closedOrdersShowPosition`, `closedOrdersNumber` | Multiple sub-toggles |
| **Position** | | | | |
| Break-even | `breakEven` | `miscShowBreakEvenPoint` | | |
| PnL handle | `pnl` | `positionsShowPnl` | | |
| **Bid/Ask** | | | | |
| Bid/Ask lines | `bidAsk` | `miscShowOrderBookAskBid` | | |
| **Bases** | | | | |
| Bases | `bases` | `basesShow` | `basesShowRespected`, `basesShowNotRespected`, `basesShowNotCracked`, `basesShowBox` | `basesShow` is in `state.chartSettings` but not exposed in settings modal |
| **Orders** | | | | |
| All submitted orders | `submitted*` | `openOrdersShow` | | Parent component gates on this |
| Entry conditions | `submittedEntryConditions-{posId}` | `openOrdersShow` | | Via parent |
| Entry expirations | `submittedEntryExpirations-{posId}` | `openOrdersShow` | | Via parent |
| **Grid Bot** | | | | |
| Grid bot prices | `gridBotPrices` | (always shown) | | Grid bot chart only |
| Grid bot orders | `gridBotOrders` | (always shown) | | Grid bot chart only |
| **Backtest** | | | | |
| Backtest times | `backtestTimes` | (always shown) | | Replay UI only |
