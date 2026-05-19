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

**Local-only part: done.** `super-chart/storage-adapter.js`
(`AltradyStorageAdapter`) wraps SC's `LocalStorageAdapter` with a
TV-faithful split: layout (indicators + panes + styles) under one
global record, drawings per-symbol. Drawing/indicator/chart templates
pass through. Wired via `useChartLifecycle`. Surfaces all four UI
buckets natively in SC.

**Pending — backend swap.** Replace the `LocalStorageAdapter` delegation
with HTTP calls against the endpoints proposed in
`phase-6/sc-endpoints.md` (`/superchart/states`,
`/superchart/indicator_templates`, `/superchart/drawing_templates`).
Blocked on the endpoints existing.

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

## 4. Trendline-to-alert conversion

TV's `tradingview-enhancements.js` shows a bell icon when a
`LineToolTrendLine` or `LineToolRay` is selected, converting the drawn
line into a trend-line alert (feature-gated `trend_line_alerts`). Uses
replay's `currentTime` to compute direction.

SC equivalent needs: an "overlay selected" event/callback to render the
bell button, the selected overlay's points + properties to build the
alert payload, then `removeOverlay` on commit. Wire to the existing
`newAlert` action.

(The rest of TV's `tradingview-enhancements.js` — drawing-template
save/load/apply, selection/delete plumbing, toolbar-visibility observer
— is **obsolete**: SC provides drawing templates natively via the
storage adapter, plus its own selection/right-click APIs.)

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

