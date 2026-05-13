# SuperChart Backlog

TV-only features that still need to be implemented natively in SC. While
unimplemented, each item runs through the restored TV widget when
`chartProvider = tradingview` (post-`[sc-tv-coex]`). SC users do not get
these features yet.

Source paths reference the live (5.3.x-restored)
`src/containers/trade/trading-terminal/widgets/center-view/tradingview/`
tree unless noted.

---

## 1. Generic chart-layout persistence (non-quiz)

TV had server-side `SaveLoadAdapter` against `/api/v2/tradingview_charts`
saving drawings + studies + chart templates + study templates + line tools
groups (auto-save via `onAutoSaveNeeded`), plus `LocalSaveLoadAdapter` for
non-trading users. SC only has `QuizStorageAdapter`. TT, /charts, grid-bot,
preview don't persist drawings/indicators across reloads.

---

## 2. Custom indicators — 24 PineJS studies, none ported

Lives in `controllers/ci.js` (20 inline studies) + `controllers/ci/*.js`
(4 separate files).

- **2a.** `rsiStoch` — `controllers/ci/rsi-stoch.js`
- **2b.** `previousCandleOutliers` — `controllers/ci/previous-candle-outliers.js`
  (emits custom shapes via `updateCustomIndicators`)
- **2c.** `smartMoney` — `controllers/ci/smart-money.js`
  (feature-gated `essential_indicators`, emits custom shapes)
- **2d.** `liquidations` — `controllers/ci/liquidations.js`
  (feature-gated `essential_indicators`, emits custom shapes + dashboard data)
- **2e.** `Willams21EMA13`
- **2f.** `Trend Trigger Factor [LazyBear]`
- **2g.** `Relative Momentum Index`
- **2h.** `CM_Enhanced_Ichimoku Cloud-V5`
- **2i.** `True Strength Index [LazyBear]`
- **2j.** `On Balance Volume EMA-13`
- **2k.** `CM_Williams_Vix_Fix`
- **2l.** `CM_EMA Trend Bars`
- **2m.** `CM_Double EMA Trend Color`
- **2n.** `Bitcoin Kill Zones v2 [oscarvs]`
- **2o.** `Fisher Transform Indicator by Ehlers Strategy`
- **2p.** `Squeeze Momentum Indicator [LazyBear]`
- **2q.** `CM_SlingShotSystem`
- **2r.** `CM_Pivot Bands V1`
- **2s.** `Almost Zero Lag EMA [LazyBear]`
- **2t.** `On Balance Volume Oscillator [LazyBear]`
- **2u.** `SuperTrend BF`
- **2v.** `Exponential Bollinger Bands`
- **2w.** `WaveTrend [LazyBear]`
- **2x.** `KDJ Indicator - iamaltcoin`

---

## 3. Custom-indicator support overlays (consumers of #2)

- **3a. Liquidations Dashboard** (`liquidations-dashboard.js`) — floating
  panel showing which leverage tiers (5x/10x/25x/50x/100x) are active.
  Pulls from `customIndicators` ChartContext entry; tied to **2d**.
- **3b. Custom-indicator shapes** (`custom-indicators.js`) — generic React
  component that takes shape drawings emitted by custom indicators
  (`updateCustomIndicators` callback) and renders them on the chart.
  Used by **2b**, **2c**, **2d**.

---

## 4. TradingView Enhancements (`tradingview-enhancements.js` + folder)

TV iframe-DOM-injection layer that added buttons to TV's floating drawing
toolbar when a drawing is selected.

- **4a. Drawing template save/load/apply** — Save Drawing Template As /
  Apply Default Drawing Template / list+apply+delete saved templates per
  tool name. Uses `loadTemplates`/`deleteTemplate` from
  `actions/chart-settings`. Modal:
  `tradingview-enhancements/drawing_template_modal.js`.
- **4b. Trendline-to-alert conversion** — bell icon on `LineToolTrendLine`
  / `LineToolRay` selection that converts the drawn line into a trend-line
  alert (uses `trend_line_alerts` feature gate). Hooks up replay's
  `currentTime` to compute direction.
- **4c. Selection / delete plumbing** — `getSelectedEntities`,
  `onSelectionChanged`, `clickDelete`, `createToolbarPlaceholder`,
  `createToolbarButton`.
- **4d. `useToolbarVisibility`** — MutationObserver-based detection of TV's
  drawing toolbar visibility.

---

## 5. Resume-from-background data reset

`use-trading-view.js` listened on `visibilitychange` +
`MobileMessageTypes.FOREGROUND_STATE` and called `datafeed.resetData()` to
re-fetch candles when the tab/app returned from background. Not in SC.

`klinecharts` caches candles in its own data store, so a stale
subscription after backgrounding produces the same gap on resume. Before
porting 1:1, verify:
1. Whether `getCoinrayCache()` already handles WS reconnect on visibility
   resume (in which case SC just needs to trigger a chart-side refetch).
2. Whether SC's datafeed exposes a "reset" hook equivalent to TV's
   `onResetCacheNeededCallback`.

---

## 6. Server-side snapshot upload

TV's `snapshot_url` option pointed at
`/api/v2/tradingview_charts/snapshot?user_id=…`, giving users a shareable
hosted screenshot URL. On SC, screenshots are local-only — no server
upload. Port the upload step into SC's screenshot flow.

