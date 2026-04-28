# Review: Customer Service Charts — `sc-customer-service-charts`

## Round 1: initial implementation (TBD)

### Implemented

- _Filled in during Step 4 of `tasks.md`._

### Verification

Each TV behaviour the chart had on CS pages must have a matching
SC behaviour (or an explicit "deliberately dropped" entry below). Run
through this list against both `account/market.js` and
`account/position.js` unless a step is page-specific.

#### A. Pre-flight (TV → SC code swap)

1. `account/market.js` imports `CustomerServiceSuperChartWidget`, not
   `DefaultTradingWidget`. `mainChart={false}` prop is gone.
2. `account/position.js` imports `CustomerServiceSuperChartWidget`,
   not `DefaultTradingWidget`. `mainChart={false}` prop is gone.
3. `controllers/header-buttons-controller.js` Replay-button creation
   sits inside the `if (mainChart)` block.
4. No regressions in non-CS chart consumers (`grep` confirms
   `DefaultTradingWidget` is still imported by quiz / charts page;
   those routes still render the TV chart).

#### B. Chart engine — basics

5. SC chart container fills the left half of the CS page (`flex flex-1
   h-full min-w-[400px] min-h-[200px]` parent). Right panel of tabs
   unaffected.
6. Live candles arrive for the URL `coinraySymbol`.
7. Period bar is visible. Changing period in the period bar reloads
   candles at the new resolution. Period change is **not** persisted
   anywhere (no MarketTab to write to).
8. Symbol change via URL navigation (e.g. open another CS market)
   reuses the chart container — chart re-fetches candles for the new
   symbol cleanly, no stale candles.
9. Theme switch (light ↔ dark) re-styles the chart.
10. Editing chart colors in the TT chart settings modal — when the
    staff returns to the CS page (or has it open in another window),
    the colors apply.
11. Toggling chart settings (e.g. `miscShowOrderBookAskBid`,
    `miscShowBreakEvenPoint`, `basesShow`, `alertsShowLine`) updates
    the relevant overlays live on the CS chart.
12. Resize: shrink/grow the browser window, the chart resizes via
    `ResizeObserver`. Tabs panel layout doesn't break.

#### C. Header buttons

13. **Alert** button is visible in the period bar.
14. **Settings** button is **NOT** visible.
15. **Buy** button is **NOT** visible.
16. **Sell** button is **NOT** visible.
17. **Replay** button is **NOT** visible.
17a. Symbol-search trigger in the period bar is greyed out and not
     clickable. Hover does not turn the cursor into a pointer.
17b. Period picker (timeframe) is fully clickable; switching from `60`
     to `15` reloads candles at the new resolution.

#### D. Alert flow (must work as in TV, against staff session)

18. Click Alert button → `state.alertsForm.isEditing` flips to true.
19. An editable price-alert order line appears on the chart at the
    last price.
20. Drag the price-alert line vertically → price updates; on drag
    end, `editAlert` action dispatches with the new price.
21. Click the line body → `submitAlertsForm` dispatches; the alert is
    saved (visible in the staff's alerts list under
    `state.alerts.alerts`).
22. After save, the editable line is gone; the saved (read-only)
    alert line stays drawn.
23. Click the cancel-button on the editable line → `resetAlertForm`
    dispatches; the editable line disappears without saving.
24. Pre-existing staff price alerts for the chart's market are drawn
    on mount.
25. Pre-existing staff time alerts for the market are drawn on mount.
26. Pre-existing staff trendline alerts for the market are drawn on
    mount.
27. Triggered alerts (price / time / trendline) draw the FA bell
    marker at the trigger candle.
28. TA-scanner alerts (live, non-replay) draw on the chart for any
    matching TA scanner state in the staff session.

#### E. Trading interaction (must NOT work)

29. Customer's **open orders** are drawn as read-only order lines from
    `marketTradingInfo.openOrders` / `openSmartOrders`. Order-handle
    labels include base currency (e.g. `"104 XNO"`, not `"104"`).
30. Order lines are **not draggable** — attempting to drag does
    nothing.
31. Order lines have **no modify button** even when the staff has
    `openOrdersEnableEditing` on in their TT chart settings — the
    `getChartSettings` override pins this to `false` for CS.
32. Order lines have **no cancel button** even when the staff has
    `openOrdersEnableCanceling` on — same override mechanism.
33. PnL handle (position page) has **no cancel button** even when the
    staff has `positionsEnableCanceling` on — same override.
34. No "Edit Order" overlay exists — `EditOrders` is not in the
    React tree.
35. Right-click the chart background → no context menu opens (no
    "Create Buy at price", "Create Sell at price", etc.).
36. Right-click an order line → no overlay context menu opens.
37. No keyboard shortcut starts a trade (no `TradingHotkeys`).
38. Mobile (resize to mobile width): no `ActionButtons` bar appears
    below the chart.
39. While inspecting a customer with active open orders: clicking
    anywhere on an open-order line never dispatches `editOrder` /
    `cancelOrder` / `closeOrDeletePosition` (verify with Redux
    devtools — no actions for those types).

#### F. Replay (must NOT exist on CS)

37. No Replay header button (covered by step 17).
38. No replay timeline or controls.
39. `Ctrl+R` / replay hotkeys do not start a replay (no
    `ReplayHotkeys`).
40. Selectors for replay state keyed by `marketTabId === undefined`
    return falsy — no overlay (`BreakEven`, `Trades`, `PnlHandle`,
    `Bases`, alerts) accidentally enters a replay branch.

#### G. Market page-specific

41. `BreakEven` does **not** draw (no `CurrentPositionContext` from
    `WithPosition`; market page has no current position).
42. `PnlHandle` does **not** draw (same reason).
43. Bid/ask line draws for the customer's market.
44. Closed trades from `marketTradingInfo` draw as trade markers.
45. Bases overlay draws if the staff session has bases for the
    market.

#### H. Position page-specific

46. `BreakEven` draws at the customer's position break-even price
    when `miscShowBreakEvenPoint` is on. Disabled setting → no draw.
47. `PnlHandle` draws the customer's position PnL marker.
48. Switching position pages (`/customer-service/positions/<id>` →
    `/customer-service/positions/<otherId>`) re-fetches the position;
    `BreakEven` and `PnlHandle` redraw against the new position.
49. Customer's open orders for the position's market draw.
50. Customer's closed trades for the position's market draw.

#### I. Screenshot

51. The Screenshot button (added by `HeaderController.createShareButton`)
    appears in the period bar.
52. Click → opens the share modal with a screenshot of the chart.
53. Copy / share buttons inside the modal work as on the TT.

#### J. CS-page context tests

The Trading Terminal `Trading Terminal context tests` section in
`workflow.md` doesn't apply directly (no MarketTabContext above the
chart). The CS-equivalent context tests:

54. **Change `coinraySymbol`** — navigate from one CS market page to
    another. Chart unmounts/re-mounts cleanly:
    - `ChartRegistry` shows only one `cs-<uuid>` entry at a time.
    - No console errors / no double-disposed warnings.
    - Overlays redraw against the new market.
55. **Change `exchangeApiKeyId`** within a market — the right panel's
    `marketTradingInfo` re-fetches; the chart's overlays
    (`Orders`, `Trades`, `BreakEven`) update with the new
    exchangeApiKey's data. The chart instance itself does not need
    to remount (same `coinraySymbol`).
56. **Switch market page → position page** for the same market. New
    chart instance mounts, customer position now drives `BreakEven`
    and `PnlHandle`.
57. **Switch position page → market page** of a different market.
    Old chart disposes; new chart mounts; no leftover overlays.
58. **Switch tab in the right-side panel** (Market Info → Open
    Orders → Trades → Alerts → etc.) — chart is in a separate flex
    column and is unaffected by tab changes.

#### K. Concurrency / lifecycle

59. Open the TT in another browser window while a CS page is open in
    this window. Both charts render independently (separate windows
    → separate SC stores).
60. On the same window, navigating from a CS page to the TT and back
    cleanly mounts/unmounts both charts. `ChartRegistry` reflects
    only what's currently mounted.
61. HMR: editing `customer-service-super-chart.js` reloads the chart
    cleanly (controller dispose + remount).

### Apply steps

- HMR should pick up React changes.
- `chart-controller.js` and `header-buttons-controller.js` are class
  modules — HMR may reload, but SC instances created before the change
  retain the old class. Reload the page to be sure after editing
  controllers.
- No Superchart library build needed (changes are app-side only).
