# Tasks: Sync Visible Range for SuperChart

## Task 1: Add `visibleRangeFromTo` to market tab state

### File: `src/actions/constants/market-tabs.js`

Add `visibleRangeFromTo: undefined` to `MARKET_TAB_DEFAULT_STATE`.

### File: `src/models/market-tabs/market-tab.js`

Add getter and setter:

```javascript
get visibleRangeFromTo() {
  return this.state.visibleRangeFromTo
}

setVisibleRangeFromTo = async (visibleRangeFromTo) => {
  this.setState({visibleRangeFromTo})
  await this.saveState()
}
```

Place after the existing `visibleRange` getter (line 88) and `setVisibleRange` method
(line 145).

### File: `src/models/market-tabs/market-tabs-selectors.js`

Add selector after `selectMarketTabVisibleRange`:

```javascript
selectMarketTabVisibleRangeFromTo: (state, marketTabId) => {
  const marketTab = MarketTabsSelectors.selectMarketTab(state, marketTabId)
  return marketTab?.visibleRangeFromTo
},
```

### Verification

- `MarketTabContext` automatically includes `visibleRangeFromTo` (context-providers.js
  line 126 spreads the full tab state)

---

## Task 2: Add VR state + handlers to `SuperChartContextProvider`

### File: `src/containers/trade/trading-terminal/widgets/super-chart/context.js`

Add `visibleRange` state (`{from, to}` or `{}`) and a `setVisibleRange` callback:

```javascript
const [visibleRange, setVisibleRange] = useState({})
```

Expose in the context value:

```javascript
const value = useMemo(() => ({
  readyToDraw,
  chartColors,
  visibleRange,
  _setVisibleRange: setVisibleRange,
  get chartController() { return controllerRef.current },
  _register: registerController,
  _notifyReady: notifyReady,
}), [readyToDraw, chartColors, visibleRange, registerController, notifyReady])
```

Note: `visibleRange` is added to `useMemo` deps so overlays re-render when VR changes.

### Verification

- `useSuperChart()` now returns `visibleRange` and `_setVisibleRange`

---

## Task 3: Wire `onVisibleRangeChange` + persist + restore in `super-chart.js`

### File: `src/containers/trade/trading-terminal/widgets/super-chart/super-chart.js`

#### 3a: Subscribe to `onVisibleRangeChange`

In the init `useEffect` (line 64), after chart creation and before the cleanup:

```javascript
const unsubVR = superchart.onVisibleRangeChange(({from, to}) => {
  _setVisibleRange({from, to})
})
```

Add `unsubVR()` to the cleanup function.

Access `_setVisibleRange` from `useSuperChart()` (line 25).

#### 3b: Debounced persist

Add a new `useEffect` that watches the VR state and persists when enabled:

```javascript
const miscRememberVisibleRange = useSelector(state => state.chartSettings.miscRememberVisibleRange)
const persistTimeoutRef = useRef()

useEffect(() => {
  return () => clearTimeout(persistTimeoutRef.current)
}, [])

useEffect(() => {
  const {from, to} = visibleRange
  if (!from || !to || !miscRememberVisibleRange) return

  clearTimeout(persistTimeoutRef.current)
  persistTimeoutRef.current = setTimeout(() => {
    TradingTabsController.get()
      .getTabById(marketTabId)
      .setVisibleRangeFromTo({from, to})
      .catch(console.error)
  }, 500)
}, [visibleRange, miscRememberVisibleRange, marketTabId])
```

Read `visibleRange` from `useSuperChart()`.

#### 3c: Restore helper

Add a helper function that computes the restore range from stored `{from, to}`:

```javascript
const restoreVisibleRange = useCallback(() => {
  if (!chartRef.current || !miscRememberVisibleRange || !visibleRangeFromTo) return
  const {from, to} = visibleRangeFromTo
  if (!from || !to) return
  const duration = to - from
  const percentRightMargin = 10
  const correctedDuration = duration * ((100 - percentRightMargin) / 100)
  const newTo = Date.now() / 1000
  const newFrom = newTo - correctedDuration
  chartRef.current.setVisibleRange({from: Math.floor(newFrom), to: Math.floor(newTo)})
}, [miscRememberVisibleRange, visibleRangeFromTo])
```

Read `visibleRangeFromTo` from `MarketTabContext`.

#### 3d: Restore VR on chart ready

Call `restoreVisibleRange()` after readyToDraw becomes true:

```javascript
useEffect(() => {
  if (!readyToDraw) return
  restoreVisibleRange()
}, [readyToDraw])
```

#### 3e: Restore VR on tab switch

The existing `[coinraySymbol]` effect handles tab switches (symbol changes). After
`setSymbol()`, the chart reloads data. We need to restore VR after the new data loads.

Add a ref to track pending VR restore, and trigger it from the `onVisibleRangeChange`
callback (which fires after data loads and the chart renders):

```javascript
const pendingVRRestore = useRef(false)

// In the coinraySymbol effect, after setSymbol():
if (miscRememberVisibleRange && visibleRangeFromTo) {
  pendingVRRestore.current = true
}

// In the onVisibleRangeChange callback, after _setVisibleRange:
if (pendingVRRestore.current) {
  pendingVRRestore.current = false
  restoreVisibleRange()
}
```

### Verification

- Scroll/zoom SC → `visibleRange` in context updates → overlays re-filter
- With "Remember visible range" on: switch tabs and back → zoom level restored
  (latest candles in view, same horizontal zoom)
- With it off: switch tabs and back → chart resets to default

---

## Task 4: SC overlays read VR from SC context

### File: `src/containers/trade/trading-terminal/widgets/super-chart/overlays/trades.js`

1. Remove import of `VisibleRangeContext` (line 6)
2. Remove `const {visibleRange} = useContext(VisibleRangeContext)` (line 36)
3. Add `visibleRange` to the existing `useSuperChart()` destructure (line 11):
   ```javascript
   const {readyToDraw, chartController, chartColors, visibleRange} = useSuperChart()
   ```
4. Fix the filter units bug (line 51) — remove `* 1000`:
   ```javascript
   // Before (wrong — compares ms to seconds):
   trades = trades.filter(({time}) => time && time * 1000 >= from && time * 1000 < to)
   // After (correct — both in seconds):
   trades = trades.filter(({time}) => time && time >= from && time < to)
   ```

### File: `src/containers/trade/trading-terminal/widgets/super-chart/overlays/bases.js`

1. Remove import of `VisibleRangeContext` (line 4)
2. Remove `const {visibleRange} = useContext(VisibleRangeContext)` (line 28)
3. Add `visibleRange` to the existing `useSuperChart()` destructure (line 13):
   ```javascript
   const {readyToDraw, chartController, chartColors, visibleRange} = useSuperChart()
   ```
4. No filter change needed — bases already use `ChartController.toUnix()` which returns
   seconds, matching SC's `{from, to}` format.

### Verification

- Zoom into a narrow range → only trades/bases in that range are drawn
- Zoom out → more trades/bases appear
- TV overlays unaffected (they still use `VisibleRangeContext`)
