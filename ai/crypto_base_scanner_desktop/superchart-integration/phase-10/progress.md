# TV/SC Coexistence — Progress Tracker

Living doc. Updated as work proceeds. Companion to `tv-coex-plan.md` and `audit/`.

## Phase status

- **1 Audit** ✓
- **2 Global flag + UI toggle** ✓
- **3 Move SC aside** — skipped (no path collisions; verified)
- **4 Restore deleted TV files** ✓ — 87 files byte-identical to BASE
- **5 Wire TV alongside SC** ✓
  - 5.1 candle-chart entry ✓ (+ quiz stub provider)
  - 5.2 replay actions/reducer/selectors ✓ (TV+SC union)
  - 5.3 wrapper consumers ✓ (charts-grid, grid-bot×6, customer-service×2, quiz-question-chart)
  - 5.4 callsite branches ✓ (notes-form takeScreenshot, getSmartReplayController dual)
  - 5.5 i18n ✓ (centerView.tradingView restored + SC overlay/replay closures)
  - 5.6 remaining bucket-A ✓
  - 5.6b proactive export cross-check ✓
- **6 State/datafeed reconciliation** ✓ — replay state unions, offset helpers (A), position overrides (C) all dual-mode
- **7 Verify both libs work** ✓ — B4/B5/C/D confirmed; B3 (TV→SC mid-replay trades) unverified, tracked under Other open
- **8 Squash final commit** ✓ — items 1–28 squashed into `622aa818e2 feat: SuperChart integration with TV coexistence [sc-tv-coex]`

## ABCD audit (deeper provider-split items)

- **A** Price/time offset dual helpers ✓ — 4 callsites (`actions/trading`, `actions/alerts`, `util/trade-form`, `entry-expiration`). Pattern: `getTvPriceOffset() ?? ChartRegistry.get(activeTabId)?.getPriceOffset()`. Also fixed pre-existing SC-only regression: `util/trade-form.priceOffset` was using `this.id` (random form UUID, not a chart id) → ChartRegistry lookup failed → TP/SL placed at current price with no offset. Now uses `TradingTabsController.get().activeTab.id`.
- **B** Backtests widget — controllers wired ✓; mid-replay switches:
  - **B1** TV→SC mid-replay crash ✓ (root cause: save handler bypassed the safe-callback gate)
  - **B2** SC→TV must block via "stop first" modal ✓ (root cause: same)
  - **B3** TV chart still shows session trades when switching back ⏳ (defer — likely fixed by B1/B2 fully gating the switch; user to retest)
  - **B4** TV trade-form limit-entry order-line not drawn ✓ (root cause: C — getPriceOverrides was SC-only, so lastPrice stayed at real-time while chart showed replay candles → line offscreen)
  - **B5** TV "pick on chart" for date + price ✓ (both dual-mode now)
- **C** `market-tab.js getPriceOverrides()` ✓ — dual-mode: TV reads `state.replay.replayContextGlobal.price` (BASE-pattern, with symbol guard); SC keeps per-tab session
- **D** Quiz controllers ✓ — `/quiz` route now dual-mode. Single `QuizController` exposes both `animation` (SC) and `draw` (TV) sub-controllers. Question controllers carry both code paths and dispatch on `quizController.draw?.tv` (truthy once TV's onChartReady fires `setTradingView`). Both `QuizContext` (SC-side, `~/containers/quizzes/quiz-context`) and `TvQuizContext` (`~/containers/trade/trading-terminal/quiz/quiz-context`) are populated with the same controller in `containers/quizzes.js`. `use-quiz.js` pick-on-chart is dual-mode: SC `ChartRegistry.get("quiz")` first, TV `startPriceTimeSelect` fallback.

## Other open

- **Task 24** Modal preview chart switches with toggle ✓ — `preview-chart.js` PreviewChartWidget branches on `chartSettings.chartProvider`. TV path renders the restored BASE `TradingPreviewComponent` (no overlays in BASE → nothing to port). SC path unchanged.
- **B3** TV→SC mid-replay still shows session trades when switching back — unverified after B1/B2 root-cause fixes. Needs explicit retest.

## Known issues (not regressions, not fixed)

- **Time-alert / entry-expiration timezone bug on TV `v28.5`**: chart-click pick lands 4h earlier on UTC+4. Caused by `tradingview/price-time-select.js`'s `+ utcOffset*60` adjustment over-correcting against `v28.5`'s `crossHairMoved.time` semantics. Confirmed to work on `v27.003` (default) and to reproduce identically in prod on `v28.5`. Not introduced by this branch — leaving as-is.

## Hard rules in force

- TV files at TV paths: byte-identical to BASE — **relaxed for the per-section TV preview follow-up** (commit 30): `tradingpreview.js` + `tradingview/controllers/dummy-data-provider.js` modified, additive files under `tradingview/settings/` added. Hard rule still applies to all other TV-path files.
- Shared files: additive only (TV restored + SC kept)
- Default no comments; explain only non-obvious WHY
- No commits/push without explicit ask; tag commits `[sc-tv-coex]`
- Post-BASE 5.3.x commits (favicon, etc.) are out of scope (separate porting)
- Quiz: removed from trading-terminal (kept), lives only in `/quiz` route, must support both libs

## Reactive fixes applied so far (Phase 7)

- TV vendor script loader + eslint global + webpack copy
- TV quiz stub for TT
- TV i18n `centerView.tradingView` subtree (en/nl/es)
- `useActiveSmartReplay` provider-aware (reads `replayContextGlobal` in TV mode)
- `getSmartReplayController` dual-mode (SC mode uses `TradingTabsController.get().activeTab.id`)
- `switchChartProvider` clears backtests + awaits outgoing lib's `handleStop`
- `replay-backtests` reloads on smart-controller identity change
- **B1**: clear widget/backtest state pre-handleStop (avoid stale-closure renders)
- **B2**: `switchChartProvider` routes via outgoing lib's `replaySafeCallback` when replay is active — confirm modal fires before switch

## Active work

- (none — feature branch sits on two commits: `622aa818e2` (squashed feature) + `42204e4ec1` (per-section TV preview follow-up))

## Commit log on this branch (`feature/superchart-integration-tv-coex`)

Tag suffix: `[sc-tv-coex]`. Latest commits in chrono order:

1. Phase 2 chart-provider toggle
2. Phase 4 restore 87 TV files
3. Phase 5 wire TV alongside SC (router components, replay state union, notes-form, candle-chart)
4. Phase 5.6b TV-era exports restored (CHART_VERSIONS, comboToTvCombo, etc.)
5. TV vendor script loader + toggle defer-to-save UX
6. webpack TV vendor copy (dev configs)
7. eslint TradingView global + webpack import position parity
8. webpack.build-web revert of speculative TV pattern
9. TV quiz stub + i18n centerView.tradingView subtree
10. `useActiveSmartReplay` TV-aware
11. `getSmartReplayController` SC-mode `getState` fix
12. Backtests-clear + TV-aware session fields
13. Backtests reload on controller identity change
14. Stop active replay before provider switch (initial cut)
15. B1+B2 — clear-before-stop + replay-safe confirm modal (partial)
16. **B1+B2 root-cause fix**: gate the entire chartSettings save behind the replay-safe callback — Save handler no longer leaks chartProvider through outer editChartSettings dispatch
17. **B1+B2 confirm modal**: switch uses our own openModal("confirm") with Yes/No instead of the lib's "stop first" info-only modal — fires for ANY active replay (lib's modal needed willLoseDataIfStopped which TV gates on trades.length)
18. **Modal hotkey rebind after TV→SC**: key outer ModalsHotkeys on chartProvider so Mousetrap rebinds esc/enter when TV's inner ModalsHotkeys unmounts. Also dropped `[sc-tv-coex]` console.logs from chart-provider.
19. **B5 date-picker chart-pick dual-mode**: TV uses `startPriceTimeSelect`, SC uses `ChartRegistry.interaction`. Eye-dropper button now works in TV mode.
20. **B5 price-field chart-pick dual-mode**: same pattern applied. TV → `startPriceTimeSelect`; SC unchanged.
21. **C — getPriceOverrides dual-mode** (`models/market-tabs/market-tab.js`): TV branch reads `state.replay.replayContextGlobal.price` with coinraySymbol guard (BASE pattern); SC keeps per-tab session. Fixes **B4** (order-line was drawn at real-time price → offscreen during replay).
22. **Removed temporary debug logs** from `tradingview/edit-orders.js` — now byte-identical to BASE again.
23. **A — offset helpers dual-mode** at all 4 callsites. Also fixes pre-existing SC-only TP/SL placement regression in `util/trade-form.priceOffset` (was using wrong id).
24. **A follow-up — swap ?? order to SC-first, TV-fallback**: TV's module-level `chart` (in `price-time-select.js`) lingers after TV unmount; its `getPriceOffset`/`getTimeOffset` then return the fallback (60 / 0.001) instead of `undefined`, polluting SC mode after a TV→SC toggle. New pattern: `ChartRegistry.get(id)?.getXxxOffset() ?? getTvXxxOffset() ?? <default>`. When SC is active, ChartRegistry has the controller, so TV's stale value is never consulted.
25. **SC trade-form reset on backtest stop** (`trading-terminal-chart.js`): added `ResetTradeFormOnReplayChange` inside TT's ReplayContextProvider — watches `session.startTime` for active marketTab, dispatches `resetTradeForm(true, true)` on transition after first mount. Mirrors TV's `use-replay` pattern. Prevents leftover limit-order state from a finished backtest carrying into the next context.
26. **D — quiz controllers dual-mode**: shared `QuizController` now has `animation` (SC) AND `draw` (TV). Question/edit/play/preview controllers restore BASE TV methods (chartComponents, tvSetup, saveLoadAdapter, refreshTv, getInitialCandles, getGapCandles) and dispatch by `quizController.draw?.tv` for the few divergent methods (`drawQuestion`, `loadQuestion`, `refreshRanges`, `questionsCanTransition`, `reloadQuestion`). Both QuizContexts (`~/containers/quizzes/quiz-context` SC-side, `~/containers/trade/trading-terminal/quiz/quiz-context` TV-side) populated from a single useQuiz() in `containers/quizzes.js`. `use-quiz.js` pick-on-chart dual-mode: SC `ChartRegistry.get("quiz")` first, TV `startPriceTimeSelect` fallback. TV chart's `onChartReady` calls `quizController.draw.setTradingView(...)` which activates `draw.tv`.
27. **NoopQuizContextProvider mounted once** in `containers/logged-in.js` around all Routes. Quiz lives only on /quizzes; everywhere else TV's restored files would NPE reading `quizController.draw`/`questionController`. Single inert stub satisfies those reads. /quizzes shadows the stub locally with its real Providers. Removed per-chart wrappers (`candle-chart.js`, `customer-service-chart.js`, `charts-grid-item.js`).
28. **D follow-up — Question TV methods restored**: `updateDrawingsTrigger`, `setCandles`, `refreshStudies`, `createStudies`, `loadStudies`/`removeStudies`, `loadDrawings`/`clearDrawings`, `fetchCandlesToDraw`, `loadQuestionCandles` re-added on `Question` (TV-only, no-ops in SC). `drawSolutionCandles` now dispatches on `draw.tv`. `api-controller.fetchCandles` restored. **Race fix**: provider dispatch in quiz controllers switched from `draw?.tv` (set asynchronously by TV's `onChartReady`) to `chartSettings.chartProvider` (synchronous redux state). All TV-path entry points (`refreshTv`, `drawQuestion`, `loadQuestion`, `getInitialCandles`, `questionsCanTransition`, `reloadQuestion`) `await draw.loadTv()` first so TV chart-ready becomes a hard dependency.

---

**Pre-squash refactors** (rolled into commit `622aa818e2`, didn't get their own log entries):

- `CHART_PROVIDER` enum replaces `"tradingview"`/`"superchart"` literals; `DEFAULT_CHART_PROVIDER` + `DEFAULT_CHART_VERSION` exported.
- `useChartProvider()` hook adopted in date-picker-input, price-field, modals-global-context, use-active-smart-replay; `notes-form` mapStateToProps gets `|| DEFAULT_CHART_PROVIDER` for parity.
- `isTradingView(state)` helper added; adopted in `actions/replay`, `market-tab`, all 4 quiz controllers, and `switchChartProvider` itself.
- Removed dead `SET_REPLAY_HANDLERS` (was already dead in BASE — declared + reducer-cased but never dispatched/read).
- Quiz-context re-exports shape constants from TV-side to prevent drift; SC keeps its own `React.createContext` so quizzes.js can mount distinct providers.
- `selectActiveReplay*` selectors (`models/replay/selectors.js`) now WeakMap-memoized TV→session projection. Fixes time-alert validation, entry-expiration "would expire immediately" warning, and market-tab `lastPrice` pinning during TV active replay.
- `?.`-chain hardening in `actions/trading.js` and `actions/alerts.js` for `TradingTabsController.get()?.activeTab?.id`.
- i18n closure of hardcoded labels in SC overlay context-menu groups, position-label prefixes, replay-controls (Draw speed, Order amount, Exit Backtesting, etc.).

---

29. **Squash to single commit** (`622aa818e2 feat: SuperChart integration with TV coexistence [sc-tv-coex]`): 298 files, ~18.6k inserts; all items 1–28 + pre-squash refactors collapsed.

30. **Per-section TV preview chart** (`42204e4ec1 feat: per-section TV preview chart in chart-settings modal [sc-tv-coex]`):
    - TV preview now mirrors SC's per-tab behavior — different overlays + candle subset + visible price range per chart-settings tab. Previously TV preview rendered all overlays simultaneously regardless of tab.
    - Shared preview module: moved `preview-candles.js` + `preview-trading-data.js` from `super-chart/preview/` to `widgets/preview/` (provider-neutral location). New `preview-view.js` holds per-section `rightOffsetPx` + `priceRange` constants consumed by both `super-chart/preview/preview-tab-configs.js` and `tradingview/settings/preview-sections.js`. Render JSX stays provider-specific.
    - New TV-side overlay components: `preview-sections.js`, `preview-quiz-replay-timelines.js`, `preview-editing-handles.js` (entry-condition price+time handles, stop-loss handle drawn from `previewEditingState`; live `EditEntryConditions`/`EditOrders` are Redux-coupled and skipped in preview).
    - `tradingpreview.js` + `tradingview/controllers/dummy-data-provider.js` modified — accepts SC candles via constructor, ChartContext's `marketTradingInfo` merged from SC's preview-trading-data (openOrders + trades + alerts + triggeredAlerts + taScannerAlerts), `timeIsInVisibleRange: () => true` added so TimeAlert overlay doesn't NPE. Per-section visible-range computed from `VISIBLE_FIRST_BAR=36` (matches SC's last-67-candle window) + `rightOffsetBars` (`rightOffsetPx/10`). Y-axis pinned via `chart.getPanes().find(hasMainSeries).getMainSourcePriceScale().setVisiblePriceRange(range)` with 30% padding (10% per side → 60% pad total; SC's klinecharts edge-pins overlays outside its range, TV clips them — pad keeps stop-loss order at 66000 visible above the 65500 pin).
    - Added missing defaults to SC's `previewMarketPositions[0].smartSettings`: `entryExpiration: {enabled: false}`, `entryCondition: {enabled: false}`, `exitLadder: {exitPriceType: "FIXED"}` — TV's Orders reads these, SC doesn't.
    - `closedOrdersShowTop` setting reinstated in unified chart-settings UI, TV-only render gate (`activeProvider === TRADINGVIEW`). Reducer default added. Draw-logic was already intact in `tradingview/controllers/chart-functions.js` + `tradingview/trades.js` (it survived the SC port; only the UI line + reducer default were missing).
    - `togglePreviewChart()` global registered (via `storeGlobal`) whenever the preview chart is mounted — flips local `chartSettings.chartProvider` without persisting. Mirrors `toggleChart()` for the modal-local case.

## Updating this doc

- Update after each commit that ships a meaningful unit of behavior
- Move ABCD/Task items into "fixes applied" once their fix is committed
- Don't bloat — terse status, ~150-line cap
