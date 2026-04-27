---
id: sc-symbol-search
---

# Phase 1 — Symbol Search

## Summary

Enable SuperChart's built-in symbol-search modal (shipped in SC commit `eace49b`) in
Altrady's trading terminal chart. Clicking the symbol name in the period bar opens
SC's modal; the user types, picks a market, and the chart + active trading tab
update to the selected market.

## Why this now

SC's period bar already calls `onSymbolClick` when the symbol text is clicked
(internal to SC — not exposed to the consumer). The modal renders, but because
Altrady's datafeed stubs `searchSymbols` to return `[]` and omits
`exchanges` / `symbolsTypes` in `onReady`, the modal is currently empty and
unfilterable. Making the datafeed populate the modal unlocks the feature with no
host-side UI work.

## Requirements

### Functional

R1. Clicking the symbol text in the period bar opens SC's built-in search modal.
    (Behavior already shipped in SC — no Altrady wiring needed beyond what follows.)

R2. On modal open with an empty query, the modal shows a usable default list of
    markets. Default source and ordering: `CoinrayCache.searchMarkets("")` (or an
    equivalent list) capped at **50** results.

R3. As the user types, the modal calls `Datafeed.searchSymbols(query, exchange,
    symbolType, onResult)`. Altrady's datafeed must return matching markets via
    `onResult(results)` within a single callback, also capped at 50.

R4. Each result row carries enough data to render cleanly:

    | SC `SearchSymbolResult` field | Altrady source |
    |-------------------------------|----------------|
    | `symbol` (ticker)             | `market.coinraySymbol` (e.g. `BINA_USDT_BTC`) |
    | `full_name` (bold display)    | `${baseCurrency}/${quoteCurrency}` |
    | `description`                 | Base currency long name if available, else empty |
    | `exchange`                    | `exchange.name` (e.g. `"Binance"`) |
    | `type`                        | `"crypto"` (single type in phase 1) |
    | `logo`                        | `market.baseLogoUrl` |
    | `exchange_logo`               | `market.getExchange().logo` |

R5. `Datafeed.onReady` must include:
    - `supportedResolutions` — unchanged from today.
    - `exchanges: Array<{value, name}>` — the full list from
      `CoinrayCache.getExchanges()` mapped to `{value: code, name: name}`. Even
      though SC does not yet render the exchange filter UI, the datafeed must
      provide the data so the filter works the moment SC ships the dropdown.
    - `symbolsTypes: Array<{name, value}>` — phase 1: single entry
      `[{name: "Crypto", value: "crypto"}]`. Multi-type support is out of scope.

R6. Selecting a result in the modal triggers SC's existing `onSymbolChange`
    callback. Altrady's existing `market-tab-sync-controller` handles it and
    updates the active trading tab's `coinraySymbol` via Redux. No new wiring
    needed — verify only.

R7. Cross-exchange selection is permitted. If the selected market's
    `exchangeCode` differs from the active trading tab's exchange, the tab keeps
    its `exchangeApiKeyId` as-is; the chart switches to the new symbol. Trading
    actions on that tab will simply not line up with the chart symbol until the
    user also switches exchange — matching current behavior when a user changes
    `coinraySymbol` through other means. (Verification item — do not add guard
    rails in phase 1.)

### Search semantics

R8. `searchSymbols(userInput, exchange, symbolType, onResult)` contract for the
    Altrady datafeed:
    - Empty `userInput` → return the first 50 markets (server order / cache order).
    - Non-empty `userInput` → delegate to `CoinrayCache.searchMarkets(userInput)`.
      That coinrayjs API already does substring match across currency, pair, and
      exchange code. Cap at 50.
    - `exchange` argument: if non-empty, filter results to
      `market.exchangeCode === exchange`. Today SC always passes `""`; this
      branch is forward-compatible.
    - `symbolType` argument: ignore in phase 1 (we emit only `"crypto"`).
    - Callback is called exactly once per SC invocation.

### Visual / behavioral

R9. Styling is fully owned by SC (theme-aware via `data-theme` on the chart
    root). Altrady does not style the modal in phase 1.

R10. Debouncing is fully owned by SC (250 ms). Altrady's datafeed does no
     debouncing of its own — it responds to each callback synchronously or with
     at most one microtask.

R11. A missing `logo` on a result is acceptable — SC renders a placeholder.
     A missing `exchange_logo` is likewise acceptable.

R12. Closing the modal without selecting (Esc / backdrop click) does **not**
     change the chart symbol.

## Non-requirements (out of scope)

N1. **No programmatic open.** SC does not expose `openSymbolSearch()`. Altrady
    will not build a parallel search trigger in phase 1.

N2. **No trigger hiding.** SC does not expose a way to hide the symbol-name
    click target. We keep it visible.

N3. **No styling override** for the modal.

N4. **No integration with `MarketsList`** (`containers/trade/trading-terminal/widgets/markets/markets-list.js`).
    The existing exchange filter Redux state (`state.markets.filterExchangeCodes`)
    is independent and does not constrain or interact with SC's modal.

N5. **No multi-type tabs.** Spot vs Futures split is deferred. Phase 1 ships a
    single `"Crypto"` type.

N6. **No exchange auto-switch** on cross-exchange symbol selection — see R7.

N7. **No grid-bot chart integration.** The grid-bot standalone SC widget is out
    of scope for this subtask. Phase 1 covers the trading terminal chart only
    (`super-chart.js`).

N8. **No Altrady-side result caching** beyond what CoinrayCache already does.

## Open questions (resolve during design)

Q1. Should `description` fall back to the base currency's display name? Is such
    a name available on the coinray market or exchange object? If not, leave
    `description` empty and rely on `full_name` alone.

Q2. For the default list (R2, empty query), does `searchMarkets("")` return a
    sensible order, or should we surface popular pairs instead? Acceptable in
    phase 1: whatever `searchMarkets("")` returns, sliced to 50.

Q3. Ordering of `exchanges` array: alphabetical by name, or coinray's native
    order? Propose alphabetical by name. No UI impact today (SC doesn't render
    the filter) — pick whichever is cheaper.

Q4. Do we need to exclude `DELISTED` / `INACTIVE` markets (Market.status) from
    search results? Propose: yes, exclude anything not `"ACTIVE"`.

## Verification (for review phase)

V1. Click the symbol text in the period bar → SC modal opens.
V2. Modal shows a non-empty default list on open (no typing required).
V3. Typing a partial query (e.g. `"eth"`) filters to matching markets.
V4. Each row shows pair, exchange name, base logo, exchange logo.
V5. Selecting a result switches the chart to that market; tab Redux state
    reflects the new `coinraySymbol`.
V6. Pressing Esc closes the modal without changing the chart.
V7. Trading Terminal context tests (per `ai/workflow.md`):
    - Open modal from Tab A → select a symbol → switch to Tab B → switch back
      to Tab A. Tab A shows the newly selected symbol.
    - Change resolution on a tab → open modal → select a symbol. Resolution is
      preserved after selection.
    - Change exchangeApiKeyId on a tab → open modal → select a same-exchange
      symbol. Works. Then select a different-exchange symbol (R7). Chart
      switches; tab's exchangeApiKeyId is unchanged.
    - Switch coinraySymbol through the existing markets list → open modal → the
      modal does not reflect the list's exchange filter (modal is independent).
