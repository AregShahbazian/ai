# Refactor: Make `ChartController` page-agnostic via sub-controller composition

## Goal

Today's `ChartController`
(`src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`)
is **implicitly coupled to the Trading Terminal**. Fields like `_marketTabId`,
`_tradeForm`, and calls into `TradingTabsController` sit on the base class, so
every chart that uses it either inherits TT assumptions or threads around them
via feature flags (`isMainChart`, `isGridBotChart`).

This refactor makes `ChartController` work unchanged on **any** Altrady chart
(Trading Terminal, `/charts`, grid-bot, settings preview, quiz, CS, …). TT-only
behaviour (market-tab sync, trading buttons, context menu, positions, replay)
moves into **sub-controllers that the TT / `/charts` call sites attach
externally** — not via inheritance.

**Zero behavioural change** on the TT path, on the grid-bot path, or on any
existing feature. This is a structural move: same guards, same conditionals,
same event ordering, same dispose ordering — only the *location* of code
changes.

## Motivation

1. **`/charts` page port.** `/charts` already uses the same `MarketTabContext`
   shape as TT, but with `ChartTabsController` (not `TradingTabsController`).
   Porting it onto SC requires the same sync logic as TT, only pointed at a
   different singleton. Today, TT's sync is hardcoded — there is no seam.
2. **Chart settings preview (phase-9).** A tiny preview chart needs no market
   tab, no trade form, no replay. Today it would inherit all of that and have
   to defensively null-check.
3. **Future non-TT charts** (quiz, CS, training) likewise need a bare chart.
4. **The `isMainChart` / `isGridBotChart` flags are a smell.** They exist to
   gate TT-only side effects (`replay.init()`, `syncChartColors()`) on a class
   that isn't supposed to know about pages.

## Non-goals

- No change to any overlay component or any sub-controller's *internal*
  behaviour.
- No change to `SuperChart` (the upstream lib) or to `coinray-datafeed.js`.
- No change to `ChartRegistry` semantics.
- No performance work, no new features, no style/lint pass outside touched
  files.
- Not touching the `/charts` page yet — this refactor only unblocks that port.
  Actually porting `/charts` to SC is a separate task.

---

## Current state — what's on `ChartController` today

### Constructor inputs

```js
new ChartController(superchart, datafeed, {
  dispatch, getState,
  marketTabId,                       // TT-only — missing on grid-bot
  setVisibleRange, setReadyToDraw,   // generic (React plumbing)
  isMainChart = false,               // TT-only feature flag
  isGridBotChart = false,            // grid-bot feature flag
})
```

### Fields / getters — categorised

| Member | Scope | Notes |
|---|---|---|
| `_superchart`, `_datafeed`, `_overlays`, `_disposed` | **generic** | |
| `dispatch`, `getState` | **generic** | |
| `_setVisibleRange`, `_setReadyToDraw` | **generic** | |
| `_currentMarket`, `setCurrentMarket`, `currentMarket` | **generic** | |
| `_visibleRange`, `visibleRange` (getter) | **generic** | |
| `colors` (getter) | **generic** | reads global `chartSettings`/theme |
| `chartSettings` (getter) | **generic** | reads global `chartSettings` |
| `_marketTabId`, `setMarketTabId` | **TT-only** | |
| `isMainChart`, `isGridBotChart` | feature flags — **remove** | |
| `_symbolEcho`, `_periodEcho` (EchoGuard instances) | **TT-only** | |
| `pendingVRRestore` | **TT-only** | VR restore after symbol change |
| `_tradeForm`, `setTradeForm`, `_onSubmitTradeForm`, `setOnSubmitTradeForm` | **TT-only** | |
| `isBacktestFinished` (getter) | **TT-only** | proxies `replay.smart.backtest` |
| `visibleRangeFromTo` (getter) | **TT-only** | `MarketTabsSelectors` |

### Methods — categorised

**Generic (stay on base):**
- `_applyTemporaryHacks()` — the no-scrollbar hack on `.superchart-period-bar`
- `_onChartVisibleRangeChange` — always subscribed; feeds `_setVisibleRange`
- `syncThemeToChart(themeName)`
- `syncChartColors()`
- `resize()`
- `printVisibleRange()` (debug)
- Overlay registry: `_register`, `_unregister`, `getOverlay`, `getOverlayGroup`,
  `clearOverlays`, `overlays` (getter), `removeOverlay`
- Chart accessors: `getChart`, `getChartDom`, `getContainer`
- Shared overlay primitives: `_toPrice`, `_yAxisLabel`, `_cancelButton`,
  `_createOverlay`, `_createOrderLine`, `_buildMoveEndCallback`,
  `_isHideAmounts`, `_createPriceLevelLine`, `_updatePriceLevelLine`,
  `_createTimeLine`, `_createTrendlineLine`
- `dispose()`

**TT-only (move out):**
- `_onChartSymbolChange`, `_onChartPeriodChange` — write back to the tabs
  controller
- `syncSymbolToChart(coinraySymbol, resolution)`
- `syncResolutionToChart(resolution)`
- `restoreVisibleRange()`
- `_formatTimelineLabel`, `createReplayTimelines(...)` — only used by replay
- `_getBidAskColor`, `_createBidAskLine`, `_updateBidAskLine`,
  `updateOrCreateBidLine`, `updateOrCreateAskLine` — used by bid/ask overlay
  which is mounted only on the TT tree

### Sub-controllers instantiated in the constructor today

| Sub-controller | Actually page-agnostic? | Today's location |
|---|---|---|
| `interaction` | ✅ generic | base ctor |
| `bases` | ✅ generic | base ctor |
| `trades` | ✅ generic | base ctor |
| `alerts` | ✅ generic | base ctor |
| `gridBot` | ✅ generic (overlay logic; grid-bot *page* picks it up) | base ctor |
| `header` | **mixed** — share/screenshot is generic, trading buttons are TT-only | base ctor |
| `contextMenu` | **TT-only** — trading/alerts/positions editing via right-click | base ctor |
| `positions` | **TT-only** — live position break-even, PnL, close button | base ctor |
| `replay` | **TT-only** — replay/backtest orchestration | base ctor |

### Consumers of the TT-only surface

Outside `controllers/`, only these 5 call-sites touch TT-only fields; all are
trivially re-pointable:

| File:line | Accesses | Post-refactor path |
|---|---|---|
| `super-chart.js:120` | `controller._marketTabId` (unregister key) | `controller.marketTabSync._marketTabId` |
| `super-chart.js:129-130` | `controller._marketTabId`, `controller.setMarketTabId` | `marketTabSync._marketTabId`, `marketTabSync.setMarketTabId` |
| `super-chart.js:146` | `syncSymbolToChart` | `marketTabSync.syncSymbolToChart` |
| `super-chart.js:152` | `syncResolutionToChart` | `marketTabSync.syncResolutionToChart` |
| `chart-context-menu.js:31` | `chartController?._marketTabId` fallback | `chartController?.marketTabSync?._marketTabId` |

`ChartRegistry` consumers split cleanly:
- TT-only (already in the TT tree or in TT-scoped thunks): `actions/replay.js`,
  `use-active-smart-replay.js`, `header-buttons.js` — still work unchanged
  because `.replay` / `.header` sub-controllers are still attached to the same
  controller instance, just attached externally.
- Generic: `date-picker-input.js`, `price-field.js`, `screenshot.js`,
  `context.js` — all rely only on `interaction`, slim `header`, or the base
  instance. No change.

### Method signatures we depend on across tabs controllers

Both `TradingTabsController` and `ChartTabsController` extend the same
`MarketTabsController`, and both `TradingTab` and `ChartTab` extend
`MarketTab`. The methods we call are **API-compatible**:

| Method | On `MarketTab` base? | Overrides? |
|---|---|---|
| `getTabById(id)` (on controller) | ✅ inherited | — |
| `setCoinraySymbol(sym)` | ✅ | both override, single-arg call works on both |
| `setResolution(res)` | ✅ | `ChartTab` adds a pre-dispatch, then calls `super`. Same signature. |
| `setVisibleRangeFromTo({from, to, barSpace})` | ✅ inherited | — |

Conclusion: a single `MarketTabSyncController` parameterised with the tabs
controller singleton handles **both** TT and `/charts`.

---

## Design

### Shape after refactor

```
ChartController (page-agnostic, single class — no subclasses)
├── ctor inputs: superchart, datafeed, {dispatch, getState,
│                                        setVisibleRange, setReadyToDraw}
├── always subscribes: onReady, onVisibleRangeChange
│   (drops the marketTabId-gated onSymbolChange / onPeriodChange)
├── always runs on ready: _applyTemporaryHacks, setReadyToDraw(true),
│                         syncChartColors
│   (drops the `isMainChart || isGridBotChart` gate — preview still wants
│   colors; it's idempotent and harmless for any chart)
├── sub-controllers instantiated in ctor (all generic):
│     interaction, bases, trades, alerts, gridBot, header (slim)
├── generic overlay registry + primitives
├── dispose(): tears down attached sub-controllers, then superchart, datafeed

TradingButtonsController (new; split from HeaderController)
├── owns: alert / buy / sell / replay / settings / toggleChart toolbar buttons
├── owns: setHeaderButtonsEnabled, setReplayButtonHighlight
├── attached by: TT call site only

HeaderController (slim — after split)
├── owns: _createToolbarButton, createShareButton, _captureScreenshotBlob,
│         shareScreenshot, captureScreenshotForNote
├── attached by: base ctor (used by TT and grid-bot today; any chart in
│   future)

MarketTabSyncController (new — extracted)
├── ctor(chartController, {marketTabId, tabsController})
├── owns: _marketTabId, setMarketTabId, _symbolEcho, _periodEcho,
│         pendingVRRestore, onChartSymbolChange / onChartPeriodChange
│         subscriptions, syncSymbolToChart, syncResolutionToChart,
│         restoreVisibleRange, visibleRangeFromTo
├── hooks base ChartController's _onChartVisibleRangeChange via an
│   `onVisibleRange` callback — so pendingVRRestore drains on the next
│   VR event, identically to today
├── attached by: TT call site (with TradingTabsController);
│                future /charts call site (with ChartTabsController)

ContextMenuController (unchanged location; now TT-attached)
PositionsController (unchanged location; now TT-attached)
ReplayController (unchanged location; now TT-attached)
```

### Trade-form access — `_tradeForm`, `_onSubmitTradeForm`

Currently set via `setTradeForm(tradeForm)` / `setOnSubmitTradeForm(fn)` on
the controller, read by other sub-controllers (positions/replay/trading flows).
**Move both to `MarketTabSyncController`** (they are strictly TT-scoped — each
market tab has its own trade form). Sub-controllers that need them go through
`this.c.marketTabSync?._tradeForm`. This is the minimum surgery that removes
the leakage from the base class without restructuring unrelated code.

If this turns out to pollute `MarketTabSyncController`'s concept, a tiny
`TradeFormController` (wired TT-only, same pattern) is a one-line split.
Decide during implementation, not now.

### `isBacktestFinished`

Getter currently lives on base (`this.replay?.smart?.backtest?.isFinished`).
Replay is TT-only, so the getter moves off base. Callers of
`controller.isBacktestFinished` become `controller.replay?.isBacktestFinished`
(move the getter into `ReplayController`).

### Bid/Ask overlay helpers

`_getBidAskColor`, `_createBidAskLine`, `_updateBidAskLine`,
`updateOrCreateBidLine`, `updateOrCreateAskLine` currently sit on base but
are only called from the bid-ask overlay (TT tree).

Decision: move them *into* the bid-ask overlay component (it already knows
about `OverlayGroups.bidAsk`), OR keep them on base behind the generic overlay
primitives they already use. Not a blocker either way. Default: **keep on base
as private helpers** — they're thin wrappers around the generic primitives
and moving them adds churn without removing any TT coupling from the base
class (they don't touch market-tab state; they just happen to only have
one caller today).

### Replay timelines

`createReplayTimelines(...)` and `_formatTimelineLabel(...)` currently on base.
Only called from `ReplayController` and the `ReplayTimelines` overlay.
**Move both into `ReplayController`** (TT-only). Removes a TT-flavoured
method from the base class.

### Sub-controller attach protocol

Sub-controllers are plain objects attached to the controller by field name:

```js
const c = new ChartController(sc, df, {dispatch, getState, ...})
c.marketTabSync = new MarketTabSyncController(c, {marketTabId, tabsController: TradingTabsController})
c.tradingButtons = new TradingButtonsController(c)
c.contextMenu   = new ContextMenuController(c)
c.positions     = new PositionsController(c)
c.replay        = new ReplayController(c)
c.contextMenu.mount(c._superchart)   // unchanged
c.replay.init()                       // unchanged
```

Grid-bot attaches **nothing extra** beyond the base constructor's sub-set.
Preview attaches nothing. Quiz / CS attach nothing (for now).

### Dispose protocol

Base `dispose()` already disposes generic sub-controllers in a fixed order.
Post-refactor it iterates all attached sub-controllers via a small attach-list
kept on the controller. Order is **preserved** to match today's:

```
interaction → contextMenu → header → replay → alerts → positions →
trades → bases → gridBot → marketTabSync → tradingButtons → _superchart → _datafeed
```

New additions (`marketTabSync`, `tradingButtons`) dispose last among
sub-controllers, before `_superchart.dispose()` / `_datafeed.dispose()`.
Missing sub-controllers (e.g. grid-bot has no `replay`) are skipped via
optional chaining.

### Event subscription ownership

| Event | Owner after refactor |
|---|---|
| `superchart.onReady` | base (for `setReadyToDraw`, hacks, colors; then asks each attached sub-controller to run its own `onReady` hook if present) |
| `superchart.onSymbolChange` | `MarketTabSyncController` (subscribes only when attached) |
| `superchart.onPeriodChange` | `MarketTabSyncController` |
| `superchart.onVisibleRangeChange` | base — captures `_visibleRange`, calls `_setVisibleRange`, then invokes an optional `marketTabSync.onVisibleRange?.()` hook to drain `pendingVRRestore` |
| `superchart.onRightSelect` | `ContextMenuController` (unchanged) |

`replay.init()` moves to the TT call site (or runs inside the base `onReady`
handler if `c.replay?.init` exists — decide during implementation; both
preserve today's behaviour).

### The `"main"` / marketTabId fallback pattern

Today: `ChartRegistry.register(marketTabId || "main", controller)` in
`super-chart.js`, and `controller._marketTabId || "main"` in
`chart-context-menu.js`. This `"main"` default is a **TT call-site concern**,
not a base-class concern. Stays in `super-chart.js` untouched, with
`controller.marketTabSync._marketTabId || "main"` as the post-refactor read.

---

## Invariants — functionality that MUST NOT be lost

Every item below is present today and must be preserved exactly. This is the
main acceptance criterion for the refactor.

### Echo-guard protocol for symbol + period

1. `EchoGuard` class moves with `MarketTabSyncController`. Protocol unchanged:
   - `mark(source, value)` before sending
   - `isEcho(source, value)` on receipt → drop if true
   - `isPending(source, value)` to skip double-dispatches on the same side
2. Bidirectional: chart → state (SC's onChange → `TradingTabsController`) and
   state → chart (`syncSymbolToChart` / `syncResolutionToChart` →
   `superchart.setSymbol` / `setPeriod`).
3. `syncResolutionToChart` **must** skip when `isPending("state", resolution)`
   — guards against two state dispatches colliding before the chart echoes.

### Symbol-change cascade (currently in `syncSymbolToChart`)

When a symbol change is applied to the chart, the following actions MUST still
fire in this order, before `setSymbol`:

1. `interaction?.stop("symbol-change")` — abort in-flight chart interactions
   so a stale click doesn't fire on the new symbol.
2. `contextMenu?.closeAllContextMenus()` — close any open chart/overlay menu.
3. Clear **all** overlay groups (`for (group of overlays.keys()) clearOverlays(group)`)
   — prevent stale overlays flashing on the new chart.
4. If `resolution` differs from the chart's current period, **first** set the
   period (with `_periodEcho.mark("state", res)`) — then set the symbol. This
   order matters: SC reloads data when `setSymbol` runs, so period must be
   correct first.
5. `_symbolEcho.mark("state", coinraySymbol)` then `superchart.setSymbol(...)`.
6. If `chartSettings.miscRememberVisibleRange` is on AND a stored VR exists,
   set `pendingVRRestore = true` so the next `onVisibleRangeChange` event
   (fired after the reload) triggers `restoreVisibleRange()`.

**All** of these stay in `MarketTabSyncController.syncSymbolToChart`. The
controller calls `this.c.interaction?.stop(...)`, `this.c.contextMenu?.
closeAllContextMenus()`, and `this.c.clearOverlays(...)` against its parent
controller. If any of `interaction`, `contextMenu` are not attached (e.g. on
`/charts` if/when it doesn't mount context-menu), the optional chains become
no-ops — identical to today's grid-bot path (which already doesn't have a
contextMenu-driven path since it has no market-tab sync).

### Visible-range restore

1. `restoreVisibleRange` no-ops unless `chartSettings.miscRememberVisibleRange`
   is truthy.
2. Bails if `visibleRangeFromTo.barSpace` is missing.
3. Bails if `getChart()` returns null.
4. Applies `setBarSpace(barSpace)`, `scrollToRealTime()`, and the
   `offsetRightDistance = paneWidth * 0.1` padding. All three steps preserved.
5. Drained exactly once via `pendingVRRestore` on the next VR event after a
   symbol change.

### Chart → state sync

`_onChartSymbolChange` and `_onChartPeriodChange` remain subscribed **only
when** a `marketTabId` is present. On grid-bot today they aren't subscribed;
post-refactor they still aren't — because the grid-bot call site doesn't
attach `MarketTabSyncController`. Same end behaviour.

### Grid-bot one-way symbol sync (app → SC)

Grid-bot does **not** use `controller.syncSymbolToChart` — it bypasses the
controller entirely and calls `controllerRef.current._superchart.setSymbol(
toSymbolInfo(coinraySymbol))` from a `useEffect` in
`grid-bot-super-chart.js:57-61`. This is intentional: without a market tab
there is no echo-guard, no overlay-clear cascade, no context-menu close, no
VR-restore — just "the bot's symbol changed, retarget the chart".

Invariants for this path:
1. The `_superchart` field must remain accessible on `ChartController` (it
   already is — no refactor change needed).
2. The `useEffect` in `grid-bot-super-chart.js` that re-runs on
   `[coinraySymbol]` stays as-is; the refactor does not touch
   `grid-bot-super-chart.js` beyond dropping the `isGridBotChart: true`
   constructor flag.
3. No echo-guard is needed or wanted on this path — SC's `onSymbolChange`
   is not subscribed (no `MarketTabSyncController` attached), so there is
   no echo to guard against.
4. Direction is strictly one-way: app (bot form) → SC. SC-side symbol
   changes (if the user opens SC's symbol picker) are **not** propagated
   back to the bot form. This matches today's behaviour and is preserved.

### Grid-bot resolution (neither direction)

Grid-bot's resolution is hardcoded `toPeriod("60")` at chart construction.
There is no prop, no `useEffect` for period, and no subscription to
`onPeriodChange`. The user can change the period via SC's period-bar, but
the change lives only inside SC for the lifetime of the mount and snaps
back to `60` on remount. Post-refactor: identical behaviour (no
`MarketTabSyncController` = no period subscription). If a future product
decision wants the bot form to drive the chart's resolution, or to
persist the user's period selection, that's a separate change — see
Deferred.

### `_onChartVisibleRangeChange`

1. Still subscribed **unconditionally** on every chart.
2. Still computes `{from: range.from/1000, to: range.to/1000}` and
   `barSpace = chart.getBarSpace()?.bar`.
3. Still stores on `_visibleRange` and calls `_setVisibleRange?.({from, to, barSpace})`.
4. Still drains `pendingVRRestore` once. Post-refactor: base invokes
   `this.marketTabSync?.onVisibleRange?.(this._visibleRange)` after its own
   update, and that hook handles the drain.

### `syncChartColors` on ready

Today gated by `isMainChart || isGridBotChart`. After refactor: **always
runs**. This is a behaviour change *only* for charts that previously did not
run it (preview, quiz, CS, /charts) — and running it on them is strictly
additive (applies the user's chart colors, which is what those charts should
have done anyway). For TT and grid-bot paths it's identical to today.
If the user objects to "always-on" for any page, the call moves into a per-page
attach just like `replay.init()`.

### `replay.init()` on ready

Today gated by `isMainChart`. After refactor: runs from the TT call site (or
from the base `onReady` handler only when `c.replay?.init` is present — both
produce identical effects).

### Share / screenshot buttons

1. `HeaderController.createShareButton` is still called unconditionally from
   `HeaderButtons` (see `header-buttons.js:41`).
2. `screenshot.js` still reaches `ChartRegistry.getActive().header.captureScreenshotForNote(callback)`.
3. Works on TT and grid-bot today; works on any future chart that mounts
   `HeaderButtons`.

### `_applyTemporaryHacks`

The `.superchart-period-bar` → `.no-scrollbar` class toggle runs on every
chart on `onReady`. Preserved.

### Dispose order

Preserved (see "Dispose protocol" above). `_disposed = true` flag set first.
All generic sub-controllers disposed before `_superchart.dispose()` and
`_datafeed.dispose()`. Attached TT-only sub-controllers (`contextMenu`,
`positions`, `replay`, `tradingButtons`, `marketTabSync`) dispose in the same
relative order as today.

### `dispose` idempotence

`this._disposed = true` guards `onReady` (line 97 today). Preserved.

### `ChartRegistry` coherence

- TT: register under `marketTabId || "main"`, unregister on dispose,
  re-register when `marketTabId` prop changes (`super-chart.js:126-136`). All
  unchanged — `super-chart.js` still owns registry calls.
- Grid-bot: per-mount UUID (`grid-bot-${UUID()}`), unchanged.

### Consumer-side reads

- `ChartRegistry.getActive().replay.*` — still works (replay still attached).
- `ChartRegistry.getActive().header.*` — still works (slim header always
  attached).
- `ChartRegistry.getActive().interaction.*` — unchanged.
- `chartController._marketTabId` **is no longer present**; one call site
  (`chart-context-menu.js:31`) updates to `chartController?.marketTabSync?._marketTabId || "main"`.

---

## Tasks

Each task is verifiable in isolation. Implementation stops after each task
and yields a runnable build.

### Task 1 — Split `HeaderController`

**Files:**
- `controllers/header-controller.js` — remove `createHeaderButtons`,
  `setHeaderButtonsEnabled`, `setReplayButtonHighlight`, the `_alertButton` /
  `_buyButton` / `_sellButton` / `_replayButton` / `_settingsButton` /
  `_toggleChartButton` fields, and the trading-button entries from
  `_toolbarButtons` / `updateLabels`. Keep `_createToolbarButton`,
  `createShareButton`, screenshot methods, the share-button entry in
  `_toolbarButtons`, and the language-change subscription for that entry.
- `controllers/trading-buttons-controller.js` — new. Owns the removed
  methods. Constructor: `(controller)`. Manages its own language-change
  listener for the buttons it owns (re-use the same `updateLabels`
  pattern).
- `chart-controller.js` — still instantiates `header` (slim) in the
  constructor. No `tradingButtons` here.
- `super-chart.js` — after `new ChartController(...)`, attach
  `controller.tradingButtons = new TradingButtonsController(controller)`.
- `header-buttons.js` — switch calls from `chartController.header.createHeaderButtons(...)`
  → `chartController.tradingButtons.createHeaderButtons(...)`. Leave the
  `createShareButton` call on `chartController.header` unchanged. Switch
  `setHeaderButtonsEnabled` / `setReplayButtonHighlight` calls to
  `tradingButtons.*`.

**Verification:**
- TT: alert / buy / sell / replay / settings / TV-toggle buttons still
  appear and work.
- TT: replay button highlight toggles correctly.
- TT: replay DEFAULT mode disables alert/buy/sell, SMART mode enables.
- TT: language change updates button labels.
- Grid-bot: only the share button appears (as today).
- Screenshot: `takeScreenshot` still works from any mounted chart.

### Task 2 — Extract `MarketTabSyncController`

**Files:**
- `controllers/market-tab-sync-controller.js` — new. Owns:
  - the `EchoGuard` class (move from chart-controller.js)
  - `_marketTabId`, `setMarketTabId`
  - `_symbolEcho`, `_periodEcho`, `pendingVRRestore`
  - `_unsubSymbol` / `_unsubPeriod` subscriptions (subscribed in ctor,
    unsubscribed in `dispose()`)
  - `_onChartSymbolChange`, `_onChartPeriodChange`
  - `syncSymbolToChart`, `syncResolutionToChart`
  - `restoreVisibleRange`
  - `visibleRangeFromTo` getter
  - `onVisibleRange()` hook invoked by base after its own VR update;
    drains `pendingVRRestore` via `restoreVisibleRange()`
  - `_tradeForm`, `setTradeForm`, `_onSubmitTradeForm`, `setOnSubmitTradeForm`
  - `dispose()`
  - Constructor: `(controller, {marketTabId, tabsController})`. Stores
    `this.c = controller`, `this._tabsController = tabsController`. All
    writes to the tabs controller go through
    `this._tabsController.get().getTabById(this._marketTabId).setX(...)`.
- `chart-controller.js`:
  - Drop `marketTabId`, `isMainChart`, `isGridBotChart` from ctor params.
  - Drop `_unsubSymbol`, `_unsubPeriod`, `_onChartSymbolChange`,
    `_onChartPeriodChange`, `syncSymbolToChart`, `syncResolutionToChart`,
    `restoreVisibleRange`, `visibleRangeFromTo`, `pendingVRRestore`,
    `setMarketTabId`, `setTradeForm`, `setOnSubmitTradeForm`, `isBacktestFinished`,
    `EchoGuard`, `_symbolEcho`, `_periodEcho`.
  - `_onChartVisibleRangeChange`: keep, minus the `pendingVRRestore`
    branch. After the `_setVisibleRange` call, invoke
    `this.marketTabSync?.onVisibleRange?.(this._visibleRange)`.
  - `onReady`: remove the `isMainChart || isGridBotChart` gate around
    `syncChartColors()`. Remove the `isMainChart` gate around
    `replay.init()` — move that call to the TT call site (see Task 3).
  - Keep everything else as-is structurally (generic sub-controllers,
    overlay registry, primitives, dispose).
- `super-chart.js`:
  - After `new ChartController(...)`, attach
    `controller.marketTabSync = new MarketTabSyncController(controller, {
      marketTabId,
      tabsController: TradingTabsController,
    })`.
  - `controller._marketTabId` → `controller.marketTabSync._marketTabId`
    (line 120, 129).
  - `controller.setMarketTabId(...)` → `controller.marketTabSync.setMarketTabId(...)`.
  - `controller.syncSymbolToChart(...)` → `controller.marketTabSync.syncSymbolToChart(...)`.
  - `controller.syncResolutionToChart(...)` → `controller.marketTabSync.syncResolutionToChart(...)`.
- `chart-context-menu.js:31` — `chartController?._marketTabId` →
  `chartController?.marketTabSync?._marketTabId`.
- Any sub-controller that reads `this.c._tradeForm` / `this.c._onSubmitTradeForm`
  → `this.c.marketTabSync?._tradeForm` / `?._onSubmitTradeForm` (grep and
  update — should be contained to `positions-controller.js` and/or
  `replay-*-controller.js`).

**Verification — full TT context-test matrix (per workflow.md §4):**
- Change `TradingTab` — chart re-renders, VR restores if setting is on,
  overlays clear during the symbol cascade.
- Change `coinraySymbol` within a tab — echo guards prevent ping-pong;
  period is set first if resolution differs; overlays cleared; context
  menus closed; interaction aborted.
- Change resolution — echo guards fire; `isPending` skip holds on
  double-dispatches.
- Change `exchangeApiKeyId` — unaffected (not part of sync path, but
  verify no regression).
- `miscRememberVisibleRange` on — VR restore drains once after symbol
  change. Off — no restore.
- Bidirectional: change period from SC's period bar, observe write to
  `TradingTabsController`.

### Task 3 — Move replay init + isBacktestFinished

**Files:**
- `controllers/replay-controller.js` — add `get isBacktestFinished()`
  that returns `!!this.smart?.backtest?.isFinished` (move the getter in
  from base).
- `chart-controller.js` — drop `isBacktestFinished` getter. Drop
  `replay.init()` call from the `onReady` handler. Drop `replay` from the
  constructor's sub-controller list.
- `super-chart.js` — after `new ChartController(...)`, attach
  `controller.replay = new ReplayController(controller)` and call
  `controller.replay.init()` from within a `superchart.onReady(...)`
  one-shot OR in a `useEffect` that waits on `readyToDraw`. Preserve the
  current semantics: init runs once, after SC is ready, and only on TT.
- Update any `controller.isBacktestFinished` callers to
  `controller.replay?.isBacktestFinished`.

**Verification:**
- Replay enters, plays, pauses, finishes. Finished backtest stays
  read-only for alerts/orders/context-menu (same guard path).
- Disposing the chart during replay tears down replay before superchart
  (same order as today).

### Task 4 — Move `contextMenu` and `positions` attachment to TT call site

**Files:**
- `chart-controller.js` — drop `contextMenu` and `positions` from
  constructor. Drop the `contextMenu.mount(superchart)` line.
- `super-chart.js` — after `new ChartController(...)`:
  ```js
  controller.contextMenu = new ContextMenuController(controller)
  controller.contextMenu.mount(superchart)
  controller.positions = new PositionsController(controller)
  ```
  Attach order: after `marketTabSync`, `tradingButtons`, `replay`; before
  `ChartRegistry.register`.
- Replay-timelines move: migrate `_formatTimelineLabel` and
  `createReplayTimelines` from base into `ReplayController` (or the
  `ReplayTimelines` overlay). Update the one caller.

**Verification:**
- Right-click on chart background opens chart context menu.
- Right-click on alert / position / order overlay opens overlay context
  menu (same entries).
- Position break-even, PnL handle, close button all still render and
  function.
- TradingTab switch / symbol change / replay-mode change auto-close menus
  (same auto-close effect in `chart-context-menu.js`).

### Task 5 — Sweep and cleanup

- Remove `isMainChart`, `isGridBotChart` from `chart-controller.js` ctor
  signature entirely. Remove their last references in `super-chart.js` and
  `grid-bot-super-chart.js`.
- Verify `_createOverlay` still has access to `this.contextMenu` — the
  overlay is only created after `onReady`, by which point the TT call
  site has attached `contextMenu`. For charts without `contextMenu`
  (grid-bot, preview), `this.contextMenu?.onOverlayRightClick` falls
  through to undefined, which SC treats as "no right-click handler"
  (confirm during implementation; add optional chaining if needed).
- Confirm dispose order matches today's for all still-attached
  sub-controllers (see "Dispose protocol").
- Confirm no remaining reads of: `controller._marketTabId`,
  `controller._tradeForm`, `controller._onSubmitTradeForm`,
  `controller.syncSymbolToChart`, `controller.syncResolutionToChart`,
  `controller.restoreVisibleRange`, `controller.visibleRangeFromTo`,
  `controller.isBacktestFinished`, outside `MarketTabSyncController` and
  `ReplayController`. Grep before merging.

**Verification — full regression pass:**
- TT golden path: open tab → chart renders → symbol change → period
  change → VR persists → TT switch → replay enter/exit → positions edit →
  alerts edit → context menus → screenshot.
- Grid-bot: settings page + backtest modal both render charts with grid
  lines, orders, trades, backtest times; share button works; color sync
  works; theme sync works.
- `ChartRegistry.getActive()` returns the expected controller for each
  page (verify via `storeGlobal`).

### Task 6 — Review doc

Per `ai/workflow.md §4`: write `review.md` covering the Trading-Terminal
context matrix (TradingTab change, coinraySymbol change, resolution
change, exchangeApiKeyId change) × (replay off / replay DEFAULT / replay
SMART) × (`miscRememberVisibleRange` on/off). Grid-bot regression
checklist as well.

---

## Deferred

- **Porting `/charts` to SC** — separate task. This refactor only exposes
  the seam (pass `ChartTabsController` to `MarketTabSyncController`);
  actual SC mount + TV removal for `/charts` is a phase-10 item.
- **Grid-bot sync** — grid-bot today does not subscribe to SC's
  `onSymbolChange` / `onPeriodChange`. If a future product decision wants
  to (e.g. write bot symbol back when user picks a symbol from SC's
  selector, or block symbol changes entirely), that's a new
  `GridBotSyncController` attached on the grid-bot call site. Out of
  scope here.
- **Bid/ask helpers relocation** — stays on base for now (private helpers
  that happen to have one caller). Revisit if a second caller appears or
  if the bid-ask overlay gets its own controller.
- **`TradeFormController` split from `MarketTabSyncController`** — only if
  the trade-form surface grows. Today it's two setters and two getters;
  not worth its own class yet.
