# Review: Price Alerts — SuperChart Integration

## Round 1: Body text casing, cancel button colors, marketTradingInfo safety (2026-03-24)

### Bug 1: Editing alert body text not uppercased
**Root cause:** `bodyText` passed as-is from i18n. TV's `createOrderLine` calls `.toUpperCase()` on text internally; SC does not.
**Fix:** Call `.toUpperCase()` on `bodyText` in `createEditingPriceAlert` before passing to `createOrderLine`.

### Bug 2: Submitted alert cancel button colors inverted
**Root cause:** Cancel button has `cancelButtonBackgroundColor: "#FFFFFF"` and `cancelButtonIconColor: color` — but for submitted alerts the cancel button should have alert-color background with white icon (matching the quantity style).
**Fix:** Swap: `cancelButtonBackgroundColor: color`, `cancelButtonIconColor: "#FFFFFF"`. Also update `cancelButtonBorderColor: color` (stays same).
**Design notes:** Also update PRD R2 and design doc to reflect correct submitted cancel button colors.

### Bug 3: Console error on symbol change — `marketTradingInfo` undefined
**Root cause:** `marketTradingInfo` from `MarketTabDataContext` can be `undefined` during loading or when no symbol is set. Destructuring `{alerts, triggeredAlerts}` from `undefined` throws. The TV approach uses `useTradingViewMarket()` which defaults to `EMPTY_MARKET_TRADING_INFO` (safe empty arrays). SC overlays access `MarketTabDataContext` directly, which has no such safety.
**Fix:** Import `EMPTY_MARKET_TRADING_INFO` from `~/actions/trading` and default: `const {alerts, triggeredAlerts} = marketTradingInfo || EMPTY_MARKET_TRADING_INFO`. Apply same pattern in `trades.js` for consistency.
**Design notes:** This is the standard pattern for all SC overlays accessing `marketTradingInfo`. Document in the design that `marketTradingInfo` must always be defaulted to `EMPTY_MARKET_TRADING_INFO`.

### Verification
- [x] Editing alert body text shows "ALERT ME WHEN" (all caps)
- [x] Submitted alert cancel button: blue background, white icon
- [x] Switch symbols rapidly — no console errors from undefined marketTradingInfo
- [ ] Triggered alerts still render correctly with closedAlert color

## Round 2: Empty note shows space, line hide uses wrong approach (2026-03-24)

### Bug 4: Empty quantity text renders visible space when alertsShowNote is false
**Root cause:** `buildQuantityText` returns `""` when `alertsShowNote` is false, but `createPriceAlert` still passes it as `quantity`, and the quantity section renders visibly (perhaps as a space/padding). Should hide the quantity section entirely.
**Fix:** When `quantityText` is empty, set `isQuantityVisible: false` in `createPriceAlert`. Also hide body (`isBodyVisible: false` is already set). This ensures the handle shows only the cancel button and y-axis label when notes are off.

### Bug 5: Line not hidden by `undefined` lineStyle
**Root cause:** `createPriceAlert` uses `lineStyle: showLine ? "dashed" : undefined` to hide the line. SC doesn't interpret `undefined` lineStyle as "no line" — it falls back to a default style.
**Fix:** Use `lineColor: showLine ? color : "transparent"` instead. Keep `lineStyle: "dashed"` always (or omit when transparent). Same fix needed in `createSavingPriceAlert`.

### Verification
- [ ] With alertsShowNote off — no visible body or quantity, only cancel button + y-axis label
- [ ] With alertsShowLine off — no horizontal line visible
- [ ] With both off — only cancel button and y-axis label at price level

## Round 3: Triggered alerts are icons, not order lines (2026-03-24)

### Bug 6: Triggered alerts rendered as order-line handles
**Root cause:** PRD R6 initially said triggered alerts use the same visual structure as submitted alerts. In reality, TV renders triggered alerts as bell icon markers on the candle (via `drawClosedAlert` → `createMultipointShape` with icon `0xf0f3`), not as order lines.
**Fix (PRD only):** Updated R6 to describe icon markers. Triggered alert rendering must be a separate component (`triggered-price-alerts.js`). Remove triggered alert code from `price-alerts.js` — that code currently creates order-line handles for triggered alerts, which is wrong. Implementation deferred to a follow-up task.

### Verification
- [ ] PRD R6 correctly describes icon marker behavior
- [ ] `price-alerts.js` no longer renders triggered alerts (removed in implementation)
