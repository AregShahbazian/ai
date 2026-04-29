# Review: /charts Page — `sc-charts-page`

## Round 1: initial implementation (TBD)

### Implemented

- _Filled in during Step 6 of `tasks.md`._

### Verification

Each TV behaviour the chart had on /charts must have a matching SC
behaviour (or an explicit "deliberately dropped" entry below).

#### A. Chart engine — basics

1. ✅ SC chart container fills each /charts grid cell. Other widgets in
   the layout (if any) are unaffected.
2. ✅ Live candles arrive for each cell's `coinraySymbol`.
3. ✅ Period bar visible. Changing period reloads candles at the new
   resolution; `ChartTab.resolution` updates in Redux DevTools.
4. ✅ Symbol change via the period bar's symbol-search reloads candles;
   `ChartTab.coinraySymbol` updates. Other charts unaffected.
5. ✅ Theme switch (light ↔ dark) re-styles every chart on /charts.
6. ✅ Editing chart colors in the chart-settings modal — preview updates
   live; Save → all live grid charts pick up the new colors.
7. ✅ Toggling chart settings (`miscShowOrderBookAskBid`,
   `miscShowBreakEvenPoint`, `basesShow`, `alertsShowLine`, etc.)
   updates the relevant overlays live across every cell.
8. ✅ Resize: shrink/grow the browser window, each cell resizes, layout
   doesn't break.
9. ✅ Adding a new chart-tab via the chart-tabs top bar mounts a new SC
   instance immediately. Closing a chart-tab disposes it cleanly.

#### B. Header buttons

10. ✅ **Alert** button visible on every cell.
11. ✅ **Replay** button visible on every cell.
12. ✅ **Settings** button visible on every cell.
13. ✅ **Buy** button NOT visible.
14. ✅ **Sell** button NOT visible.
15. ✅ Click **Settings** on chart 1 → chart-settings modal opens; preview
    chart renders alongside the live grid charts; no overlay bleed;
    Save → all live charts pick up new colors.
16. ✅ Click **Alert** on chart 1 → alerts form opens for chart 1's
    `coinraySymbol`. Editable price-alert overlay appears on chart 1.
17. ✅ Click **Replay** on chart 1 → picker mode arms on chart 1; click
    a candle on chart 1 → default replay starts.
18. ✅ Symbol-search trigger in the period bar IS clickable. Picking a
    different symbol re-binds the chart-tab to the new symbol.

#### C. Context menu (chart background right-click)

19. ✅ Right-click chart 1 background → context menu opens.
20. ✅ Menu items: **Create Alert at price** + **Start Replay** (and
    replay sub-items if a session is active) + **Copy Price**.
21. ✅ Buy/Sell entries NOT present.
22. ✅ Click "Create Alert at price" → alert form opens for chart 1's
    symbol with the clicked price prefilled.
23. ✅ Click "Start Replay" → replay session starts at the clicked time
    on chart 1.
24. ✅ Right-click on an overlay (order line, alert line) → overlay
    context menu opens with Edit/Delete/Save/Copy entries appropriate
    to the overlay type.

#### D. Per-tab replay isolation (HEADLINE)

25. ✅ Start a default replay on chart 1 → engine plays; replay timelines
    (start/end/current) draw on chart 1 only. Chart 2 keeps streaming
    live candles.
26. ✅ While chart 1 replays, start a default replay on chart 2 → both
    run independently; each cell shows its own `<ReplayControls>`.
27. ✅ Each chart's right-click context menu shows replay sub-items keyed
    to its own session.
28. ✅ Stop chart 1's session → `state.replay.sessions[chart1Id]`
    cleared; chart 2's session continues; `state.replay.sessions[chart2Id]`
    intact.
29. ✅ Stop chart 2's session → both back to live candles.
30. ✅ The mode-pick dialog never appears on /charts (every replay starts
    in DEFAULT mode); the toggle-mode button is absent from the
    `<ReplayControls/>` bar.

#### E. Replay hotkeys — last-interacted scoping

31. ✅ Start a default replay on each of chart 1 and chart 2.
32. ✅ Click chart 1's canvas → press the play/pause hotkey → chart 1's
    session responds. Chart 2 ignored.
33. ✅ Click chart 2's canvas → press play/pause → chart 2's session
    responds; chart 1 ignored.
34. ✅ Step / step-back / back-to-start / stop / cancel hotkeys all
    target the last-clicked chart.
35. ✅ Fresh page load — before any chart interaction, press a replay
    hotkey → no-op, no console errors.

#### F. Account selector per-cell replay gate

36. ✅ Account selector on chart 1's `MarketHeaderBar` is enabled while
    no chart is in replay.
37. ✅ Start a default replay on chart 1 → chart 1's account selector
    becomes disabled. Chart 2 / 3 / 4 selectors stay enabled.
38. ✅ Stop chart 1's session → chart 1's selector re-enables.

#### G. Per-cell currency data (icon, market cap, TA)

39. ✅ Open /charts with 4 cells, 4 different markets. Each cell's
    `MarketHeaderBar` shows its own currency icon, market cap, and rank.
    No cell shares another cell's currency.
40. ✅ Click the market-cap button on chart 1 → `CurrencyTechnicalAnalysis`
    popup shows chart 1's currency. Repeat on chart 2 → shows chart 2's.
41. ✅ After live `marketsUpdated` events fire, the icons / market caps
    don't flip between cells.

#### G2. Last-interacted chart-tab — bumps, visuals, swap-in

A. **Bump triggers**

42. ✅ Fresh page load → no chart-tab has the blue underline yet
    (`lastInteractedChartTabId === undefined`).
43. ✅ Pointerdown on chart 1's canvas → chart 1's per-cell
    `MarketHeaderBar` shows a 2px `var(--general-primary)` line at its
    bottom. Top tab-bar handle for chart 1 turns blue at the bottom
    (was grey).
44. ✅ Pointerdown on chart 2's `MarketHeaderBar` → bump moves to chart 2;
    chart 1 reverts to grey.
45. ✅ Pointerdown on an overlay (alert line / order line) inside chart
    3 → bumps to chart 3 (capture-phase listener on the cell wrapper
    catches it).
46. ✅ Click the Replay button on chart 4's header → bumps to chart 4
    even before clicking the canvas to pick a start time.
47. ✅ Click another active tab handle in the top tab-bar → bumps to that
    tab. Bottom line on the clicked handle turns blue.

B. **Chartless tabs**

48. ✅ Identify a chartless (inactive) tab in the top tab-bar — no bottom
    line (active tabs have grey or blue, inactive have none).
49. ✅ Click the chartless tab handle → swap fires:
    - The previously last-interacted (with chart) becomes chartless
      (no chart in the grid; handle in the top bar shows no bottom
      line).
    - The clicked tab becomes active and takes the chart slot in the
      grid.
    - `lastInteractedChartTabId` updates to the new active tab; its
      tab-handle and `MarketHeaderBar` show the blue line.
50. ✅ Click the now-chartless previously-last-interacted tab handle →
    triggers another swap (uses the new last-interacted's chart).
51. ✅ Click any chartless tab handle when no charts exist (degenerate
    case — every tab is inactive) → no-op, no errors.
52. ✅ The chartless tab CANNOT be set as last-interacted by clicking
    its handle alone — it has to first become active via the swap,
    after which the bump fires automatically.

C. **Page-level commands operate on last-interacted**

53. ✅ Press `closeSelectedChart` hotkey → closes the last-interacted
    chart-tab. Hotkey + bump propagation: clicking chart 2's canvas
    then pressing the hotkey closes chart 2.
54. ✅ Press `changeSelectedChartMarket` hotkey → market-select popup
    opens scoped to the last-interacted chart-tab.
55. ✅ Press `toggleWatchlist` hotkey → adds/removes the last-interacted
    tab's `coinraySymbol` to/from the default watchlist.
56. ✅ Fresh load (no bump yet) → page-level commands fall back to the
    first active tab.

D. **Visual indicator survival across state changes**

57. ✅ Start a default replay on the last-interacted chart → blue
    underline on the cell's `MarketHeaderBar` and blue line on the
    top tab-bar handle stay during the replay.
58. ✅ Stop the replay → indicators stay (the tab is still
    last-interacted, just live again).
59. ✅ Open chart-settings modal via the bumped chart's Settings button
    → indicators stay; close modal → indicators stay.
60. ✅ Switch chart layouts → `lastInteractedChartTabId` resets to
    `undefined` (or first active tab fallback fires); first
    canvas/tab interaction bumps and lights up the new chart.

#### H. Page-level hotkeys (`ChartsHotkeys`)

61. ✅ `newChart` hotkey opens the market-select popup with the
    "add new chart tab" intent.
62. ✅ `closeSelectedChart` hotkey closes the last-interacted chart-tab
    (with fallback to first active tab when nothing has been bumped).
63. ✅ `changeSelectedChartMarket` hotkey opens the popup keyed to the
    last-interacted chart-tab.
64. ✅ `toggleWatchlist` hotkey adds/removes the last-interacted tab's
    `coinraySymbol` to/from the default watchlist.
65. ✅ `toggleHotkeyInfo` hotkey works as before.

#### I. Visible-range persist

66. ✅ Pan chart 1, switch to a different chart-layout, switch back —
    chart 1's visible range is restored.
67. ✅ Toggle `miscRememberVisibleRange` off in settings → panning no
    longer persists; switching layouts resets to default view.

#### J. Trading interaction (must NOT work on /charts)

68. ✅ Open orders draw as read-only order lines.
69. ✅ Order lines are NOT draggable.
70. ✅ No "Edit Order" / `EditEntryConditions` / `EditEntryExpirations`
    overlays render in the DOM.
71. ✅ Buy / sell / closed-orders trading hotkeys do nothing on /charts.
72. ✅ No mobile `<ActionButtons/>` bar appears below any chart cell.

#### K. Trading Terminal regression

73. ✅ Open `/trade`. Header still shows Alert + Buy + Sell + Replay +
    Settings.
74. ✅ Switch tabs, change symbol, change resolution, change
    `exchangeApiKeyId`. All work as before.
75. ✅ Start a default replay session, run hotkeys, stop.
76. ✅ Open the chart-settings modal — preview chart renders alongside TT
    main; Save applies.
77. ✅ Replay-mode dialog still appears on TT (when
    `chartSettings.replayShowModeDialog` is on). Toggle button visible
    in the `<ReplayControls/>` bar.

#### L. Customer Service regression

78. ✅ Open a CS market or position page. Header shows Alert only
    (no Replay, no Settings, no Buy, no Sell).
79. ✅ Alert flow works against the staff session.
80. ✅ No replay UI; no chart context menu; no overlay context menu.

#### M. Grid-bot regression

81. ✅ Open a grid-bot settings page. Chart renders.
82. ✅ Open the backtest modal — both charts render; price handles +
    backtest time markers + order lines isolated per chart.
83. ✅ Backtest flow operates correctly.

#### N. Concurrency / lifecycle

84. ✅ Open `/charts` and `/trade` in separate browser windows. Both
    pages render independently.
85. ✅ Same window, navigate `/charts` → `/trade` → `/charts`. Charts
    remount cleanly. `window.chartRegistry.getAll()` (DevTools console)
    reflects only what's currently mounted.

#### O. Console / errors

86. ✅ Full smoke produces no React warnings, no
    `Cannot read properties of null` errors, no SC console errors.
87. ✅ Repo grep `<CandleChart .* toggleable` — zero hits.
88. ✅ Repo grep `DefaultTradingWidget` in `widgets/candle-chart.js` —
    zero hits.
89. ✅ Repo grep `handleTVSymbolChanged|handleTVIntervalChanged|handleTVVisibleRangeChanged`
    — only hits remain in
    `containers/trade/trading-terminal/widgets/center-view/tradingview/`
    (TV implementation — out of scope until Phase 10f).

### Known issues / cleanup

- ~~**Redux ↔ controller desync on `chartTabs`.**~~ ✅ Resolved
  (commit `daa709fb1f`). The apparent drift was a stale closure in
  `containers/market-tabs.js`: `itemProps` useMemo was missing
  `handleTabClick` / `onTabClose` from its deps, so `onClick` kept
  pointing at an old `handleTabClick` whose `tabs` closure was outdated.
  After clicking a tab to deactivate it, the next click on that same
  tab still saw it as active in the stale array → dispatched a
  `setLastInteractedChartTabId` for an inactive tab → controller's
  `currentTab` getter fell back to `activeTabs[0]` → wrong swap target.
  Fix: added `handleTabClick` and `onTabClose` to the `itemProps` deps
  and reverted `handleTabClick` to read `tab.active` from the React
  selector (no longer needs the controller-read workaround). Redux
  state was always correct.

### Apply steps

- HMR picks up most React changes.
- The new `LastInteractedChartContext` and the `ReplayHotkeys`
  optional-prop change require a hard reload after first save (context
  shape / component prop signature changes are not HMR-safe).
- No Superchart library build needed.
