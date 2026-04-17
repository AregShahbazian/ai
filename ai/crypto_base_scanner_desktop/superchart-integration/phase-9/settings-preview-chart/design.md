# Design: Chart Settings Preview — SuperChart Integration

## Key Design Decisions

### 1. Third SC widget variant — `PreviewSuperChartWidget`

Mirrors `GridBotSuperChartWidget` (standalone, no `MarketTabContext`),
with the further simplification that **no sub-controllers are attached**.
The post-refactor `ChartController` base is page-agnostic: it contains
only the overlay registry, VR echo, color sync, theme sync, and shared
overlay primitives. Everything TT-specific
(`marketTabSync`, `contextMenu`, `positions`, `replay`, `tradingButtons`,
`tradeForm`) is attached externally by `super-chart.js`. The preview
attaches nothing — it's a render-only chart.

Constants live at the top of the preview widget file:

```js
const PREVIEW_SYMBOL = "BINA_USDT_BTC"
const PREVIEW_RESOLUTION = "60"
const PREVIEW_SYMBOL_INFO = {
  ticker: PREVIEW_SYMBOL,
  name: "BTC / USDT",
  shortName: "BTC/USDT",
  pricePrecision: 2,
  volumePrecision: 0,
}
```

Registry key: `preview-<uuid>` (per-mount), same pattern as
`GridBotSuperChartWidget`. Safe against accidental double-mount.

### 2. `PreviewDatafeed` — static, mirrors `DummyDataProvider` shape

Returns the hardcoded `candles` array from
`center-view/tradingview/settings/dummy-data.js` on the first `getBars`
call; `{noData: true}` afterwards. `subscribeBars` / `unsubscribeBars`
are no-ops. `resolveSymbol` emits a minimal `LibrarySymbolInfo`.

Dummy `candles[i].time` is already in ms — SC's `Bar.time` is ms, so no
conversion in `getBars`.

Lives in `super-chart/preview-datafeed.js` and is imported only by
`preview-super-chart.js`. It does not reuse `DummyDataProvider` — the
latter is TV-specific and goes away in Phase 10f.

The datafeed must expose a no-op `dispose()` because
`ChartController.dispose()` calls `this._datafeed.dispose()`
(`CoinrayDatafeed` has one). Add an empty `dispose() {}` method.

### 3. Color override from modal-local `chartSettings` prop

`ChartController.get colors()` still reads Redux
(`state.device.theme` + `state.chartSettings.chartColors`). The preview
needs to bypass that path so unsaved edits are visible.

Add two pieces to `ChartController`:

```js
setColorsOverride(colors) {
  this._colorsOverride = colors
}

get colors() {
  if (this._colorsOverride) return this._colorsOverride
  const state = this.getState()
  return getChartColors(state.device.theme, state.chartSettings.chartColors)
}
```

Timing: the base controller's onReady always calls `syncChartColors()`
now (refactor removed the main/grid gate). So the override **must be
set synchronously between constructing the controller and the chart
becoming ready** — otherwise the first paint briefly uses Redux colors.

In practice this means the preview widget, inside its mount effect,
calls `controller.setColorsOverride(initialColors)` immediately after
`new ChartController(...)`. Subsequent changes to the prop flow through
a React effect that calls `setColorsOverride` + `syncChartColors`.

### 4. Fixed visible range + disabled interaction

Both applied from a single `superchart.onReady` callback registered by
the preview widget (after the base controller's onReady, which is
registered inside the constructor):

```js
const unsubReady = superchart.onReady(() => {
  superchart.setVisibleRange({from: PREVIEW_RANGE_FROM, to: PREVIEW_RANGE_TO})
  const chart = superchart.getChart()
  if (!chart) return
  chart.setScrollEnabled(false)
  chart.setZoomEnabled(false)
})
```

`PREVIEW_RANGE_FROM` / `PREVIEW_RANGE_TO` are derived once from the
first and last dummy candle (`candles[0].time` and
`candles[candles.length - 1].time`, both ms → seconds) at module scope
in `preview-datafeed.js`. No runtime computation.

### 5. Single-instance coordination via `GridItemSettingsContext`

Extend `GridItemSettingsContext` with `previewShown` /
`setPreviewShown`:

```js
{component, isOpen, onToggle, previewShown, setPreviewShown}
```

- The settings modal (`TradingviewSettings`, class component) publishes
  its `showPreview` state into the context via `setPreviewShown` on
  mount, on every `showPreview` change, and `setPreviewShown(false)` on
  unmount.
- `GridItemSettingsProvider` also resets `previewShown = false` whenever
  `isOpen` flips to false, defensively — in case the modal unmounts
  abruptly.
- `candle-chart.js` reads the context. When `isOpen && component ===
  "CenterView" && previewShown` and `toggleable === true`, it returns
  null in place of `SuperChartWidgetWithProvider`. This unmounts the TT
  SC tree entirely: the provider (resets `readyToDraw` / visibleRange
  state), the widget (useEffect cleanup disposes the controller and
  unregisters from `ChartRegistry`), and all overlay components.

The preview mount point is the settings modal body itself (not
`CandleChart`). The two mount conditions — TT-side
`!previewActive` and modal-side `showPreview` — are driven by the same
state, so they can never both be true.

### 6. Preview widget lifecycle (effects)

- **Mount effect** — build `PreviewDatafeed`, dataLoader, Superchart,
  ChartController. Call `controller.setColorsOverride(initialColors)`
  synchronously. Register an `onReady` callback for VR +
  scroll/zoom-disable. Register in `ChartRegistry` as `preview-<uuid>`.
  Cleanup: unsub onReady, unregister, `controller.dispose()`.
- **Theme effect** — `controller.syncThemeToChart(theme?._name)`.
- **Colors effect** — on every (`theme._name`, `chartSettings.chartColors`)
  change: compute `getChartColors(themeName, chartColors)`, call
  `setColorsOverride` + `syncChartColors`. Redundant with the mount-time
  initial override, but cheap and keeps the prop reactive.
- **Resize effect** — `ResizeObserver` → `controller.resize()`.

No symbol/resolution effects — symbol and period are hardcoded. No VR
persist effect — VR is fixed.

### 7. `SuperChartContextProvider` wraps the preview

Preserved for future overlay work — no overlays in this PRD. The
provider's `chartColors` value (from `useChartColors`) still reads
Redux; that's fine because nothing in this PRD consumes it. When
overlays are added, the overlay PRD decides how to route modal-local
colors to the context.

## Data Flow

```
grid-item-settings.js
  GridItemSettingsProvider
    ├── previewShown state ──────────────────────────┐
    │                                                │
    └── <TradingviewSettings/> (modal body)          │
          ├── local chartSettings state              │
          ├── showPreview state → setPreviewShown() ─┤
          └── <PreviewSuperChartWidget               │
                chartSettings={localChartSettings}/> │
                                                     │
candle-chart.js                                      │
  reads previewShown ◄─────────────────────────────  ┘
  renders <SuperChartWidgetWithProvider/> unless previewActive
```

## File Changes

### New files

| File | Purpose |
|---|---|
| `super-chart/preview-super-chart.js` | `PreviewSuperChartWidget` + inner `PreviewSuperChart` |
| `super-chart/preview-datafeed.js` | Static datafeed over `settings/dummy-data.js` candles + `PREVIEW_SYMBOL` / `PREVIEW_RESOLUTION` / `PREVIEW_RANGE_FROM` / `PREVIEW_RANGE_TO` exports |

### Modified files

| File | Changes |
|---|---|
| `super-chart/chart-controller.js` | Add `setColorsOverride(colors)` method + `_colorsOverride` field; change `get colors()` to prefer the override |
| `grid-layout/grid-item-settings.js` | Extend context with `previewShown` / `setPreviewShown`, add defensive reset on `isOpen → false` |
| `center-view/tradingview/settings.js` | Swap `<TradingPreview/>` → `<PreviewSuperChartWidget/>`; publish `showPreview` via `contextType = GridItemSettingsContext` |
| `widgets/candle-chart.js` | Consume context and short-circuit when `previewActive` |

## Invariants / Constraints

- The preview widget attaches **no** sub-controllers. Anything that
  requires one (symbol/period sync, replay, context menu, positions,
  trade form, trading buttons) is out of scope.
- The base `ChartController.dispose()` iterates all sub-controller fields
  with optional chaining, so leaving them `null` is safe.
- `PreviewDatafeed.dispose()` is mandatory because the base controller's
  dispose calls it unconditionally.
- TT side uses unmount-on-preview (not "hide via CSS") — mirrors the
  grid-bot workaround and ensures the SC singleton store has only one
  active instance.
- `ChartRegistry.getActive()` briefly returns the preview controller
  while the modal is open. No TT consumer is expected to call
  `getActive()` during that window. Not guarded in this PRD.
