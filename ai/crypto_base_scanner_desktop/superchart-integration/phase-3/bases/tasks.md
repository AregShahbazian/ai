# Tasks: Bases Overlay — SuperChart Integration

## Task 1: ChartController — base overlay methods

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`

Add:
1. `_applyOverlayProperties(id, props)` — private helper for Pro overlay `setProperties`
2. `createBaseSegment(startMs, endMs, price, color, width, style)` — creates a `segment` overlay
3. `createBaseBox(startMs, endMs, topPrice, bottomPrice, color)` — creates a filled `rect` overlay
4. `removeBaseOverlay(id)` — removes an overlay by ID

**Verify:** No runtime errors on app load (methods are just added, not called yet).

## Task 2: Bases overlay component

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/overlays/bases.js` (new)

1. Helper functions: `getBaseColor`, `toMs`, `drawBaseLine`, `drawSelectedBase`
2. `Bases` component:
   - Reads bases, selectedBase, medianDrop from Redux (or props override)
   - Reads chartSettings, colors from Redux + theme
   - Consumes `VisibleRangeContext` for visible-range filtering (currently empty — no-op)
   - Consumes `ReplayContext` for replay filtering (currently default — no-op)
   - Filters bases by toggles, visible range, replay, excludes selected base (R5)
   - Optimization: only updates filteredBases when the set actually changes
   - Draws via chartController methods, tracks IDs in ref
   - Clears on symbol change, unmount, settings change

**Verify:** Component renders without errors. With `basesShow: false` (default), nothing is drawn.

## Task 3: Mount Bases in SuperChart

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/super-chart.js`

1. Import `Bases` from `./overlays/bases`
2. Add `<Bases />` inside `SuperChartContextProvider`

**Verify:** App loads without errors. Open SuperChart widget, enable bases in chart settings — bases should render if data is available for the current symbol.
