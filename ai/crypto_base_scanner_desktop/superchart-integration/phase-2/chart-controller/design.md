# Design: Phase 2 — ChartController + SuperChartContext

## Component Tree

```
SuperChartContextProvider       ← new, context.js
  SuperChartWidget              ← existing super-chart.js (minimal changes)
    <div ref={containerRef} />  ← Superchart mounts here
```

`SuperChartContextProvider` is the default export of `super-chart.js` — it wraps the
widget and is what the widget slot renders. `SuperChartWidget` becomes an internal component.

---

## ChartController (`chart-controller.js`)

Plain JS class. Created once per chart instance inside `SuperChartWidget` on mount.

```js
export class ChartController {
  constructor(superchart, datafeed) {
    this._superchart = superchart
    this._datafeed = datafeed
  }

  getChart() {
    return this._superchart.getChart()   // klinecharts instance, may be null initially
  }

  dispose() {
    this._superchart.dispose()
    this._datafeed.dispose()
  }
}
```

No convenience methods added upfront. Overlays access `superchart` APIs through
`chartController.getChart()` or via future convenience methods added as needed.

---

## Context (`context.js`)

### Shape

```js
SuperChartContext = {
  // Public — consumed by overlay components
  readyToDraw: boolean,               // true once getChart() !== null
  chartController: ChartController,   // stable ref, read via getter (no re-render on access)

  // Internal — used only by SuperChartWidget
  _register(controller): void,
  _notifyReady(): void,
}
```

`chartController` is exposed via a getter on the value object so it reads `controllerRef.current`
at call time — avoids stale closure issues since refs don't trigger re-renders:

```js
const value = useMemo(() => ({
  readyToDraw,
  get chartController() { return controllerRef.current },
  _register: registerController,
  _notifyReady: notifyReady,
}), [readyToDraw, registerController, notifyReady])
```

### Provider

```js
export function SuperChartContextProvider({ children }) {
  const [readyToDraw, setReadyToDraw] = useState(false)
  const controllerRef = useRef(null)

  const registerController = useCallback((controller) => {
    controllerRef.current = controller
  }, [])

  const notifyReady = useCallback(() => setReadyToDraw(true), [])

  const value = useMemo(() => ({
    readyToDraw,
    get chartController() { return controllerRef.current },
    _register: registerController,
    _notifyReady: notifyReady,
  }), [readyToDraw, registerController, notifyReady])

  return <SuperChartContext.Provider value={value}>{children}</SuperChartContext.Provider>
}
```

### Public hook

```js
export function useSuperChart() {
  const ctx = useContext(SuperChartContext)
  if (!ctx) throw new Error("useSuperChart must be used within SuperChartContextProvider")
  return ctx
}
```

Consumers only get `{ readyToDraw, chartController }` — the `_register`/`_notifyReady`
internals are on the context but not part of the documented API.

---

## SuperChartWidget changes (`super-chart.js`)

Two additions to the existing `useEffect`:

1. Create `ChartController`, call `_register(controller)`
2. Poll `getChart()` via `requestAnimationFrame` until non-null, then call `_notifyReady()`

```js
const SuperChartWidget = () => {
  const containerRef = useRef(null)
  const chartRef = useRef(null)
  const { _register, _notifyReady } = useSuperChart()

  // ... existing context reads unchanged

  useEffect(() => {
    if (!containerRef.current || !coinraySymbol) return

    const datafeed = new CoinrayDatafeed()
    const dataLoader = createDataLoader(datafeed)
    const superchart = new Superchart({ ...existing options... })

    chartRef.current = superchart

    const controller = new ChartController(superchart, datafeed)
    _register(controller)

    // Notify context when klinecharts instance is ready
    let rafId
    const checkReady = () => {
      if (superchart.getChart() !== null) {
        _notifyReady()
      } else {
        rafId = requestAnimationFrame(checkReady)
      }
    }
    rafId = requestAnimationFrame(checkReady)

    return () => {
      cancelAnimationFrame(rafId)
      controller.dispose()
      chartRef.current = null
    }
  }, [])

  // symbol/resolution/theme/resize sync effects — unchanged
  // (still use chartRef.current directly, no need to go through controller)

  return <div ref={containerRef} tw="flex-1 h-full" />
}
```

The widget slot renders the provider wrapping the widget:

```js
const SuperChartWidgetWithProvider = () => (
  <SuperChartContextProvider>
    <SuperChartWidget />
  </SuperChartContextProvider>
)

export default SuperChartWidgetWithProvider
```

---

## readyToDraw gating

Overlays (future phases) gate rendering on `readyToDraw`:

```js
const { readyToDraw, chartController } = useSuperChart()
if (!readyToDraw) return null
// safe to call chartController.getChart() here
```

---

## What Doesn't Change

- `CoinrayDatafeed` — untouched
- `helpers.js` — untouched
- Symbol/resolution/theme/resize sync logic in `super-chart.js` — untouched
- External API of the widget (what the widget slot renders) — unchanged
- TV chart widget — untouched
