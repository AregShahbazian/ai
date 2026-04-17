# SuperChart Integration — Context

We're replacing the vendored TradingView charting library with our own **SuperChart** library
(built on a forked klinecharts). SuperChart lives in a sibling repo (`../Superchart`) and is
linked into this project via `link:` deps in `package.json`.

## Constraints

**TV chart must stay functional.** The existing TradingView chart widget (`CenterView` /
`MainChartTradingWidget`) must remain fully functional throughout the entire integration.
SuperChart is being built as a separate widget alongside TV. Do not modify, break, or remove
any TV chart code until SuperChart is feature-complete and ready to replace it.

**Do not modify the SuperChart library.** The SuperChart library (`../Superchart`) is maintained
by another developer. We only consume it — never modify its source code, build config, or
exports. If we need new API surface, request it from the SuperChart dev and work around the
limitation until it ships.

**Do not use `chartController.dispatch` or `chartController.getState` outside of the controller.**
`dispatch` and `getState` are internal to `ChartController`. External code (components, screenshot
module, etc.) must not call these directly. If logic needs dispatch/getState, either make it a
Redux thunk action dispatched by the controller, or a method on the controller itself.

## Accessing `ChartController` from outside the SC React tree

React components rendered inside the SC widget's subtree use `useSuperChart()` (stable context)
to reach `chartController`. Code that runs **outside that subtree** — Redux thunks, action
creators, utility modules, design-system components shared with other widgets, screenshot
capture, anything that needs "the currently active chart" — uses **`ChartRegistry`**
(`src/models/chart-registry.js`).

```js
import ChartRegistry from "~/models/chart-registry"

ChartRegistry.getActive()        // most recently registered ChartController, or null
ChartRegistry.get("main")        // trading tabs register as marketTabId || "main"
ChartRegistry.get("grid-bot")    // grid bot standalone chart
```

`register` / `unregister` are called automatically by `super-chart.js` (trading terminal) and
`grid-bot-super-chart.js` (grid bot) when a widget mounts / unmounts. Consumers never register
charts themselves. Never invent a parallel registry, dispatch module, or context provider for
looking up the active chart — `ChartRegistry` already handles it. Existing consumers:
`actions/replay.js`, `super-chart/screenshot.js`, `replay-backtests/use-active-smart-replay.js`.

## Reference Docs

- `ai/INTEGRATION.md` — phase breakdown, architecture, full TV audit, key risks
- `ai/deps/SUPERCHART_API.md` — Superchart + klinecharts API reference
- `ai/deps/SUPERCHART_USAGE.md` — initialization patterns, datafeed wiring, gotchas
- `ai/deps/COINRAYJS_API.md` — CoinrayCache API reference

**Before writing any PRD, design, tasks, or code**, trigger the staleness check by
reading line 4 of `ai/deps/SUPERCHART_API.md`. This ensures the hook fires even if
you don't need the full docs. If stale, update the docs before proceeding.

## Phase PRDs

Each phase directory (`ai/superchart-integration/phase-N/`) may contain a `prd.md` at its
root — the overview and status tracker for that phase. **When starting work on any phase,
always read its `prd.md` first** (if it exists) to understand what's done, what's TODO, and
any constraints specific to that phase.

## Dev Workflow

`package.json` links superchart as a local package:

```json
"superchart": "link:../Superchart",
"resolutions": { "klinecharts": "link:../Superchart/packages/coinray-chart" }
```

**Initial setup (one-time):**
```bash
cd Superchart && pnpm run build
cd crypto_base_scanner_desktop && yarn install
```

**After changing superchart source:**
```bash
cd Superchart && pnpm run build
# then restart webpack dev server (won't hot-reload linked packages)
```

**After pulling superchart changes:**
```bash
cd Superchart && git pull && pnpm install && pnpm run build
```

**Quick reference:**

| Task | Command |
|---|---|
| Build superchart | `cd Superchart && pnpm run build` |
| Start desktop (electron) | `yarn start` |
| Start desktop (web) | `yarn start-web` |
| Check symlinks | `ls -la node_modules/superchart node_modules/klinecharts` |

**Troubleshooting:**
- *"Cannot find module 'superchart'"* — run `yarn install`, check `../Superchart` exists
- *Stale build* — rebuild superchart, restart webpack
- *Duplicate React / "Invalid hook call"* — Superchart should externalize React in its vite config

## Overlay Architecture

### Overlay component pattern

A standard overlay component looks like this:

```js
import {OverlayGroups} from "../overlay-helpers"
import {useSuperChart} from "../context"
import useDrawOverlayEffect from "../hooks/use-draw-overlay-effect"

const MyOverlay = ({data}) => {
  const {chartController} = useSuperChart()

  useDrawOverlayEffect(OverlayGroups.myOverlay, () => {
    chartController.createMyOverlay(data)
  }, [data])

  return null
}
```

**`useDrawOverlayEffect(group, draw, deps)`** handles everything:
- Clears the overlay group before every draw
- Guards on `readyToDraw` (skips draw if chart not ready)
- Clears on symbol change (`useSymbolChangeCleanup`)
- Includes common deps: `readyToDraw`, `chartColors`, `language`
- Passes `clear` to `draw(clear)` for editing overlays that need unmount cleanup

**Components only provide:** the overlay group, the draw callback, and component-specific deps.

### Editing overlays

Editing overlays that can unmount while drawn must return `clear` for unmount cleanup:

```js
useDrawOverlayEffect(OverlayGroups.editMyOverlay, (clear) => {
  if (!data) return
  chartController.createEditingMyOverlay(data)
  return clear
}, [data])
```

### Per-item overlay groups

If a component is rendered per-item (e.g. one per position), use per-item groups:

```js
useDrawOverlayEffect(`${OverlayGroups.submittedEntryOrders}-${position.id}`, () => {
  // ...
}, [position])
```

Shared groups cause one instance's cleanup to wipe all instances' overlays. Only singleton
components (one instance at a time) can use plain `OverlayGroups.xxx`.

### Custom draw patterns

Overlays with non-standard patterns (update-or-create, partial redraw) use `useOverlayDeps()`
directly instead of `useDrawOverlayEffect`:

```js
import {useOverlayDeps} from "../hooks/use-draw-overlay-effect"

const {readyToDraw, deps: commonDeps} = useOverlayDeps()

useEffect(() => {
  // custom logic
}, [...specificDeps, ...commonDeps])
```

Currently used by `bid-ask.js` (update-or-create) and `trades.js` (partial/full dual-effect).

### Component vs Controller responsibilities

**Components own WHEN to draw:**
- Redux selectors and context reads to decide visibility
- Filtering data (e.g. `alertType === "price"`, exclude editing alerts)
- `useDrawOverlayEffect` with component-specific deps

**Components pass to controller:** Raw data objects only (`alert`, `currentPosition`,
`entryCondition`, `trade`). Never extracted fields, formatted strings, colors, callbacks,
group names, or registry keys.

**`ChartController` owns HOW and WHAT to draw:**
- All SuperChart/klinecharts API calls (create, remove, update, override)
- Data extraction from objects (alert.id, alert.price, position.smartSettings, etc.)
- Format conversions (timestamps sec↔ms, stored↔SC point formats)
- Color resolution from `this.colors` (based on side, status, type)
- Text/label building (alert notes, trigger labels, PnL text, quantity strings)
- All callbacks — dispatches Redux actions (`editAlert`, `deleteAlert`, `submitAlertsForm`,
  `resetAlertForm`, `closeOrDeletePosition`) and calls trade form methods
  (`updateEntryCondition`, `resetTradeForm`) via `this._tradeForm`
- Overlay registry — groups and keys are internal, defined once per method
- State access via `this.chartSettings`, `this.getState()`, `this._currentMarket`,
  `this._tradeForm`

### Effect deps rules

- **Common deps are automatic** — `useDrawOverlayEffect` includes `readyToDraw`,
  `chartColors`, and `language`. Components never add these manually.
- Include chart settings that affect **visuals** (e.g. `chartSettings` object, `hideAmounts`)
- Do NOT include settings only used for **callbacks** — the controller reads them from
  `this.chartSettings` / `this.getState()` at invocation time, not at creation time
- Note: `hideAmounts` is in `state.balances`, not `state.chartSettings` — needs own dep

### Shared modules

- **`overlay-helpers.js`** — shared between controller and components:
  `OverlayGroups` (group name constants), `fromScPoints`/`toScPoints` (point converters),
  `toMs`/`toUnix` (date converters), `BID_KEY`/`ASK_KEY` (registry keys)
- **`chart-helpers.js`** — chart setup: `toSymbolInfo`, `toPeriod`, `periodToResolution`,
  `toSuperchartTheme`, `SUPPORTED_PERIODS`

### Controller setters

The controller holds references to objects it needs for visual logic and callbacks:

- `setCurrentMarket(currentMarket)` — synced from `super-chart.js` via `useEffect`.
  Used for `precisionPrice`, `quoteCurrency`, `lastPrice`.
- `setTradeForm(tradeForm)` — synced from `edit-orders.js` when form is initialized.
  Used for `updateEntryCondition`, `updateEntryExpiration`, `resetTradeForm`.
- `setMarketTabId(id)` — synced from `super-chart.js`. Used for state selectors.

### Pro overlay caveat

`segment` and `rect` are Pro overlays whose `createPointFigures` reads from an internal
properties Map via `setProperties()`, not from the `styles` object. The shared
`_createOverlay()` method handles this — it calls `_applyOverlayProperties()` after
`chart.createOverlay()` to apply `lineColor`/`lineWidth`/`lineStyle` via `setProperties`.
Standard overlays like `priceLine` and `simpleAnnotation` work fine with `styles`.

### Mutable object workaround

`form.current` objects (e.g. `entryCondition`, `entryExpiration`) are mutated in place —
React's effect dep comparison (`Object.is`) won't detect changes. When passing these as
props to child components, spread them (`{...form.current.entryCondition}`) to create a
new reference each render. Only needed at the parent→child boundary for mutable objects
from the trade form.

### Context split

`SuperChartContext` is split into two contexts to avoid unnecessary re-renders:

- **Stable context** (`useSuperChart()`) — `readyToDraw`, `chartColors`, `chartController`.
  Changes rarely (theme switch, chart init). All overlay components use this.
- **Volatile context** (`useVisibleRange()`) — `visibleRange`. Changes on every horizontal
  scroll/zoom. Only components that filter by visible range subscribe (trades, bases).

## Build Checks

**Do not run build checks** (`npx webpack ...`) unless the user explicitly asks for it.

## After Every Code Change

End your response with two sections:

### Testing Steps
How to verify the changes work. Be specific — which page to open, what to click, what to look for.

### Apply Steps
What the user needs to do to see the changes — rebuild superchart, restart webpack dev server,
reload the app, let HMR pick it up, etc. Only include steps that are actually needed (e.g. skip
"rebuild superchart" if only desktop app files changed).
