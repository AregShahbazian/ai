# Multi-Chart Unblock — Tasks

Order matters: 1 → 2 → 3 → 4 (controller.id) → 5 (rewires depending on
controller.id) → 6 → 7. Steps 8–9 are independent of 4–7.

Each task lists files, change, and a one-line manual verification. Full
verification matrix lives in `review.md`.

## 1. Update deps docs

**Files:** `ai/deps/SUPERCHART_API.md`, `ai/deps/SUPERCHART_USAGE.md`.

- `SUPERCHART_API.md` line 4-5: bump SC hash → `42d90ae`,
  coinray-chart hash → `c99a96f`.
- Append/update notes covering: per-instance store, `SymbolInfo.shortName`
  legend fallback, `createTradeLine` `onRightClick`,
  `PriceTimeResult.coordinate.pageX`/`pageY`, touch longpress
  → `onRightSelect`.
- `SUPERCHART_USAGE.md`: bump same hashes; add a one-paragraph
  "Multi-instance" section pointing at `MultiChart.stories.tsx`
  patterns (datafeed-per-instance, distinct container ref, dispose
  order).

**Verify:** doc hashes match `git -C $SUPERCHART_DIR rev-parse HEAD` and
`git -C $SUPERCHART_DIR/packages/coinray-chart rev-parse HEAD`.

## 2. Remove TT main ↔ settings-preview unmount workaround

**Files:**
- `src/containers/trade/trading-terminal/grid-layout/grid-item-settings.js`
- `src/containers/trade/trading-terminal/widgets/center-view/tradingview/settings.js`
- `src/containers/trade/trading-terminal/widgets/candle-chart.js`

**`grid-item-settings.js`:**
- Default context value (line 85-88): drop `previewShown: false,
  setPreviewShown: () => null,`.
- `GridItemSettingsProvider`: drop `const [previewShown, setPreviewShown]
  = useState(false)` (line 95) and the `useEffect(() => { if (!isOpen)
  setPreviewShown(false) }, [isOpen])` block (lines 103-105).
- Memo (line 107-109): drop `previewShown, setPreviewShown` from value
  + deps.

**`settings.js`:**
- Line 33: drop `previewShown, setPreviewShown` from the
  `useContext(GridItemSettingsContext)` destructure.
- Lines 50-53: delete the entire `useEffect` that calls
  `setPreviewShown(showPreview)`.
- Lines 141-148: delete the `/* Gate on context previewShown ... */`
  comment block; change the gate from `{showPreview && previewShown &&`
  to `{showPreview &&`.

**`candle-chart.js`:**
- Drop `import { GridItemSettingsContext }`.
- Drop `const {component, isOpen, previewShown} = useContext(...)`.
- Delete the `// TEMPORARY: ...` comment block.
- Delete the `previewActive` const.
- Replace the toggleable branch with unconditional
  `<SuperChartWidgetWithProvider key="sc"/>`.

**Verify:** open chart settings modal → both TT main chart AND preview
render simultaneously, no overlay bleed, no console errors. Close →
TT main unaffected.

## 3. Remove grid-bot kill-switch

**File:** `src/containers/bots/grid-bot/grid-bot-settings.js`.

- Delete the `// TEMPORARY: the SC library's global singleton store
  ...` comment block (lines 27-32).
- Delete `const SHOW_SETTINGS_CHART = true` (line 33).
- In the collapsed-layout chart render (line 174), drop
  `&& SHOW_SETTINGS_CHART` from the condition.

**Verify:** open grid-bot settings → chart still renders (no behavior
change since constant was `true`).

## 4. Add `controller.id` to ChartController

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`.

- Constructor: accept `{id}` in the options object; set `this.id = id`
  alongside the other initial fields. No mutation point — `id` is set
  once and read everywhere.
- No method changes; no getter; just a plain field.

**Verify:** type-check / static analysis only — no runtime path hits
this until step 5.

## 5. Pass `id` from each mount site + sync on TT tab switch

**Files:**
- `src/containers/trade/trading-terminal/widgets/super-chart/super-chart.js`
- `src/containers/trade/trading-terminal/widgets/super-chart/grid-bot-super-chart.js`
- `src/containers/trade/trading-terminal/widgets/super-chart/preview-super-chart.js`

**`super-chart.js`:**
- Compute `const chartId = marketTabId || "main"` once near the top of
  the init effect.
- Pass `id: chartId` in the `ChartController` constructor options.
- In the tab-switch effect (lines 145-156), assign
  `controller.id = newId` adjacent to the existing
  `ChartRegistry.unregister(prevId); ChartRegistry.register(newId,
  controller)`.

**`grid-bot-super-chart.js`:**
- Accept a new optional `chartId` prop on `GridBotSuperChartWidget`;
  fall back to internal `useMemo(() => `grid-bot-${UUID()}`, [])` when
  not provided (defensive — keeps `grid-bot-overview.js` working with
  no callsite change).
- Pass `id: chartId` into `ChartController` constructor options.

**`preview-super-chart.js`:**
- Pass `id: chartId` into `ChartController` constructor options. The
  widget already generates `chartId` and threads it through
  `SuperChartContextProvider` (line 184); reuse that.

**Verify:** in dev tools, `ChartRegistry.getAll()` (still callable
until step 9) lists controllers and `ctrl.id` matches the registry key
for each. After tab switch, `ctrl.id` reflects the new tab id.

## 6. Rewire replay's chart-id resolution

**Files:**
- `src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js`
- `src/containers/trade/trading-terminal/widgets/super-chart/replay/replay-context.js`

**`replay-controller.js` line 94-96:**
```js
get _chartId() {
  return this._sessionChartId || this._chartController?.id || "main"
}
```

Drop the `marketTabSync._marketTabId` read entirely. Pin lines that
reference `marketTabSync._marketTabId` (e.g. line 388 in
`_startSession`) — switch them to `this._chartController?.id || "main"`.

**`replay-context.js`:**
- Drop `import {MarketTabContext}`.
- Add `import {useSuperChart} from "../context"`.
- Inside the hook: `const {chartController} = useSuperChart(); const
  chartId = chartController?.id || "main"`.

**Verify:** start a replay session in TT, switch tabs, switch back —
session is preserved, no console errors, `selectReplaySession(tabId)`
in Redux DevTools shows state for the right tab.

## 7. Convert four `getActive()` callers

**Files:**
- `src/containers/trade/trading-terminal/widgets/super-chart/screenshot.js`
- `src/containers/trade/trading-terminal/widgets/notes-form.js`
- `src/components/design-system/v2/trade/inputs/price-field.js`
- `src/components/design-system/v2/trade/inputs/date-picker-input.js`
- `src/actions/replay.js`
- `src/components/design-system/v2/list-items.js`
- `src/containers/trade/trading-terminal/widgets/my-orders/order-row.js`
- `src/containers/trade/trading-terminal/widgets/my-orders/my-orders-header.js`

**`screenshot.js` line 16-23:**
```js
export const takeScreenshot = async (chartId, callback) => {
  const controller = chartId ? ChartRegistry.get(chartId) : null
  if (!controller?.header) {
    callback(false)
    return
  }
  await controller.header.captureScreenshotForNote(callback)
}
```

**`notes-form.js`:** wire `marketTabId` from `MarketTabContext` to the
class. Smallest path: thin functional wrapper that reads context and
passes `marketTabId` as a prop, OR `static contextType =
MarketTabContext` if `notes-form` doesn't already consume another
context. Pass `marketTabId` to `takeScreenshot(this.props.marketTabId,
(url) => { ... })`.

**`price-field.js` line 88-93:**
```js
const marketTabId = useContext(MarketTabContext)?.id
const botChartId = useContext(BotFormContext)?.chartId
const chartId = marketTabId || botChartId
const ctrl = chartId ? ChartRegistry.get(chartId) : null
```

Same in **`date-picker-input.js`**. Drop the `ChartRegistry.getActive()`
call.

**`actions/replay.js`:**
```js
export function getSmartReplayController(chartId) {
  return chartId ? ChartRegistry.get(chartId)?.replay?.smart || null : null
}

export const replaySafeCallback = (callback, chartId) => {
  return () => {
    const scReplay = chartId ? ChartRegistry.get(chartId)?.replay : null
    if (scReplay) return scReplay.replaySafeCallback(callback)
    return (...args) => callback(...args)
  }
}
```

**`list-items.js`, `order-row.js`, `my-orders-header.js`:** at each
`replaySafeCallback(...)` call site, capture
`const {id: marketTabId} = useContext(MarketTabContext)` near the top
of the component (or read from existing context destructure if
already there) and pass it as the second arg.

**`BotFormContext` extension:** in
`src/components/design-system/v2/trade/bots/context.js`, add
`chartId: null` to the default value.

**`grid-bot-settings.js`, `backtest-content.js`,
`backtest-content-mobile-form.js`:**
- Generate the `chartId` UUID at the page/modal level
  (`useMemo(() => `grid-bot-${UUID()}`, [])`).
- Add `chartId` to the `BotFormContext.Provider` `value` object.
- Pass `chartId` as a prop to `<GridBotSuperChartWidget chartId={...}/>`.

**Verify:**
- Take a notes screenshot from TT — image is of the TT main chart.
- Click chart-pick on a TT price-field — crosshair attaches to TT main.
- Click chart-pick on a grid-bot price-range-form price-field while
  backtest modal is also open — crosshair attaches to the settings
  page's chart, not the backtest modal's chart.
- Trigger a `replaySafeCallback`-guarded action while a replay session
  is active — confirmation dialog appears with correct context.

## 8. Strip dead `chart-registry.js` surface

**File:** `src/models/chart-registry.js`.

- Delete `let activeId = null`.
- Delete the `activeId = id` line in `register`.
- Delete the entire `if (activeId === id) { ... }` block in `unregister`.
- Delete `getActive()`, `setActive()`, `getAll()` methods.

Final shape: `register(id, controller)`, `unregister(id)`, `get(id)`,
`subscribe(listener)`, plus the dev-only `storeGlobal`.

**Verify:** repo grep for `getActive\|setActive\|getAll` against
`ChartRegistry` returns zero hits. App still loads.

## 9. Walk through review.md

The dev server is already running. HMR picks up most changes; hard-reload
the browser when needed (context shape changes, `ChartController`
constructor change). Step through `review.md` items 1–44.

## Out-of-scope reminders

- Do **not** add a `useActiveChartId()` hook or `ActiveChartContext`.
- Do **not** touch `useActiveSmartReplay` (TT-only by construction;
  see Q3 in PRD).
- Do **not** touch `MarketTabSyncController` semantics — TT tab
  switching keeps mutating the same controller; only the registry
  re-register and `controller.id` reassignment happen on tab change.
- Do **not** add new comments. The TEMPORARY/WORKAROUND comments are
  deleted; the resulting code is self-explanatory.
- Do **not** wire StorageAdapter (R7.1).
- Do **not** modify SC source.
