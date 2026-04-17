# Review: Header Buttons — SuperChart Migration

## Code changes

### Header buttons (new)
- `super-chart/chart-controller.js` — `_createToolbarButton` helper, `createShareButton` (icon-only, no label), `createHeaderButtons` (5 buttons with FA icons, border colors, i18n listener), `setHeaderButtonsEnabled`, `setReplayButtonHighlight`, cleanup in `dispose()`
- `super-chart/header-buttons.js` — new React component, renders null, creates buttons on `readyToDraw` with `conditionalCallback` gating
- `super-chart/super-chart.js` — mounts `<HeaderButtons mainChart/>`, calls `createShareButton` instead of old `createToolbarButtons`

### Toolbar fixes
- `chart-controller.js` — `hideToolbarScrollbars()` adds `no-scrollbar` class to period bar
- `chart-controller.js` — split `getContainer()` (SC outer container for DOM queries) and `getChartDom()` (klinecharts canvas for mouse events)
- `overlays/price-time-select.js` — updated to use `getChartDom()` instead of `getContainer()`

### EditOrders stale form fix
- `overlays/orders/edit-orders.js` — fixed bug where switching sides (Buy→Sell) drew order handle at price 0 because `form.current` was stale from the previous effect run. Root cause: the `useRef` was set inside a `useEffect` (runs after render), but children read it during render. Fix: call `getInitializedTradeForm()` synchronously during render instead of in the effect. Removed the `useRef` entirely.

### Mobile action buttons + widget option
- `super-chart/super-chart.js` — added `SuperChartControls` component (mobile action buttons bar below chart, same styling as TV's `TradingViewControls`), wrapped chart + controls in flex column container
- `actions/constants/layout.js` — added `"SuperChart"` to `MOBILE_WIDGETS_DEFAULT_ORDER` after `"CenterView"` so it appears in the widget tabs modal

### Unified i18n for toolbar buttons
- `chart-controller.js` — single `_toolbarButtons` array and one `languageChanged` listener for all buttons (share + header). Previously share button had a separate listener (or was missing one for tooltip).

## Verification

### Desktop buttons
1. ✅ Open Trading Terminal with SC chart
2. ✅ Verify 5 buttons in toolbar: Alert, Buy, Sell, Replay, Settings
3. ✅ Verify correct FA icons: bell, arrow-up, arrow-down, backward, gear
4. ✅ Verify button labels match current language
5. ✅ Verify colored bottom borders: Alert (blue), Buy (green), Sell (red), Settings (gray), Replay (none)
6. ✅ Verify button order after Full Screen: Share, Alert, Buy, Sell, Replay, Settings
7. ✅ Verify icons have 4px right margin when button has a label

### Button actions
8. ✅ Alert: click opens alert creation form with current market price
9. ✅ Buy: click opens buy order form, handle appears on SC chart
10. ✅ Sell: click opens sell order form, handle appears on SC chart
11. ✅ Settings: click opens CenterView settings modal
12. ✅ Replay: click does nothing (expected — Phase 5)

### Buy/Sell side switching (regression from stale form fix)
13. ✅ Click Buy → handle appears at correct price
14. ✅ Reset form
15. ✅ Click Sell → handle appears at correct price (was broken: drew at price 0)
16. ✅ Reset form
17. ✅ Click Buy → handle appears at correct price
18. ✅ Drag handle → price updates in trade form
19. ✅ Cancel editing via handle → form resets

### Conditional callback gating
20. ✅ Alert: blocked without "trading" feature (shows upgrade modal)
21. ✅ Buy/Sell: blocked without "trading" feature
22. ✅ Buy/Sell: blocked without active device (unless paper trading)
23. ✅ Settings: no gating, always works

### Conditional visibility
24. ✅ Buy/Sell buttons do NOT appear on non-main charts (if testable)
25. ✅ Grid bot chart: only Share button appears (no Alert, Buy, Sell, Replay, Settings)

### Grid bot — Share button
26. ✅ Open grid bot settings or overview page with SC chart
27. ✅ Share button appears in toolbar
28. ✅ Click Share — uploads screenshot and opens share modal with URL
29. ✅ Share modal: copy URL, Facebook, X buttons work

### Toolbar
30. ✅ No scrollbars on the period bar
31. ✅ Share button is icon-only (no "Share" label)

### i18n
32. ✅ Change language in settings
33. ✅ Verify all header button labels and tooltips update (including Share tooltip)

### Coexistence with SC built-in buttons
34. ✅ SC's own Settings button still works
35. ✅ SC's own Screenshot button still works
36. ✅ Two settings buttons visible (expected — temporary)

### Cleanup
37. ✅ Navigate away from Trading Terminal and back
38. ✅ Verify no duplicate buttons appear
39. ✅ Verify no console errors on unmount

### Mobile — widget option
40. ✅ Open mobile view
41. ✅ Open widget tabs modal (settings icon)
42. ✅ Verify "SuperChart" appears in the list, right after "CenterView"
43. ✅ Enable SuperChart widget
44. ✅ Switch to SuperChart tab — chart renders

### Mobile — header buttons
45. ✅ Header buttons appear in SC toolbar on mobile (same as desktop)

### Mobile — action buttons
46. ✅ On SC tab: verify action buttons bar appears below chart (Create Alert, Trade)
47. ✅ "Create Alert" switches to AlertForm tab
48. ✅ "Trade" switches to Trade tab
49. ✅ Action buttons bar has top/bottom divider shadows
50. ✅ Action buttons bar is horizontally scrollable with no scrollbar

### Mobile — action buttons with forms
51. ✅ Switch to Trade tab, start editing an order, switch back to SC tab
52. ✅ Verify trade form buttons appear (Reset Form + Place Order)
53. ✅ Switch to AlertForm tab, start editing an alert, switch back to SC tab
54. ✅ Verify alert form buttons appear (Reset Form + Save Alert)
55. ✅ Verify correct button set shows based on last touched form
