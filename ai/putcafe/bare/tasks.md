# Bare MVP — Tasks

PRD: [`prd.md`](prd.md) · Design: [`design.md`](design.md)

## 1. Scaffold

- Repo root: `.gitignore` (node_modules, dist, .idea), `README.md` (one-liner +
  how to run).
- `frontend/package.json` (react, react-dom, lightweight-charts ^5; dev: vite,
  @vitejs/plugin-react, typescript, @types/react{,-dom}), `vite.config.ts`,
  `tsconfig.json`, `index.html`, `src/main.tsx`.
- Verify: `npm install` then `npm run build` passes.

## 2. Binance API module — `src/binance/api.ts`

- `Market`, `Candle` types; `fetchMarkets()` (exchangeInfo + USDT/TRADING
  filter, sorted by symbol); `fetchKlines(symbol, interval, endTime?)`.
- Verify: types compile; manual curl of both endpoints matches mapping.

## 3. ChartView — `src/chart/ChartView.tsx`

- Chart + candle/volume series, dark theme, autoSize.
- Initial load, lazy older-history loading, exhausted flag, overlap guard.
- Crosshair OHLCV legend; loading overlay; error + retry state.
- Verify: build passes; behaviors on the review checklist.

## 4. Selectors + shell — `App.tsx`, components, `app.css`

- MarketSelector (searchable dropdown), TimeframeSelector (segmented).
- Header layout, chart fills remaining viewport; state wiring
  (`market`,`interval` → ChartView key).
- Verify: `npm run build`; checklist below.

## 5. Review doc

- Write `review.md` with the numbered verification checklist.
