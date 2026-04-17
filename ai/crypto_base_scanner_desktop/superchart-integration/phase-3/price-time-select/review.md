# Review: PriceTimeSelect — SuperChart Port

## Round 1: Initial verification plan (2026-04-14)

Pre-implementation test plan. Each item is numbered so review rounds can reference
it directly. Prefix items with ✅ once verified. Item groups map 1:1 to PRD
requirements R1-R3 plus the Trading Terminal context cases mandated by
`ai/workflow.md`.

### Verification

**R1 — Price input chart-pick**

1. On SC chart: open the trade form. Click the eye-dropper next to the entry price input. The button shows an active state.
2. While armed, click a candle on the chart. The price input is populated with the clicked price, normalized to the field's precision.
3. While armed, press Escape. The armed state clears and the price input is unchanged.
4. While armed, click outside the chart container (sidebar, menu, other widget). The armed state clears and the price input is unchanged.
5. While armed, right-click the chart. The armed state clears and the price input is unchanged.
6. Arm price input A (e.g. entry price), then arm price input B (e.g. stop-loss price) on the same form. A's armed state clears before B arms.
7. Arm a price input, then perform an unrelated UI interaction (navigate menu, open a balloon). The armed state clears.

**R2 — Date input chart-pick**

8. On SC chart: open the alert form. Click the eye-dropper next to the alert time input. The button shows an active state.
9. While armed, click a candle. The date input is populated with the candle's UTC timestamp. Display reflects the user's locale correctly.
10. Repeat cancellation tests 3, 4, and 5 for the date input — Escape, outside-click, right-click all cancel cleanly.

**R3 — No TV regression outside the trading terminal**

11. Grid bot page (TV chart): use an input that supports chart-pick (e.g. price-field on the bot config form). Arm a pick, click the chart. Pick still works via the TV code path — no regression from the SC port work.
12. Grid bot backtest modal (TV chart): same flow. Pick still works.

**Trading Terminal context test cases** (mandatory per `ai/workflow.md`)

13. Arm a pick on TradingTab A, then switch to TradingTab B. The armed state clears.
14. Arm a pick, then change coinraySymbol within the same tab. The armed state clears.
15. Arm a pick, then change resolution within the same tab. The armed state clears.
16. Arm a pick, then change exchangeApiKeyId for the current tab. The armed state clears.
17. Arm a pick, then unmount the chart (close the widget or navigate away). No dangling listeners, no console errors on unmount.
18. Arm a pick, then open a modal (confirm dialog, alert edit modal, etc.). Decide and document whether the pick cancels or survives — verify the behavior is consistent with the PRD and does not leave the app in an inconsistent state.
