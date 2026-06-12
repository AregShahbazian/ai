# Candle tools — Tasks

PRD: [`prd.md`](prd.md) · Design: [`design.md`](design.md)

1. positions-backend: bulk `DELETE /sessions?except=` route. Verify: curl live.
2. `frontend/src/util/download.ts` + `util/savedCandles.ts` (+hook).
3. API client `clearSessions`; ChartView context-menu candle lookup;
   ChartContextMenu "Save candle" item.
4. BacktestPanel: export-range button (disabled logic), Clear sessions button,
   Saved candles section (list/export/clear). Styles.
5. Build, deploy api + staging, verify (curl + browser), `review.md`.
