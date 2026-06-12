# Candle tools — Design

PRD: [`prd.md`](prd.md) (`pc-candle-tools`)

- **Clear sessions** — new positions endpoint
  `DELETE /api/positions/sessions?except=<id>` (bulk; `except` optional).
  Frontend `positions.clearSessions(exceptId?)`, called with the active
  session id when one exists; panel refreshes the list (cascade removes
  trades).
- **Export range** — no backend: `fetchKlinesRange` for the selected range →
  JSON download (`Blob` + anchor). Shared `download.ts` util. Filename:
  `candles_<SYMBOL>_<interval>_<DD-MM-YYYY-HHmm>_<DD-MM-YYYY-HHmm>.json`.
  Button sits under the range pickers; disabled until both picked.
- **Saved candles** — `savedCandles.ts`: localStorage-backed store
  (`{market, interval, candle}[]`, exact-duplicate skip) with a `useSavedCandles`
  hook. ChartView's context-menu callback also passes the candle at the
  clicked time (lookup in `candlesRef`); menu gains "Save candle" (shown only
  when a candle is hit). New panel section: count + compact list (time+close,
  remove per row), Export (JSON download `saved-candles_<DD-MM-YYYY-HHmm>.json`),
  Clear.
- JSON as the export format (matches the `Candle` shape; bot-seed compatible).
