# Superchart API Reference

> Source: `$SUPERCHART_DIR` (branch: main)
> Superchart git hash: `42d90ae95bdf1d8d1fa25c7f48a9d21044ab4009`
> coinray-chart (`packages/coinray-chart`, branch: main) git hash: `c99a96fa8a554bc8a6e9a7fe3fecb655ec6c5b52`
> Do NOT explore source — use this doc instead.

## Multi-instance support

As of SC `276e661`, every `Superchart` instance owns an isolated `ChartStore`
(symbol, period, theme, overlays, providers, popup state). Two or more
instances on the same page coexist without bleed. Required disciplines for
the host:

- One `Datafeed` (and its `createDataLoader`) per `Superchart` instance —
  never share.
- Distinct container DOM elements — never reuse a ref across two
  constructors.
- Dispose order on unmount: `superchart.dispose()` then
  `datafeed.dispose()`.
- If two instances share `symbol.ticker` and a `storageAdapter` is wired,
  pass distinct `storageKey`s — SC's default key is `symbol.ticker`.
- `SymbolInfo.shortName` is rendered in the legend with template
  `{shortName||ticker} · {period}` (coinray-chart `2d463e69`). Set it for
  human-friendly labels (`BTC/USDT` instead of `BINA_USDT_BTC`).

Reference story: `$SUPERCHART_DIR/.storybook/api-stories/MultiChart.stories.tsx`.

## Exports (`import { ... } from "superchart"`)

```
Superchart              — Main class
loadLocale              — Load i18n locale
createDataLoader        — Convert Datafeed → klinecharts DataLoader
createOrderLine         — Create order line overlay (Superchart extension)
createPriceLine         — Create price line overlay (from klinecharts)
createTradeLine         — Create trade line overlay (from klinecharts)
registerOverlay         — Register custom overlay type (call before new Superchart())
registerFigure          — Register custom figure primitive (canvas shape)
registerIndicator       — Register custom indicator template
DEFAULT_OVERLAY_PROPERTIES — Default overlay styling constants
```

Also re-exports klinecharts core types: `Chart`, `Nullable`, `DeepPartial`, `KLineData`,
`Point`, `Styles`, `Overlay`, `OverlayCreate`, `OverlayEvent`, `OverlayTemplate`, `Indicator`,
`IndicatorCreate`, `IndicatorTemplate`, `FigureTemplate`, `ReplayEngine`, `ReplayStatus`.

Also re-exports Superchart-specific types: `SuperchartOptions`, `SuperchartApi`, `VisibleTimeRange`,
`PriceTimeResult`, `ToolbarButtonOptions`, `ToolbarDropdownOptions`, `ToolbarDropdownItem`,
`ToolbarDropdownActionItem`, `ToolbarDropdownSeparator`, `Period`, `SymbolInfo`,
`StorageAdapter`, `ChartState`, `IndicatorProvider`, `OverlayProperties`, `Datafeed`,
`Bar`, `PeriodParams`, `HistoryMetadata`, `OrderLine`, `OrderLineProperties`,
`PriceLine`, `PriceLineProperties`, `PriceLineEventListener`,
`TradeLine`, `TradeLineProperties`,
`ScriptProvider`, `PaneProperties`, `SuperchartDataLoader`, `LibrarySymbolInfo`.

## SuperchartOptions (constructor)

```typescript
{
  // Required
  container: string | HTMLElement
  symbol: SymbolInfo
  period: Period
  dataLoader: DataLoader

  // Optional
  indicatorProvider?: IndicatorProvider
  storageAdapter?: StorageAdapter
  storageKey?: string                   // default: symbol.ticker
  mainIndicators?: string[]
  subIndicators?: string[]
  locale?: string                       // default: 'en-US'
  theme?: 'light' | 'dark' | string     // default: 'light'
  timezone?: string                     // default: 'Etc/UTC'
  watermark?: string | Node
  styleOverrides?: DeepPartial<Styles>
  scriptProvider?: ScriptProvider
  drawingBarVisible?: boolean           // default: false
  showVolume?: boolean                  // default: true
  periodBarVisible?: boolean            // default: true — hide to reclaim toolbar space; per-button CSS via [data-button="<id>"]
  periods?: Period[]
  debug?: boolean                       // default: true — set false to silence non-essential logs

  // Event callbacks
  onSymbolChange?: (symbol: SymbolInfo) => void
  onPeriodChange?: (period: Period) => void
  onVisibleRangeChange?: (range: VisibleTimeRange) => void
  onCrosshairMoved?: (result: PriceTimeResult) => void  // fires on crosshair move
  onSelect?: (result: PriceTimeResult) => void          // fires on chart click (see gotchas — 250ms deferred)
  onRightSelect?: (result: PriceTimeResult) => void     // fires on chart right-click
  onDoubleSelect?: (result: PriceTimeResult) => void    // fires on chart double-click
  onReady?: () => void                                   // fires when chart is fully initialized; getChart() guaranteed after this
}
```

## SuperchartApi (instance methods)

```typescript
setTheme(theme: string): void
getTheme(): string
setStyles(styles: DeepPartial<PaneProperties>): void
getStyles(): DeepPartial<PaneProperties>
setLocale(locale: string): void
getLocale(): string
setTimezone(timezone: string): void
getTimezone(): string
setSymbol(symbol: SymbolInfo): void
getSymbol(): SymbolInfo
setPeriod(period: Period): void
getPeriod(): Period
getChart(): Nullable<Chart>                    // klinecharts Chart instance
resize(): void
getScreenshotUrl(type?: 'png' | 'jpeg', backgroundColor?: string): string
createOverlay(overlay: OverlayCreate & { properties?: DeepPartial<OverlayProperties> }, paneId?: string): string | null
setOverlayMode(mode: OverlayMode): void
getBackendIndicators(): UseBackendIndicatorsReturn | null
openScriptEditor(options?: { initialCode?: string; readOnly?: boolean }): void
closeScriptEditor(): void
setPeriodBarVisible(visible: boolean): void   // show/hide the entire period bar at runtime
createButton(options?: ToolbarButtonOptions): HTMLElement
createDropdown(options: ToolbarDropdownOptions): HTMLElement
onSymbolChange(callback: (symbol: SymbolInfo) => void): () => void   // returns unsubscribe
onPeriodChange(callback: (period: Period) => void): () => void       // returns unsubscribe
onVisibleRangeChange(callback: (range: VisibleTimeRange) => void): () => void  // returns unsubscribe
onCrosshairMoved(callback: (result: PriceTimeResult) => void): () => void      // returns unsubscribe
onSelect(callback: (result: PriceTimeResult) => void): () => void              // returns unsubscribe
onRightSelect(callback: (result: PriceTimeResult) => void): () => void         // returns unsubscribe
onDoubleSelect(callback: (result: PriceTimeResult) => void): () => void        // returns unsubscribe
onReady(callback: () => void): () => void          // fires immediately if already ready; returns unsubscribe
setVisibleRange(range: VisibleTimeRange): void    // scroll/zoom to show {from, to} (unix seconds)
readonly replay: ReplayEngine | null           // null until chart mounts; reading also installs internal error→period-sync
dispose(): void
destroy(): void                                // alias for dispose()
getOptions(): SuperchartOptions
```

## Datafeed Interface

Passed to `createDataLoader(datafeed)`. TradingView-compatible.

```typescript
interface Datafeed {
  onReady(callback: (config: DatafeedConfiguration) => void): void
  searchSymbols(userInput: string, exchange: string, symbolType: string,
    onResult: (results: SearchSymbolResult[]) => void): void
  resolveSymbol(symbolName: string,
    onResolve: (symbolInfo: LibrarySymbolInfo) => void,
    onError: (reason: string) => void): void
  getBars(symbolInfo: LibrarySymbolInfo, resolution: string, periodParams: PeriodParams,
    onResult: (bars: Bar[], meta?: HistoryMetadata) => void,
    onError: (reason: string) => void): void
  subscribeBars(symbolInfo: LibrarySymbolInfo, resolution: string, onTick: (bar: Bar) => void,
    subscriberUID: string, onResetCacheNeeded?: () => void): void
  unsubscribeBars(subscriberUID: string): void

  // Optional — required for replay start-time validation
  getFirstCandleTime?(symbolName: string, resolution: string,
    callback: (timestamp: number | null) => void): void
}
```

## SuperchartDataLoader (returned by createDataLoader)

```typescript
interface SuperchartDataLoader extends DataLoader {
  searchSymbols(userInput: string, exchange: string, symbolType: string,
    onResult: (results: SearchSymbolResult[]) => void): void
  /** DatafeedConfiguration captured from Datafeed.onReady, or null if not yet fired. */
  getConfiguration(): DatafeedConfiguration | null
  setOnBarsLoaded(callback: (fromMs: number) => void): void

  // Internal — used by ReplayEngine. getBars is called with countBack: 0, so
  // your Datafeed.getBars implementation must honour `from` in that path.
  getRange(params: {
    symbol: SymbolInfo, period: Period,
    from: number, to: number,
    callback: (bars: KLineData[]) => void
  }): void

  // Present only if Datafeed.getFirstCandleTime is defined.
  getFirstCandleTime?: (params: {
    symbol: SymbolInfo, period: Period,
    callback: (timestamp: number | null) => void
  }) => void
}
```

## Key Types

### Bar
```typescript
{ time: number /* ms */, open: number, high: number, low: number, close: number, volume?: number }
```

### PeriodParams
```typescript
{ from: number /* seconds */, to: number /* seconds */, countBack: number, firstDataRequest: boolean }
```

### HistoryMetadata
```typescript
{ noData?: boolean, nextTime?: number /* seconds */ }
```

### Period
```typescript
{ type: 'second'|'minute'|'hour'|'day'|'week'|'month'|'year', span: number, text: string }
```

Predefined PERIODS constant:
```
'1s'  → {second,1}   '1m'  → {minute,1}   '3m'  → {minute,3}
'5m'  → {minute,5}   '15m' → {minute,15}  '30m' → {minute,30}
'1h'  → {hour,1}     '2h'  → {hour,2}     '4h'  → {hour,4}
'6h'  → {hour,6}     '12h' → {hour,12}    '1D'  → {day,1}
'3D'  → {day,3}      '1W'  → {week,1}     '1M'  → {month,1}
```

### SymbolInfo
```typescript
{
  ticker: string                 // unique ID
  pricePrecision: number
  volumePrecision: number
  name?: string                  // display name
  shortName?: string
  exchange?: string
  market?: string
  priceCurrency?: string
  logo?: string
}
```

### LibrarySymbolInfo
```typescript
{
  ticker: string, name: string, type?: string, exchange?: string,
  timezone?: string, pricescale: number, minmov?: number,
  has_intraday?: boolean, has_daily?: boolean,
  supported_resolutions?: string[], session?: string,
  logo?: string, currency_code?: string
}
```

### DatafeedConfiguration
```typescript
{ supportedResolutions: string[], exchanges?: {value: string, name: string}[], symbolsTypes?: {name: string, value: string}[] }
```

### VisibleTimeRange
```typescript
{ from: number /* unix seconds */, to: number /* unix seconds */ }
```

### PriceTimeResult
```typescript
{
  coordinate: { x: number; y: number; pageX: number; pageY: number }
  // x/y are pixels on the chart canvas.
  // pageX/pageY are page-relative pixels. Populated for onSelect / onRightSelect /
  // onDoubleSelect (from the originating DOM event). Always 0 for onCrosshairMoved
  // (no native event origin).
  point: { time: number /* unix seconds */, price: number }
}
```
Delivered to `onCrosshairMoved`, `onSelect`, `onRightSelect`, `onDoubleSelect`.
`time` is computed from the crosshair timestamp (or falls back to pixel→data conversion).
`price` is computed via `chart.convertFromPixel` on the `candle_pane`.

### SearchSymbolResult
```typescript
interface SearchSymbolResult {
  symbol: string          // internal ticker ID
  full_name: string       // display name (e.g. "BTC/USDT")
  description?: string    // human-readable (e.g. "Bitcoin / Tether")
  exchange?: string
  type?: string           // "crypto" | "forex" | "stock" | ...
  logo?: string           // symbol logo URL
  exchange_logo?: string  // exchange logo URL
}
```

### ToolbarButtonOptions
```typescript
{ align?: 'left'|'right' /* default: 'right' */, icon?: string /* SVG/HTML */, text?: string,
  tooltip?: string, onClick?: () => void }
```

### ToolbarDropdownOptions
```typescript
{ align?: 'left'|'right', icon?: string, text?: string, tooltip?: string,
  items: ToolbarDropdownItem[] /* required */ }
```

### ToolbarDropdownItem
```typescript
// Union:
{ type?: 'item', text: string, icon?: string, onClick: () => void }  // clickable item
{ type: 'separator' }                                                  // visual separator
```

### Period Bar Button IDs

Each built-in period-bar element has a `data-button` attribute for targeted CSS
hiding/disabling without removing the whole bar. Custom buttons added via
`createButton` do NOT get `data-button` — style those via the returned `HTMLElement`.

| `data-button` value  | Element                        |
|----------------------|--------------------------------|
| `leftToolbarToggle`  | Left toolbar expand/collapse   |
| `symbolSearch`       | Symbol name / search trigger   |
| `periodPicker`       | Period (timeframe) picker      |
| `indicators`         | Indicators modal button        |
| `timezone`           | Timezone selector              |
| `settings`           | Chart settings button          |
| `screenshot`         | Screenshot button              |
| `fullscreen`         | Fullscreen toggle              |

### TimeframeVisibility
```typescript
{ showOnAll: boolean, rules: Record<PeriodCategory, TimeframeVisibilityRule> }
// PeriodCategory = 'second'|'minute'|'hour'|'day'|'week'|'month'
// TimeframeVisibilityRule = { enabled: boolean, from: number, to: number }
```

### StorageAdapter
```typescript
{
  save(key: string, state: ChartState): Promise<void>
  load(key: string): Promise<ChartState | null>
  delete(key: string): Promise<void>
  list?(prefix?: string): Promise<string[]>
}
```

### ChartState
```typescript
{
  version: number, indicators: SavedIndicator[], overlays: SavedOverlay[],
  styles: DeepPartial<Styles>, paneLayout: PaneLayout[],
  preferences: ChartPreferences, savedAt?: number, symbol?: string, period?: string,
  overlayDefaults?: Record<string, DeepPartial<OverlayProperties>>
}
```

### ChartPreferences
```typescript
{
  showVolume: boolean, showCrosshair: boolean, showGrid: boolean,
  showLegend: boolean, magnetMode: 'normal'|'weak'|'strong',
  timezone?: string, locale?: string
}
```

### OverlayProperties
```typescript
{ style, text, textColor, textFont, textFontSize, textFontWeight, textBackgroundColor,
  textPaddingLeft/Right/Top/Bottom, lineColor, lineWidth, lineStyle, lineLength,
  lineDashedValue, tooltip, backgroundColor, borderStyle, borderColor, borderWidth }
```

### IndicatorProvider
```typescript
{ getAvailableIndicators(), subscribe(params), updateSettings(id, settings),
  unsubscribe(id), onSymbolPeriodChange?(symbol, period, active), dispose?() }
```

### createOrderLine

```typescript
function createOrderLine(chart: Chart, options?: Partial<OrderLineProperties>): OrderLine
```

Creates a horizontal price-level overlay with body, quantity, and cancel button sections.
Returns a TradingView-compatible fluent API with getter/setter pairs.

Three sections rendered left-to-right: **body** (draggable label), **quantity** (click → onModify), **cancelButton** (click → onCancel). Each independently toggleable via visibility setters. Hidden sections leave no gap.

### OrderLine (fluent API)

All setters return `this` for chaining. Readonly: `id`, `paneId`.

```typescript
// Core data
getPrice/setPrice(price: number)
getText/setText(text: string)
getQuantity/setQuantity(quantity: number | string)
getTooltip/setTooltip(tooltip: string)
getModifyTooltip/setModifyTooltip(tooltip: string)
getCancelTooltip/setCancelTooltip(tooltip: string)

// Behavior
getEditable/setEditable(editable: boolean)       // default: true (draggable)
getExtendLeft/setExtendLeft(extend: boolean)     // extend line left of labels (default: true)
getExtendRight/setExtendRight(extend: boolean)   // extend line right of labels (default: true)

// Layout
setAlign(align: 'left' | 'right')
setMarginLeft(margin: number)
setMarginRight(margin: number)

// Line styling
getLineColor/setLineColor(color: string)
getLineWidth/setLineWidth(width: number)
getLineStyle/setLineStyle(style: 'solid' | 'dashed')
setLineDashedValue(dashedValue: number[])
getLineLength/setLineLength(length: number)

// Body label
getBodyFont/setBodyFont(font: string)
setBodyFontWeight(weight: number | string)
getBodyTextColor/setBodyTextColor(color: string)
getBodyBackgroundColor/setBodyBackgroundColor(color: string)
getBodyBorderColor/setBodyBorderColor(color: string)

// Quantity label
getQuantityFont/setQuantityFont(font: string)
setQuantityFontWeight(weight: number | string)
getQuantityTextColor/setQuantityTextColor(color: string)
getQuantityBackgroundColor/setQuantityBackgroundColor(color: string)
getQuantityBorderColor/setQuantityBorderColor(color: string)

// Cancel button
getCancelButtonIconColor/setCancelButtonIconColor(color: string)
getCancelButtonBackgroundColor/setCancelButtonBackgroundColor(color: string)
getCancelButtonBorderColor/setCancelButtonBorderColor(color: string)

// Y-axis label styling
getYAxisLabelTextColor/setYAxisLabelTextColor(color: string)
getYAxisLabelBackgroundColor/setYAxisLabelBackgroundColor(color: string)
getYAxisLabelBorderColor/setYAxisLabelBorderColor(color: string)
setYAxisLabelBorderSize(size: number)

// Shared border
setBorderStyle(style: 'solid' | 'dashed')
setBorderSize(size: number)
setBorderRadius(radius: number)

// Visibility
setBodyVisible(visible: boolean)
setQuantityVisible(visible: boolean)
setCancelButtonVisible(visible: boolean)

// Events (generic T for consumer data)
onMoveStart<T>(params: T, callback: (params: T, event?) => void)
onMove<T>(params: T, callback: (params: T, event?) => void)
onMoveEnd<T>(params: T, callback: (params: T, event?) => void)  // Only fires if user actually dragged (not on simple click)
onCancel<T>(params: T, callback: (params: T, event?) => void)
onModify<T>(params: T, callback: (params: T, event?) => void)

// Lifecycle
getProperties(): OrderLineProperties
remove(): void
```

### OrderLineProperties

```typescript
{
  price?: number
  text?: string
  quantity?: number | string
  tooltip?: string
  modifyTooltip?: string
  cancelTooltip?: string

  // Layout
  align?: 'left' | 'right'
  marginRight?: number
  marginLeft?: number

  // Behavior
  editable?: boolean          // default: true (draggable)
  extendLeft?: boolean        // extend line left of labels (default: true)
  extendRight?: boolean       // extend line right of labels (default: true)

  // Line
  lineColor?: string
  lineWidth?: number
  lineStyle?: 'solid' | 'dashed'
  lineDashedValue?: number[]
  lineLength?: number

  // Body label
  bodyFont?: string, bodyFontSize?: number, bodyFontWeight?: number | string
  bodyTextColor?: string, bodyBackgroundColor?: string, bodyBorderColor?: string
  bodyPaddingLeft/Right/Top/Bottom?: number
  isBodyVisible?: boolean

  // Quantity label
  quantityFont?: string, quantityFontSize?: number, quantityFontWeight?: number | string
  quantityTextColor?: string, quantityBackgroundColor?: string, quantityBorderColor?: string
  quantityPaddingLeft/Right/Top/Bottom?: number
  isQuantityVisible?: boolean

  // Cancel button
  cancelButtonFontSize?: number, cancelButtonFontWeight?: number | string
  cancelButtonIconColor?: string, cancelButtonBackgroundColor?: string, cancelButtonBorderColor?: string
  cancelButtonPaddingLeft/Right/Top/Bottom?: number
  isCancelButtonVisible?: boolean

  // Y-axis label styling
  yAxisLabelTextColor?: string
  yAxisLabelBackgroundColor?: string
  yAxisLabelBorderColor?: string
  yAxisLabelBorderSize?: number

  // Shared border
  borderStyle?: 'solid' | 'dashed'
  borderSize?: number
  borderDashedValue?: number[]
  borderRadius?: number          // default: 0

  // Events
  onMoveStart?: OrderLineEventListener
  onMove?: OrderLineEventListener
  onMoveEnd?: OrderLineEventListener
  onCancel?: OrderLineEventListener
  onModify?: OrderLineEventListener
}

interface OrderLineEventListener {
  params: unknown
  callback: (params: unknown, event?: OverlayEvent) => void
}
```

### PriceLine (via `createPriceLine(chart, options?)`)
Chainable setters (each returns PriceLine): `setPrice`, `setText`,
`setLabelVisible`, `setEditable`,
`setLineColor`, `setLineWidth`, `setLineStyle`, `setLineDashedValue`,
`setLabelFont`, `setLabelFontSize`, `setLabelFontWeight`, `setLabelTextColor`,
`setLabelBackgroundColor`, `setLabelBorderColor`, `setLabelBorderStyle`,
`setLabelBorderSize`, `setLabelBorderRadius`, `setLabelPadding`,
`setLabelPosition`, `setLabelAlign`, `setLabelOffsetX`, `setLabelOffsetY`, `setLabelOffsetPercentX`,
`setYAxisLabelVisible`, `setYAxisLabelTextColor`, `setYAxisLabelBackgroundColor`, `setYAxisLabelBorderColor`.
Events: `onMoveStart`, `onMove`, `onMoveEnd` — each takes `(params, cb)`.
Other: `getProperties(): PriceLineProperties`, `remove(): void`.
Properties: `id` (readonly), `paneId` (readonly).

### TradeLine (via `createTradeLine(chart, options?)`)

Creates an arrow marker at a specific price point on a candle. Used for trade markers.

```typescript
type TradeLineOptions = Partial<TradeLineProperties> & {
  onRightClick?: OverlayEventCallback<unknown>  // fires on right-click on the marker
}

function createTradeLine(chart: Chart, options?: TradeLineOptions): TradeLine
```

`onRightClick` was added in SC `42d90ae`. The engine's built-in right-click-delete
on trade lines is `preventDefault`-ed internally so consumer trade lines are not
deleted by a right-click.

Chainable setters (each returns TradeLine): `setTimestamp`, `setPrice`, `setDirection` (`'up'`|`'down'`),
`setText`, `setColor`, `setTextColor`, `setTextBackgroundColor`, `setTextFontSize`,
`setArrowType` (`'wide'`|`'tiny'`), `setShowLabelArrow`.
Other: `getProperties(): TradeLineProperties`, `remove(): void`.
Properties: `id` (readonly), `paneId` (readonly).

**Arrow positioning**: The main arrow tip is at the exact price point (`price` prop).
Buy (`up`): tip at price, body extends downward. Sell (`down`): tip at price, body extends
upward. Label arrow and text are positioned beyond the main arrow base (away from price),
not relative to candle wick/body.

## klinecharts Chart API (via `getChart()`)

```typescript
// Data
getDataList(mutateToCandleType?: boolean): KLineData[]
resetData(): void
setDataLoader(dataLoader: DataLoader): void

// Display
getVisibleRange(): VisibleRange  // { from, to, realFrom, realTo } — data indices
getVisibleRangeTimestamps(): Nullable<{ from: number, to: number }>  // timestamps (ms) of first/last visible bars
setBarSpace(space: number): void
getBarSpace(): BarSpace
setOffsetRightDistance(distance: number): void
resize(): void

// Navigation
scrollByDistance(distance: number, animationDuration?: number): void
scrollToRealTime(animationDuration?: number): void
scrollToDataIndex(dataIndex: number, animationDuration?: number): void
scrollToTimestamp(timestamp: number, animationDuration?: number): void
zoomAtCoordinate(scale: number, coordinate?: Coordinate, animationDuration?: number): void

// Indicators
createIndicator(value: string | IndicatorCreate, isStack?: boolean, paneOptions?: PaneOptions): Nullable<string>
getIndicators(filter?: IndicatorFilter): Indicator[]
overrideIndicator(override: IndicatorCreate): boolean
removeIndicator(filter?: IndicatorFilter): boolean

// Overlays
createOverlay(value: string | OverlayCreate | Array<...>): Nullable<string> | Array<Nullable<string>>
getOverlays(filter?: OverlayFilter): Overlay[]
overrideOverlay(override: Partial<OverlayCreate>): boolean
removeOverlay(filter?: OverlayFilter): boolean
// Built-in overlay names:
//   Lines: horizontalStraightLine, horizontalRayLine, horizontalSegment, priceLine,
//     verticalStraightLine, verticalRayLine, verticalSegment, straightLine, rayLine,
//     segment, parallelStraightLine, priceChannelLine, fibonacciLine
//   Annotations: simpleAnnotation (upward arrow+text at point), simpleTag, freePath
//   Shapes (pro): arrow, circle, rect, triangle, parallelogram, brush
//   Fibonacci (pro): fibonacciCircle, fibonacciSegment, fibonacciSpiral,
//     fibonacciSpeedResistanceFan, fibonacciExtension
//   Waves (pro): threeWaves, fiveWaves, eightWaves, anyWaves
//   Harmonic (pro): abcd, xabcd
//   Other (pro): gannBox, orderLine
//   Generic primitives (pro): priceLevelLine, timeLine, styledSegment, box
// OverlayCreate: { name, points: [{timestamp, value}], styles?, extendData?, lock?, visible?, ... }

// Coordinate conversion
convertToPixel(points, filter?): Partial<Coordinate> | Array<...>
convertFromPixel(coordinates, filter?): Partial<Point> | Array<...>

// Actions
subscribeAction(type: ActionType, callback): void
unsubscribeAction(type: ActionType, callback?): void
// ActionType: 'onZoom' | 'onScroll' | 'onVisibleRangeChange' | 'onCandleTooltipFeatureClick'
//           | 'onIndicatorTooltipFeatureClick' | 'onCrosshairFeatureClick' | 'onCrosshairChange'
//           | 'onCandleBarClick' | 'onChartClick' | 'onChartRightClick' | 'onChartDoubleClick' | 'onPaneDrag'
// onChartClick / onChartRightClick / onChartDoubleClick only fire on MAIN widget clicks
// that were NOT consumed by an overlay. Payload: { x, y, timestamp, ...crosshair }

// Style & config
setStyles(value: string | DeepPartial<Styles>): void
getStyles(): Styles
setSymbol(symbol): void
setPeriod(period): void
setZoomEnabled(enabled: boolean): void
setScrollEnabled(enabled: boolean): void

// Export
getConvertPictureUrl(includeOverlay?: boolean, type?: 'png'|'jpeg'|'bmp', bg?: string): string
```

## Resolution ↔ Period Conversion

NOT exported from main package. Implemented locally in `helpers.js`.

```
Period → Resolution:
  second → "${span}S"     minute → "${span}" (plain number)
  hour → "${span*60}"     day → "${span}D"
  week → "${span}W"       month → "${span}M"

Resolution → Period:
  "1"=1min  "5"=5min  "60"=1hr  "240"=4hr  "1D"=1day  "1W"=1week  "1M"=1month
```

## Timestamp Conventions

| Context | Format |
|---------|--------|
| Bar.time | milliseconds |
| KLineData.timestamp | milliseconds |
| PeriodParams.from/to | seconds |
| HistoryMetadata.nextTime | seconds |
| VisibleTimeRange.from/to | seconds |

## New Built-in Overlay Types

Registered by coinray-chart. Use via `chart.createOverlay({name: "...", ...})`.
Properties are passed via `extendData` on the overlay (so they can be updated at runtime
without re-registering the template). All four generic primitives below expose
`ignoreEvent?: boolean` (default `true`) — set `false` to make the overlay pick up mouse/
touch events (select, drag, right-click menu).

These four overlays replaced the previous purpose-built `breakEvenLine`, `timeAlertLine`,
and `trendlineAlertLine` templates (removed in coinray-chart `main`). Consumers compose
alert visuals by styling these generic primitives and passing `extendData` at create time.

### priceLevelLine
Horizontal price line split into two segments with a plain text label in the gap (no
background/border on text). Includes a customizable Y-axis price badge.

```typescript
interface PriceLevelLineProperties {
  price?: number
  text?: string                             // default: ''
  textColor?: string                        // default: '#D05DDF'
  textFontSize?: number                     // default: 12
  textFont?: string                         // default: 'Helvetica Neue'
  textGap?: number                          // default: 6 (px gap around text)
  lineColor?: string                        // default: '#D05DDF'
  lineWidth?: number                        // default: 1
  lineStyle?: 'solid' | 'dashed'            // default: 'solid'
  lineDashedValue?: number[]                // default: [4, 4]
  textPositionPercent?: number              // default: 50 (0–100 along the line)
  textAlign?: 'left' | 'center' | 'right'   // shorthand for textPositionPercent (5/50/95)
  yAxisLabelVisible?: boolean               // default: true
  yAxisLabelBackgroundColor?: string        // falls back to lineColor
  yAxisLabelTextColor?: string              // default: '#FFFFFF'
  yAxisLabelBorderColor?: string            // falls back to yAxisLabelBackgroundColor
  ignoreEvent?: boolean                     // default: true
}
```

Usage: 1 point (price level). `totalStep: 2`. Generic replacement for the old `breakEvenLine`.

### timeLine
Vertical line split into two segments with rotated (-90°) text label in the gap.

```typescript
interface TimeLineProperties {
  lineColor?: string               // default: '#3ea6ff'
  lineWidth?: number               // default: 1
  lineStyle?: 'solid' | 'dashed'   // default: 'solid'
  lineDashedValue?: number[]       // default: [4, 4]
  text?: string                    // default: '' (no text = single full line)
  textColor?: string               // default: '#3ea6ff'
  textFontSize?: number            // default: 12
  textFont?: string                // default: 'Helvetica Neue'
  textGap?: number                 // default: 4
  ignoreEvent?: boolean            // default: true
}
```

Usage: 1 point (timestamp). `totalStep: 2`. Has X-axis label. Generic replacement for the
old `timeAlertLine`.

### styledSegment
Two-point segment line with optional text label rotated to match the line's angle,
offset perpendicular from the line midpoint.

```typescript
interface StyledSegmentProperties {
  lineColor?: string               // default: '#3ea6ff'
  lineWidth?: number               // default: 1
  lineStyle?: 'solid' | 'dashed'   // default: 'solid'
  lineDashedValue?: number[]       // default: [4, 4]
  text?: string                    // default: '' (no text)
  textColor?: string               // default: '#3ea6ff'
  textFontSize?: number            // default: 12
  textFont?: string                // default: 'Helvetica Neue'
  textOffset?: number              // default: 12 (perpendicular px offset from line)
  ignoreEvent?: boolean            // default: true
}
```

Usage: 2 points. `totalStep: 3`. Generic replacement for the old `trendlineAlertLine`.

### box
Filled rectangle defined by two corner points (rendered as a polygon).

```typescript
interface BoxProperties {
  backgroundColor?: string         // default: 'rgba(33,150,243,0.15)'
  ignoreEvent?: boolean            // default: true
}
```

Usage: 2 points (opposite corners). `totalStep: 3`. Right-click inside a non-ignored box
calls `event.preventDefault()` to suppress the native context menu.

### emojiMarker (storybook only)
Single emoji at a point. Properties via `extendData`: `text` (emoji), `fontSize`, `color`.
**Note:** This overlay is only in storybook helpers, not registered in coinray-chart.

**Storybook helpers** (`overlay-stories/overlays/`) wrap the generic primitives with
convenience builders (e.g. `alerts.ts`, `break-even.ts`, `price-time-select.ts`). These
are NOT exported from the library. In Altrady, call `chart.createOverlay()` directly and
pass the visual configuration via `extendData`.

## New Built-in Figures

### rotatedText
Draws text rotated by a given angle. Used internally by `timeLine` and `styledSegment`.

```typescript
interface RotatedTextAttrs {
  x: number
  y: number
  text: string
  angle?: number                   // radians, default: 0. Use -Math.PI/2 for vertical
  align?: CanvasTextAlign
  baseline?: CanvasTextBaseline
}
// Styles: Partial<TextStyle> — color, size, family, weight
```

## Built-in Screenshot Feature

SC has a built-in screenshot button in the toolbar (PeriodBar) and a `Ctrl+P` / `Cmd+P` keyboard shortcut.

### Flow
1. Button click → `onScreenshotClick` in `SuperchartComponent.tsx:499`
2. Calls `chart.getConvertPictureUrl(true, 'jpeg', backgroundColor)` (klinecharts API)
3. Sets `screenshotUrl` signal in `chartStore.ts`
4. Renders `ScreenshotModal` — shows image + "Save" button (downloads as file)

### Key files
| Component | File |
|-----------|------|
| Button | `src/lib/widget/period-bar/index.tsx` (line ~232) |
| Click handler | `src/lib/components/SuperchartComponent.tsx` (line ~499) |
| Modal | `src/lib/widget/screenshot-modal/index.tsx` |
| Keyboard shortcut | `src/lib/store/keyEventStore.ts` (line ~211, `case 'p'`) |
| Store signal | `src/lib/store/chartStore.ts` (`screenshotUrl` signal) |

### Customization: none
No constructor option, callback, or event to disable, hide, or override the screenshot button or its behavior. The button is hardcoded in the toolbar. Image format is hardcoded to JPEG in the UI (though `getScreenshotUrl` API accepts `'png' | 'jpeg'`). Background color is auto-selected from theme (`#151517` dark, `#ffffff` light).

### Override approach
To replace the built-in screenshot behavior with custom logic (e.g., upload + share modal), the SC library needs a new option. Possible API additions:
- `onScreenshot?: (url: string) => void` callback in `SuperchartOptions` — if provided, called instead of opening the built-in modal
- `disableScreenshot?: boolean` in `SuperchartOptions` — hides the button so consumer can add their own via `createButton`

## Known Limitations

- **Global singleton store** — `chartStore.ts` uses module-level signals. Two simultaneous `Superchart` instances share all state (`instanceApi`, `symbol`, `period`, etc.). The second instance overwrites the first. Multi-instance support requires per-instance stores. Reported to SC dev with reproduction story (`API/MultiChart`).
- **PriceLine `editable: false` not working** — `createPriceLine` does not respect `editable: false`. Lines remain draggable. Reported to SC dev.
- **Screenshot button not customizable** — No way to override or disable the built-in screenshot button/modal. Need `onScreenshot` callback or `disableScreenshot` option for Altrady's share-modal integration.

## Replay Engine

Access via `sc.replay`. Returns `ReplayEngine | null` — `null` until the chart mounts
(same timing as `getChart()`). Reading `sc.replay` also installs an internal
error→period-sync handler on the engine (idempotent). Full upstream reference:
`$SUPERCHART_DIR/docs/replay.md`.

### ReplayEngine interface

```typescript
export interface ReplayEngine {
  // Session control
  setCurrentTime(timestamp: number | null, endTime?: number | null): Promise<void>
  // timestamp — Unix ms cursor. `null` exits replay and resumes live mode.
  // endTime   — optional upper bound (defaults to Date.now() at call time).

  // Playback
  play(speed?: number): void          // candles/sec; omit to keep current speed (initial: 1)
  pause(): void
  step(): void                        // advance one candle forward
  stepBack(): Promise<void>           // remove last candle (may fetch sub-resolution data)
  playUntil(timestamp: number, speed?: number): void  // play then auto-pause at timestamp

  // Getters
  getReplayStatus(): ReplayStatus
  getReplayCurrentTime(): number | null   // Unix ms close-time of last visible candle
  getReplayEndTime(): number | null       // upper bound captured at session start
  getReplayBufferLength(): number         // remaining candles in forward buffer

  // Subscriptions (each returns an unsubscribe function)
  onReplayStatusChange(callback: (status: ReplayStatus) => void): () => void
  onReplayStep(callback: (candle: KLineData, direction: 'forward' | 'back') => void): () => void
  onReplayError(callback: (error: { type: string; detail?: unknown }) => void): () => void
}
```

### ReplayStatus

```typescript
type ReplayStatus = 'idle' | 'loading' | 'ready' | 'playing' | 'paused' | 'finished'
```

State machine: `idle → loading → ready → playing ⇄ paused → finished`. Any state →
`idle` on `setCurrentTime(null)` or on `sc.setSymbol(...)`.

### onReplayError types

| `type` | When |
|---|---|
| `unsupported_resolution` | Second-resolution period, or period change returned no data |
| `no_data_at_time` | Cursor before datafeed's first available candle |
| `resolution_change_failed` | `handlePeriodChange` threw; session auto-reverted to prior period |
| `partial_construction_failed` | Boundary `stepBack` could not build a partial candle (no sub-resolution data) |

### Period changes during replay

Call `sc.setPeriod(newPeriod)` as usual — replay intercepts it internally and rebuilds
its buffer. On failure, the engine emits `resolution_change_failed` and reverts;
Superchart auto-syncs its own store. External period state (Redux, URL, etc.) must be
resynced by the consumer — subscribe to `onReplayError` and read
`sc.getChart()?.getPeriod()` when `resolution_change_failed` fires.

### Symbol changes during replay

`sc.setSymbol(newSymbol)` automatically exits replay first (status → `idle`). No
manual `setCurrentTime(null)` is required.

### Datafeed prerequisites for replay

| Requirement | Purpose |
|---|---|
| `Datafeed.getBars` must honour `from` when `countBack === 0` | `SuperchartDataLoader.getRange` (replay's only data-fetch path) always passes `countBack: 0`. A `getBars` that derives `from` from `countBack` will return wrong data here. |
| `Datafeed.getFirstCandleTime?` (optional) | Validates the cursor timestamp against data availability. Without it, cursors before data silently yield an empty chart instead of `no_data_at_time`. |

Append to the Type Glossary table:

| `ReplayEngine` | superchart / klinecharts | Replay playback controller (`sc.replay`) |
| `ReplayStatus` | superchart / klinecharts | `'idle' \| 'loading' \| 'ready' \| 'playing' \| 'paused' \| 'finished'` |
