# Design: Bases Overlay — SuperChart Integration

## Overview

Implements the bases overlay per the [PRD](prd.md). Two files change, one file is new:

- **`chart-controller.js`** — new methods for creating/removing base overlays
- **`overlays/bases.js`** — new overlay component (React, no rendering)
- **`super-chart.js`** — mount `<Bases />` inside the provider

All files in `src/containers/trade/trading-terminal/widgets/super-chart/`.

---

## ChartController Methods

### Private helper: `_applyOverlayProperties`

Pro overlays (`segment`, `rect`) ignore `styles` — they read from an internal properties Map via `setProperties()`. This helper encapsulates that pattern.

```js
_applyOverlayProperties(id, props) {
  const chart = this.getChart()
  if (!chart) return
  const overlay = chart.getOverlays({id})[0]
  if (overlay?.setProperties) overlay.setProperties(props, id)
}
```

### `createBaseSegment(startMs, endMs, price, color, width, style)`

Creates a horizontal `segment` overlay at `price` from `startMs` to `endMs`.

```js
createBaseSegment(startMs, endMs, price, color, width, style = "solid") {
  const chart = this.getChart()
  if (!chart) return null
  const id = chart.createOverlay({
    name: "segment",
    points: [
      {timestamp: startMs, value: price},
      {timestamp: endMs, value: price},
    ],
    lock: true,
  })
  if (id) this._applyOverlayProperties(id, {lineColor: color, lineWidth: width, lineStyle: style})
  return id
}
```

### `createBaseBox(startMs, endMs, topPrice, bottomPrice, backgroundColor)`

Creates a filled `rect` overlay (no borders) for the selected base box. The caller is responsible for computing the background color with alpha.

```js
createBaseBox(startMs, endMs, topPrice, bottomPrice, backgroundColor) {
  const chart = this.getChart()
  if (!chart) return null
  const id = chart.createOverlay({
    name: "rect",
    points: [
      {timestamp: startMs, value: topPrice},
      {timestamp: endMs, value: bottomPrice},
    ],
    lock: true,
  })
  if (id) this._applyOverlayProperties(id, {style: "fill", backgroundColor, borderWidth: 0})
  return id
}
```

### `removeBaseOverlay(id)`

```js
removeBaseOverlay(id) {
  this.getChart()?.removeOverlay({id})
}
```

No `updateBase` method needed — bases are cleared and redrawn, not updated in place. This matches the TradingView pattern and avoids complexity.

---

## Overlay Component: `overlays/bases.js`

### Color Resolution

```js
function getBaseColor(base, colors) {
  if (base.respectedAt) return colors.respected
  if (base.crackedAt) return colors.cracked
  return colors.notCracked
}
```

`colors` is derived from `theme.chart` + `chartSettings.chartColors[theme._name]`:
- `notCracked` ← `notCrackedLine2`
- `cracked` ← `crackedLine2`
- `respected` ← `respectedLine2`

### Drawing Functions

These are plain functions (not controller methods) that call controller methods and return arrays of overlay IDs. They live in the component file since they compose controller primitives with base-specific logic.

#### `drawBaseLine(chartController, base, nextFormedAtMs, colors)`

Draws a non-selected base (PRD R1 + R2). Returns `string[]`.

1. `startMs = toMs(base.formedAt)`
2. `endMs = base.crackedAt ? toMs(base.crackedAt) : (nextFormedAtMs ?? Date.now())`
3. `color = getBaseColor(base, colors)`
4. Create main segment: `chartController.createBaseSegment(startMs, endMs, base.price, color, 2)`
5. If `base.respectedAt && base.crackedAt`: create continuation segment from `crackedAt` to `respectedAt` with `colors.notCracked`, width 1
6. Return all IDs

#### `drawSelectedBase(chartController, base, colors, showBox, medianDrop)`

Draws the selected base (PRD R3 + R4). Returns `string[]`.

1. `startMs = toMs(base.formedAt)`
2. `endMs = base.respectedAt ? toMs(base.respectedAt) : Date.now()`
3. `color = getBaseColor(base, colors)`
4. Create main segment: width 2
5. If `showBox`:
   - `dropPrice = base.price * (100 + medianDrop) / 100`
   - `midPrice = (base.price + dropPrice) / 2`
   - Create box: `chartController.createBaseBox(startMs, endMs, base.price, dropPrice, util.hex2rgba(util.rgba2hex(color), 0.2))`
   - Create bottom border segment: `dropPrice`, width 1, solid
   - Create midline segment: `midPrice`, width 1, dashed
6. Return all IDs

### `toMs` Helper

Bases from Redux have `formedAt`/`crackedAt`/`respectedAt` as moment objects (`.unix()` returns seconds). The TradingView code uses `.unix()`. For the controller methods which expect milliseconds:

```js
function toMs(momentOrIso) {
  if (momentOrIso?.unix) return momentOrIso.unix() * 1000
  return new Date(momentOrIso).getTime()
}
```

This handles both moment objects (from Redux) and ISO strings (if props override passes strings).

### Component: `Bases`

```js
const Bases = React.memo((props) => { ... })
```

#### Hooks and State

```js
const {readyToDraw, chartController} = useSuperChart()
const {currentMarket} = useContext(MarketTabContext)
const theme = useContext(ThemeContext)
const chartSettings = useSelector(state => state.chartSettings)
const algorithm = useSelector(state => state.baseScanner.algorithm)
const marketInfo = useSelector(state => state.baseScanner.marketInfo)
const selectedBases = useSelector(state => state.baseScanner.selectedBases)
const {time: replayTime} = useContext(ReplayContext)
const {visibleRange} = useContext(VisibleRangeContext)
```

#### Derived Values (useMemo)

**`bases`** — base list from Redux or props override:
```js
props.bases || marketInfo[currentMarket.coinraySymbol]?.[algorithm]?.bases || []
```

**`selectedBase`** — selected base from Redux or props override. Drawable if it has a `price` and (if replay mode) `formedAt` is before replay time. Returns `undefined` if not drawable.

**`medianDrop`** — from `marketInfo[coinraySymbol][algorithm].marketStats.medianDrop`, parsed as float, default `-3.0`.

**`colors`** — resolved from theme + chartColors:
```js
const chartColors = {...theme?.chart, ...chartSettings?.chartColors?.[theme?._name]}
const colors = {
  notCracked: chartColors.notCrackedLine2,
  cracked: chartColors.crackedLine2,
  respected: chartColors.respectedLine2,
}
```

#### Filtering (useEffect → `filteredBases` state)

Runs when `bases`, `chartSettings`, `visibleRange`, `replayMode`, `replayTime` change.

1. Apply toggle filters (PRD Filtering section)
2. Apply visible-range filter (`formedAt < to`, `respectedAt >= from` if respected)
3. Apply replay filter if in replay mode
4. Compare new filtered set against previous by ID — only `setFilteredBases` if the set changed (optimization from PRD)

Note: the selected base is NOT excluded from `filteredBases`. It stays in the list so that surrounding bases get the correct `nextBase` for their end-time calculation. Instead, it is skipped during the draw iteration (matching the TV pattern).

#### Visible Range

Consumed from `VisibleRangeContext` (same as the TradingView `bases.js`):

```js
const {visibleRange} = useContext(VisibleRangeContext)
```

`visibleRange` has `{from, to}` in unix seconds. This context is already wired up for the TradingView chart. When the SuperChart visible-range callback is ready, it will populate this same context — so bases will start filtering automatically without any changes to this component.

#### Drawing (clear + draw)

Overlay IDs tracked in `shapesRef = useRef([])`.

**`clear`**: iterate `shapesRef.current`, call `chartController.removeBaseOverlay(id)` for each, reset to `[]`.

**`draw`**: called when `filteredBases`, `selectedBase`, `chartSettings`, `medianDrop`, `readyToDraw` change.

1. `clear()`
2. If `!basesShow` or `!readyToDraw`, return
3. For each filtered base: if not the selected base, call `drawBaseLine` with `nextFormedAtMs` from next base in list. Push IDs to `shapesRef`. The selected base stays in the list for correct `nextBase` calculation but is skipped for drawing.
4. If `selectedBase`: call `drawSelectedBase`. Push IDs to `shapesRef`.

Uses a `useEffect` with these dependencies. The `basesUpdated` flag pattern from TradingView is not needed — React's effect system handles the dependency tracking.

#### Symbol Change Cleanup

```js
useEffect(() => {
  if (!currentMarket) return
  const onSymbolChange = () => clear()
  currentMarket.subscribeCoinraySymbolWillChange(onSymbolChange)
  return () => {
    currentMarket?.unsubscribeCoinraySymbolWillChange(onSymbolChange)
    clear()
  }
}, [currentMarket])
```

---

## Mounting

In `super-chart.js`, add `<Bases />` inside `SuperChartWidgetWithProvider`:

```jsx
<SuperChartContextProvider>
  <SuperChartWidget />
  <BidAsk />
  <BreakEven />
  <Trades />
  <PriceTimeSelect />
  <Bases />
</SuperChartContextProvider>
```

---

## Differences from Storybook Implementation

| Aspect | Storybook (`bases.ts`) | Integration (`bases.js`) |
|--------|----------------------|-------------------------|
| Drawing logic location | Standalone helper file | `ChartController` methods + component-local composing functions |
| Data format | ISO strings | Moment objects from Redux (`.unix()`) |
| Selected base filtering | Subject to toggle/range filters | Always drawn regardless of filters (R5) |
| Visible range source | `onVisibleRangeChange` callback | `VisibleRangeContext` (shared, populated when SuperChart callback is ready) |
| Replay mode | Not supported | Supported — filters bases by `formedAt < replayTime` |
| Props override | N/A | `props.base`, `props.bases` for training chart |
