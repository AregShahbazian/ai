# Phase 1 — Symbol Search — Tasks

Single-file change. No imports beyond what the file already has, except for
`getCoinrayCache` which is already imported.

## Task 1 — Add `marketToSearchResult` helper

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/coinray-datafeed.js`

**Where:** Module scope, above the `CoinrayDatafeed` class (after the imports).

**Add:**

```js
const marketToSearchResult = (market) => {
  const exchange = market.getExchange()
  return {
    symbol: market.coinraySymbol,
    full_name: market.displayName,
    description: "",
    exchange: exchange.name,
    type: "crypto",
    logo: market.baseLogoUrl,
    exchange_logo: exchange.logo,
  }
}
```

**Why:** Reused by `searchSymbols` in Task 3. Module-level (not a class method
or static) because it's a pure data transform with no dependency on instance
state. Easier to read in isolation.

**Verify:** Syntax only. No runtime path hits it yet.

## Task 2 — Populate `onReady` with `exchanges` + `symbolsTypes`

**File:** same.

**Replace** the existing `onReady`:

```js
onReady = (callback) => {
  setTimeout(() => {
    callback({
      supportedResolutions: SUPPORTED_RESOLUTIONS,
    })
  }, 0)
}
```

**With:**

```js
onReady = (callback) => {
  setTimeout(() => {
    const exchanges = Object.values(getCoinrayCache().getExchanges())
      .filter((ex) => ex.active)
      .map((ex) => ({value: ex.code, name: ex.name}))
      .sort((a, b) => a.name.localeCompare(b.name))
    callback({
      supportedResolutions: SUPPORTED_RESOLUTIONS,
      exchanges,
      symbolsTypes: [{name: "Crypto", value: "crypto"}],
    })
  }, 0)
}
```

**Verify:**
- Console-log `dataLoader.getConfiguration()` once after chart mount (temporary,
  removed after verification). Confirm `exchanges` is a non-empty array of
  `{value, name}` objects in alphabetical order, and `symbolsTypes` is
  `[{name: "Crypto", value: "crypto"}]`.

## Task 3 — Implement `searchSymbols`

**File:** same.

**Replace** the stub:

```js
searchSymbols = (userInput, exchange, symbolType, onResult) => {
  onResult([])
}
```

**With:**

```js
searchSymbols = (userInput, exchange, symbolType, onResult) => {
  try {
    const query = (userInput || "").trim()
    const cache = getCoinrayCache()
    const markets = query
      ? Object.values(cache.searchMarkets(query))
      : Object.values(cache.searchMarkets(""))
    const results = markets
      .filter((m) => m && m.status === "ACTIVE")
      .filter((m) => !exchange || m.exchangeCode === exchange)
      .slice(0, 50)
      .map(marketToSearchResult)
    onResult(results)
  } catch (error) {
    console.error("CoinrayDatafeed searchSymbols error:", error)
    onResult([])
  }
}
```

Notes:
- The empty/non-empty query branches both call `searchMarkets` for symmetry.
  `searchMarkets("")` returns the input map unchanged (`filterMarkets` bails
  early when no truthy query), so this is a single code path with no wasted
  work.
- Filter order matters: `ACTIVE` first (cheap), then `exchange` (cheap),
  `slice(50)` before `map` to keep object construction bounded.
- Synchronous `onResult` — SC wraps it into a promise internally. No
  `setTimeout` needed; it would only add latency.
- `onResult([])` on error so the modal clears the results list rather than
  hanging on stale content.

**Verify:**
- Open modal → default (empty query) list populates within 250 ms of open.
- Type `eth` → filtered list appears after debounce.
- Type `btc/usdt` (slash triggers regex mode in `filterMarkets`) → matches.
- Type a gibberish query → modal shows "no results" state.

## Task 4 — Smoke test (manual, no code)

1. `yarn start-web` (or `yarn start`).
2. Open the trading terminal, make sure a chart is visible.
3. Click the symbol name in the period bar → modal opens, default list is
   populated.
4. Type `btc` → list filters.
5. Click a result → modal closes, chart switches to that symbol, active
   trading tab's symbol reflects the selection.
6. Press Esc without selecting → modal closes, chart unchanged.

Detailed verification items (for review phase) live in PRD §Verification
(V1–V7). Tasks 1–3 together satisfy V1–V5 and the foundation for V6–V7; V6/V7
are review-time verifications on the user side.

## Out-of-scope reminders

- Do **not** touch `super-chart.js`.
- Do **not** touch `market-tab-sync-controller.js`.
- Do **not** add Redux state for the modal.
- Do **not** add an i18n string for `"Crypto"` — this field is an SC data value
  (the `symbolsTypes[i].name`), not user-facing copy that the host app owns.
  SC's own i18n handles modal chrome. If the label needs to vary by locale
  that's an SC API request.
- Do **not** alter `SUPPORTED_RESOLUTIONS` or any existing method on the class.
