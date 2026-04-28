---
id: sc-customer-service-charts
---

# PRD: Customer Service Charts — SuperChart Integration

## Overview

Replace the TradingView-based chart on the two **Customer Service** pages
that mount one (`account/market.js` and `account/position.js`) with a new
SuperChart variant. The CS chart is a read-only view of a customer's
market/position used by Altrady support staff during account inspection —
the goal of this PRD is a clean port that preserves what's there today,
not a redesign.

Scope is intentionally narrow:

- A new SC widget variant (`CustomerServiceSuperChartWidget`) alongside
  `SuperChartWidget` (TT), `GridBotSuperChartWidget`, and
  `PreviewSuperChartWidget`.
- Overlay set: bid/ask, break-even, bases, trades, pnl handle, orders
  (read-only display, no edit), all alert types **with** their edit
  overlays (so staff alert creation flow works), TA-scanner alerts.
- A minimal header with **Alert** + **Settings** buttons only (matches
  TV's CS behaviour). No Buy/Sell, no Replay.
- No trading hotkeys, no chart context menu, no overlay context menu,
  no mobile action buttons.
- Customer's `marketTradingInfo` (already fetched per
  `exchangeApiKeyId`) flows through unchanged.
- Customer's position (on the position page) flows through unchanged via
  the existing `WithPosition` wrapper — no new wiring needed.

**Explicit constraints — what stays vs what is dropped vs TV:**

TV's CS chart today (with `mainChart={false}`) shows two header
buttons: **Alert** (always) and **Settings** (always). The Alert button
starts an alert-creation flow that is finalized by clicking on the
chart canvas. Buy/Sell/Replay are absent because `mainChart={false}`
gates them off (and TV had no Replay button at all on CS).

SC port preserves this:

- **Keep:** the Alert header button, the staff's full alert-creation /
  edit / delete flow against the staff session.
- **Drop:** the Settings header button — the chart-settings modal is
  TT-only (no `GridItemSettingsProvider` above the CS chart, so the
  button was inert anyway).
- **Drop:** Buy/Sell trading buttons, any trading interaction
  (order-line drag, chart right-click "Create Buy/Sell at price",
  mobile action-button bar, trading hotkeys).
- **Drop:** the entire Replay surface — no Replay header button (SC
  default mounts one even when `mainChart={false}`; we gate it off),
  no replay timelines, no replay hotkeys, no "pick replay start".
- **Drop:** chart context menu and overlay context menu — both depend
  on `ContextMenuController` which we don't attach. Alert
  delete-via-right-click was a TV affordance; staff can delete alerts
  from the existing alerts UI on the right-side panel of the CS page,
  so chart-side right-click is not required.
- **Disable:** the period-bar **symbol-search** trigger. CS pages
  drive the symbol from the URL — letting the staff pick a different
  symbol from the chart UI would desync chart and route. The period
  picker stays enabled (staff can change resolution locally).

The CS pages currently mount `DefaultTradingWidget` from
`tradingview.js` with `mainChart={false}`. After this PRD they will
instead mount the new SC widget; the TV widget stays in tree only for
non-CS consumers (quizzes, /charts page) until their own ports land.

## Current Behavior (TradingView)

### Where the chart lives

Two pages mount `DefaultTradingWidget`:

| Page | File | Route |
|---|---|---|
| Market | `containers/customer-service/account/market.js` | `/customer-service/accounts/:accountId/markets/:coinraySymbol/:exchangeApiKeyId?tab=…` |
| Position | `containers/customer-service/account/position.js` | `/customer-service/positions/:id?tab=…` |

In both cases the chart sits in the left half of a `flex-row flex-wrap`
layout and the right half is a `WidgetTabs` panel (Market Info / Open
Orders / Orders / Trades / Alerts / Position Info / Log / Position
Settings / etc.). The right panel reads from `MarketContext` /
`PositionContext` (CS-specific contexts) and is unrelated to the chart.

### What's mounted on the chart

`DefaultTradingWidget` (`widgets/center-view/tradingview.js:43-47`) wraps
`TradingViewChart` and mounts `DEFAULT_CHART_COMPONENTS`:

```
PriceTimeSelect, BidAsk, BreakEven, Bases, Alerts, EditAlerts,
TradingViewEnhancements, Orders, Trades, CustomIndicators,
TaScannerAlerts
```

CS passes `mainChart={false}`, which:
- Hides the **Buy / Sell / Replay / Settings** header buttons
  (`tradingview/header.js`).
- Hides the **Submit / Reset / Cancel** action buttons bar on mobile
  (`tradingview/action-buttons.js`).

`DefaultTradingWidget` (vs `MainChartTradingWidget`) **already excludes**
the editing overlays (`EditOrders`, `EditEntryConditions`,
`EditEntryExpirations`) — so dragging an order line on CS today is not
possible. The included `EditAlerts` component is dormant unless an alert
is being edited from the alerts UI; the alerts UI is not on the CS page.

### Data flow (preserve as-is)

| Chart input | Source on CS pages |
|---|---|
| Candles | Live Coinray for `coinraySymbol` |
| `marketTradingInfo` | `fetchMarketTradingInfo({exchangeApiKeyId, coinraySymbol})` — **the customer's** open orders, smart orders, base trades, balances, etc. |
| Current position | Position page only — `fetchPosition(positionId)`, parsed and provided through `WithPosition` → `CurrentPositionContext`. |
| Alerts / TA-scanner alerts / bases settings / chart colors | Redux — **the staff member's** state (existing limitation; intentionally preserved). |

The "staff state for alerts/scanner" leakage is pre-existing TV
behaviour. This PRD does **not** try to scope alerts/TA-scanner data per
customer — that would be a larger product change.

### Other CS surfaces touching TV

- `account/layouts.js` — admin table at
  `/customer-service/accounts/:id/layouts` listing user-saved chart
  layouts via `actions/customer_service/tradingview-charts.js`. This is
  **not a chart**; it edits server-side TV chart-layout records via
  `/api/v2/tradingview_charts`. Out of scope here — handled by Phase 10f
  TV-removal cleanup, when SC's `StorageAdapter` (Phase 6) replaces this
  endpoint.

## Requirements

### R1 — `CustomerServiceSuperChartWidget` (new SC variant)

New widget at `super-chart/customer-service-super-chart.js`, alongside
`super-chart.js`, `grid-bot-super-chart.js`, and
`preview-super-chart.js`. Behaviour:

- Mounts a single `Superchart` instance on mount, disposes on unmount.
- Symbol: from required `coinraySymbol` prop, resolved via
  `toSymbolInfo(coinraySymbol)`.
- Period: hardcoded `toPeriod("60")` initial — same default the existing
  CS chart uses today (resolution comes from TV's persisted state on the
  staff session, but the CS chart has no resolution prop and ends up at
  `60`).
- DataLoader: standard `CoinrayDatafeed` (live data — same as TT/grid-bot).
- Theme: synced from `ThemeContext`, same pattern as the other variants.
- Wraps children in `SuperChartContextProvider`.
- Registers with `ChartRegistry` under `cs-<uuid>` (per-mount) — same
  pattern and rationale as `GridBotSuperChartWidget`. The id never goes
  into `MarketTabContext` so replay-keyed selectors stay inert (R3).
- Renders `<HeaderButtons/>` with `mainChart={false}` and **no**
  `gridBotChart` prop — produces the Alert button only. Buy / Sell /
  Replay / Settings are all gated under `mainChart` in the controller
  (R3 library tweak).
- Disables the period-bar **symbol-search** trigger after `onReady`
  (CSS scoped to the chart container — staff can't change symbol
  from the chart). Period picker stays enabled.
- Renders **no** action buttons bar, **no** trading hotkeys, **no**
  replay hotkeys, **no** chart context menu, **no** overlay context
  menu.
- Mounts the overlay set (R4).

### R2 — Synthesized market context

CS pages don't have a `MarketTabContext` (those exist in the Trading
Terminal). To let the existing SC overlays work unchanged, the widget
publishes thin synthesized contexts above the chart container:

- `MarketTabContext.Provider` with:
  - `id: undefined` — keeps replay/positions/tradeForm selectors that key
    by `marketTabId` returning falsy, so no replay UI mounts.
  - `coinraySymbol` (from prop)
  - `currentMarket` — derived via
    `createCurrentMarket(coinraySymbol)` (mirrors
    `useTradingViewMarket`'s prop-override branch).
  - `exchangeCode: currentMarket?.exchangeCode`
  - `resolution: "60"` — fixed; the chart's own period selector still
    works locally but doesn't write back to any persisted state.
- `MarketTabDataContext.Provider` with `{marketTradingInfo}` from prop.
  Other fields (`exchangeApiKey`, `marketPositions`, ws update streams)
  default to `undefined` — overlays that read them already handle that
  shape.
- `CurrentPositionContext` is **not** provided by this widget — the
  position page already wraps its subtree in `WithPosition` (which
  provides it with the customer's parsed position), and the market page
  intentionally has no current position.

This is the same trick used by overlays' "preview override" props in
spirit (`bidPrice`, `marketTradingInfo` overrides) but applied at the
context level so we don't have to thread an override prop through every
overlay.

### R3 — Sub-controllers (two attached, rest off)

The TT widget attaches a stack of sub-controllers to its
`ChartController` after construction (`super-chart.js:122-134`):
`MarketTabSyncController`, `HeaderButtonsController`,
`ContextMenuController`, `PositionsController`, `TradeFormController`,
`ReplayController`. The CS widget attaches two:

- `HeaderButtonsController` — needed for the Alert header
  buttons (`<HeaderButtons mainChart={false}/>` calls
  `chartController.headerButtons?.createHeaderButtons(...)`).
- `PositionsController` — needed for `BreakEven`, `PnlHandle`, and
  every `Orders` child overlay (`entry-orders`, `exit-orders`,
  `stop-loss-orders`, `smart-orders`, `standalone-orders`,
  `entry-conditions`, `entry-expirations`, `saving-orders`). All call
  into `chartController.positions.*` methods.

All other optional sub-controllers stay off:

- `MarketTabSyncController` — off. CS has no MarketTab to write back to.
- `ContextMenuController` — off. No chart-area or overlay right-click
  menus (which would otherwise expose trading/replay options).
- `TradeFormController` — off. Not used by any overlay we mount; alert
  flow goes through `AlertsController` Redux dispatches; PositionsController's
  TT-specific edit-handle helpers reference `tradeForm` only on
  optional-chained paths that never fire because we don't mount the
  edit-order overlays.
- `ReplayController` — off. No replay UI is mounted.

The base `ChartController` constructor already sets up the always-on
sub-controllers (`HeaderController`, `AlertsController`,
`TradesController`, `BasesController`, `GridBotController`,
`InteractionController`); those stay.

`ChartController.dispose()` already tears optional sub-controllers down
via optional chaining — null fields are a no-op.

`nonInteractive: false`. The chart is fully interactive (scroll, zoom,
period change, alert click-to-submit) — only trading-specific
interactions are denied, and that denial is enforced two ways:

1. **Structural** — no `EditOrders`/edit-condition/edit-expiration
   overlays in the React tree, no `ContextMenuController` to wire
   right-click trading actions.
2. **Chart-settings override** — `PositionsController` reads
   `openOrdersEnableEditing`, `openOrdersEnableCanceling`, and
   `positionsEnableCanceling` from `controller.chartSettings` when
   wiring `onModify`/`onCancel` callbacks on the customer's order
   handles and the PnL handle. The CS widget passes a
   `getChartSettings` override to `ChartController` that pins these
   three flags to `false` regardless of the staff's actual chart
   settings. Read-only display flags (line/label visibility) and
   alert-related flags pass through unchanged, so the staff alert
   creation/edit/delete flow against the staff session is unaffected.

The override hook is the same one `PreviewSuperChartWidget` uses for
its modal-local color/setting preview — see
`chart-controller.js` `_getChartSettings` / `get chartSettings`.

**One library tweak** to make the Alert-only header possible: in
`HeaderButtonsController.createHeaderButtons`, move Replay and
Settings into the `mainChart` block alongside Buy/Sell.
Today they're created unconditionally; this is fine for
TT (`mainChart=true`) and grid-bot (skips `createHeaderButtons` via
`if (!gridBotChart)` in `HeaderButtons`), but bleeds onto CS once we
mount `<HeaderButtons mainChart={false}/>`. The fix is one
`if (mainChart)` block in the controller — no behaviour change for
TT or grid-bot.

### R4 — Overlay set

Mount these overlays as children of `SuperChartContextProvider`. Set
mirrors TV's `DEFAULT_CHART_COMPONENTS` minus TV-only chrome (custom
indicators / TV enhancements / `PriceTimeSelect`) minus order-edit, but
keeps the alert-edit overlays so the Alert button flow finalizes
correctly:

| Overlay | Why it ports |
|---|---|
| `BidAsk` | TV had it. Live bid/ask from Coinray. |
| `BreakEven` | TV had it. Reads `marketTradingInfo` + `CurrentPositionContext`. |
| `Bases` | TV had it. Reads staff's base scanner state from Redux (preserve existing behaviour). |
| `Trades` | TV had it. Reads `marketTradingInfo` for closed trades. |
| `PnlHandle` | New since TV — adds value on the position page; harmless on the market page (no current position → no draw). |
| `Orders` | TV had it. Reads `marketTradingInfo.openOrders` / `openSmartOrders`. **No** `EditOrders` sibling — order-line drag and order-edit are off. |
| `PriceAlerts` + `EditPriceAlert` + `TriggeredPriceAlerts` | TV had them under the `Alerts`/`EditAlerts` umbrella. Edit overlay is required for the Alert-header-button flow to capture the staff's chart click and submit. |
| `TimeAlerts` + `EditTimeAlert` + `TriggeredTimeAlerts` | Same rationale as price alerts. |
| `TrendlineAlerts` + `EditTrendlineAlert` + `TriggeredTrendlineAlerts` | Same rationale. |
| `TaScannerAlerts` | TV had it. Live-only Redux-sourced alerts. |
| `Screenshot` | TV had it (via `ChartController.createButton`). SC version is a thin React component listening for the screenshot button / clipboard share. |
| `HeaderButtons` (`mainChart={false}`, no `gridBotChart`) | Renders the Alert button only. R3 library tweak moves Buy/Sell/Replay/Settings under the `mainChart` gate. |

**Not mounted** on CS:

- `EditOrders` (and entry-condition / entry-expiration siblings) — no
  trading interaction.
- `ChartContextMenu`, `OverlayContextMenu` — no right-click menus.
  Both depend on `ContextMenuController` which we don't attach.
- `ReplayTimelines` and any replay UI — no replay on CS.
- `ActionButtons`, `PickReplayStartButton` — no mobile trading bar.
- `TradingHotkeys`, `ReplayHotkeys`, `ChartHotkeys` — no global
  hotkeys take over the staff session while a CS page is open.
- `PriceTimeSelect`, `TradingViewEnhancements`, `CustomIndicators` from
  the TV set — TV-specific or Phase 8.

### R5 — Chart settings + colors

Standard live behaviour: `useSuperChart()` reads `chartSettings` and
`chartColors` from Redux. Toggling chart settings on the staff session
updates the CS chart immediately, identical to the existing TV
behaviour. No prop overrides needed.

### R6 — No persistence, no MarketTab writes

- The widget does **not** persist visible range, period, or symbol
  changes anywhere — there is no MarketTab to write to and no CS-side
  state to keep.
- The widget does **not** persist drawings or layouts. SC's
  `StorageAdapter` is not wired (Phase 6); CS's read-only nature means
  drawings made by the staff member are session-local. (The staff
  could already do this on TV today; persistence parity is a Phase 6
  concern, not this PRD.)
- `MarketTabSyncController` is not attached, so chart-driven symbol or
  resolution changes don't propagate anywhere.

### R7 — Single-instance coordination

The CS pages live under `/customer-service/...` routes, **outside** the
Trading Terminal route. The TT chart is not mounted while a CS page is
open, so the SC singleton-store concern that drives the
settings-preview's `previewShown` coordination (PRD `sc-settings-preview`
R6) does not apply here. No special mount/unmount choreography needed.

The only same-page case is opening a CS market page and a CS position
page in two browser windows — each window is a separate SC store, so
that is fine.

### R8 — Visibility / mobile

The CS pages are admin-only and desktop-first. Existing CS pages have no
mobile-specific chart treatment; this PRD inherits that. No `ScreenContext`
gating, no `ActionButtons` mobile bar.

## Data Sources

| Piece | Source |
|---|---|
| Candles | Live Coinray (`CoinrayDatafeed`) |
| `coinraySymbol` | URL param on the CS page |
| `currentMarket` | `createCurrentMarket(coinraySymbol)` inside the widget |
| `marketTradingInfo` | Prop — `fetchMarketTradingInfo({exchangeApiKeyId, coinraySymbol})` on the CS page |
| Current position (position page only) | `WithPosition` → `CurrentPositionContext` (already in tree) |
| Chart settings / colors | Redux (staff session) — same as TT |
| Alerts / bases / TA-scanner alerts | Redux (staff session) — preserves existing TV behaviour |

## File Structure

New:

```
super-chart/
  customer-service-super-chart.js   # CustomerServiceSuperChartWidget
```

Modified:

```
super-chart/
  controllers/header-buttons-controller.js   # gate Replay button under `if (mainChart)`
containers/customer-service/account/
  market.js     # swap DefaultTradingWidget → CustomerServiceSuperChartWidget
  position.js   # same swap
```

No new datafeed, controllers, or hooks. The widget reuses
`CoinrayDatafeed`, `ChartController`, the existing context, and the
existing overlay components.

## Incremental Implementation Plan

### Step 1: Widget skeleton + market page swap

Create `customer-service-super-chart.js` with the SC init effect (mirror
the structure of `grid-bot-super-chart.js`), the synthesized
`MarketTabContext` / `MarketTabDataContext` providers, and an empty
overlay slot. Swap the import in `account/market.js`. Verify candles
render and theme/symbol changes work.

**Files:** `customer-service-super-chart.js`, `account/market.js`.

### Step 2: Read-only overlay set

Mount the R4 overlays as children of `SuperChartContextProvider`. Verify
break-even draws on the market page when the customer has an open
position for that market (covered: position context falls through from
`WithPosition` once we hit Step 3, but `marketTradingInfo` already feeds
break-even on the market page). Verify orders/trades/bases all render
from staff Redux + customer `marketTradingInfo` exactly as before.

**Files:** `customer-service-super-chart.js`.

### Step 3: Position page swap

Swap the import in `account/position.js`. The position is already wired
through `WithPosition`'s `CurrentPositionContext.Provider` above the
chart, so `BreakEven` and `PnlHandle` see the customer's position with
no extra wiring. Verify both overlays draw using the customer's
position.

**Files:** `account/position.js`.

### Step 4: Visual / behavioural parity check

Walk through the chart with a staff session against a known account:

- Bid/ask line follows live ticks.
- Break-even line draws from `marketTradingInfo.position` (market page)
  / parsed customer position (position page).
- Open orders draw at correct prices, no drag handles.
- Trades draw with markers; closed-trade visualization matches TV.
- Bases draw if the staff session has bases for that market.
- Price/time/trendline alerts and TA-scanner alerts draw if the staff
  session has them.
- Right-click on the chart does **not** open a trading context menu.
- No header buttons / action bar present.
- Period selector inside SC works locally; switching pages doesn't
  persist the change anywhere.

**Files:** none — verification only.

### Step 5: TV cleanup (future — Phase 10f)

`DefaultTradingWidget` and the broader TV chart entry stay in tree
because /charts page (9a) and quiz (9d) still consume them. Removal is
the Phase 10f task. This PRD changes only the two CS pages.

## Non-Requirements

- **No customer-scoped alerts or bases.** Alerts, TA-scanner alerts, and
  bases continue to be sourced from the staff session's Redux state —
  the existing TV behaviour. Scoping these to the inspected customer is
  a separate product change.
- **No editing.** The chart is read-only: no drag-to-modify orders, no
  alert creation/editing, no order context-menu placement, no trading
  hotkeys.
- **No replay.** Replay UI is not mounted; replay-keyed Redux selectors
  resolve via `id: undefined` and stay inert.
- **No `account/layouts.js` change.** The "TradingView Charts" admin
  table stays on the TV-storage backend until Phase 6 ships SC's
  `StorageAdapter` and Phase 10f migrates this surface. Out of scope.
- **No mobile-specific UI.** Matches existing CS page behaviour.
- **No persistence of visible range, period, drawings, or layouts** on
  CS. The staff member's edits to the chart are session-local.
- **No removal of TV chart entry / `DefaultTradingWidget`.** Other
  consumers still depend on it; deletion belongs to Phase 10f.
