---
id: sc-charts-page
---

# PRD: /charts Page — SuperChart Integration

## Overview

Replace the TradingView-based chart on the `/charts` page (Altrady's
multi-chart workspace) with a new SuperChart variant. Each cell of the
flex-layout grid is a chart-tab managed by `ChartTabsController` /
`ChartLayoutsController`. Today every cell still mounts
`DefaultTradingWidget` (TV) via `containers/trade/trading-terminal/widgets/
candle-chart.js` with `toggleable={false}`.

The remaining blocker — multi-instance SC support — was resolved in
`[sc-multi-chart]` (see `phase-9/multi-chart-unblock`). Replay is
page-agnostic via `controller.id`; `ChartRegistry.getActive()` is gone;
several SC instances on one page coexist cleanly. /charts can now move
to SC.

Scope is intentionally narrow: a clean port that preserves what TV
/charts shipped — no redesign, no new product features, no editing
overlays beyond what TV /charts had.

**Explicit constraints — what stays vs what drops vs TV /charts:**

TV /charts mounts `DefaultTradingWidget` with `mainChart={false}` and
exposes:
- **Header buttons:** Alert (always), Replay (no `mainChart` gate in TV),
  Settings (always). Buy/Sell are gated behind `mainChart` and absent.
- **Background context menu:** Create Alert + replay sub-items
  (start/play-pause/speed/stop/go-back). Buy/Sell entries gated on
  `mainChart` and absent.
- **Replay:** per-chart `ReplayController` instantiated via `useRef`,
  no Redux global mirror (mirror is mainChart-only). Each tab's session
  is fully local.
- **Trading hotkeys:** bound but no-op outside replay mode (Buy/Sell
  silently dropped when `!mainChart`).
- **Replay hotkeys:** active per chart-tab.
- **Page-level hotkeys:** `ChartsHotkeys` (`newChart`,
  `closeSelectedChart`, `changeSelectedChartMarket`, `toggleWatchlist`,
  `toggleHotkeyInfo`).
- **Visible-range persist:** per chart-tab via
  `ChartTabsController.get().getTabById(id).setVisibleRange(vr)`.

SC port preserves this:

- **Keep:** Alert + Replay + Settings header buttons; alert + replay
  context-menu entries; per-tab replay isolation; per-tab visible-range
  persist (using SC's `from/to/barSpace` shape — `setVisibleRangeFromTo`);
  the page-level `ChartsHotkeys` (already mounted in
  `containers/charts.js`, no change).
- **Drop:** Buy/Sell header buttons, Buy/Sell context-menu entries,
  Trading hotkeys (no-op outside replay anyway — gain nothing by
  mounting them on /charts).
- **Drop:** `EditOrders` / `EditEntryConditions` / `EditEntryExpirations`
  overlays — TV /charts didn't include them either.
- **Drop:** the mobile `ActionButtons` bar + `PickReplayStartButton` —
  TV /charts doesn't render them (they gate on `mainChart` paths or on
  TT-only forms).
- **Adjust:** `ReplayHotkeys` mounts **once at the page level** (not
  per cell). It targets the **last-interacted** chart-tab — tracked in
  a small React context and updated on `pointerdown` over each cell's
  chart container (and on Replay header button click). TV resolved the
  same problem via `tvWidget.onShortcut` (focus-scoped to the TV widget
  instance — see "Mousetrap collision" note below); SC has no
  equivalent, so we replicate the behaviour with explicit tracking.
  The chart-tabs `selected` field is **not** the right handle — that's
  for tab-bar UI / page-level commands like `closeSelectedChart`.

After this PRD lands, `containers/charts.js` runs SC end-to-end and
`CandleChart`'s `toggleable` prop / TV branch can be deleted. TV's
`DefaultTradingWidget` and dependent files stay in tree because
quiz / training / market-explorer / customer-service-layouts admin
still consume them — full TV removal is Phase 10f.

## Current Behaviour (TradingView)

### Where the chart lives

`containers/charts.js` mounts `FlexGrid` with
`gridComponent={ChartGridItem}`. Each grid cell is a
`ChartsGridItem` (`grid-layout/flex-grid/charts-grid-item.js`)
that:
1. Looks up the chart-tab via `MarketTabsSelectors.selectChartTab(state, node.getId())`.
2. Wraps in `<MarketTabContextProvider marketTabId={node.getId()}>` —
   which surfaces `coinraySymbol`, `currentMarket`, `resolution` via
   `MarketTabContext`.
3. Mounts `<CandleChart toggleable={false} handleTV*={...}/>` — picks
   `DefaultTradingWidget` (TV).

The `handleTV*` callbacks bridge TV's symbol/interval/visibleRange events
back to `ChartTabsController.get().getTabById(marketTabId).set*`.

### Widget surface (TV `DefaultTradingWidget`, `mainChart={false}`)

Overlays in `DEFAULT_CHART_COMPONENTS`:
```
PriceTimeSelect, BidAsk, BreakEven, Bases, Alerts, EditAlerts,
TradingViewEnhancements, Orders, Trades, CustomIndicators,
TaScannerAlerts
```

`mainChart={false}` produces:
- Header: Alert + Replay + Settings (Buy/Sell hidden in `header.js`).
- Action buttons mobile bar: hidden.
- Trading hotkeys: bound but `if (!mainChart) return` outside replay.

`MainChartTradingWidget` is **not** used on /charts — only
`DefaultTradingWidget`.

### Per-tab state isolation

| Input | Source on /charts |
|---|---|
| `marketTabId` | `node.getId()` from flex-layout — also the chart-tab id |
| `coinraySymbol` | `MarketTabContext.coinraySymbol` (per-tab via `MarketTabContextProvider`) |
| `currentMarket` | `MarketTabContext.currentMarket` |
| `resolution` | `MarketTabContext.resolution` (from `ChartTab.resolution`) |
| `marketTradingInfo` | `MarketTabDataContext.marketTradingInfo` (auto-fetched per tab) |
| Replay session | `state.replay.sessions[chartId]` keyed per chart |
| Visible range | `ChartTab.visibleRange` / `visibleRangeFromTo` |

### Default replay independence

TV: each chart's `useReplay()` hook calls `useRef(new ReplayController())`,
so every grid cell owns its own controller. `setReplayContextGlobal` only
fires when `mainChart` is true → /charts never publishes its replay state
globally, so Tab A's session is invisible to Tab B's React tree.

SC: equivalent isolation already in place after `[sc-multi-chart]`:
`ReplayController` keys to `controller.id`, `state.replay.sessions[chartId]`
is per-chart, `ReplayContext` reads its controller via `useSuperChart`.
No new mechanism is needed.

### Mousetrap collision (TV → SC behaviour gap)

TV mounted `TradingviewHotkeys` and `ReplayHotkeys` **twice** per cell
(`tradingview-component.js:127–138`):

- `inChart` mount — bound via `tvWidget.onShortcut(...)`, scoped to the
  specific TV widget instance. TV's internal focus model decided which
  widget received the keypress, so 4 charts on /charts never fought
  over the same combo. The `replayController` for the cell was captured
  via `ReplayContext`, so the closure always targeted the correct
  chart.
- Non-`inChart` mount — bound via global Mousetrap `bindHotkey` as a
  fallback for when keyboard focus was outside the TV iframe. This
  *was* last-bind-wins, but rarely hit in practice.

SC has **no `tvWidget.onShortcut` equivalent** — every Altrady SC hotkey
goes through global Mousetrap. So the TV-internal focus trick doesn't
port. We replicate the result with explicit "last-interacted chart"
tracking on the Altrady side (R5).

## Requirements

### R1 — `ChartsPageChartWidget` (new SC variant)

New widget at `super-chart/charts/charts-page-chart.js`, alongside
`trading-terminal-chart.js`, `customer-service-chart.js`,
`grid-bot-chart.js`, `preview-chart.js`. Behaviour:

- Mounts a single `Superchart` instance per grid cell on mount; disposes
  on unmount.
- Symbol: from `MarketTabContext.currentMarket?.coinraySymbol`, resolved
  via `toSymbolInfo`.
- Period: from `MarketTabContext.resolution || "60"`, resolved via
  `toPeriod`.
- DataLoader: standard `CoinrayDatafeed` (live data).
- Theme + chart-colors: from `ThemeContext` / Redux, same pattern as TT.
- Wraps children in `SuperChartContextProvider` keyed by
  `marketTabId || node.getId()`. The chart-tab id never collides because
  flex-layout enforces uniqueness.
- Registers with `ChartRegistry` under that same id (the `useChartLifecycle`
  default — same as TT's `marketTabId || "main"` minus the `"main"`
  fallback, which doesn't apply on /charts).
- Renders `<HeaderButtons mainChart={false} showReplay showSettings/>` —
  Alert + Replay + Settings only (R3 controller flag split).
- Renders **no** `TradingHotkeys`, **no** `ActionButtons` /
  `PickReplayStartButton` mobile bar.
- Does **not** render `<ReplayHotkeys/>` — that mounts once at the page
  level (R5).
- On `pointerdown` over the chart container, updates the
  page-level `LastInteractedChartContext` to this cell's tab id (R5).
- Mounts the overlay set (R4).
- Visible-range persist via debounced
  `ChartTabsController.get().getTabById(marketTabId).setVisibleRangeFromTo({from, to, barSpace})`.
- Symbol/period sync via `MarketTabSyncController(controller, {marketTabId, tabsController: ChartTabsController})`.

### R2 — Sub-controllers attached

The widget's `useChartLifecycle.setup` attaches:

- `MarketTabSyncController` — `{marketTabId, tabsController: ChartTabsController}`.
  The controller already accepts an injected tabs controller — same
  symbol/period/visible-range sync logic powers TT and /charts.
- `HeaderButtonsController` — for Alert + Replay + Settings buttons.
- `ContextMenuController` — `{showTradingOptions: false}`. Background
  right-click shows Alert + Replay items; Buy/Sell entries are gated on
  `_showTradingOptions` and stay hidden.
- `PositionsController` — needed by Orders, BreakEven, PnlHandle child
  overlays.
- `TradeFormController` — needed by `PositionsController`'s
  entry-condition / entry-expiration handle wiring even though the edit
  overlays themselves aren't mounted (CS does the same pattern).
- `ReplayController` — per-chart replay engine. Init via
  `superchart.onReady(() => controller.replay?.init())`, same as TT.

`storeGlobal({chartController, ChartRegistry})` is dev-only; either
include or skip — the multi-chart-unblock review noted last-writer-wins
is harmless.

The base `ChartController` constructor sets up the always-on
sub-controllers (`HeaderController`, `AlertsController`,
`TradesController`, `BasesController`, `GridBotController`,
`InteractionController`); those stay.

### R3 — Header-buttons controller flag split

`controllers/header-buttons-controller.js` currently gates Buy / Sell /
Replay / Settings on a single `mainChart` flag. To produce the /charts
button set (Alert + Replay + Settings, no Buy/Sell), split into
independent flags:

```js
createHeaderButtons({mainChart, showReplay, showSettings, ...handlers})

// Alert always
if (mainChart)   { Buy; Sell }
if (showReplay)   { Replay }
if (showSettings) { Settings }
```

`<HeaderButtons/>` (`super-chart/header-buttons.js`) accepts
`showReplay`/`showSettings` props and forwards them. Existing handlers
(`onReplay`, `onSettings`) are already wired unconditionally.

Caller updates:

| Caller | Props |
|---|---|
| `trading-terminal-chart.js` (TT) | `mainChart showReplay showSettings` |
| `customer-service-chart.js` (CS) | `mainChart={false}` (Alert only — unchanged) |
| `charts-page-chart.js` (/charts) | `mainChart={false} showReplay showSettings` |
| `grid-bot-chart.js` | `gridBotChart` (skips `createHeaderButtons` entirely — unchanged) |

### R4 — Overlay set

Children of `<SuperChartContextProvider>` for /charts mirror TT's
`SuperChartOverlays` minus the editing overlays TV /charts didn't ship:

```
Always mounted:
  Trades, Bases, BreakEven, PnlHandle,
  Screenshot, ChartContextMenu

Live-only (!replayMode):
  TaScannerAlerts

Hidden during DEFAULT replay (mounted in live and SMART):
  BidAsk
  PriceAlerts, EditPriceAlert, TriggeredPriceAlerts
  TimeAlerts,  EditTimeAlert,  TriggeredTimeAlerts
  TrendlineAlerts, EditTrendlineAlert, TriggeredTrendlineAlerts
  Orders
  OverlayContextMenu

Replay-only:
  ReplayTimelines
```

**Not mounted on /charts:**

- `EditOrders`, `EditEntryConditions`, `EditEntryExpirations` — TV
  /charts didn't ship them; trading interaction is off.
- `ActionButtons`, `PickReplayStartButton` — mobile bar absent.
- `TradingHotkeys` — no buy/sell hotkeys on /charts.
- `PriceTimeSelect`, `TradingViewEnhancements`, `CustomIndicators` —
  TV-specific.

The `Edit*Alert` overlays **are** mounted (same as TT) so the Alert
header button's click-to-place flow works.

### R5 — Page-level `<ReplayHotkeys/>` + last-interacted chart tracking

R5.1. Mount `<ReplayHotkeys/>` **once** at the page level in
`containers/charts.js`. Per-cell mounts would cause Mousetrap
last-bind-wins collisions (see "Mousetrap collision" note above).

R5.2. Track the last-interacted chart-tab id in a small React context
that wraps the page subtree:

```jsx
// containers/charts/last-interacted-chart-context.js (new)
const LastInteractedChartContext = createContext({
  lastInteractedChartTabId: null,
  setLastInteractedChartTabId: () => {},
})

export const LastInteractedChartProvider = ({children}) => {
  const [lastInteractedChartTabId, setLastInteractedChartTabId] = useState(null)
  const value = useMemo(
    () => ({lastInteractedChartTabId, setLastInteractedChartTabId}),
    [lastInteractedChartTabId],
  )
  return <LastInteractedChartContext.Provider value={value}>
    {children}
  </LastInteractedChartContext.Provider>
}

export const useLastInteractedChart = () => useContext(LastInteractedChartContext)
```

Wrap the /charts page with the provider:

```jsx
// containers/charts.js
<GridItemSettingsProvider>
  <LastInteractedChartProvider>
    {/* MarketHeaderBar, FlexGrid, ... */}
    <ReplayHotkeys chartId={lastInteractedChartTabId}/>
    <ChartsHotkeys/>
  </LastInteractedChartProvider>
</GridItemSettingsProvider>
```

R5.3. **Producer** — each `ChartsPageChartWidget` calls
`setLastInteractedChartTabId(thisTabId)` from a `pointerdown` listener
on the chart container. The Replay header button's `onClick` (in
`HeaderButtons`) also bumps it, so arming the picker on chart A
naturally targets chart A even before the user clicks the canvas.
Setting the same id repeatedly is a no-op (`useState` setter dedupes
by `Object.is`).

R5.4. **Consumer** — `<ReplayHotkeys/>` accepts a new optional
`chartId` prop (R5.5). When provided, it resolves the controller via
`ChartRegistry.get(chartId)` instead of `useSuperChart()`'s
`chartController`. /charts mounts as
`<ReplayHotkeys chartId={lastInteractedChartTabId}/>` outside any
`SuperChartContextProvider` — so it must NOT call `useSuperChart()`
when `chartId` is passed.

R5.5. **`ReplayHotkeys` change** —
`super-chart/replay/replay-hotkeys.js`:

- Add an optional `chartId` prop.
- When `chartId` is provided: skip `useSuperChart()`, resolve controller
  via `ChartRegistry.get(chartId)`. `replayMode` selector keys on
  `chartId`. `currentMarket` for hotkey-handler closures is read from
  `controller._currentMarket?.getMarket()` (already maintained by
  `MarketTabSyncController`) — avoids requiring a `MarketTabContext`
  ancestor.
- When `chartId` is absent: existing behaviour — read everything via
  `useSuperChart()` and `MarketTabContext` (TT path, unchanged).
- When `chartId` is provided but `ChartRegistry.get(chartId)` returns
  `undefined` (no chart focused yet on /charts), bind nothing — the
  hotkeys are no-ops until a cell is interacted with.

R5.6. **Trading hotkeys** are not mounted on /charts at all (no
buy/sell). So the trading-hotkeys analogue of this work is not needed.

R5.7. **TT regression guard** — TT keeps mounting `<ReplayHotkeys/>`
without `chartId` from `trading-terminal-chart.js`. The new prop is
purely additive and optional.

### R6 — Replay UI (controls + timelines)

- `<ReplayContextProvider>` wraps each chart's subtree (same shape as
  TT). Reads its controller via `useSuperChart` so each cell's context
  references its own `ReplayController`.
- `<ReplayControls>` rendered when `replayMode` is truthy on this chart.
  Reads `MarketTabContext.currentMarket` (already provided per cell) and
  `WidgetContext.containerWidth` (provided by `withSizeProps` in
  `charts-grid-item.js`). No new wiring.
- `<ReplayTimelines/>` rendered as part of the overlay set (R4).
- The mobile pre-replay action bar (`PickReplayStartButton`, replay
  start picker mobile UI) is NOT rendered — TV /charts didn't have it.

### R7 — Visible-range persist

Same debounce pattern as TT, but persist via `ChartTabsController`
(through `MarketTab.setVisibleRangeFromTo`, which `ChartTab` inherits):

```js
useEffect(() => {
  const {from, to, barSpace} = visibleRange
  if (!from || !to || !miscRememberVisibleRange) return
  clearTimeout(persistTimeoutRef.current)
  persistTimeoutRef.current = setTimeout(() => {
    ChartTabsController.get()
      .getTabById(marketTabId)
      .setVisibleRangeFromTo({from, to, barSpace})
      .catch(console.error)
  }, 500)
}, [visibleRange, miscRememberVisibleRange, marketTabId])
```

Restoration on tab/symbol switch is handled by
`MarketTabSyncController.restoreVisibleRange` — same path as TT. No
new code required.

### R8 — Wire-up

`containers/charts.js`:

- Wrap the page subtree in `<LastInteractedChartProvider>` (R5.2).
- Mount `<ReplayHotkeys chartId={lastInteractedChartTabId}/>` once,
  inside the provider (R5.1).
- Existing `<ChartsHotkeys/>` mount stays unchanged.

`grid-layout/flex-grid/charts-grid-item.js`:

- Replace
  `<CandleChart toggleable={false} handleTVSymbolChanged={...} ...>`
  with `<ChartsPageChartWidget/>`.
- Drop `handleTVSymbolChanged` / `handleTVIntervalChanged` /
  `handleTVVisibleRangeChanged` callbacks — SC variant owns those
  internally via `MarketTabSyncController` + visible-range effect.
- Keep the `currentMarket?.coinraySymbol !== coinraySymbol` activity
  indicator gate.
- Keep `MarketTabContextProvider`, `WidgetContext.Provider`, the
  `ChartGridItemSelectMarket` empty-state.

`widgets/candle-chart.js`:

- Drop `toggleable` prop and TV branch. Always render
  `<TradingTerminalChartWithProvider/>`. Wrapper becomes a one-line
  pass-through; left in place because TT call sites already import it.

### R9 — Page-level hotkeys (no change)

`containers/charts.js` already mounts `<ChartsHotkeys/>`. No change.
The page-level commands (`newChart`, `closeSelectedChart`,
`changeSelectedChartMarket`, `toggleWatchlist`, `toggleHotkeyInfo`)
operate on `ChartTabsController` and don't depend on the chart widget.

### R10 — Settings modal preview interaction

Opening the chart-settings modal (Settings header button) mounts a
`PreviewSuperChartWidget`. With /charts running SC end-to-end, the
page can have **N + 1** SC instances: N live grid charts + 1 preview.
The multi-chart-unblock review confirmed multi-instance is safe;
no new coordination required.

### R11 — Single-instance / mount cleanup hygiene

Each grid cell's `useChartLifecycle` already disposes its controller +
datafeed on unmount; `ChartRegistry.unregister(controller.id)` runs
from the cleanup callback. Closing a chart-tab triggers
`ChartTabsController.removeMarketTab` → flex-layout removes the node
→ `ChartsGridItem` unmounts → SC chart disposes. No new lifecycle code.

### R12 — Mobile / fullscreen

The TT-only landscape-fullscreen treatment in
`trading-terminal-chart.js` is **not** ported. /charts inherits the
page's own layout. Mobile testing is non-blocking for this PRD.

## Data Sources

| Piece | Source |
|---|---|
| Candles | Live Coinray (`CoinrayDatafeed`) |
| `coinraySymbol` | `MarketTabContext.coinraySymbol` (per-tab) |
| `currentMarket` | `MarketTabContext.currentMarket` |
| `resolution` | `MarketTabContext.resolution` |
| `marketTradingInfo` | `MarketTabDataContext.marketTradingInfo` |
| `marketTabId` | `node.getId()` from flex-layout (= chart-tab id) |
| Chart settings / colors | Redux (user session) — same as TT |
| Alerts / bases / TA-scanner alerts | Redux (user session) — same as TT |
| Replay session | `state.replay.sessions[chartId]` keyed per chart |
| Visible-range persist | `ChartTab.visibleRangeFromTo` |

## File Structure

**New:**

```
super-chart/charts/
  charts-page-chart.js                       # ChartsPageChartWidget (default export)
containers/charts/
  last-interacted-chart-context.js           # LastInteractedChartProvider + useLastInteractedChart
```

(The new context file lives next to `containers/charts.js`. If a
sibling folder is preferred, drop it under `containers/charts/` — the
exact path is design-time, not requirements-level.)

**Modified:**

```
super-chart/
  controllers/header-buttons-controller.js   # split flags (R3)
  header-buttons.js                           # accept showReplay/showSettings (R3); on Replay-button click, also bump lastInteractedChartTabId when a setter is in scope (R5.3)
  charts/trading-terminal-chart.js            # pass showReplay showSettings to <HeaderButtons/>
  replay/replay-hotkeys.js                    # accept optional `chartId` prop (R5.5)

containers/
  charts.js                                  # wrap in LastInteractedChartProvider; mount page-level <ReplayHotkeys chartId=.../> (R8)
  trade/trading-terminal/
    grid-layout/flex-grid/charts-grid-item.js   # mount ChartsPageChartWidget
    widgets/candle-chart.js                     # drop toggleable, always SC
```

No new datafeed, controllers, or overlays — the variant reuses existing
pieces. Library/controller-side changes are limited to the
`HeaderButtonsController` flag split (R3) and the `ReplayHotkeys`
optional-prop addition (R5.5).

## Incremental Implementation Plan

### Step 1: Header-buttons flag split

Refactor `header-buttons-controller.js` and `header-buttons.js` to
support `showReplay`/`showSettings` independent of `mainChart`. Update
the TT call site to pass `showReplay showSettings`. Verify TT still
shows all five buttons; CS still shows Alert only. No /charts touched
yet.

**Files:** `controllers/header-buttons-controller.js`, `header-buttons.js`,
`charts/trading-terminal-chart.js`.

### Step 2: ChartsPageChartWidget skeleton + grid-item swap

Create `charts/charts-page-chart.js` as a copy of
`trading-terminal-chart.js`, adjusted per R1–R4, R6, R7. Skip
`<ReplayHotkeys/>` — it'll be page-level (Step 4). Replace
`CandleChart` in `charts-grid-item.js` with the new widget. Verify
candles render in each grid cell; symbol/period changes round-trip
through `ChartTabsController`; visible-range persists; multi-tab grid
layout works.

**Files:** `charts/charts-page-chart.js` (new),
`grid-layout/flex-grid/charts-grid-item.js`.

### Step 3: Header / context-menu surface verification

With the widget mounted, verify Alert + Replay + Settings header
buttons appear; alert + replay context-menu items appear, no Buy/Sell;
replay sessions are isolated per chart-tab when started via header
button or context menu (no hotkeys yet).

**Files:** none — verification only (or small fixes if any surface
misbehaves).

### Step 4: Last-interacted chart context + page-level replay hotkeys

Add the `LastInteractedChartContext` provider/hook. Wrap
`containers/charts.js` in the provider. Add an optional `chartId`
prop to `ReplayHotkeys` (R5.5). Wire each `ChartsPageChartWidget`'s
chart-container `pointerdown` to `setLastInteractedChartTabId`. Wire
the Replay header button click to bump it as well (when a
`LastInteractedChartContext` setter is reachable — only on /charts;
TT and CS are inert via the default no-op setter).

Mount `<ReplayHotkeys chartId={lastInteractedChartTabId}/>` once at
the page level. Verify replay hotkeys (play/pause, step, step-back,
back-to-start, stop) target the most recently interacted chart-tab
and nothing else. Switch tabs by clicking another chart's canvas →
hotkeys retarget.

**Files:** `containers/charts.js` (or `containers/charts/index.js` if
split), `containers/charts/last-interacted-chart-context.js` (new),
`super-chart/replay/replay-hotkeys.js`,
`super-chart/charts/charts-page-chart.js`,
`super-chart/header-buttons.js` (Replay-button onClick bump).

### Step 5: CandleChart cleanup

Drop `toggleable` prop and TV branch from `widgets/candle-chart.js`.
Verify TT still renders. The TV `DefaultTradingWidget` import in
`candle-chart.js` becomes unused — remove the import.

**Files:** `widgets/candle-chart.js`.

### Step 6: TV cleanup (future — Phase 10f)

`DefaultTradingWidget` and the broader TV chart entry stay in tree
because quizzes / training / market-explorer / customer-service-layouts
admin still consume them. Removal is the Phase 10f task.

## Non-Requirements

- **No buy/sell trading on /charts.** Header Buy/Sell buttons,
  context-menu trading entries, trading hotkeys — all absent. Matches
  TV /charts behaviour exactly.
- **No new replay UI.** Replay controls / timelines / hotkeys reuse
  the SC TT components verbatim.
- **No new context shape.** `MarketTabContext` /
  `MarketTabDataContext` already work for both TT and /charts.
- **No mobile-specific UI.** No `ActionButtons`, no
  `PickReplayStartButton`, no fullscreen-on-landscape.
- **No edit-overlays.** `EditOrders` / `EditEntryConditions` /
  `EditEntryExpirations` not mounted (TV /charts didn't either).
- **No persistence beyond visible-range.** Drawings / indicator
  templates are Phase 6.
- **No removal of TV chart entry / `DefaultTradingWidget`.** Other
  consumers still depend on it; deletion belongs to Phase 10f.

## Verification (review phase)

V1. Navigate to `/charts`. Default layout loads with one chart-tab —
chart renders, candles load.

V2. Add a second chart-tab via the new-chart hotkey or the chart-tabs
top bar — second chart renders alongside the first; both display live
candles for their own symbols.

V3. **Tab change (workflow context test)** — switch the selected
chart-tab via tab-click. Page-level commands (`closeSelectedChart`,
`changeSelectedChartMarket`, `toggleWatchlist`) operate on the new
selection; the per-chart canvas state of the previously selected tab
is untouched. (Replay-hotkey targeting is **not** driven by `selected`
— it's driven by last-interacted-canvas; covered separately in V14.)

V4. **Symbol change (workflow context test)** — change symbol from
chart 1's period-bar symbol search → chart 1 reloads; `ChartTab.coinraySymbol`
updates in Redux DevTools; chart 2 unaffected.

V5. **Resolution change (workflow context test)** — change resolution
from chart 1's period bar → chart 1 redraws; `ChartTab.resolution`
updates; chart 2 unaffected.

V6. **Visible-range persist** — pan chart 1, switch to a different
chart-layout, switch back → chart 1's visible range restored (verifies
`setVisibleRangeFromTo` debounce + `MarketTabSyncController.restoreVisibleRange`).

V7. **Per-tab default replay (the headline scenario)** — start a default
replay session on chart 1 → engine plays, replay timelines render on
chart 1 only. Chart 2 keeps streaming live candles.

V8. **Per-tab smart replay overlap** — while chart 1 replays, start a
smart replay (backtest) session on chart 2 → both run independently,
each with its own context-menu state and replay controls.

V9. **Replay session cleanup isolation** — stop chart 1's session →
`state.replay.sessions[chart1Id]` cleared; `[chart2Id]` retained;
chart 2's session continues.

V10. **Background context menu** — right-click chart 1 → menu shows
Alert + Start Replay (and replay sub-items if a session is active).
No Buy/Sell items. Click Alert → alerts form opens for chart 1's symbol.

V11. **Header buttons** — Alert + Replay + Settings present; Buy/Sell
absent. Click Settings → chart-settings modal opens; preview chart
renders alongside the live grid charts (5+ SC instances total) without
overlay bleed. Save → all live charts pick up the new colors.

V12. **Header alert** — click Alert → alerts form opens for the
chart's symbol.

V13. **Header replay** — click Replay → pick-replay-start mode
activates on that chart; clicking a candle starts default replay.

V14. **Replay hotkeys — last-interacted scoping**
- Click chart 1's canvas → press play/pause hotkey → chart 1's
  replay engine receives the call. Chart 2 unaffected.
- Click chart 2's canvas → press the hotkey → chart 2's engine
  responds; chart 1 ignored.
- Click chart 1's Replay header button (without canvas click) →
  the picker arms on chart 1; subsequent canvas click on chart 1
  starts replay. Hotkeys also target chart 1 because the header
  button bumped `lastInteractedChartTabId` (R5.3).
- With no chart yet interacted with on /charts (fresh load), pressing
  a replay hotkey is a no-op (R5.5 — `ChartRegistry.get(undefined)`
  returns nothing). No errors.

V15. **Note screenshot** — take a screenshot from a /charts tab → the
last-interacted chart-tab's chart is captured (TT-style screenshot
target resolution; on /charts the equivalent of "active" is
`lastInteractedChartTabId`). Confirm the existing screenshot pathway
is still wired correctly under the new model.

V16. **Page-level hotkeys** — `newChart`, `closeSelectedChart`,
`toggleWatchlist`, `changeSelectedChartMarket`, `toggleHotkeyInfo` all
work as before.

V17. **TT regression** — open `/trade`, exercise tab switch / symbol
change / resolution change / replay start-stop. Header buttons full set
(Alert + Buy + Sell + Replay + Settings) visible. No regression from the
header-buttons-controller flag split.

V18. **CS regression** — open a CS market or position page → only the
Alert button is visible (CS still passes `mainChart={false}` with neither
`showReplay` nor `showSettings`).

V19. **Console / errors** — full smoke (V1–V18) produces no React
warnings, no `Cannot read properties of null` errors, no SC console
errors.
