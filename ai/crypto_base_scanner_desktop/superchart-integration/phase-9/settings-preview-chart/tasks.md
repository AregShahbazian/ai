# Tasks: Chart Settings Preview — SuperChart Integration

## Step 1: `PreviewDatafeed` + `PreviewSuperChartWidget` skeleton

### Task 1.1: Create `PreviewDatafeed`

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/preview-datafeed.js` (new)

Static datafeed over the existing dummy candles.

```js
import {candles} from "../center-view/tradingview/settings/dummy-data"

export const PREVIEW_SYMBOL = "BINA_USDT_BTC"
export const PREVIEW_RESOLUTION = "60"
export const PREVIEW_RANGE_FROM = Math.floor(candles[0].time / 1000)
export const PREVIEW_RANGE_TO = Math.floor(candles[candles.length - 1].time / 1000)

export default class PreviewDatafeed {
  onReady = (callback) => {
    setTimeout(() => callback({supported_resolutions: [PREVIEW_RESOLUTION]}), 0)
  }

  searchSymbols = (_userInput, _exchange, _symbolType, onResult) => {
    onResult([])
  }

  resolveSymbol = (symbolName, onResolve) => {
    setTimeout(() => onResolve({
      name: symbolName,
      description: "Preview",
      ticker: symbolName,
      supported_resolutions: [PREVIEW_RESOLUTION],
      minmov: 1,
      pricescale: 100,
      session: "24x7",
      timezone: "UTC",
      has_intraday: true,
    }), 0)
  }

  getBars = (_symbolInfo, _resolution, periodParams, onResult) => {
    if (!periodParams.firstDataRequest) {
      onResult([], {noData: true})
      return
    }
    onResult(candles, {noData: candles.length === 0})
  }

  subscribeBars = () => {}
  unsubscribeBars = () => {}

  // Called by ChartController.dispose()
  dispose() {}
}
```

### Task 1.2: Create `PreviewSuperChartWidget`

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/preview-super-chart.js` (new)

Pattern matches `GridBotSuperChartWidget`, minus overlays/header/screenshot.
No sub-controllers attached.

```js
import React, {useContext, useEffect, useMemo, useRef} from "react"
import PropTypes from "prop-types"
import {useStore} from "react-redux"
import {ThemeContext} from "styled-components"
import UUID from "uuid-random"
import "twin.macro"
import {createDataLoader, Superchart} from "superchart"
import "superchart/styles"

import PreviewDatafeed, {
  PREVIEW_SYMBOL,
  PREVIEW_RESOLUTION,
  PREVIEW_RANGE_FROM,
  PREVIEW_RANGE_TO,
} from "./preview-datafeed"
import {SUPPORTED_PERIODS, toPeriod, toSuperchartTheme} from "./chart-helpers"
import {ChartController} from "./chart-controller"
import {SuperChartContextProvider, useSuperChart} from "./context"
import {getChartColors} from "./hooks/use-chart-colors"
import ChartRegistry from "~/models/chart-registry"

const PREVIEW_SYMBOL_INFO = {
  ticker: PREVIEW_SYMBOL,
  name: "BTC / USDT",
  shortName: "BTC/USDT",
  pricePrecision: 2,
  volumePrecision: 0,
}

const PreviewSuperChart = ({chartId, chartSettings}) => {
  const containerRef = useRef(null)
  const {_setReadyToDraw, _setVisibleRange} = useSuperChart()
  const store = useStore()
  const theme = useContext(ThemeContext)
  const controllerRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current) return

    const datafeed = new PreviewDatafeed()
    const dataLoader = createDataLoader(datafeed)

    const superchart = new Superchart({
      container: containerRef.current,
      symbol: PREVIEW_SYMBOL_INFO,
      period: toPeriod(PREVIEW_RESOLUTION),
      dataLoader,
      theme: toSuperchartTheme(theme?._name),
      periods: SUPPORTED_PERIODS,
      debug: false,
    })

    const controller = new ChartController(superchart, datafeed, {
      dispatch: store.dispatch,
      getState: store.getState,
      setVisibleRange: _setVisibleRange,
      setReadyToDraw: _setReadyToDraw,
    })

    // Must precede the base controller's own onReady (which calls
    // syncChartColors via `get colors()`), so the first paint uses modal-
    // local colors, not Redux.
    controller.setColorsOverride(getChartColors(theme?._name, chartSettings?.chartColors))

    controllerRef.current = controller
    ChartRegistry.register(chartId, controller)

    const unsubReady = superchart.onReady(() => {
      superchart.setVisibleRange({from: PREVIEW_RANGE_FROM, to: PREVIEW_RANGE_TO})
      const chart = superchart.getChart()
      if (!chart) return
      chart.setScrollEnabled(false)
      chart.setZoomEnabled(false)
    })

    return () => {
      unsubReady?.()
      ChartRegistry.unregister(chartId)
      controller.dispose()
    }
  }, [])

  useEffect(() => {
    controllerRef.current?.syncThemeToChart(theme?._name)
  }, [theme?._name])

  useEffect(() => {
    const controller = controllerRef.current
    if (!controller) return
    controller.setColorsOverride(getChartColors(theme?._name, chartSettings?.chartColors))
    controller.syncChartColors()
  }, [chartSettings?.chartColors, theme?._name])

  useEffect(() => {
    if (!containerRef.current) return
    const ro = new ResizeObserver(() => controllerRef.current?.resize())
    ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, [])

  return <div ref={containerRef} tw="flex-1 h-full"/>
}

PreviewSuperChart.propTypes = {
  chartId: PropTypes.string.isRequired,
  chartSettings: PropTypes.object,
}

const PreviewSuperChartWidget = ({chartSettings}) => {
  const chartId = useMemo(() => `preview-${UUID()}`, [])

  return (
    <SuperChartContextProvider chartId={chartId}>
      <PreviewSuperChart chartId={chartId} chartSettings={chartSettings}/>
    </SuperChartContextProvider>
  )
}

PreviewSuperChartWidget.propTypes = {
  chartSettings: PropTypes.object,
}

export default PreviewSuperChartWidget
```

### Task 1.3: Add `setColorsOverride` + update `get colors()` on `ChartController`

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`

Add next to the other setters (`setCurrentMarket`):

```js
setColorsOverride(colors) {
  this._colorsOverride = colors
}
```

Replace the existing `get colors()`:

```js
get colors() {
  if (this._colorsOverride) return this._colorsOverride
  const state = this.getState()
  return getChartColors(state.device.theme, state.chartSettings.chartColors)
}
```

### Task 1.4: Swap preview component in settings modal

**File:** `src/containers/trade/trading-terminal/widgets/center-view/tradingview/settings.js`

Replace the `TradingPreview` import and JSX:

```js
import PreviewSuperChartWidget from "../../super-chart/preview-super-chart"
```

```jsx
<PreviewSuperChartWidget
  chartSettings={{...this.state.chartSettings, ...this.state.previewSetting}}
/>
```

**Verify (Step 1):**

1. Open the Trading Terminal.
2. Open the chart settings modal (`Ctrl+Shift+S` or the gear icon on
   the chart widget).
3. The preview row at the top shows a SuperChart with the dummy
   candles framed across the full visible range.
4. Scroll horizontally on the preview — does not move. Mouse-wheel
   zoom — does not move.
5. No console errors.
6. Known issue at this step: both the TT main SC and the preview may
   be mounted simultaneously. Fixed in Step 2.

---

## Step 2: Single-instance coordination

### Task 2.1: Extend `GridItemSettingsContext` with `previewShown`

**File:** `src/containers/trade/trading-terminal/grid-layout/grid-item-settings.js`

Update the default context shape:

```js
export const GridItemSettingsContext = React.createContext({
  component: undefined, isOpen: false, onToggle: () => null,
  previewShown: false, setPreviewShown: () => null,
})
```

In `GridItemSettingsProvider`, add a `previewShown` state and a
defensive reset when the modal closes:

```js
const [previewShown, setPreviewShown] = useState(false)

useEffect(() => {
  if (!isOpen) setPreviewShown(false)
}, [isOpen])

const context = useMemo(() => ({
  component, isOpen, onToggle, previewShown, setPreviewShown,
}), [component, isOpen, onToggle, previewShown])
```

### Task 2.2: Publish `showPreview` from the settings modal

**File:** `src/containers/trade/trading-terminal/widgets/center-view/tradingview/settings.js`

`TradingviewSettings` is a class component. Consume the context via
`contextType` (the class has none currently, so this is safe):

```js
import {GridItemSettingsContext} from "../../../grid-layout/grid-item-settings"

class TradingviewSettings extends Component {
  static contextType = GridItemSettingsContext

  componentDidMount() {
    this.context.setPreviewShown(this.state.showPreview)
  }

  componentDidUpdate(prevProps, prevState) {
    if (prevProps.chartSettings !== this.props.chartSettings) {
      // existing logic unchanged
    }
    if (prevState.showPreview !== this.state.showPreview) {
      this.context.setPreviewShown(this.state.showPreview)
    }
  }

  componentWillUnmount() {
    this.context.setPreviewShown(false)
  }
  // ...
}
```

The JSX gate `{showPreview && ...}` stays as-is.

### Task 2.3: Gate the TT SC mount in `CandleChart`

**File:** `src/containers/trade/trading-terminal/widgets/candle-chart.js`

```js
import React, {useContext} from "react"
import "twin.macro"
import {DefaultTradingWidget} from "./center-view/tradingview"
import SuperChartWidgetWithProvider from "./super-chart/super-chart"
import {GridItemSettingsContext} from "../grid-layout/grid-item-settings"

const CandleChart = ({toggleable = true, ...tvProps}) => {
  const {component, isOpen, previewShown} = useContext(GridItemSettingsContext)
  const previewActive = toggleable && isOpen && component === "CenterView" && previewShown

  return <div tw="flex flex-col flex-1 h-full">
    {toggleable
      ? (previewActive ? null : <SuperChartWidgetWithProvider key="sc"/>)
      : <DefaultTradingWidget {...tvProps}/>}
  </div>
}

export default CandleChart
```

Only the Trading Terminal path (`toggleable=true`) is affected. The
Charts page path (`toggleable=false`) is unchanged.

**Verify (Step 2):**

1. Open the Trading Terminal — TT main SC renders.
2. Open the settings modal.
   - Preview SC mounts in the modal.
   - TT main SC unmounts (the chart area behind the modal goes blank).
   - No "two SC instances" console warnings; no overlay bleed.
3. Toggle "Preview: No" in the modal header.
   - Preview SC unmounts.
   - TT main SC remounts (fresh load).
4. Toggle "Preview: Yes" again. Preview remounts; TT unmounts.
5. Close the modal (Save or Cancel). Preview unmounts; TT remounts.
   `previewShown` resets to false.
6. Edit a candle color in the modal — preview updates live; TT
   (unmounted) is unaffected. Click Save — modal closes, TT remounts
   with the new color.
7. Click Cancel after edits — modal closes without persisting; TT
   remounts unaffected by the preview edits.
8. Mobile: the preview row is hidden (`hidden tablet:flex`). Open the
   modal on mobile — TT stays mounted; `setPreviewShown` is never called
   because the toggle UI doesn't render.
9. On a TT tab with chart scroll/VR history: the chart remounts fresh
   after the modal closes (VR restored from Redux if
   `miscRememberVisibleRange`, otherwise default) — same as the
   grid-bot workaround.

---

## Step 3: Overlays (out of scope — separate PRDs)

No tasks here. Overlay content is rebuilt from scratch in follow-up
PRDs.

## Step 4: Remove TV preview (out of scope — Phase 10f)

No tasks. `tradingpreview.js` and `DummyDataProvider` stay in the tree
until the broader TV-removal task.
