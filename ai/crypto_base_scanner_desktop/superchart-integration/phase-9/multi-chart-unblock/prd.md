---
id: sc-multi-chart
---

# Multi-Chart Unblock

## Summary

SuperChart commit `276e661` ships per-instance state — every `Superchart`
instance now owns its own internal store (symbol, period, theme, overlays,
providers, popup state) instead of sharing module-level singletons. Two SC
instances can finally coexist on one page without overlay bleed.

This PRD covers the Altrady-side cleanup that becomes possible once SC
`main` (currently `42d90ae`, four commits past `276e661`) is in use:

1. **Remove the TT-main ↔ settings-preview unmount workaround.** Active
   coordination via `GridItemSettingsContext.previewShown` is no longer
   needed — both charts can stay mounted together.
2. **Remove the grid-bot settings kill-switch (`SHOW_SETTINGS_CHART`).**
   Dormant but still in the tree; the comment block also references the
   now-resolved blocker.
3. **Tighten `ChartRegistry.getActive()` callers.** The "last-registered
   wins" semantic was a singleton concession. With two SC charts mountable
   simultaneously, each consumer that uses `getActive()` should resolve a
   chart by an explicit ID instead.

Scope is intentionally narrow. We adopt the SC version that's already
linked, delete the workarounds, and convert four `getActive()` callers to
explicit-ID lookups. No architectural rework, no new abstractions, no new
context plumbing beyond what already exists.

## Why this now

SC `main` is at `42d90ae`, which includes `276e661`. The library is
symlinked into `node_modules/superchart`, so the fix is loadable as soon as
`pnpm run build` is run in the SC repo. The workarounds are no longer
needed and the `getActive()` semantics are now actively wrong in two
flows:

- TT main + settings preview both mounted → "active" = whichever
  registered last → notes-screenshot / price-picker / time-picker target
  the wrong chart.
- Grid-bot settings + grid-bot backtest modal both mounted → same problem.

Only the first flow is currently masked by the unmount workaround. The
second flow already produces the bug today (the kill-switch is set to
`true`, both charts are mounted, `getActive()` is undefined behavior).
Removing the workarounds without fixing `getActive()` would expose the
first flow to the same bug.

## Requirements

### R1 — Pin to a SuperChart commit that includes the fix

R1.1. Altrady's SC consumption must use a SuperChart build that includes
`276e661`. Today SC is symlinked (`node_modules/superchart →
../../Superchart`) and SC `main` is `42d90ae`, so the requirement is
satisfied once `pnpm run build` has been run in the SC repo. No
`package.json` change is needed.

R1.2. `ai/deps/SUPERCHART_API.md` and `ai/deps/SUPERCHART_USAGE.md` must
be patched so their tracked hashes match `42d90ae` (Superchart) and
`c99a96f` (coinray-chart). Doc updates cover only what changed between
the recorded hashes and HEAD; no broader rewrite. Specifically:
- Note that `Superchart` is fully per-instance — multiple instances on
  one page are supported.
- Note that `SymbolInfo.shortName` is rendered in the legend with
  `{shortName||ticker} · {period}` fallback.
- Note `createTradeLine`'s new `onRightClick` option.
- Note `PriceTimeResult.coordinate` now includes `pageX`/`pageY`.
- Note touch right-click (longpress → `onRightSelect`) is now active.

### R2 — Remove the TT main ↔ settings-preview unmount workaround

R2.1. The TT main `SuperChartWidget` must stay mounted while the chart
settings modal preview is open. Both SC instances can coexist.

R2.2. The `previewShown` plumbing must be removed end to end:
- `GridItemSettingsContext` returns to `{component, isOpen, onToggle}`
  only — no `previewShown`, no `setPreviewShown`.
- `TradingviewSettings` no longer publishes `showPreview` to context;
  the preview gates on local `showPreview` only.
- `CandleChart` no longer reads `GridItemSettingsContext`; it
  unconditionally renders `SuperChartWidgetWithProvider` in the
  toggleable case.

R2.3. Every TEMPORARY / WORKAROUND comment that references the SC
multi-instance blocker is deleted at the same time. Specifically:
- The `// TEMPORARY: the SC library's global singleton store...` comment
  block in `candle-chart.js` (above `previewActive`).
- The `/* Gate on context previewShown ... SC's global singleton store
  trashes one of them. ... */` block in `settings.js` (above the
  preview render).
No replacement comment is added — the resulting code is self-explanatory.

### R3 — Remove the grid-bot settings chart kill-switch

R3.1. `SHOW_SETTINGS_CHART` and its `// TEMPORARY: the SC library's
global singleton store...` comment block must be deleted from
`grid-bot-settings.js`. The `&& SHOW_SETTINGS_CHART` guard on the
collapsed-layout chart goes with it. The constant is currently `true`,
so behavior does not change. No replacement comment is added.

### R4 — Replace `ChartRegistry.getActive()` callers with explicit IDs

R4.1. With two SC instances mountable, "the active chart" is no longer
well defined. Every `getActive()` caller must select a chart by a known
ID. Inputs are not inside `SuperChartContextProvider` (verified in the
Q2 audit) — they sit in TT widgets (inside `MarketTabContext`) or on
grid-bot pages (inside `BotFormContext`). Affected callers:

| File:line | New resolution |
|---|---|
| `super-chart/screenshot.js:17` (`takeScreenshot`) | Accept `chartId` argument from caller. Notes-form passes the chart it intends to capture — TT call sites pass `MarketTabContext.id`, grid-bot call sites pass the page's `chartId`. There is no portable "active page" abstraction (`TradingTabsController` is TT-only and absent on grid-bot, customer service, etc.). |
| `components/design-system/v2/trade/inputs/price-field.js:89` | `useContext(MarketTabContext)?.id` for TT forms (Group A); `useContext(BotFormContext)?.chartId` for grid-bot forms (Group B). One of the two is always non-null for these inputs' real call sites. |
| `components/design-system/v2/trade/inputs/date-picker-input.js:29` | Same as price-field. |
| `actions/replay.js:7,55` (`getSmartReplayController`, `replaySafeCallback`) | Accept `chartId` argument from caller. TT callers pass `MarketTabContext.id` (today's only call sites). Future page-agnostic replay (Q3) inherits this contract. |

R4.2. `BotFormContext` is extended with a `chartId` field. The
settings page and the backtest modal each set it to the
`grid-bot-<uuid>` they generated for their `GridBotSuperChartWidget`
mount. Forms inside the provider read it via `useContext`. This is the
only context-shape change in this PRD — no new context, no new hook,
no new abstraction.

R4.3. Once the four callers are converted, `ChartRegistry.getActive()`,
`setActive()`, and the `activeId` mutation in `register` / `unregister`
must be deleted from `chart-registry.js`. `getAll()` is kept — it has
no production callers but is useful for dev-tools inspection of all
mounted controllers, and is single-instance-safe by construction. The
remaining public surface is `register / unregister / get / getAll /
subscribe`.

R4.4. The chart-pick button on `price-field` / `date-picker-input` must
remain visible and active in every place these inputs render today —
it is never hidden or disabled by this PRD. The Q2 audit confirms every
real call site has a resolvable `chartId`; the existing
`if (!ctrl) return` early-out stays only as a defensive null-guard
against transient races (e.g. registry write order during fast
remounts), not as a UI state.

### R5 — Per-instance disciplines (confirm, do not change)

R5.1. Each SC mount must construct its own `CoinrayDatafeed`. Already
true at every mount site (`super-chart.js:101`,
`grid-bot-super-chart.js:33`, `preview-super-chart.js:55`).

R5.2. Each SC mount must own a unique container ref. Already true.

R5.3. Disposal order is `superchart.dispose()` → `datafeed.dispose()` (chart
before its datafeed, mirroring `MultiChart.stories.tsx:56-60`). Verify in
each mount site's cleanup; today the `ChartController.dispose()` path is
the only thing called and we must confirm it disposes in this order
internally. If it does not, the cleanup must be adjusted at the SC mount
site.

R5.4. `SymbolInfo.shortName` must be set on every SC mount. Already true
via `toSymbolInfo()` in `chart-helpers.js` and the hardcoded preview
symbol info.

R5.5. Each SC mount continues to register its `ChartController` with
`ChartRegistry` under a stable, unique ID. No change — TT tabs use
`marketTabId || "main"`, grid-bot uses `grid-bot-<uuid>`, preview uses
`preview-<uuid>`. The per-mount UUID for grid-bot and preview is kept;
its rationale shifts from "dodge SC singleton" to "avoid race between
unregister(old) and register(new) when remounts run in close
succession."

### R6 — Multi-instance compatibility audit

Every SC chart feature must work with two simultaneous instances. The
audit below enumerates each feature, its current implementation, and
whether it relies on single-instance assumptions. Features marked
**OK** require no change. Features marked **CHANGE** are addressed by
other requirements in this PRD. Items not listed are out of scope.

#### Per-instance state (no change)

- **`Superchart` instance state** — per-instance after SC `276e661`.
  Container, dataLoader, theme, period, indicators, overlays, popups,
  storage adapter, debug flag, locale, timezone — all isolated. **OK.**
- **`CoinrayDatafeed`** — instance fields `_subscribers`,
  `_lastCandles`, `_firstCandleTimeCache`. Constructed per mount.
  `MarketUpdates` subscriptions are routed through `subscriberGuid`
  on the instance. **OK.**
- **`ChartController` and sub-controllers** — `HeaderController`,
  `AlertsController`, `TradesController`, `BasesController`,
  `GridBotController`, `InteractionController`, `ContextMenuController`,
  `PositionsController`, `TradeFormController`,
  `MarketTabSyncController`, `TradingButtonsController`,
  `ReplayController` — all instantiated per `ChartController`. State
  lives on instance fields. **OK.**
- **Overlay registry** — `ChartController._overlays` is a per-instance
  `Map<group, Map<key, overlayId>>`. `_createOverlay` /
  `_clearOverlays` operate on `this._overlays` and `this._superchart`.
  Two charts with the same overlay group (e.g. `OverlayGroups.bases`)
  do not collide. **OK.**
- **`SuperChartContext` consumers** — `useSuperChart()` returns the
  controller for the chart subtree it's used in
  (`SuperChartContextProvider` plumbs `chartId`, the context resolves
  via `ChartRegistry.get(chartId)`). All overlay components, header
  buttons, context-menu components, hotkeys, hooks already use this.
  **OK.**

#### Replay (no change — already multi-instance-safe)

R6.1. Replay is currently wired only on the TT main chart
(`super-chart.js:129`: `controller.replay = new ReplayController(...)`).
Grid-bot and preview do not instantiate `ReplayController`. So today
there is no scenario where two charts both have replay engines.

R6.2. Even though only one chart has replay today, the existing design
is already multi-instance-safe and should stay that way:
- **Redux session keying.** `selectReplaySession`,
  `setReplaySession`, `clearReplaySession` all take `chartId`
  (`actions/replay.js:45-51`). Each chart's session is its own slice.
- **Pinned `_sessionChartId`.** `ReplayController` pins `chartId` at
  session start (`replay-controller.js:386-388`) so a TT tab switch
  during replay does not migrate the session to the new tab — the
  pinned id wins. With multi-instance, the same pin would isolate the
  session to the originating chart instance.
- **`BaseReplayController._chartId`** — every reader/writer in
  `ReplayController`, `ReplayTradingController`,
  `SmartReplayController` routes through this getter
  (`base-replay-controller.js:12,17,21`,
  `replay-trading-controller.js:20,23,27`,
  `smart-replay-controller.js:56`). No global replay state.
- **`ReplayContext`** — keys by `marketTabId || "main"`
  (`replay-context.js:13`). Already multi-instance-safe.
- **`useActiveSmartReplay`** — already keys on `activeTabId` via
  `MarketTabsSelectors.selectActiveTradingTab`
  (`use-active-smart-replay.js:13,20`). Already multi-instance-safe.

R6.3. Replay-related `getActive()` callers in `actions/replay.js`
(`getSmartReplayController`, `replaySafeCallback`) are covered by R4.
After R4 they resolve to the active TT tab id, which is the only chart
with replay today. No behavior change in single-chart flows;
forward-compatible if a second replay-capable chart is ever added.

#### Single-instance assumptions (covered by R4)

The only chart-layer code that assumes one chart at a time is the four
`ChartRegistry.getActive()` callers enumerated in R4
(`screenshot.js:17`, `price-field.js:89`, `date-picker-input.js:29`,
`actions/replay.js:7,55`). Removing `getActive` and converting these
callers leaves the chart layer fully multi-instance-safe.

#### Globals that are by-design or inert (no change)

R6.4. **`Screenshot` modal singleton (`screenshot.js:10`,
`let showShareModal`).** One share modal in the DOM, fed by
`triggerScreenshotShare(url)` from any chart's share button. Only one
modal can be visible at a time, but only one chart-share interaction
happens at a time too — the singleton is correct. **No change.**

R6.5. **Period-bar CSS overrides (`chart-controller.js:90-95`).**
Global `<style id="altrady-sc-period-bar-overrides">` injected once,
guarded by `getElementById`. Applies to all SC instances by selector.
**No change.**

R6.6. **`InteractionController` document listeners
(`interaction-controller.js:79-94`).** Each controller installs its own
`keydown`/`mousedown` listener only while a picker consumer is active,
and only inspects `this.c.getContainer().contains(e.target)`. Two
simultaneous pickers (one per chart) would both fire on Escape — that's
the intended behavior. Outside-click is per-container. **No change.**

R6.7. **`storeGlobal({chartController, previewChartController, ...})`
(`super-chart.js:134`, `preview-super-chart.js:86`).** Dev-only
debugging affordance — only writes to `window` when
`process.env.NODE_ENV === "development"`
(`util/store-global.js:2`). Last-writer-wins on the `chartController`
key in dev. Inert in production; cosmetic in dev. **No change.**

R6.8. **`MarketTabSyncController` and one-chart-per-TT semantics.** The
TT main chart is reused across tabs — switching tabs mutates
`_marketTabId` on the same `ChartController` rather than creating a new
chart. This is intentional and out of scope for this PRD. The
multi-instance fix unlocks running a *second* SC widget alongside the
TT main; it does not change the TT-main-as-singleton model. **No
change.**

#### Out-of-scope residuals (track only)

R6.9. **SC's `keyEventStore.ts` module-level state.** Still has shared
`ctrlKeyedDown`, `widgetRef`, `timerId`, `modalCallbacks`. SC does not
auto-attach key handlers; Altrady has its own hotkey system and does
not call `setModalCallbacks` / `useKeyEvents`. Inert for us. **No
change.**

R6.10. **SC's custom-toolbar dropdowns portaled to `document.body`.**
Altrady does not use SC's `createButton`/`createDropdown`-style
floating menus from outside the chart subtree. Inert for us. **No
change.**

### R7 — Out of scope (residual SC concerns documented, not fixed)

R7.1. **`storageKey` collision risk.** Two simultaneous instances on
the same `symbol.ticker` share SC's default storage key. Altrady does
not pass a `storageAdapter`, so SC has nowhere to persist and the
collision is currently inert. If a `StorageAdapter` is wired in a
future PRD, that PRD must take ownership of distinct `storageKey`s
(e.g. `"main-<ticker>"`, `"settings-preview-<ticker>"`,
`"grid-bot-<chartId>"`). Not addressed here.

R7.2. **`/charts` page multi-tab.** Listed in
`SUPERCHART_BACKLOG.md` #1 as a downstream beneficiary. The page is
not yet on SC; nothing to change here.

R7.3. **Phase-10 R2 `CandleChart` ↔ `SuperChart` dev-widget guard.**
Phase 10 was reverted; there is no active guard wiring to remove.

R7.4. **Right-click on tradeLine workaround removal** (per SC `42d90ae`).
Out of scope — separate concern from multi-chart, may or may not exist
in altrady; investigate in a follow-up.

## Non-requirements

N1. **No new shared abstraction.** No "ActiveChartContext" or
"useActiveChartId" hook. The chart id is already in
`SuperChartContext` (for code inside an SC widget) or knowable from
`TradingTabsController.getCurrent()` (for code in TT thunks). Nothing
new is needed.

N2. **No `ChartRegistry` rewrite.** Only the dead `getActive` /
`setActive` / `getAll` / `activeId` parts go. The map of
`id → ChartController`, `register`, `unregister`, `get`, `subscribe`
stay exactly as they are.

N3. **No SC-source change.** This is host-side cleanup; SC's fix is
adopted as-is.

N4. **No StorageAdapter wiring.** See R6.1.

N5. **No phase-10 dev-widget choreography.** See R6.5.

N6. **No keyboard / focus changes.** See R6.2.

N7. **No new test infrastructure.** Verification is manual (V1–V8) and
mirrors the verification model of `phase-3/grid-bot-backtest/review.md`.

## Open questions

Q1. **`takeScreenshot` chart resolution — caller-provided id.**
`notes-form.js` invokes `takeScreenshot(callback)` and today receives
the "active" chart. After R4 the caller must pass `chartId`. Resolution
must not depend on `TradingTabsController` — that controller exists on
TT only, and notes-screenshot will be invoked from grid-bot, customer
service, and other pages that have no `TradingTabsController`. Each
page's notes-form call site already knows which chart it lives next to:

- TT — `useContext(MarketTabContext)?.id`.
- Grid-bot — `useContext(BotFormContext)?.chartId` (R4.2).
- Customer service / shared bots / quiz (when they ship on SC) — the
  page mounts a single chart with a known id, passed through whatever
  page-level context already exists.

`/charts` page is out of scope (separate PRD will design routing among
multiple SC instances). Resolve in design: confirm `takeScreenshot`'s
new signature is `takeScreenshot(chartId, callback)`, and audit each
existing notes-form call site to confirm a `chartId` is available
where the call is made.

Q2. **Inputs outside `SuperChartContext` — closed.** `price-field` and
`date-picker-input` are never inside `SuperChartContextProvider`. The
audit (Group A: TT widgets inside `MarketTabContext`; Group B: grid-bot
forms inside `BotFormContext`) confirms every real call site has a
resolvable `chartId`. The chart-pick button stays visible and active
in every case — no UI hide/disable state needed (R4.4). No further
question.

Q3. **Page-agnostic replay.** Replay is wired only on the TT main chart
today, but it is expected to ship on non-TT pages later. The current
implementation has three `MarketTabContext`-shaped dependencies that
will not generalize as-is:

- **`ReplayController._chartId` getter** (`replay-controller.js:94-96`)
  reads `controller.marketTabSync._marketTabId || "main"`. On a chart
  whose `ChartController` has no `marketTabSync` sub-controller (grid-bot,
  preview), the getter falls back to `"main"` — colliding with the TT
  main chart's session key.
- **`useActiveSmartReplay`**
  (`replay-backtests/use-active-smart-replay.js:13-21`) resolves the
  controller via `MarketTabsSelectors.selectActiveTradingTab` — TT-only
  by construction. Used from the backtests widget and several trade-side
  components (`v2/trade/index.js`, `forms/position-controls.js`,
  `order-submit-buttons.js`, `futures-trading-controls.js`,
  `grid-item-refresh.js`, `alerts-form.js`, `replay-backtests.js`).
- **`replay-context.js`** keys by
  `useContext(MarketTabContext)?.id || "main"` — falls back to `"main"`
  outside TT, same collision as the first bullet.

The minimal page-agnostic fix is to make `chartId` a property of
`ChartController` itself (set on registration, exposed as `controller.id`),
and have `_chartId` and the hooks read from it instead of from
`marketTabSync` / `MarketTabContext`. TT call sites that today read
`MarketTabContext.id` keep doing so — and pass it through R4-style.

Decision needed in design: do we rewire these three dependencies in
this PRD (small, mechanical change once `controller.id` is in place),
or defer to whichever PRD ships replay on a non-TT page (no change
here, accept that future grid-bot replay will also need the rewire)?
Recommended: do it here — same surface as R4, keeps the
"multi-instance unblock" boundary clean. The `useActiveSmartReplay`
hook stays TT-shaped (the backtests widget *is* TT-only); only the
controller-internal `_chartId` and `replay-context.js` change.

## Verification (review phase)

V1. Open the chart settings modal in TT → preview chart appears
**alongside** the TT main chart, both rendering candles for the active
tab's symbol. No overlay bleed. Close the modal → preview unmounts, TT
main chart is unaffected (no remount, no overlay redraw flicker).

V2. Toggle the modal's "Preview" switch off → only the TT main chart
remains. Toggle back on → preview reappears alongside.

V3. Open the grid-bot settings page → main settings chart renders. Open
the backtest modal over it → backtest chart appears alongside; both
charts have their own order lines, price handles, time markers. Drag a
price handle on one chart → only that chart's form/handle reflects the
change. Close the backtest modal → settings chart unaffected.

V4. Take a note screenshot from the active TT tab while the settings
modal is open → screenshot is of the TT main chart, not the preview.
(Verifies R4 for `takeScreenshot`.)

V5. In TT, click a price-field's chart-pick affordance → the crosshair
attaches to the TT main chart, not to a settings-preview / grid-bot
chart that may be mounted. Same for date-picker-input.

V6. Replay flow: start a smart-replay session on a TT tab; while it's
running, open the chart settings modal. Replay continues to drive the
TT main chart, not the preview.

V7. Trading Terminal context tests (`ai/workflow.md`):
- **Tab change:** Switch tabs → `ChartRegistry` re-keys correctly,
  notes screenshot / price picker target the new tab's chart.
- **Symbol change:** Change `coinraySymbol` → settings preview is
  unaffected (it has its own hardcoded symbol). TT main updates.
- **Resolution change:** Change resolution → same as above.
- **API key change:** No interaction expected — verify nothing breaks.

V8. Run with grid-bot backtest modal open across all four context
actions in V7 — both grid-bot charts must keep their independent state.
