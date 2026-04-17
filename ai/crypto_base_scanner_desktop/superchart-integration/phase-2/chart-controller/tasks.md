# Tasks: Phase 2 — ChartController + SuperChartContext

## 1. Create `chart-controller.js`

Create `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`.

```js
export class ChartController {
  constructor(superchart, datafeed) {
    this._superchart = superchart
    this._datafeed = datafeed
  }

  getChart() {
    return this._superchart.getChart()
  }

  dispose() {
    this._superchart.dispose()
    this._datafeed.dispose()
  }
}
```

---

## 2. Create `context.js`

Create `src/containers/trade/trading-terminal/widgets/super-chart/context.js`.

- `SuperChartContext` — createContext(null)
- `SuperChartContextProvider` — holds `readyToDraw` state + `controllerRef`, exposes getter for `chartController`, internal `_register` and `_notifyReady`
- `useSuperChart()` — thin wrapper around useContext, throws if used outside provider

---

## 3. Update `super-chart.js`

- Import `ChartController` from `./chart-controller`
- Import `useSuperChart` from `./context`
- Inside the mount `useEffect`: create `ChartController`, call `_register(controller)`, start `requestAnimationFrame` loop calling `_notifyReady()` once `getChart() !== null`, cancel RAF on cleanup
- Replace `chartRef.current?.dispose()` + `datafeedRef.current?.dispose()` cleanup with `controller.dispose()` (ChartController handles both)
- Extract internal `SuperChartWidget` component, wrap in `SuperChartContextProvider` for the default export

---

## 4. Verify

- Open Trading Terminal, confirm SuperChart renders and syncs symbol/resolution/theme/resize as before
- Add a temporary `console.log` in `_notifyReady` to confirm `readyToDraw` fires
- Confirm TV chart widget still works alongside SuperChart
- Remove the console.log
