# Phase 1 — Symbol Search — Design

## Scope

All functional work lives in one file:
`src/containers/trade/trading-terminal/widgets/super-chart/coinray-datafeed.js`.

No changes to `super-chart.js`, `market-tab-sync-controller.js`, or any overlay
component. SC owns the modal UI; Altrady owns the data surface.

## Architecture

```
  Period-bar symbol click
           │
           ▼
  SC SymbolSearchModal          ◄── SC-internal (not touched)
           │ debounce 250ms
           ▼
  dataLoader.searchSymbols("query", "", "crypto", onResult)
           │
           ▼                                      ┌─ CoinrayCache (singleton) ─┐
  CoinrayDatafeed.searchSymbols  ──────────►  │  searchMarkets(query)       │
           │                                      │  getExchanges()             │
           ▼                                      └─────────────────────────────┘
  map Market → SearchSymbolResult (sliced to 50)
           │
           ▼
  onResult(results)
           │
           ▼
  SC renders rows → user clicks → SC calls onSymbolChange(symbolInfo)
           │
           ▼
  MarketTabSyncController._onChartSymbolChange  ◄── already wired
           │
           ▼
  TradingTabsController tab.setCoinraySymbol(ticker)
```

## Data flow

### `onReady(callback)`

Called once, shortly after SC construction. Returns the `DatafeedConfiguration`
used by the modal to build the type tab row and the (future) exchange filter.

Today's call (stub):
```js
callback({ supportedResolutions: SUPPORTED_RESOLUTIONS })
```

New call:
```js
callback({
  supportedResolutions: SUPPORTED_RESOLUTIONS,
  exchanges: <alpha-sorted active exchanges mapped to {value, name}>,
  symbolsTypes: [{ name: "Crypto", value: "crypto" }],
})
```

- `exchanges` built from `CoinrayCache.getExchanges()`. Filter by `exchange.active === true`
  to avoid offering inactive ones. Map to `{value: exchange.code, name: exchange.name}`.
  Sort alphabetically by `name` (Q3 resolved).
- `symbolsTypes`: single phase-1 entry. SC prepends an "All" tab automatically.
- `supportedResolutions`: unchanged.

Async behaviour is preserved via the existing `setTimeout(..., 0)` wrapper — SC
expects `onReady` to fire via microtask.

### `searchSymbols(userInput, exchange, symbolType, onResult)`

Contract:

| Input       | Handling                                                           |
|-------------|--------------------------------------------------------------------|
| `userInput` | `.trim()`. Empty → return all markets (sliced). Non-empty → `searchMarkets(query)`. |
| `exchange`  | If non-empty, post-filter by `market.exchangeCode === exchange`. SC passes `""` today; this is forward-compatible. |
| `symbolType`| Ignored in phase 1 (only one type emitted).                        |

Steps:

1. Resolve the market map:
   - Empty query → `Object.values(cache.searchMarkets(""))`. `filterMarkets`
     returns the input map unchanged when no truthy query is supplied, so this
     is effectively "all markets".
   - Non-empty query → `Object.values(cache.searchMarkets(query))`. coinrayjs'
     `filterMarkets` already matches against `fullDisplayName`
     (`"BINA: BTC/USDT"`) — case-insensitive keyword match, with slash/colon
     queries treated as regex. No additional normalization on our side.
2. Drop non-active markets: `market.status === "ACTIVE"` (Q4 resolved).
3. Apply `exchange` post-filter if provided.
4. Slice to **50** (before mapping to avoid wasted object construction).
5. Map each surviving `Market` through `marketToSearchResult`.
6. Call `onResult(results)` once, synchronously inside `try`, or `onResult([])`
   on error (with a `console.error`, matching the style of the rest of the
   file).

No `setTimeout` wrapper — SC already bridges to a promise internally.

### `marketToSearchResult(market) → SearchSymbolResult`

Private module-level helper (not a class method). Shape:

```js
{
  symbol: market.coinraySymbol,          // e.g. "BINA_USDT_BTC" — ticker SC sets on select
  full_name: market.displayName,         // "BTC/USDT"
  description: "",                       // Q1: no base-currency long name available; leave empty
  exchange: exchange.name,               // "Binance"
  type: "crypto",
  logo: market.baseLogoUrl,              // may be empty — SC placeholders
  exchange_logo: exchange.logo,          // may be empty — ditto
}
```

`exchange = market.getExchange()`. This returns a real Exchange object for any
market that came out of the cache (markets are always owned by an exchange in
the map).

### `onSymbolChange` — no changes

`MarketTabSyncController._onChartSymbolChange` (constructor line ~51) already
handles the selection case. The same `symbolInfo.ticker` field SC emits on
modal-select flows through the existing echo-guard and
`tab.setCoinraySymbol(sym)`. Cross-exchange pick (R7): the sync controller does
**not** touch `exchangeApiKeyId`, so phase 1 correctness is already in place.

Verification during review, not code.

## Open questions — resolutions

| # | Question | Resolution |
|---|----------|------------|
| Q1 | `description` fallback? | Leave empty — no base-currency long name on the Market object. |
| Q2 | Default list (empty query) order? | `searchMarkets("")` result order (coinray-native), sliced to 50. |
| Q3 | `exchanges` array ordering? | Alphabetical by `name`. |
| Q4 | Exclude non-ACTIVE markets? | Yes. `status === "ACTIVE"` only. |

## Risks / non-obvious considerations

- **Symbol resolution after pick.** SC calls `resolveSymbol(ticker, ...)` after
  selection. Altrady's existing `resolveSymbol` calls `cache.getMarket(ticker)`
  which will succeed for any ticker the search returned (same cache source).
  No change needed.
- **Cache readiness.** `onReady` fires shortly after chart construction. In
  Altrady the chart is only mounted once the user is authenticated and
  `coinray-initialization` has loaded exchanges+markets, so
  `cache.getExchanges()` will return populated data. If for some reason it
  doesn't, we pass an empty `exchanges` array — modal still renders, filter
  tabs just don't populate. No crash.
- **Result count — one-shot.** SC calls the callback once per `searchSymbols`
  invocation; no pagination, no "load more". The 50-cap is final per query.
  Users who want a specific market beyond the 50 cap must narrow via typing.
- **`filterMarkets` regex mode.** When the user types a slash (`BTC/USDT`) or
  colon (`BINA:`), coinrayjs switches to regex matching on `fullDisplayName`.
  This is desirable — matches TV-style search expectations.
- **No cache invalidation.** If the user connects a new exchange api-key while
  the chart is already constructed, the `exchanges` list seen by SC is the one
  we passed at `onReady` time. SC caches it via `dataLoader.getConfiguration()`.
  Phase 1 accepts this staleness — the `exchanges` filter UI isn't rendered
  yet anyway. Revisit when SC ships the dropdown.

## Non-goals (from PRD, reiterated)

- No programmatic open.
- No trigger hiding.
- No styling override.
- No grid-bot support.
- No multi-type tabs.
- No exchange auto-switch.
- No Altrady-side caching beyond CoinrayCache's own.

## Open items for implementation

None — all decisions closed. Implementer applies `tasks.md` directly.
