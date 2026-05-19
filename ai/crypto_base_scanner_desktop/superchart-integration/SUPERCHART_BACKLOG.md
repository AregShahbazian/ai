# SuperChart Backlog

TV-only features that still need to be implemented natively in SC. While
unimplemented, each item runs through the restored TV widget when
`chartProvider = tradingview` (post-`[sc-tv-coex]`). SC users do not get
these features yet.

Source paths reference the live (5.3.x-restored)
`src/containers/trade/trading-terminal/widgets/center-view/tradingview/`
tree unless noted.

---

## 1. Custom indicators — 24 PineJS studies, none ported

Lives in `controllers/ci.js` (20 inline studies) + `controllers/ci/*.js`
(4 separate files).

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

---

## 2. Custom-indicator support overlays (consumers of #1)

- **2a. Liquidations Dashboard** (`liquidations-dashboard.js`) — floating
  panel showing which leverage tiers (5x/10x/25x/50x/100x) are active.
  Pulls from `customIndicators` ChartContext entry; tied to **1d**.
- **2b. Custom-indicator shapes** (`custom-indicators.js`) — generic React
  component that takes shape drawings emitted by custom indicators
  (`updateCustomIndicators` callback) and renders them on the chart.
  Used by **1b**, **1c**, **1d**.

---

## 3. Trendline-to-alert conversion

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

## 4. Resume-from-background data reset

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

