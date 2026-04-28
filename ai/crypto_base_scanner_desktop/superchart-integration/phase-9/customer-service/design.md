# Design: Customer Service Charts — SuperChart Integration

## Key Design Decisions

### 1. Fourth SC widget variant — `CustomerServiceSuperChartWidget`

Mirrors the established pattern of `GridBotSuperChartWidget` (standalone,
no `MarketTabContext` from above) and `PreviewSuperChartWidget` (no
sub-controllers). Difference from those two:

- Unlike preview: real `CoinrayDatafeed`, real symbol/period from prop,
  and a small subset of sub-controllers attached.
- Unlike grid-bot: no grid-bot overlays; mounts the trading-page-style
  read-only overlay set; renders Alert header buttons.

Constants at the top of the widget file:

```js
const CS_RESOLUTION = "60"   // matches existing TV CS default
```

Registry key: `cs-<uuid>` (per-mount). The chart never participates in
multi-chart sync — it's standalone and its id is not derived from a
MarketTab.

### 2. Synthesized `MarketTabContext` + `MarketTabDataContext`

Existing SC overlays consume `MarketTabContext` and `MarketTabDataContext`
directly. Rather than threading a "marketTabId override" prop through
every overlay (the preview chart's "override props" pattern), the CS
widget publishes thin contexts above the chart container so all
overlays Just Work.

```jsx
const csMarketTab = useMemo(() => ({
  id: undefined,
  coinraySymbol,
  currentMarket,
  exchangeCode: currentMarket?.exchangeCode,
  resolution: CS_RESOLUTION,
}), [coinraySymbol, currentMarket])

const csMarketTabData = useMemo(() => ({
  marketTradingInfo: marketTradingInfo || EMPTY_MARKET_TRADING_INFO,
}), [marketTradingInfo])

return (
  <SuperChartContextProvider chartId={chartId}>
    <MarketTabContext.Provider value={csMarketTab}>
      <MarketTabDataContext.Provider value={csMarketTabData}>
        <CustomerServiceSuperChart .../>
        ...overlays + HeaderButtons + Screenshot
      </MarketTabDataContext.Provider>
    </MarketTabContext.Provider>
  </SuperChartContextProvider>
)
```

`currentMarket` is derived inside the widget via
`createCurrentMarket(coinraySymbol)` (the same call
`useTradingViewMarket` uses on the prop-override path). This keeps the
CS pages' call site clean — they only need to pass `coinraySymbol` +
`marketTradingInfo`.

`CurrentPositionContext` is **not** synthesized here. The position page
already wraps its subtree in `WithPosition`, which provides
`CurrentPositionContext` with the customer's parsed position. The
market page intentionally has no current position; default empty
context is the right behaviour.

`id: undefined` is intentional. Replay/positions/tradeForm Redux
selectors key by `marketTabId`; with `undefined` they return falsy and
no replay UI mounts — even though the matching React components also
aren't in our tree, this is a defence-in-depth.

### 3. Sub-controller attach: `HeaderButtonsController` + `PositionsController`

The base `ChartController` constructor sets up the always-on
sub-controllers (`HeaderController`, `AlertsController`,
`TradesController`, `BasesController`, `GridBotController`,
`InteractionController`). Optional sub-controllers (`marketTabSync`,
`headerButtons`, `contextMenu`, `positions`, `tradeForm`, `replay`)
are nullable; the base `dispose()` tears them down via optional
chaining.

CS attach list (after `new ChartController(...)`, before `onReady`):

```js
controller.headerButtons = new HeaderButtonsController(controller)
controller.positions = new PositionsController(controller)
```

Everything else stays null. Sub-controller dependency map for the
overlays we mount (verified by `grep -E "chartController\.(positions|trades|alerts|bases|gridBot|tradeForm|headerButtons|contextMenu|replay|marketTabSync|interaction|header)"`
across the overlay tree):

| Overlay | Controller(s) used |
|---|---|
| `BidAsk` | (none — uses base `ChartController` helpers) |
| `BreakEven` | `positions.createBreakEven` |
| `Bases` | `bases.*` (always-on) |
| `Trades` | `trades.*` (always-on) |
| `PnlHandle` | `positions.createPnlHandle` |
| `Orders` (and entry/exit/stop-loss/smart/standalone/conditions/expirations/saving children) | `positions.createSubmitted*` |
| `PriceAlerts` / `EditPriceAlert` / `TriggeredPriceAlerts` | `alerts.*` (always-on) |
| `TimeAlerts` / `EditTimeAlert` / `TriggeredTimeAlerts` | `alerts.*` |
| `TrendlineAlerts` / `EditTrendlineAlert` / `TriggeredTrendlineAlerts` | `alerts.*` |
| `TaScannerAlerts` | `alerts.createTaScannerAlert` |
| `HeaderButtons` | `headerButtons.createHeaderButtons` + `header.createShareButton` |
| `Screenshot` | (none — modal triggered via header button) |

Why the others stay off:

| Controller | Why off on CS |
|---|---|
| `MarketTabSyncController` | No MarketTab to write back to — chart-driven symbol/period changes are session-local and do not propagate. |
| `ContextMenuController` | Avoids chart-area and overlay right-click menus. The chart-area menu would expose trading/replay options; the overlay menu would expose alert delete (routed through the existing alerts UI on the right-side panel of the CS page). |
| `TradeFormController` | TT trade-form lifecycle. `PositionsController`'s TT-specific edit-handle helpers reference `this.c.tradeForm?._tradeForm?.*` only on paths that fire from edit-order overlays, which we don't mount. Optional chains short-circuit safely. |
| `ReplayController` | No replay UI, no replay button. |

### 3a. Chart-settings override — block customer-side trading from order handles

`PositionsController` is required by the read-only `Orders` display, but
its order-handle and PnL-handle code wires `onModify` / `onCancel`
callbacks (which dispatch `editOrder` / `cancelOrder` /
`closeOrDeletePosition` against the **customer**'s data) when these
chart settings are on:

- `openOrdersEnableEditing` — order modify button
- `openOrdersEnableCanceling` — order cancel button
- `positionsEnableCanceling` — PnL handle close button

The staff has these on by default; without scoping, mounting
`PositionsController` on CS would let staff cancel/edit a customer's
orders by clicking on the chart. That's the trading interaction we
explicitly disallow.

Solution: pass `getChartSettings` to `ChartController` (existing hook,
introduced for the settings-preview chart). The override returns the
staff's `chartSettings` with the three interactive flags pinned to
`false`:

```js
new ChartController(superchart, datafeed, {
  ...,
  getChartSettings: () => ({
    ...store.getState().chartSettings,
    openOrdersEnableEditing: false,
    openOrdersEnableCanceling: false,
    positionsEnableCanceling: false,
  }),
})
```

`controller.chartSettings` reads through this override, so all three
sub-controllers (`PositionsController`, `AlertsController`,
`TradesController`, etc.) see the locked flags. Alert-related flags
(`alertsEnableEditing`, `alertsEnableCanceling`,
`alertsShowLine`, `alertsShowNote`) are not touched — staff alert
creation/edit/delete works.

`useSuperChart()`'s `chartSettings` value continues to come from raw
Redux (used by overlay components for display-only checks like
`miscShowOrderBookAskBid`, `miscShowBreakEvenPoint`,
`openOrdersShow`). Display behaviour matches TT exactly. Only the
controller-side callback wiring is locked.

### 4. Header buttons — Alert only

`<HeaderButtons mainChart={false}/>` (no `gridBotChart`) calls
`chartController.headerButtons.createHeaderButtons({mainChart:
false, onAlert, onBuy, onSell, onReplay, onSettings})`. Today the
controller creates Alert + Replay + Settings unconditionally, plus
Buy/Sell when `mainChart`. We need Alert only.

**One library tweak** in `controllers/header-buttons-controller.js`:
move Replay-button **and** Settings-button creation into the existing
`if (mainChart)` block alongside Buy/Sell:

```diff
   if (mainChart) {
     this._buyButton = this._createToolbarButton({...})
     this._sellButton = this._createToolbarButton({...})
+    this._replayButton = this._createToolbarButton({
+      icon: "backward", text: t("replay"), tooltip: t("pickReplayStart"),
+      onClick: onReplay,
+    })
+    this._settingsButton = this._createToolbarButton({
+      icon: "gear", text: t("settings"), tooltip: t("chartSettings"),
+      borderColor: "rgba(20,26,33,0.4)", onClick: onSettings,
+    })
   }
-
-  this._replayButton = this._createToolbarButton({
-    icon: "backward", text: t("replay"), tooltip: t("pickReplayStart"),
-    onClick: onReplay,
-  })
-
-  this._settingsButton = this._createToolbarButton({
-    icon: "gear", text: t("settings"), tooltip: t("chartSettings"),
-    borderColor: "rgba(20,26,33,0.4)", onClick: onSettings,
-  })
```

Behaviour change scope:

- TT (`mainChart=true`): unchanged — still gets all five buttons.
- Grid-bot (`gridBotChart=true`): unchanged — `HeaderButtons` early-exits
  via `if (!gridBotChart)` before `createHeaderButtons` runs at all.
- CS (`mainChart=false`, no `gridBotChart`): gets Alert only.
  This is the new and desired behaviour.

`setHeaderButtonsEnabled` and `setReplayButtonHighlight` already null-check
their button refs (`if (!btn) continue`, `if (!this._replayButton) return`)
so they remain safe with the gated buttons.

Settings is dropped on CS for two reasons: the chart-settings modal it
opens lives in the TT (`gridItemSettingsContext.onToggle("CenterView")`
falls back to the context default `() => null` on CS — the button was
inert), and the staff can change all chart settings from the TT
session anyway.

### 4a. Disabled symbol-search trigger

The SC period bar exposes a clickable symbol-search affordance
(`data-button="symbolSearch"`). On CS the chart is bound to the URL's
`coinraySymbol` — picking a different symbol from the chart UI would
desync chart and route. We therefore disable that one element.

Approach: after `superchart.onReady()` fires, query the trigger inside
the chart's `containerRef` and apply inline styles
(`pointer-events: none; opacity: 0.5; cursor: default`). Per-instance
scope — no global stylesheet, no impact on TT or any other chart.
Period picker / left-toolbar / fullscreen continue to work normally.

### 5. Alert creation flow

The staff alert flow on CS works exactly as on TT, against the staff's
own session:

```
[staff clicks Alert button]
  └── HeaderButtons.onAlert
       └── dispatch(newAlert(currentMarket.coinraySymbol, {price: lastPrice}))
            └── alertsForm Redux state goes to "creating"
                 └── EditPriceAlert overlay sees alertsForm.isEditing
                      └── chartController.alerts.createEditingPriceAlert(alert)
                           └── draws draggable order line on chart
                                └── click body / drag → submit / move
                                     └── dispatch(submitAlertsForm()) / editAlert()
```

This requires:
- `<HeaderButtons/>` mounted (R4 — yes).
- `<EditPriceAlert/>`, `<EditTimeAlert/>`, `<EditTrendlineAlert/>`
  mounted (R4 — yes).
- `AlertsController` available on the controller (always-on — yes).
- `currentMarket` in `MarketTabContext` (synthesized — yes).

No dependency on `TradeFormController`, `PositionsController`, or
`ReplayController`. Verified by grep:
`grep -n "tradeForm\|positions\." overlays/alerts/` returns nothing.

### 6. Widget lifecycle (effects)

Mirrors `grid-bot-super-chart.js`, with the synth contexts added:

- **Mount effect** — build `CoinrayDatafeed`, dataLoader, Superchart,
  ChartController (with `getChartSettings` override per §3a). Attach
  `headerButtons` and `positions`. Register in `ChartRegistry`.
  Subscribe an `onReady` callback that disables the symbol-search
  trigger (per §4a). Cleanup: unsub onReady + unregister +
  `controller.dispose()`.
- **`setCurrentMarket` effect** — `controller.setCurrentMarket(currentMarket)`
  on every `currentMarket` change (read from the synth `MarketTabContext`
  via `useContext(MarketTabContext)`). Required because
  `PositionsController` (and a few edges of `AlertsController` /
  `TradesController`) read `this.c._currentMarket?.getMarket()` to compose
  handle labels — base/quote currency, precisions. Without this,
  e.g. an open TP order draws as `"104"` instead of `"104 XNO"`. Mirrors
  TT `super-chart.js`.
- **Symbol effect** — on `coinraySymbol` change,
  `superchart.setSymbol(toSymbolInfo(coinraySymbol))`.
- **Theme effect** — `controller.syncThemeToChart(theme?._name)`.
- **Colors effect** — on `chartColors` / `theme._name`,
  `controller.syncChartColors()`.
- **Resize effect** — `ResizeObserver` → `controller.resize()`.

No resolution effect — we don't sync resolution back to anything; the
chart's own period selector handles user changes locally.
No VR-persist effect.
No mark-mounted ref dance — there is no
`MarketTabSyncController.syncSymbolToChart`, just plain
`superchart.setSymbol`, which is safe to call always.

### 7. Page-level usage

`account/market.js`:

```jsx
import CustomerServiceSuperChartWidget from "../../trade/trading-terminal/widgets/super-chart/customer-service-super-chart"
...
<CustomerServiceSuperChartWidget
  coinraySymbol={coinraySymbol}
  marketTradingInfo={marketTradingInfo}/>
```

`account/position.js`:

```jsx
<CustomerServiceSuperChartWidget
  coinraySymbol={coinraySymbol}
  marketTradingInfo={marketTradingInfo}/>
```

The position page is already wrapped in `<WithPosition position=…>` so
`CurrentPositionContext` flows down to the chart's overlays. No extra
wiring needed at the page level.

The existing `mainChart={false}` prop is dropped from both call sites —
it's no longer meaningful (no `ChartContextProvider` consumes it; the
new widget handles the equivalent semantics via its hardcoded shape).

## Data Flow

```
account/market.js or account/position.js
  ├── coinraySymbol (URL param)
  └── marketTradingInfo (fetched per exchangeApiKeyId)
       │
       ▼
  <CustomerServiceSuperChartWidget coinraySymbol marketTradingInfo>
       │
       ├── createCurrentMarket(coinraySymbol)
       │
       ├── <SuperChartContextProvider>          (Redux: chartSettings + chartColors)
       │    ├── <MarketTabContext.Provider>      (synth: id=undef, coinraySymbol, currentMarket, resolution=60)
       │    │    └── <MarketTabDataContext.Provider>   (synth: marketTradingInfo)
       │    │         ├── <CustomerServiceSuperChart/>  (chart container + lifecycle)
       │    │         ├── <HeaderButtons mainChart={false}/>   (Alert)
       │    │         ├── <Screenshot/>
       │    │         ├── <BidAsk/>
       │    │         ├── <BreakEven/>           ◄── reads CurrentPositionContext (from <WithPosition/> on position page)
       │    │         ├── <Bases/>
       │    │         ├── <Trades/>
       │    │         ├── <PnlHandle/>           ◄── reads CurrentPositionContext
       │    │         ├── <Orders/>
       │    │         ├── <PriceAlerts/> + <EditPriceAlert/> + <TriggeredPriceAlerts/>
       │    │         ├── <TimeAlerts/> + <EditTimeAlert/> + <TriggeredTimeAlerts/>
       │    │         ├── <TrendlineAlerts/> + <EditTrendlineAlert/> + <TriggeredTrendlineAlerts/>
       │    │         └── <TaScannerAlerts/>
```

## File Changes

### New files

| File | Purpose |
|---|---|
| `super-chart/customer-service-super-chart.js` | `CustomerServiceSuperChartWidget` + inner `CustomerServiceSuperChart` |

### Modified files

| File | Changes |
|---|---|
| `super-chart/controllers/header-buttons-controller.js` | Gate Replay-button creation under `if (mainChart)` |
| `containers/customer-service/account/market.js` | Swap `DefaultTradingWidget` → `CustomerServiceSuperChartWidget`; drop `mainChart={false}` prop |
| `containers/customer-service/account/position.js` | Same swap |

## Invariants / Constraints

- The widget attaches `HeaderButtonsController` and
  `PositionsController` (the latter required by `BreakEven`,
  `PnlHandle`, and all `Orders` children). Any other optional
  sub-controller stays null — `ChartController.dispose()` iterates all
  sub-controller fields with optional chaining.
- The `getChartSettings` override on `ChartController` pins
  `openOrdersEnableEditing`, `openOrdersEnableCanceling`, and
  `positionsEnableCanceling` to `false`. This is the chokepoint that
  prevents `PositionsController` from wiring `editOrder`/`cancelOrder`/
  `closeOrDeletePosition` callbacks against the customer's data.
- `<HeaderButtons mainChart={false}/>` after the library tweak produces
  exactly **Alert** — no Buy, no Sell, no Replay.
- The Settings header button is **inert** on CS (no
  `GridItemSettingsProvider` above the widget). This matches existing
  TV behaviour. Out of scope to wire up a CS-only settings modal.
- `EditPriceAlert` / `EditTimeAlert` / `EditTrendlineAlert` are
  required for the Alert flow to finalize submission. Removing them
  would break alert creation.
- `EditOrders` is **not** mounted, so order lines never become
  draggable on CS. Order-line creation/edit is structurally
  impossible.
- No `ChartHotkeys` / `TradingHotkeys` / `ReplayHotkeys` are bound —
  staff can switch to the TT in another tab without competing
  hotkey handlers.
- `marketTabId === undefined` in synth context: replay-keyed selectors
  (`selectReplayMode`, `selectReplaySession`, `selectReplayCurrentPosition`,
  `selectReplayTrades`, `state.positions.positionDates[undefined]`)
  resolve to falsy — no replay paths activate even where overlays
  reference them defensively (e.g. `BreakEven`, `Trades`, `PnlHandle`,
  `HeaderButtons`).
- `MarketTabDataContext.exchangeApiKey` is undefined — `HeaderButtons`
  uses it only inside the Buy/Sell `conditionalCallback`, which is gated
  off by `mainChart={false}`. Safe.

## Open Questions

- **Settings button on CS**: leave inert (matches TV) vs hide entirely
  vs wire to a CS-only chart settings modal. Default in this PRD: leave
  inert. Revisit if staff find it confusing during review.
- **Future /charts page port (Phase 9a)**: shares 80% of this widget's
  shape (synth contexts, read-only overlays). Likely the right move is
  to factor a `DefaultSuperChartWidget` then have CS and /charts both
  consume it. Out of scope here; deferred until /charts work begins.
