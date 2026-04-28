# Multi-Chart Unblock — Review

## Round 1 verification

Numbered checklist covering every page and feature touched by R1–R7
plus the page-agnostic replay rewires (replay-timelines, replay-hotkeys,
header-buttons). Mark ✅ when verified; add a Round 2 section below for
any bug found.

Note on what is NOT testable: Altrady gates UI such that the TT main
chart cannot be interacted with while the chart-settings modal is open,
and the grid-bot settings chart cannot be interacted with while the
backtest modal is open. Tests assume only the *visible/active* chart
of each pair is interactable.

### TT main + chart-settings preview (R2)

1. ✅ Open chart settings modal → preview chart and TT main chart render
   simultaneously, both showing the active tab's symbol on the main
   side and the hardcoded BTC/USDT on the preview. No overlay bleed
   between them.
2. ✅ Toggle "Preview" off in modal → only TT main remains, no flicker.
   Toggle on → preview reappears alongside.
3. ✅ Change a chart color in the modal → preview updates immediately,
   TT main does not change.
4. ✅ Save settings → modal closes; TT main picks up the new colors;
   preview unmounts cleanly.
5. ✅ Cancel settings → modal closes; preview unmounts; TT main colors
   unchanged.

### Grid-bot settings + backtest (R3, R4 grid-bot inputs)

6. ✅ Open grid-bot settings → settings chart renders.
7. ✅ Open the backtest modal over it → both charts render with their own
   order lines, price handles, time markers, trades. No overlay bleed.
8. ✅ Drag a price handle on the backtest chart → only the backtest
   form/handle updates.
9. ✅ Click chart-pick on a backtest-modal price-field → crosshair
   attaches to the backtest chart.
10. ✅ Drag the backtest start/end time markers → backtest date pickers
    update.
11. ✅ Close backtest modal → settings chart and form remain functional;
    settings-page price-field chart-pick attaches to the settings
    chart.
12. ✅ Mobile (collapsed): toggle "Show Chart" → settings chart still
    renders. Open backtest modal → same dual-chart behavior.
13. ✅ Grid-bot overview page → chart still renders normally (overview
    has no form, so no `BotFormContext.chartId` plumbing — defensive
    UUID fallback path).

### Notes screenshot (R4 takeScreenshot)

14. ✅ From TT, take a note screenshot → screenshot captures the active
    tab's TT main chart.
15. ✅ Switch TT tabs, take a note screenshot → screenshot captures the
    new active tab's chart.
16. ✅ Take a note screenshot with no SC widget on screen (e.g. mobile
    layout without chart tab active) → callback receives `false`,
    no crash.

### TT inputs picker (R4 price-field, date-picker-input)

17. ✅ In TradeForm, click chart-pick on entry-condition price → crosshair
    on TT main; click → price populates the field.
18. ✅ In TradeForm, click chart-pick on entry-condition date → crosshair
    on TT main; click → date populates.
19. ✅ In AlertsForm price-alert, click chart-pick → works. Same for
    trend-line-alert and time-alert.
20. ✅ In Position exit/increase modals, click chart-pick on price → works.
21. ✅ The chart-pick button is visible and clickable in every form above
    — no hidden state, no disabled state (R4.4).

### Replay (R6, Q3, page-agnostic rewires)

22. ✅ Start a default replay session on TT tab A → engine plays, replay
    timelines (start/end/current) render on the TT main chart.
23. ✅ While replay is running, switch to TT tab B → tab A's session
    terminates cleanly (engine auto-exits on symbol change); tab B
    shows live data; in Redux DevTools `state.replay.sessions[tabA.id]`
    is cleared, NOT orphaned under the new tab's key. (Verifies the
    `_sessionChartId` pin still routes cleanup to the originating tab
    after the `controller.id` rewire.)
24. ✅ Switch back to tab A → tab A shows live data, no replay session,
    no stale timelines on the chart.
25. ✅ Replay hotkeys (play/pause, step, step back, back-to-start, stop,
    buy, sell) work during an active session on the same tab.
26. ✅ Stop replay session → session cleans up; no orphan state in
    `state.replay.sessions` Redux DevTools.
27. ✅ Start a smart replay (backtest) session → backtest chart, time
    markers, order lines render on TT main. Backtests widget shows
    correct active backtest.
28. ✅ Use `replaySafeCallback`-guarded actions during a session: cancel
    an order from `my-orders/order-row` → confirmation dialog gates
    the action correctly. Same for `my-orders-header` actions and
    `list-items` go-to-position.
29. ✅ End-of-data: play replay until session marks finished → engine
    pauses, status transitions to FINISHED, chart shows full range.
30. ✅ With chart-settings modal open during a replay session: replay
    continues to drive TT main; preview chart shows static dummy
    candles unaffected by the replay engine.

### TT context tests (workflow.md)

31. ✅ **Tab change** — switch tabs while picker active → previous picker
    cancels via outside-click; new tab becomes target on next pick.
32. ✅ **Symbol change** — change `coinraySymbol` on a tab → TT main
    redraws.
33. ✅ **Resolution change** — change resolution → TT main redraws.
34. ✅ **API key change** — switch `exchangeApiKeyId` → no chart errors,
    overlays continue to render.

### Grid-bot context tests (workflow.md adapted)

35. ✅ Change market in grid-bot settings picker → settings chart switches.
36. ✅ Open backtest modal, change market in backtest's market picker →
    backtest chart switches.

### Registry + page-agnostic hygiene (R4.3, R6)

37. ✅ With both TT main and chart-settings preview open, in dev tools:
    `window.chartRegistry.getAll()` returns both controllers keyed by
    their ids; `.get(/* tabId */)` returns the TT main controller;
    `.get(/* preview-uuid */)` returns the preview controller.
    `.getActive` / `.setActive` are undefined.
38. ✅ Close all charts → `window.chartRegistry.getAll()` returns `{}`.
39. ✅ Repo grep `ChartRegistry.getActive\|ChartRegistry.setActive` →
    zero hits.
40. ✅ Repo grep `WORKAROUND\|TEMPORARY.*singleton\|TEMPORARY.*SC ` in
    `src/` → zero hits related to the multi-instance blocker.
41. ✅ Repo grep `marketTabSync\?\?\._marketTabId\|marketTabSync\._marketTabId`
    in `src/containers/trade/trading-terminal/widgets/super-chart/` →
    only one hit, in `controllers/context-menu-controller.js` (intentional
    "is this a TT chart?" gating). Neither `replay-timelines.js`,
    `replay-hotkeys.js`, `replay-context.js`, `replay-controller.js`,
    nor `header-buttons.js` references `marketTabSync._marketTabId`
    or reads `chartId`/`marketTabId` from `MarketTabContext` for
    replay state keying.

### Console / errors

42. ✅ Full smoke (steps 1–41) produces no React warnings, no
    `Cannot read properties of null` from chart-pick noop fallback,
    no SC console errors.
