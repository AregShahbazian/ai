---
id: pc-bare
---

# Putcafe — Bare MVP (chart + market selector)

Smallest runnable slice of putcafe, a crypto trading bot simulation and
backtesting app. This slice is **frontend-only, web-only, run locally** — it
proves the chart and data foundation everything else builds on. The rest of the
feature set is in [`../mvp/prd.md`](../mvp/prd.md); deployment is in
[`../devops/prd.md`](../devops/prd.md).

## Requirements

### 1. Candlestick chart

- Display real historical OHLCV candles for the selected market and timeframe.
- Data from **Binance spot public REST** (klines) — no API key, no auth.
- Chart pans/zooms smoothly; scrolling left past loaded history lazily loads
  older candles (no hard left edge until Binance history is exhausted).
- Volume shown (histogram pane or overlay).
- Crosshair with OHLCV readout for the hovered candle.

### 2. Market selector

- Searchable dropdown listing Binance **spot** markets, populated from the
  Binance exchange-info endpoint.
- USDT-quoted pairs are the primary set; default market **BTC/USDT**.
- Selecting a market reloads the chart for that market.

### 3. Timeframe selector

- Common intervals: `1m 5m 15m 1h 4h 1d 1w`. Default **1h**.
- Switching reloads the chart, preserving the selected market.

### 4. App shell

- Single-page layout: header (market selector, timeframe selector), chart
  filling the remaining viewport.
- Desktop-browser oriented; no mobile work, but nothing that *blocks* a later
  Capacitor wrap (no desktop-only APIs).
- Graceful states: loading indicator while fetching; readable error message on
  Binance fetch failure.

## Constraints (decided in discussion)

- Monorepo at `~/git/putcafe`; frontend lives in a subdir alongside future
  backends.
- React + TypeScript + Vite; charting via **Lightweight Charts** (open source).
- Identifier base `com.mby4m.putcafe` wherever the stack needs one.
- Reference repos (Superchart, Altrady cbs_desktop) cannot be imported as
  packages — logic is ported, never depended on.

## Non-requirements

- No backend, DB, or persistence.
- No replay/backtest, bots, trades, overlays, indicators, or drawing tools.
- No deploy/CI (devops PRD), no Android (future), no exchanges besides Binance.
- No API keys, accounts, or settings persistence.
