# Bare MVP — Design

PRD: [`prd.md`](prd.md) (`pc-bare`)

## Stack & layout

Monorepo; this slice creates only `frontend/`:

```
frontend/
  package.json          # name "putcafe-frontend"
  index.html
  vite.config.ts
  tsconfig.json
  src/
    main.tsx
    App.tsx               # state: market, interval, markets list
    app.css                # single dark-theme stylesheet
    binance/api.ts        # exchangeInfo + klines fetchers, types
    chart/ChartView.tsx   # lightweight-charts wrapper
    components/MarketSelector.tsx
    components/TimeframeSelector.tsx
```

React 18 + TypeScript + Vite. **lightweight-charts v5** (`chart.addSeries(CandlestickSeries, …)` API). No other runtime deps — the searchable dropdown is hand-rolled.

## Data (Binance spot public REST, CORS-enabled)

- **Markets:** `GET /api/v3/exchangeInfo`, filtered client-side to
  `status === "TRADING" && isSpotTradingAllowed && quoteAsset === "USDT"`.
  Fetched once at startup. Default `BTCUSDT`.
- **Candles:** `GET /api/v3/klines?symbol=&interval=&limit=1000[&endTime=]`.
  Kline arrays mapped to `{time(s), open, high, low, close, volume}`;
  Binance ms → seconds (`UTCTimestamp`).
- **Lazy history:** on `subscribeVisibleLogicalRangeChange`, when
  `barsInLogicalRange(range).barsBefore < 50`, fetch 1000 older candles with
  `endTime = oldestOpenTime - 1`, prepend, `setData` the full array. A
  returned batch `< 1000` marks history exhausted. Guard with an
  `isLoadingRef` so fetches never overlap.

## ChartView

- `createChart(el, { autoSize: true })`, dark layout colors.
- Candlestick series + volume `HistogramSeries` overlaid on price pane
  (`priceScaleId: ""`, `scaleMargins { top: 0.8, bottom: 0 }`), green/red by
  candle direction.
- OHLCV legend: `subscribeCrosshairMove` → fixed-position div, falls back to
  the last candle when the crosshair leaves the chart.
- On market/interval change: full reload (`setData` with fresh batch),
  `timeScale().fitContent()` is **not** used — default right-edge view.
- Chart instance created once per mount; data swaps via `setData`. Component
  remounts on `symbol+interval` key change to keep state trivially correct.

## Selectors

- **MarketSelector:** button (shows `BTC/USDT`) → dropdown panel with search
  input; case-insensitive substring filter on base asset/symbol; render
  capped at 200 rows; closes on selection or outside click.
- **TimeframeSelector:** segmented buttons `1m 5m 15m 1h 4h 1d 1w`,
  Binance interval strings used verbatim. Default `1h`.

## States

- Loading: small overlay text on the chart area while the initial batch loads.
- Error: readable message + retry button replacing the chart; selector errors
  shown inline in the dropdown.

## Open questions (resolve while implementing)

- Exact lightweight-charts v5 minor to pin (`^5`, lockfile decides).
