# TV/SC Coexistence — Shakedown Checklist

Final manual validation pass before Phase 8 squash. Work through both modes. Check off as you go.

## Provider toggle
- [ ] Open chart-settings modal in SC mode → toggle to TV → preview swaps to TV chart → Save → TT chart becomes TV
- [ ] Open chart-settings modal in TV mode → toggle to SC → preview swaps to SC → Save → TT chart becomes SC
- [ ] Toggle while replay session is active → custom Yes/No confirm modal appears → No cancels (no switch) → Yes switches and clears session
- [ ] After TV→SC switch: modal Enter/Esc hotkeys still work
- [ ] Console: `toggleChart()` flips + persists (same as Save)
- [ ] App does NOT reload on toggle

## Trading Terminal (TT)
**SC mode**
- [ ] Chart loads, candles render, indicators apply
- [ ] Limit order: price seeded from current market, % offset works
- [ ] TP / SL placement: offset from entry (not at exact entry)
- [ ] Entry expiration "time" toggle → default time depends on visible range
- [ ] "Pick on chart" eye-dropper: price-field, date-picker, entry-expiration price
- [ ] Backtest: start session → resume after pause → finish → trade form resets on stop
- [ ] During backtest: limit order seed = replay candle close (not real-time price)
- [ ] Tab switch: market tab swap preserves session/state

**TV mode**
- [ ] Chart loads with header buttons (no raw i18n keys)
- [ ] Limit order: price seeded; % offset works
- [ ] TP / SL placement: offset from entry
- [ ] Entry expiration "time": offset based on visible range
- [ ] "Pick on chart": price-field, date-picker, entry-expiration price
- [ ] Backtest: start → resume → trades render on chart → stop clears session
- [ ] During backtest: trade-form widgets read replay price (order line draws on visible candles, not offscreen)

## /charts
- [ ] SC mode: per-tab charts render, symbol/resolution/VR persist
- [ ] TV mode: charts render, no `Cannot read properties of undefined (reading 'draw'/'questionController')` errors when navigating TT↔/charts quickly
- [ ] TV mode: trade flows unchanged from BASE

## /quizzes
**SC mode**
- [ ] Dashboard loads, categories appear
- [ ] Edit a quiz question: chart shows candles, drawings, indicators
- [ ] Play a quiz: candles reveal via SC replay animation
- [ ] Preview a question: candle reveal works
- [ ] "Pick on chart" for time inside a question
- [ ] Navigate between questions: smooth transitions or hard reset

**TV mode**
- [ ] Edit `/quizzes/edit/<quizId>/question/<qId>`: candles + indicators + drawings load, visible range auto-fits to solution
- [ ] Play mode: candles render, reveal animation plays
- [ ] Preview mode: candles + drawings render
- [ ] "Pick on chart" (TV's price-time-select) works
- [ ] No console errors on first load

## Customer service / bots / portfolio (TV mode only — SC didn't touch these)
- [ ] customer-service chart renders
- [ ] grid-bot / signal-bot widgets: charts render, no NPE on quizController.draw

## Replay/Backtest cross-cuts
- [ ] Mid-replay TV→SC switch shows confirm, then doesn't crash
- [ ] Mid-replay SC→TV switch shows confirm, then doesn't crash
- [ ] Backtests widget reloads correctly after provider switch
- [ ] Saved backtests list visible in both modes

## Other
- [ ] No `[sc-tv-coex/...]` console.log noise (we cleaned them up)
- [ ] Confirm `webpack.build-web.config.js` still matches BASE (no speculative TV CopyPlugin)
- [ ] i18n: TV header buttons show real labels (English/Dutch/Spanish)

---

If anything fails, report which item, mode, and exact error message; fix before Phase 8 squash.
