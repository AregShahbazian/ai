# Candle tools — Review

PRD: [`prd.md`](prd.md) (`pc-candle-tools`)

## Round 1: initial implementation (2026-06-12)

Implemented per [`design.md`](design.md)/[`tasks.md`](tasks.md); deployed to
staging + API redeployed (via the break-glass scripts; the committed push goes
through CI).

### Verification

1. ✅ `yarn build` clean; live UI shows pickers, Export candles (disabled
   without a range), Sessions and Saved candles sections (agent-verified,
   Playwright)
2. ✅ `DELETE /sessions?except=<id>` keeps only that session;
   without `except` wipes all (agent-verified live: 17 → 1 → 0)
3. Clear sessions in the UI: with an active session running, it survives;
   list refreshes
4. Export candles with a picked range downloads
   `candles_<SYMBOL>_<interval>_<DD-MM-YYYY-HHmm>_<DD-MM-YYYY-HHmm>.json`
   with the range's candles
5. Right-click a candle → "Save candle" appears (absent when clicking
   whitespace); saving adds it to the panel section; duplicates are skipped
6. Saved candles survive reload; × removes one; Clear empties;
   "Export saved candles" downloads them
7. Context cases: saving candles works in replay mode too (saved under the
   session's market/interval)
