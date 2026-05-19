# TV → SC Port Coverage Map

**Status quo (post `[sc-tv-coex]`):** TV and SC now coexist in the app.
`chartSettings.chartProvider` (default `superchart`) switches the active
chart at runtime via `CandleChart` → either `MainChartTradingWidget` (TV)
or `TradingTerminalChartWithProvider` (SC). The entire TV tree under
`src/containers/trade/trading-terminal/widgets/center-view/tradingview/`
is live again — the "Not Ported" items below currently work via TV; SC
falls back to TV for them until each is built natively in SC.

This doc audits what SC covers vs. what is still TV-only. Source paths are
the live (5.3.x-restored) `center-view/tradingview/` tree unless noted.

---

## Ported (works in both TV and SC)

Core chart container & lifecycle (init, datafeed, theme, symbol/period sync,
visible-range sync, ready gating, symbol search).

Datafeed: Coinray candle fetch, real-time subscribe, mode routing
(live/replay/quiz), first-candle time.

Overlays
- Order overlays (open orders + edit) and edit-entry-conditions /
  edit-entry-expirations
- Price alerts, time alerts, trendline alerts (+ edit)
- TA scanner alerts
- Bid/Ask, Break-even, Trades
- Grid-bot orders (read-only) and grid-bot prices (draggable bounds/SL/TP)
- Backtest start/end time markers
- Bases (with respected / cracked / not-cracked styling and box)

Header buttons: Alert / Buy / Sell / Replay / Settings, with same
conditional visibility (mainChart, gridBot, quiz, replay, backtest finished).

Action buttons bar (mobile-only contextual bar under chart).

Hotkeys: chart shortcuts, /charts page shortcuts, replay shortcuts,
modals hotkeys.

Right-click context menu on chart background: Create Buy/Sell at price,
Create Alert at price, Break-even Start/End, Start Replay, Go Back, Play/Pause,
Speed Up/Down, Stop Replay, Set Solution Start/End (quiz),
"Set Backtest Start/End" (grid-bot backtest).

Per-overlay right-click menu (Delete on time alerts / trendlines etc.) via
SC `onRightClick`.

Screenshot capture + share modal.

Replay system (all of it):
- ReplayController (DEFAULT + SMART modes), play/pause/stop, speed
- ReplayTradingController, SmartReplayController, ReplaySmartTradingController
- ReplayBacktests widget
- ReplayControls, ReplayTimelines, ReplayPosition, ReplayHotkeys, ReplayModeDialog
- Pick-replay-start UI + ToggleReplayMode button
- Step-back / stepback optimization, trigger-timing offset, reset-to-orphan-trades

Quiz system: edit-drawings, play-drawings, preview-drawings (decision-point
arrow), questions-timelines, quiz-controls, quiz-question-chart. Persistence
via dedicated `QuizStorageAdapter`.

Chart Settings modal:
- Color picker (all chart colors per theme)
- General settings tabs: openOrders / closedOrders / positions / alerts /
  bases / quiz / misc (all boolean toggles ported)
- Live preview chart with overlay tabs and dummy data

Multi-chart support: TT, `/charts` (multi-tab), grid-bot overview/settings/
backtest, settings preview, quiz, customer-service market/position charts.

Mobile-specific behavior: mobile action buttons bar, mobile replay start
flow, fullscreen landscape layout.

`miscRememberVisibleRange` persistence to MarketTab.

`onSymbolChange` / `onPeriodChange` / `onVisibleRangeChange` callbacks
(MarketTab ↔ chart sync).

---

## Not Ported (TV-only — needs SC implementation)

Each item below currently runs through the restored TV widget when the user
is on `chartProvider = tradingview`. SC users do not get these features yet.

### 1. Custom indicators — **24 PineJS studies, none ported**
INTEGRATION.md says "4 custom indicators" — actually understated. Lives in
`controllers/ci.js` (20 inline) + `controllers/ci/*.js` (4 files):
- **1a.** `rsiStoch` — `controllers/ci/rsi-stoch.js`
- **1b.** `previousCandleOutliers` — `controllers/ci/previous-candle-outliers.js`
  (emits custom shapes via `updateCustomIndicators`)
- **1c.** `smartMoney` — `controllers/ci/smart-money.js`
  (feature-gated `essential_indicators`, emits custom shapes)
- **1d.** `liquidations` — `controllers/ci/liquidations.js`
  (feature-gated `essential_indicators`, emits custom shapes + dashboard data)
- **1e.** `Willams21EMA13`
- **1f.** `Trend Trigger Factor [LazyBear]`
- **1g.** `Relative Momentum Index`
- **1h.** `CM_Enhanced_Ichimoku Cloud-V5`
- **1i.** `True Strength Index [LazyBear]`
- **1j.** `On Balance Volume EMA-13`
- **1k.** `CM_Williams_Vix_Fix`
- **1l.** `CM_EMA Trend Bars`
- **1m.** `CM_Double EMA Trend Color`
- **1n.** `Bitcoin Kill Zones v2 [oscarvs]`
- **1o.** `Fisher Transform Indicator by Ehlers Strategy`
- **1p.** `Squeeze Momentum Indicator [LazyBear]`
- **1q.** `CM_SlingShotSystem`
- **1r.** `CM_Pivot Bands V1`
- **1s.** `Almost Zero Lag EMA [LazyBear]`
- **1t.** `On Balance Volume Oscillator [LazyBear]`
- **1u.** `SuperTrend BF`
- **1v.** `Exponential Bollinger Bands`
- **1w.** `WaveTrend [LazyBear]`
- **1x.** `KDJ Indicator - iamaltcoin`

### 2. Custom-indicator support overlays (consumers of #1)
- **2a. Liquidations Dashboard** (`liquidations-dashboard.js`) — floating
  panel showing which leverage tiers (5x/10x/25x/50x/100x) are active.
  Pulls from `customIndicators` ChartContext entry; tied to **1d**.
- **2b. Custom-indicator shapes** (`custom-indicators.js`) — generic React
  component that takes shape drawings emitted by custom indicators
  (`updateCustomIndicators` callback) and renders them on the chart.
  Used by **1b**, **1c**, **1d**.

### 3. TradingView Enhancements (`tradingview-enhancements.js` + folder)
TV iframe-DOM-injection layer that added buttons to TV's floating drawing
toolbar when a drawing is selected.
- **3a. Drawing template save/load/apply** — Save Drawing Template As /
  Apply Default Drawing Template / list+apply+delete saved templates per
  tool name. Uses `loadTemplates`/`deleteTemplate` from
  `actions/chart-settings`. Modal:
  `tradingview-enhancements/drawing_template_modal.js`.
- **3b. Trendline-to-alert conversion** — bell icon on `LineToolTrendLine`
  / `LineToolRay` selection that converts the drawn line into a trend-line
  alert (uses `trend_line_alerts` feature gate). Hooks up replay's
  `currentTime` to compute direction.
- **3c. Selection / delete plumbing** — `getSelectedEntities`,
  `onSelectionChanged`, `clickDelete`, `createToolbarPlaceholder`,
  `createToolbarButton`.
- **3d. `useToolbarVisibility`** — MutationObserver-based detection of TV's
  drawing toolbar visibility.

*(Backlog item #12 — explicitly deferred.)*

### 4. Generic chart-layout persistence (non-quiz)
TV had server-side `SaveLoadAdapter` against `/api/v2/tradingview_charts`
saving drawings + studies + chart templates + study templates + line tools
groups (auto-save via `onAutoSaveNeeded`), plus `LocalSaveLoadAdapter` for
non-trading users.
*(Done — `[sc-endpoints]`. `AltradyStorageAdapter` (HTTP default, local
debug fallback) covers TT, /charts, grid-bot, preview. TV-faithful split:
layout global per user, drawings per symbol. No migration from legacy
`/api/v2/tradingview_charts` data. See INTEGRATION.md Phase 6.)*

### 5. Chart-style settings save-back from chart UI
TV's `saveColors` extracted `paneProperties`, `scalesProperties`,
`mainSeriesProperties` from `tvWidget.save((state)=>{})` after each
auto-save, diffed against `getOverrides(colors)`, and persisted changes back
to Redux `chartColors`. Also extracted `timezone`. So modifying chart style
through TV's own settings UI flowed back into Redux. SC only persists via
the React Chart Settings modal. (`onTimezoneChange` is the SC backlog
representative.)

### 6. Resume-from-background data reset
`use-trading-view.js` listened on `visibilitychange` +
`MobileMessageTypes.FOREGROUND_STATE` and called `datafeed.resetData()` to
re-fetch candles when the tab/app returned from background. Not in SC.

### 7. TV-only widget options that had no SC equivalent set
From `controllers/setup.js`:
- **7a.** `drawings_access: {type: "black", tools: [{name: "Regression
  Trend"}]}` — blocked the Regression Trend drawing tool from the toolbar
- **7b.** `study_templates` enabled feature
- **7c.** `show_symbol_logos`, `show_exchange_logos`,
  `show_symbol_logo_in_legend`
- **7d.** `seconds_resolution` / `custom_resolutions`
- **7e.** `determine_first_data_request_size_using_visible_range`
- **7f.** `header_fullscreen_button` (disabled on mobile)
- **7g.** `snapshot_url` — server-side snapshot endpoint
  (`/api/v2/tradingview_charts/snapshot?user_id=…`). On SC, screenshots are
  local-only, no server upload.
- **7h.** Object Tree right-click entry (last item in TV context menu —
  `i18n…objectTree`). Not a feature loss in practice; just absent on SC.

### 8. Custom resolutions and `OTHER_RESOLUTIONS` mapping
TV had explicit `["D", "1D", "2D", "W", "1W", "2W", "1M"]` plus
`SECOND_RESOLUTIONS` (`1S…30S`) in supported_resolutions. SC datafeed
exposes its own. Verify that all of the same intervals are picker-available
in SC, especially seconds and 2D/2W.

