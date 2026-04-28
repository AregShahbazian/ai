# Phase 1 — Symbol Search — Review

## Round 1: initial implementation (2026-04-21)

### Changed

- `src/containers/trade/trading-terminal/widgets/super-chart/coinray-datafeed.js`
  - Added module-level `marketToSearchResult` helper.
  - `onReady` now emits `exchanges` (alpha-sorted active) and
    `symbolsTypes: [{name: "Crypto", value: "crypto"}]` alongside the existing
    `supportedResolutions`.
  - `searchSymbols` implemented on top of `CoinrayCache.searchMarkets`, filtered
    to `ACTIVE` markets with optional `exchange` filter, capped at 50.

### Verification

1. Click the symbol text in the period bar → SC modal opens.
2. Modal shows a non-empty default list on open (no typing required, ≤250 ms after open).
3. Typing `eth` (after debounce) filters results to matching markets.
4. Typing `btc/usdt` (slash triggers `filterMarkets` regex mode) still returns matches.
5. Each row shows pair (`BTC/USDT`), exchange name, base-currency logo, exchange logo; description column is blank by design.
6. Selecting a result switches the chart to that market; active trading tab's `coinraySymbol` reflects the new ticker.
7. Pressing Esc / clicking the backdrop closes the modal without changing the chart.
8. Gibberish query (e.g. `zzzzz`) → modal shows empty-results state (no crash).

### Trading Terminal context tests (per `ai/workflow.md`)

9. Open modal from Tab A → select a symbol → switch to Tab B → switch back to Tab A. Tab A shows the newly selected symbol.
10. Change resolution on a tab → open modal → select a symbol. Resolution is preserved after selection.
11. Change `exchangeApiKeyId` on a tab → open modal → select a same-exchange symbol. Chart + tab update cleanly.
12. On the same tab, select a different-exchange symbol via the modal (R7). Chart switches to the new symbol; tab's `exchangeApiKeyId` is unchanged (cross-exchange pick permitted, no auto-switch).
13. Toggle `filterExchangeCodes` via the existing markets list → open modal. Modal results are NOT constrained by the list's exchange filter (modal is independent).

### Sanity checks on the data surface

14. `dataLoader.getConfiguration()` returns `{supportedResolutions, exchanges, symbolsTypes}` with a non-empty `exchanges` array once `onReady` has fired.
15. `exchanges` entries are `{value: <code>, name: <name>}` and sorted alphabetically by `name`.
16. `DELISTED` / `INACTIVE` markets do not appear in search results.
