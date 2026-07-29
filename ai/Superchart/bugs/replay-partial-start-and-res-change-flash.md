# Replay: missing start-partial on sub-resolution start + full-candle flash on resolution change

Investigated 2026-07-27 on `fix/replay-jump-gap` (7a197a1), submodule at 831a6411.
Both issues verified live (Storybook Replay story + backend + Playwright-driven
engine inspection). **No fix applied — investigation report only.**

Regression context (both issues): the Storybook datafeed was swapped from
Coinray to the CCXT-backed `examples/server` REST adapter in `8c6040f`
(May 29), defaulted to MEXC in `ecd02aa` (May 31), merged to main Jun 1–3.
The replay engine itself is unchanged since May 4 (`c8f7e92f`). Altrady still
uses the Coinray datafeed — which is why neither issue reproduces there.
The Jul 13 fix (`044f71d`) fixed two *other* defects of the same swap
(jump-to-date ignored, MEXC 500-bar cap gap); these two are the remaining ones.

---

## Issue 1 — starting replay at 15:12 on 1H: first step jumps 15:12 → 17:00

### Symptom
Start a session at a sub-resolution timestamp (e.g. 2026-04-08 15:12, period
1H, story default `MEXC:BTC/USDT`). Expected: chart ends in a partial
15:00-candle truncated at 15:12; first step completes it (cursor → 16:00).
Actual: chart ends in the **full** 15:00 candle (future leak within the hour)
and the first step draws the 16:00 candle (cursor → 17:00). No error surfaces.

### Root cause
**MEXC (via CCXT) retains only ~30 days of 1m candles.** Probed via the
backend (`/api/datafeed/klines`, MEXC:BTC/USDT, 1m): 20d ago → data, 30d ago →
1 bar, 45d+ → empty. 5m/15m/1h are deep (200d+ probed). Binance 1m is deep
(200d+).

Chain (all in `packages/coinray-chart/src/replay/ReplayEngine.ts`):
1. `setCurrentTime(15:12)` → init load ends at the full 15:00 bar
   (`adjustFromTo` floors `to` to the hour — `src/lib/datafeed/index.ts:43`),
   buffer holds [16:00…] (`_fetchReplayBuffer` filters `>= 15:12`, line 792).
2. `_postProcessDataBoundary` hits Case 3 (mid-candle, line 868) →
   `_fetchSubResolutionPartial(15:00-bar, 15:12)`.
3. Tiers for 1H = coarse 15m + fine 1m (line 827). At :12 past the hour,
   `coarseEnd = 15:00 + floor(12/15)·15m = 15:00` → **coarse skipped**; the
   partial depends entirely on 1m data.
4. 1m fetch `[15:00→15:12]` (network: `timeframe=1m&limit=13&before=15:13Z`)
   returns **0 candles** on dates older than ~30d → `subCandles.length === 0`
   → returns `null` (line 601).
5. `partial === null` → `_postProcessDataBoundary` **silently returns**
   (line 872): full candle stays in `_dataList`, straddling candle is **not**
   queued at the buffer head, no error emitted (`partial_construction_failed`
   exists only in the `stepBack` path, line 514).
6. First `step()` shifts buffer[0] = 16:00 → `_replayCurrentTime` = 17:00.

### Evidence
- MEXC @ Apr 8 15:12: dataList tail = full 13:00Z candle (o 72066.84 h 72830.75
  l 71506.54 c 71614.8, identical to backend's full bar), buffer head 14:00Z,
  step → cursor 15:00Z (17:00 local). Exactly the reported jump.
- Counterfactual 1 — same start on **Jul 22** (within 1m retention): partial
  built (c 65668.27 vs full 65950.03), full bar queued, step completes to
  16:00. Correct.
- Counterfactual 2 — same Apr 8 start on **BINANCE**: partial built
  (c 72436.01 vs full 71600.01), step completes to 16:00. Correct.
→ Engine logic is sound; the only variable is 1m data availability.

### Why the user's resolution-change tests seemed fine
- Cursor at :45 (5m→1H): partial = 3×15m candles, fine tier skipped
  (`fineStart == truncateAt`) → deep 15m retention → works at any date.
- Cursor at :28: coarse 15m covers [.00→.15]; the empty 1m fine fetch for
  [.15→.28] just shrinks the partial (subCandles non-empty → no bail) →
  *degraded* but visually "works".
A fresh session start needs 1m whenever the cursor is <15 min past the hour.

### Altrady comparison
Altrady's `coinray-datafeed.js` → `CoinrayCache.fetchCandles` → Coinray's
candle store, which serves 1m history back to listing. The sub-resolution
fetch can't come back empty for any valid replay date → partial always builds.

### Suggested fixes (in preference order)
1. **Engine robustness** — in `_postProcessDataBoundary`, when
   `partial === null`, degrade to Case-2 semantics: pop the straddling full
   candle from `_dataList` into the buffer head and emit
   `partial_construction_failed`. No future leak, no skipped hour — the
   session effectively starts at the top of the hour. (Optionally snap
   `_replayCurrentTime` to the candle open for label consistency.)
2. **Tier fallback** — let `_fetchSubResolutionPartial` retry with a coarser
   fine tier (1m → 5m) when the fine fetch is empty; approximate partial
   truncated at floor(cursor, 5m).
3. **Emit the error** in this path regardless (parity with stepBack), so the
   story HUD / consumers get feedback instead of silence.
4. **Storybook-level workaround** — Replay story default symbol
   `BINANCE:BTC/USDT` (verified deep 1m via backend) and/or default start date
   within ~20 days. Note `ecd02aa` chose MEXC as global default deliberately;
   the replay story can override per-story.

Note: the server's SQLite cache memoizes historical pages for 5 min
(`BARS_HISTORICAL_TTL_MS`), so empty 1m responses are re-fetched soon —
caching is not a contributing cause here.

---

## Issue 2 — 5m→1H resolution change at :45 cursor: full candle flashes before the partial

### Symptom
Replay on 5m, play to 15:45, switch to 1H. The **fully completed** 15:00
candle (whole-hour OHLC — the "price future") is visible for a noticeable
time, then replaced by the correct partial (truncated at 15:45). The next
step completes the partial again (that part is correct).

### Root cause — paint-then-patch race, exposed by a slow datafeed
`Store._addData('init')` paints immediately on data arrival
(`packages/coinray-chart/src/Store.ts:770-784`: `_adjustVisibleRange` +
indicator calc/layout). The engine only patches the partial afterwards, in
`handlePeriodChange`'s `_onInitComplete` (ReplayEngine.ts:212-282), after
**sequential** network work: `_fetchReplayBuffer` (cursor→sessionEnd, here 2
pages — the second a wasted `limit=1` page caused by the `wanted+1` straddle
budget) and then `_postProcessDataBoundary` → 15m fetch → replace + relayout.
The chart's own loading overlay is dropped exactly when the full candle
paints (`setLoadingVisible(false)` in the init callback,
`src/lib/datafeed/index.ts:305`), so nothing masks it.

### Evidence (measured, warm server cache)
8ms-interval poll of `_dataList` tail during `setPeriod(1H)` at cursor
13:45Z Jul 22:
- t≈22ms: 1H init lands, last bar = **full** 13:00Z candle (h 65975,
  c 65950.03 — future vs cursor: playback close was 65889.23), painted.
- t≈1472ms: partial replaces it (h 65911.61, c 65889.23), status `ready`.
→ **~1.45s** of future OHLC on screen; cold cache (5-min TTL expired, ccxt
upstream per page) pushes this to multi-second. Buffer head correctly holds
the full candle → next step completes the partial.
Network sequence: `1h×501` (init) → `1h×121` + `1h×1` (buffer) → `15m×4`
(partial) — four sequential backend round-trips between paint and patch.

### Why Altrady doesn't show it
Identical engine code — it's a latency race, not a code difference. Coinray's
bucketed, CDN-cached candle fetches resolve in tens of ms, so the window is
~a frame. Prediction: with devtools network throttling, Altrady should show
the same flash. It has existed structurally since the replay engine landed
(April); Coinray latencies simply never exposed it — the June datafeed swap
did.

### Suggested fixes
1. **Defer the replay init paint (real fix)** — when `isInReplay()`, make
   `_addData('init')` skip the visible-range/layout pass and let the engine
   trigger the single paint after `_postProcessDataBoundary` has patched the
   partial (the engine already has `_triggerDeferredLayout` for exactly this
   concept). Eliminates the leak at any datafeed latency, for both
   `setCurrentTime` and `handlePeriodChange` paths.
2. **Cheaper mitigation** — run `_postProcessDataBoundary` before
   `_fetchReplayBuffer` so the patch lands one round-trip earlier. Caveat:
   `_fetchReplayBuffer` *assigns* `_replayBuffer` (line 792) and would clobber
   the full candle that `_postProcessDataBoundary` unshifts — it must merge
   instead. Flash shrinks but doesn't vanish; prefer (1).
3. **Cosmetic** — keep the loading overlay up until replay status `ready`
   during replay init/period change, so the intermediate paint is covered.

Also worth fixing while in there (minor): the buffer fetch's `wanted+1`
budget forces a useless `limit=1` page when the first page exactly covers the
span (BackendDatafeed paging loop).
