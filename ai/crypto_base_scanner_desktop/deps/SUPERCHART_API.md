# Superchart API Reference

> Source: `$SUPERCHART_DIR` (branch: main)
> Superchart git hash: `4bd96aaf2c69b7badbca0e9f93bc4d571e1080c6`
> coinray-chart (`packages/coinray-chart`, branch: main) git hash: `52332cebd7f8e1f06983a00544258057020cce98`
> Hashes verified current: 2026-08-18.
> Do NOT explore source — use this doc instead.

## Package name & version

- Package was renamed `superchart` → `@coinrayio/superchart` in SC `474f052`.
- Current published version: `0.1.0` (was `0.0.1`).
- Distribution: GitHub Packages (`https://npm.pkg.github.com/`), scoped + restricted.
  See `$SUPERCHART_DIR/docs/versioning-and-release.md` for the publish flow.
- **Stylesheet subpaths (updated in the design-system range `4bd96aaf`).**
  ```json
  "exports": {
    "./styles":  { "types": "./dist-enterprise/styles.d.ts", "default": "./dist-enterprise/superchart.css" },
    "./ui.css":  "./dist-enterprise/superchart-ui.css"      // NEW — design-system component CSS, standalone
  }
  ```
  `./styles` is unchanged as an import string but its *contents* changed: it is
  now the DS token/utility layer concatenated with the legacy LESS output (DS
  first — the order is load-bearing for `@layer` precedence). `./ui.css` is the
  DS-only sheet; **do not load it alongside `./styles`**. See
  `SUPERCHART_USAGE.md` → "Design-system migration" for the required
  Font Awesome import.
- **Two editions (new in `24e6fb8`).** SC now ships as two separate packages
  built from a single source tree:
  - `@coinrayio/superchart` (community) — built into `dist-community/`,
    watermark locked to the bundled Altrady badge; the `brand` constructor
    option is stripped from the type and ignored at runtime.
  - `@coinrayio/superchart-enterprise` (enterprise) — built into
    `dist-enterprise/`, exposes the `brand` option and respects it at
    runtime.

  The runtime bundles share the same implementation; the split is a
  combination of build-time `__SUPERCHART_EDITION__` define (Vite) and
  edition-specific TypeScript entry files (`src/lib/community.ts`,
  `src/lib/enterprise.ts`). The root `package.json` `main`/`module`/`types`/
  `exports` point at `dist-enterprise/` — so consuming the repo directly
  (link or git URL) always gets the enterprise edition.
- **App-side note:** `crypto_base_scanner_desktop/package.json` still pins
  `"superchart": "link:../Superchart"`. The local symlink resolves to
  `dist-enterprise/` via the root `package.json` entry fields, so the app
  gets the enterprise edition (with `brand` available). Imports continue to
  use `from "superchart"`.
- **`SuperchartOptions` is NOT exported from `src/lib/index.ts`** — each
  edition entry exports its own variant:
  - community: `type SuperchartOptions = Omit<FullOptions, 'brand'>`
  - enterprise: re-exports the full `SuperchartOptions` (with `brand`)
  Via the local symlink the app always pulls the enterprise variant.
- Examples in this doc keep the `from "superchart"` form for that reason —
  when reading the SC source / docs (`@coinrayio/superchart`), substitute
  mentally.

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

## Branding / Watermark (new in `24e6fb8`)

A bottom-left watermark badge is auto-rendered by every `Superchart`
instance (`position: absolute; bottom: 12px; left: 12px;`). It always
renders — there is no off-by-default mode.

```typescript
// Hide watermark entirely (enterprise only)
new Superchart({ ..., brand: false })

// Override with a custom mark (enterprise only)
new Superchart({
  ...,
  brand: {
    logo?: string | ReactNode   // raw SVG string, URL/data-URI, or ReactNode
    name?: string               // text rendered next to the logo
    url?: string                // when present, badge is a clickable <a>
  }
})

// Omit `brand` entirely → default Altrady badge
//   logo: inlined `altrady-symbol.svg`
//   name: "Superchart"
//   url:  "https://altrady.com/superchart"
```

**Community vs enterprise runtime.** The `Watermark` component checks
`__SUPERCHART_EDITION__ === 'enterprise'` (build-time replacement, then
dead-code-eliminated). In the community build, any `brand` value passed
at runtime — even from JS bypassing the type — is ignored; the bundled
Altrady badge always shows. In the enterprise build, `brand` is
respected. The app gets enterprise via the symlink, so `brand: false`
works today.

**CSS overrides.** Visual styling lives in `src/lib/branding/Watermark.less`
and exposes CSS custom properties (e.g. `--superchart-brand-color`,
`--superchart-brand-background`). Theme/host CSS can override these
without touching the component.

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

// setVisibleRange / resetView errors (new in 12e80de)
SetVisibleRangeError    — error class thrown by setVisibleRange / resetView
SetVisibleRangeErrorCode — 'no_data_at_time' | 'unsupported_resolution' | 'aborted'
isSetVisibleRangeError  — type guard: (e: unknown) => e is SetVisibleRangeError

// Storage utilities (new in 8c245a1)
LocalStorageAdapter     — Bundled localStorage-backed StorageAdapter
HttpStorageAdapter      — Bundled HTTP-backed StorageAdapter
StorageConflictError    — Thrown by adapters on optimistic-concurrency conflict
CHART_STATE_VERSION     — Current schema version constant (number)
createEmptyChartState   — () => ChartState
migrateChartState       — (unknown) => ChartState | null
mergeChartStates        — (local, remote: ChartState) => ChartState

// Templates (new in 8c245a1)
SYSTEM_STUDY_TEMPLATES  — Read-only bundled study template presets (5 entries)
SYSTEM_DRAWING_TEMPLATES — Read-only bundled drawing template presets (4 entries)

// Feature flags (new in 8c245a1)
FEATURE_DEFAULTS        — Record<FeatureFlag, boolean> — all flags with their defaults
useFeature              — React hook: useFeature(flag: FeatureFlag): boolean

// Fibonacci-level constants (new in 0bb516b — values, not types)
FIBONACCI_RETRACEMENT_LEVELS
FIBONACCI_EXTENSION_LEVELS
FIBONACCI_CIRCLE_LEVELS
FIBONACCI_FAN_LEVELS
// NOT exported: FIBONACCI_CHANNEL_LEVELS (new in coinray-chart 174b3244) — the default level
// set `fibonacciLine` (Fibonacci Channel) now uses internally, replacing FIBONACCI_RETRACEMENT_LEVELS.
// It exists in the engine but SC's barrel (src/lib/index.ts) was not updated to re-export it,
// so `import { FIBONACCI_CHANNEL_LEVELS } from "superchart"` FAILS. SC API gap — ask upstream if needed.
// FIBONACCI_CIRCLE_LEVELS / FIBONACCI_FAN_LEVELS are still exported but SC no longer uses them
// internally (circle + fan moved to bespoke Style tabs) — stale but harmless, still importable.
//
// The default level sets were reworked in 174b3244: levels now carry a per-level `color`, and
// 1.618 / 2.618 / 3.618 are ENABLED by default (previously disabled). The FigureLevel schema is
// unchanged — only the default values. New fib overlays therefore render with more levels and
// different colours than before unless you pass your own `figureLevels`.

// Library version (new in 17dc259)
version                 — () => string, returns bundled SC version (e.g. "0.1.0")
VERSION                 — string constant, same value as version()

// Edition (new in 24e6fb8)
edition                 — () => 'community' | 'enterprise'
EDITION                 — string constant, same value as edition()

// Branding types (new in 24e6fb8) — enterprise edition only
BrandConfig             — { logo?: string | ReactNode; name?: string; url?: string }
BrandOption             — BrandConfig | false   // false hides watermark entirely

// Overlay context-menu helpers (new in 8ea9d2c / 6d68fbb)
ExtractedDrawingTemplate — { toolName: string; template: DrawingTemplate } — returned by sc.getDrawingTemplate(id)
```

`Superchart.version()` is also exposed as a TradingView-style static
method on the class — handy from the browser console
(`window.Superchart.version()` if you've parked the constructor on
`window`, or import it). All three (static method, function, constant)
are interchangeable; the value is replaced at build time from
`package.json` via Vite `define` (`__SUPERCHART_VERSION__`).

`Superchart.edition()` mirrors this pattern (static method + `edition()`
function + `EDITION` constant). Value is replaced at build time via
Vite `define` (`__SUPERCHART_EDITION__`). For the symlinked app, this
returns `"enterprise"`. The welcome banner also appends " Enterprise"
to its console message when running the enterprise build.

> **Welcome banner side-effect.** Constructing the first `Superchart`
> instance on a page logs a one-time dashed-border banner to the
> console with the bundled version. Subsequent instances are silent.
> Survives HMR (the flag lives on the module scope). Not gated by
> `NODE_ENV` — appears in prod too. Cannot be disabled; if it ever
> becomes a problem, the upstream change is in `src/lib/version.ts`
> (`bannerPrinted` flag).

> **klinecharts is bundled (since `0bb516b`).** It moved from `dependencies` to
> `devDependencies` in SC and is excluded from `rollupOptions.external` in
> `vite.config.ts`, so it ships inside `dist/superchart.{es,cjs}.js`. Consumers
> **must not** install klinecharts and **must not** `import … from 'klinecharts'`
> — everything (types, `registerOverlay` / `registerFigure` / `registerIndicator`,
> constants) is re-exported from `superchart`. Importing from klinecharts directly
> would target a different engine instance than the one SC's overlays were
> registered against.

Also re-exports klinecharts core types: `Chart`, `Nullable`, `DeepPartial`, `KLineData`,
`Point`, `Styles`, `Overlay`, `OverlayCreate`, `OverlayEvent`, `OverlayTemplate`, `Indicator`,
`IndicatorCreate`, `IndicatorTemplate`, `FigureTemplate`, `ReplayEngine`, `ReplayStatus`.

Additional klinecharts re-exports (new in `0bb516b`):
`OverlayMode`, `OverlayDrawingMode`, `OverlayTextChangeEvent`, `OverlayTextChangeCallback`,
`OverlayPropertiesStore`, `FigureLevel`, `IndicatorSeries`, `ActionType`,
`LineType`, `PolygonType`, `CandleType`, `TooltipShowRule`, `TooltipShowType`,
`FeatureType`, `TooltipFeaturePosition`, `CandleTooltipRectPosition`,
`FormatDateType`, `BarSpaceLimit`, `ZoomAnchor`, `DomPosition`.

Also re-exports Superchart-specific types: `SuperchartOptions`, `SuperchartApi`, `VisibleTimeRange`,
`PriceTimeResult`, `ToolbarButtonOptions`, `ToolbarDropdownOptions`, `ToolbarDropdownItem`,
`ToolbarDropdownActionItem`, `ToolbarDropdownSeparator`, `Period`, `SymbolInfo`,
`StorageAdapter`, `ChartState`, `StorageRecord`, `StorageWriteResult`, `StorageEntry`,
`StudyTemplate`, `StudyTemplateMeta`, `DrawingTemplate`, `DrawingTemplateMeta`,
`ChartTemplate`, `ChartTemplateMeta`,
`SavedIndicator`, `ChartPreferences`,
`IndicatorProvider`, `OverlayProperties`, `Datafeed`,
`Bar`, `PeriodParams`, `HistoryMetadata`, `OrderLine`, `OrderLineProperties`,
`PriceLine`, `PriceLineProperties`, `PriceLineEventListener`,
`TradeLine`, `TradeLineProperties`,
`ScriptProvider`, `PaneProperties`, `SuperchartDataLoader`, `LibrarySymbolInfo`,
`FeatureFlag`,
`LocalStorageAdapterOptions`, `HttpStorageAdapterOptions`,
`ToolbarButtonOptions`, `ToolbarDropdownOptions`, `ToolbarDropdownItem`,
`ToolbarDropdownActionItem`, `ToolbarDropdownSeparator`,
`BrandConfig`, `BrandOption`.
`ExtractedDrawingTemplate`.

Alerts/events exports (new in `de73a0a` / `a523ceb`):
`Alert` (from `./store/chartStore`), `ChartEvent`, `ChartEventType` (from `./types/datafeed`).

Resolution helpers are now exported **as values**, not just types (new in the
`4bd96aaf` range): `resolutionToPeriod`, `periodToResolution`. The local
reimplementation in `helpers.js` (see "Resolution ↔ Period Conversion") can be
dropped once the app upgrades.

Indicator type re-exports (new in `f51001b2` — types existed in `src/lib/types/indicator.ts`, now added to the package surface):
`IndicatorCategory`, `IndicatorSubscribeParams`, `IndicatorSubscription`, `IndicatorDataHandler`,
`IndicatorTickHandler`, `IndicatorDataPoint`, `IndicatorMetadata`, `IndicatorPlot`, `PlotLine`,
`PlotHistogram`, `PlotHLine`, `PlotShape`, `PlotChar`, `PlotFill`, `PlotBgColor`, `PlotCandle`,
`PlotArrow`, `PlotLineStyle`, `PlotShapeStyle`, `PlotShapeLocation`, `PlotShapeSize`,
`IndicatorSettingDef`, `IndicatorSettingType`, `SettingValue`, `SettingOption`, `ActiveIndicator`
(values unchanged — purely an export-surface fix; describe the shape of a custom `IndicatorProvider`).

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
  onStorageError?: (err: Error) => void // fired after 3 failed merge-retries
  autoSaveDelay?: number                // debounce ms before writing; 0 = immediate (default)
  enabledFeatures?: FeatureFlag[]       // feature flags to enable (see Feature Flags section)
  disabledFeatures?: FeatureFlag[]      // feature flags to disable; wins over enabledFeatures
  mainIndicators?: string[]
  subIndicators?: string[]
  locale?: string                       // default: 'en-US'
  theme?: 'light' | 'dark' | string     // default: 'light'
  timezone?: string                     // default: 'Etc/UTC'
  watermark?: string | Node
  brand?: BrandOption                   // enterprise edition only — controls bottom-left Altrady-style badge; `false` hides it, `{logo,name,url}` overrides. See "Branding / Watermark" section.
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
  onUserOverlayRightClick?: (event: OverlayEvent<unknown>) => void  // fires on user-drawn overlay right-click; suppresses SC built-in popup (new in 2954fe0\/6d68fbb)
  onApiReady?: () => void                                // fires when React API mounts — getChart() non-null. Safe for subscriptions / toolbar buttons. Data not yet loaded.
  onDataLoaded?: () => void                              // fires when first dataset resolves — safe to read getDataList() / place overlays at concrete timestamps
}
```

> The pre-69a41cf `onReady` option is gone. It has been split into `onApiReady`
> (chart mounted but data may still be loading) and `onDataLoaded` (initial bars
> resolved). Use `onApiReady` for subscriptions and toolbar wiring; use
> `onDataLoaded` when the next step needs concrete bar data.

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
createOverlay(overlay: OverlayCreate & { properties?: DeepPartial<OverlayProperties>; save?: boolean }, paneId?: string): string | null
// save: false → transient overlay — renders but is never written to StorageAdapter or restored on reload
setOverlayMode(mode: OverlayMode): void
getBackendIndicators(): UseBackendIndicatorsReturn | null
openScriptEditor(options?: { initialCode?: string; readOnly?: boolean }): void
closeScriptEditor(): void
setPeriodBarVisible(visible: boolean): void   // show/hide the entire period bar at runtime
// Alerts & events — EPHEMERAL, not persisted in ChartState; re-push after reload (new in a523ceb / de73a0a)
setAlerts(alerts: Alert[]): void
getAlerts(): Alert[]
setEvents(events: ChartEvent[]): void
getEvents(): ChartEvent[]
createButton(options?: ToolbarButtonOptions): HTMLElement
createDropdown(options: ToolbarDropdownOptions): HTMLElement
onSymbolChange(callback: (symbol: SymbolInfo) => void): () => void   // returns unsubscribe
onPeriodChange(callback: (period: Period) => void): () => void       // returns unsubscribe
onVisibleRangeChange(callback: (range: VisibleTimeRange) => void): () => void  // returns unsubscribe
onCrosshairMoved(callback: (result: PriceTimeResult) => void): () => void      // returns unsubscribe
onSelect(callback: (result: PriceTimeResult) => void): () => void              // returns unsubscribe
onRightSelect(callback: (result: PriceTimeResult) => void): () => void         // returns unsubscribe
onDoubleSelect(callback: (result: PriceTimeResult) => void): () => void        // returns unsubscribe
onApiReady(callback: () => void): () => void       // fires when React API mounts (getChart() non-null); fires immediately if already mounted; returns unsubscribe
onDataLoaded(callback: () => void): () => void     // fires when first dataset resolves; fires immediately if already loaded; returns unsubscribe
// Indicator/overlay removal — routed through the persistence pipeline (canvas + storage + modal kept in sync)
removeIndicator(name: string): void                // by indicator type-name (e.g. "RSI", "MACD"); no-op if not active
removeOverlay(id: string): void                    // by overlay id from createOverlay; transient (save:false) overlays removed from canvas only
openOverlaySettings(id: string): void             // open SC native overlay style dialog (new in 8ea9d2c)
getDrawingTemplate(id: string): ExtractedDrawingTemplate | null  // snapshot overlay styling; template.name is empty (new in 8ea9d2c)
applyDrawingTemplate(id: string, template: DrawingTemplate): void  // apply DrawingTemplate to overlay (new in 8ea9d2c)
setOverlayLocked(id: string, locked: boolean): void  // lock/unlock overlay via modifyOverlay pipeline (new in 548ca06)
setVisibleRange(range: VisibleTimeRange): Promise<void>
// Async. Waits for chart ready. VisibleTimeRange uses unix SECONDS.
// Fetches missing history via dataLoader.getRange if range.from is before loaded data.
// Queued during init load; latest call wins. Throws SetVisibleRangeError on failure.
resetView(): Promise<void>
// Async. Resets bar space and offset-right to defaults (10px bar, 80px right offset).
// Queued during init load; latest call wins.
readonly replay: ReplayEngine | null           // null until chart mounts; reading also installs internal error→period-sync
dispose(): void
destroy(): void                                // alias for dispose()
getOptions(): SuperchartOptions

// Storage (no-ops when no storageAdapter configured)
saveState(): Promise<void>                         // force-save, last-write-wins
loadState(): Promise<void>                         // re-fetch and re-apply from adapter
clearState(): Promise<void>                        // delete remote record; chart visual unchanged
listSavedStates(prefix?: string): Promise<StorageEntry[]>

// Chart templates (named full-chart layouts — TV "Chart Layout" semantics)
// UI is shown when the adapter implements the *ChartTemplate methods AND the `chart_templates` flag is enabled.
listChartTemplates(): Promise<ChartTemplateMeta[]>
saveChartTemplate(name: string): Promise<void>        // snapshot current chart incl. symbol+period
applyChartTemplate(name: string): Promise<void>       // restores indicators/overlays/styles/symbol/period; full chart swap
renameChartTemplate(oldName: string, newName: string): Promise<void>      // atomic if adapter supports it; otherwise load+save+delete fallback
duplicateChartTemplate(name: string, newName: string): Promise<void>      // atomic if adapter supports it; otherwise load+save fallback
deleteChartTemplate(name: string): Promise<void>

// Feature flags
isFeatureEnabled(flag: FeatureFlag): boolean
setFeatureEnabled(flag: FeatureFlag, enabled: boolean): void  // triggers live re-render
```

## Datafeed Interface

Passed to `createDataLoader(datafeed)`. TradingView-compatible.

```typescript
interface Datafeed {
  onReady(callback: (config: DatafeedConfiguration) => void): void
  searchSymbols(userInput: string, exchange: string, symbolType: string,
    onResult: (results: SearchSymbolResult[]) => void,
    options?: { offset?: number, limit?: number }): void  // options NEW (2b25f9fb) — symbol-search modal passes offset for infinite scroll; backward-compatible
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

  // Optional (new in de73a0a) — economic/earnings event markers.
  // Datafeeds without it still work; no markers render.
  getEvents?(symbolInfo: LibrarySymbolInfo, from: number, to: number,
    callback: (events: ChartEvent[]) => void): void
}
```

## SuperchartDataLoader (returned by createDataLoader)

```typescript
interface SuperchartDataLoader extends DataLoader {
  searchSymbols(userInput: string, exchange: string, symbolType: string,
    onResult: (results: SearchSymbolResult[]) => void,
    options?: { offset?: number, limit?: number }): void  // options NEW (2b25f9fb)
  /** DatafeedConfiguration captured from Datafeed.onReady, or null if not yet fired. */
  getConfiguration(): DatafeedConfiguration | null
  setOnBarsLoaded(callback: (fromMs: number) => void): void

  // NEW (f51001b2) — called automatically by `new Superchart(...)` right after it
  // builds the instance's isolated ChartStore, to wire the loader's resolveSymbol
  // precision bridge (see LibrarySymbolInfo note) into that store. Altrady does not
  // call this directly.
  attachStore(store: ChartStore): void

  // Used by ReplayEngine AND by setVisibleRange history-fetch (both pass countBack: 0).
  // Timestamps are unix ms. Optional — if absent, setVisibleRange skips backward
  // history fetch (only applies range if already in buffer) and replay buffer will be empty.
  getRange?(params: {
    symbol: SymbolInfo, period: Period,
    from: number, to: number,
    callback: (bars: KLineData[]) => void
  }): void | Promise<void>

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
  timezone?: string              // IANA tz of the symbol's exchange (new in d2f940c)
}
```

### Alert / ChartEvent (new in `a523ceb` / `de73a0a`)
```typescript
interface Alert { id: string; price: number; label?: string; color?: string }

type ChartEventType = 'earnings' | 'dividends' | 'splits' | 'economic'
interface ChartEvent { id: string; type: ChartEventType; timestamp: number; label?: string }
```
Pushed via `setAlerts()` / `setEvents()`. **Ephemeral** — never written to
`ChartState`, so the host must re-push them after every reload.

### LibrarySymbolInfo
```typescript
{
  ticker: string, name: string, type?: string, exchange?: string,
  timezone?: string, pricescale: number, minmov?: number,
  volume_precision?: number,     // NEW (f51001b2) — decimal places, e.g. 0/3/8
  has_intraday?: boolean, has_daily?: boolean,
  supported_resolutions?: string[], session?: string,
  logo?: string, currency_code?: string
}
```

> **Precision sync (new in f51001b2).** `createDataLoader`'s `resolveSymbol` now
> pushes `pricescale`→`pricePrecision` and `volume_precision`→`volumePrecision`
> back into the chart's `SymbolInfo` on first resolve (`syncPrecisionToStore`),
> **overriding** whatever precision was passed to `new Superchart()` at
> construction. This is why a Datafeed's `resolveSymbol` result can now change the
> y-axis precision live.

### DatafeedConfiguration
```typescript
{ supported_resolutions: string[], exchanges?: {value: string, name: string}[], symbols_types?: {name: string, value: string}[] }
// BREAKING (ce4c809): `supportedResolutions` → `supported_resolutions`, `symbolsTypes` → `symbols_types`
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
interface StorageAdapter {
  // Core (all required except list)
  load(key: string): Promise<StorageRecord | null>
  save(key: string, state: ChartState, expectedRevision?: number): Promise<StorageWriteResult>
  // save without expectedRevision → last-write-wins.
  // save with expectedRevision → adapter must throw StorageConflictError if stored revision differs.
  delete(key: string): Promise<void>   // 404 must be treated as success
  list?(prefix?: string): Promise<StorageEntry[]>

  // Study templates (all optional — UI hidden when any is missing)
  listStudyTemplates?(indicatorName?: string): Promise<StudyTemplateMeta[]>
  loadStudyTemplate?(name: string): Promise<StudyTemplate | null>
  saveStudyTemplate?(name: string, template: StudyTemplate): Promise<void>
  deleteStudyTemplate?(name: string): Promise<void>  // system names must throw / 403

  // Drawing templates (all optional — UI hidden when any is missing)
  listDrawingTemplates?(toolName: string): Promise<DrawingTemplateMeta[]>
  loadDrawingTemplate?(toolName: string, name: string): Promise<DrawingTemplate | null>
  saveDrawingTemplate?(toolName: string, name: string, template: DrawingTemplate): Promise<void>
  deleteDrawingTemplate?(toolName: string, name: string): Promise<void>  // system names must throw / 403

  // Chart templates (named full-chart layouts — optional; UI hidden when list/load/save/delete are missing)
  listChartTemplates?(): Promise<ChartTemplateMeta[]>
  loadChartTemplate?(name: string): Promise<ChartTemplate | null>
  saveChartTemplate?(name: string, template: ChartTemplate): Promise<void>
  deleteChartTemplate?(name: string): Promise<void>
  renameChartTemplate?(oldName: string, newName: string): Promise<void>     // atomic; SC falls back to load+save+delete if absent
  duplicateChartTemplate?(name: string, newName: string): Promise<void>     // atomic; SC falls back to load+save if absent

  // Picker recents — MRU list for the emoji / icon overlay pickers (new in f51001b2).
  // Both optional; if unimplemented SC keeps a non-persistent in-memory MRU list.
  loadPickerRecents?(kind: 'emoji' | 'icon'): Promise<string[]>
  savePickerRecents?(kind: 'emoji' | 'icon', items: string[]): Promise<void>
}
```

### StorageRecord
```typescript
interface StorageRecord { state: ChartState; revision: number }
```

### StorageWriteResult
```typescript
interface StorageWriteResult { revision: number }
```

### StorageEntry
```typescript
interface StorageEntry { key: string; revision: number; savedAt?: number; symbol?: string; period?: string }
```

### StorageConflictError
```typescript
class StorageConflictError extends Error {
  remoteState: ChartState
  remoteRevision: number
  constructor(remoteState: ChartState, remoteRevision: number, message?: string)
}
```
Thrown by adapters when `expectedRevision` is stale. SC catches this internally and runs a merge-retry loop (up to 3 attempts). After 3 failures calls `onStorageError` and re-throws. Consumers only see it via `onStorageError`.

### LocalStorageAdapter
```typescript
class LocalStorageAdapter implements StorageAdapter {
  constructor(options?: LocalStorageAdapterOptions)
}
interface LocalStorageAdapterOptions {
  prefix?: string    // key prefix, default 'superchart:'
  storage?: Storage  // override for test / non-browser environments
}
```
Stores chart state at `${prefix}${key}`. Study templates at `${prefix}study-template:${name}`. Drawing templates at `${prefix}drawing-template:${toolName}:${name}`. Chart templates at `${prefix}chart-template:${name}`. Merges `SYSTEM_STUDY_TEMPLATES` / `SYSTEM_DRAWING_TEMPLATES` into list responses. Saving over a system name creates a user copy that shadows it; deleting a pure system name throws. Implements all template families including `list/load/save/delete/rename/duplicateChartTemplate`, plus `load/savePickerRecents` (new in f51001b2, stored at `${prefix}picker-recents:${kind}`).

### HttpStorageAdapter
```typescript
class HttpStorageAdapter implements StorageAdapter {
  constructor(options: HttpStorageAdapterOptions)
}
interface HttpStorageAdapterOptions {
  baseUrl: string                           // e.g. '/api/chart-state' — no trailing slash
  headers?: () => Record<string, string>   // re-evaluated per request (for auth tokens)
  fetch?: typeof fetch                     // override for test / non-browser
}
```
REST contract rooted at `baseUrl`:
- `GET {baseUrl}/{key}` → 200 `{state, revision}` | 404
- `PUT {baseUrl}/{key}` body `{state}`, optional header `If-Match: <revision>` → 200 `{revision}` | 409 `{remoteState, remoteRevision}`
- `DELETE {baseUrl}/{key}` → 204 | 404 (treated as success)
- `GET {baseUrl}[?prefix=…]` → 200 `StorageEntry[]`

Study templates at `{baseUrl-parent}/study-templates`, drawing templates at `{baseUrl-parent}/drawing-templates/:toolName`. System names return 403 on delete.

Chart templates rooted at `{baseUrl-parent}/chart-templates`:
- `GET    {baseUrl-parent}/chart-templates` → 200 `ChartTemplateMeta[]`
- `GET    {baseUrl-parent}/chart-templates/:name` → 200 `ChartTemplate` | 404
- `PUT    {baseUrl-parent}/chart-templates/:name` body `ChartTemplate` → 204
- `DELETE {baseUrl-parent}/chart-templates/:name` → 204 | 404 (treated as success)
- `POST   {baseUrl-parent}/chart-templates/:name/rename` body `{newName}` → 204 | 409
- `POST   {baseUrl-parent}/chart-templates/:name/duplicate` body `{newName}` → 204 | 409

### ChartState
```typescript
interface ChartState {
  version: number                   // schema version (currently 1); separate from StorageRecord.revision
  indicators: SavedIndicator[]
  overlays: SavedOverlay[]
  styles: DeepPartial<Styles>
  paneLayout: PaneLayout[]
  preferences: ChartPreferences
  savedAt?: number
  symbol?: string
  period?: string
  overlayDefaults?: Record<string, DeepPartial<OverlayProperties>>
  activeChartTemplate?: string            // name of last applied/saved chart template; shown in the period bar dropdown
  userFeatureOverrides?: Record<string, boolean>  // user toggle overrides (e.g. auto_save_state) persisted across reloads

  // Favourites (new in the 4bd96aaf range — ALTD-1909/1910/1911)
  favoriteTools?: FavoriteToolRef[]        // drawing-bar favourites, display order
  favoritesBarPosition?: {x: number, y: number}  // floating favourites-bar drag position, container-relative px;
                                                 // absent → bar centres horizontally on first paint
  favoritePeriods?: FavoritePeriodRef[]    // pinned quick-switch timeframes, display order
  favoriteLayouts?: string[]               // pinned chart-layout template names, display order
}

interface FavoriteToolRef { key: string; iconKey?: string; extendData?: unknown }
interface FavoritePeriodRef { span: number; type: string }
```

A host storing `ChartState` opaquely (as Altrady does) needs no change — these are
additive fields inside the same blob.

### ChartPreferences

Grew substantially in the `4bd96aaf` range (ALTD-1915.x — the Settings-modal
rewrite). **All additions are optional**, and the whole object is persisted
inside `ChartState`, so a host that stores chart state opaquely needs no change.

```typescript
interface ChartPreferences {
  showVolume: boolean                       // default true
  showCrosshair: boolean                    // default true
  showGrid: boolean                         // default true
  showLegend: boolean                       // default true
  magnetMode: 'normal' | 'weak' | 'strong'  // default 'normal' — overlay DRAG magnet, not the crosshair one
  timezone?: string                         // store signal defaults to 'Etc/UTC'
  locale?: string                           // store signal defaults to 'en-US'

  // ALTD-1913 — timezone follows the symbol's exchange; `timezone` then only caches
  // the last applied value. An explicit user pick from the launcher resets this to false.
  followExchangeTimezone?: boolean          // store signal defaults to false

  // ── Symbol tab (1915.2) ──
  symbolOverrides?: Record<string, {        // keyed by SymbolInfo.ticker; merged into the
    pricePrecision?: number                 // effective SymbolInfo on every chart.setSymbol
    priceSource?: 'close' | 'open' | 'high' | 'low' | 'hl2' | 'hlc3' | 'ohlc4'  // default 'close'
  }>
  adjustDividends?: boolean                 // datafeed HINT — SC does not apply these itself
  adjustSplits?: boolean
  wickSameAsBody?: boolean                  // TV's toggle; true → wick pickers grey out and mirror body

  // ── Canvas tab (1915.3) ──
  background?: {                            // absent → theme-driven default
    mode: 'solid' | 'gradient' | 'image'
    color?: string
    gradientStart?: string
    gradientEnd?: string
    gradientAngle?: number                  // default 180 (0 = top→bottom)
    imageSrc?: string                       // data-URI
    imageOpacity?: number                   // 0–100
    imageFit?: 'contain' | 'cover' | 'stretch' | 'tile'
  }
  watermark?: {                             // absent, or show:false → falls back to brand default
    show: boolean
    text: string
    fontFamily?: string
    fontSize?: number
    color?: string
    opacity?: number                        // 0–100
    position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'centre'
  }

  // ── Status Line tab (1915.4) — replaces the deprecated `volume_in_legend` flag ──
  // Every field defaults to TRUE when undefined; only an explicit false hides a piece.
  statusLine?: {
    symbolName?: boolean; description?: boolean; exchange?: boolean; interval?: boolean
    barChanges?: boolean; ohlc?: boolean; volume?: boolean
    indicatorTitle?: boolean; indicatorArguments?: boolean
    indicatorValues?: boolean; indicatorLastValueBadge?: boolean
    buySellButtons?: boolean                // tab renders disabled until 1915.7 wiring lands
  }

  // ── Scales tab (1915.5) ──
  scales?: {
    pricePlacement?: 'right' | 'left' | 'hidden'   // default 'right'
    priceReverse?: boolean
    priceLabelsInside?: boolean
    priceType?: 'normal' | 'percentage' | 'log' | 'indexed100'  // only 'normal' reaches the engine
    autoScale?: boolean                     // persisted only — engine wiring TBD
    lockScale?: boolean                     // persisted only
    noOverlap?: boolean                     // persisted only
    topMargin?: number                      // px
    bottomMargin?: number                   // px
    priceLabels?: {
      last?: boolean                        // engine-supported
      high?: boolean                        // engine-supported
      low?: boolean                         // engine-supported
      previousClose?: boolean               // persisted only
      averageClose?: boolean                // persisted only
      bidAsk?: boolean                      // persisted only — datafeed-dependent
    }
    showTimeScale?: boolean
    showSeconds?: boolean                   // applied via chart.setShowSeconds
    showDayBreaks?: boolean                 // persisted only
  }

  // ── Localization tab (1915.6) — persisted only, engine wiring deferred ──
  numberFormat?: { thousands?: ',' | '.' | ' ' | 'none'; decimal?: '.' | ',' }
  symbolDisplay?: { exchangePrefix?: boolean; typePrefix?: boolean }

  // ── Trading tab (1915.7) — visibility of HOST-provided trading overlays ──
  trading?: {
    showOrders?: boolean; showPositions?: boolean; showExecutions?: boolean
    buySellButtons?: boolean                // same key as statusLine.buySellButtons
    orderColor?: string                     // defaults for overlays created without an explicit
    positionColor?: string                  // colour; does NOT clobber already-coloured lines
    executionColor?: string
  }

  // ── Alerts tab (1915.8) — STYLE only; the Alert[] list is ephemeral/host-owned ──
  alerts?: {
    show?: boolean
    lineStyle?: 'solid' | 'dashed'
    lineColor?: string
    labelPosition?: 'left' | 'right'
    sound?: boolean
  }

  // ── Events tab (1915.9) — all default false, so a datafeed without getEvents is unaffected ──
  events?: {
    sessionBreaks?: boolean                 // persisted only — engine wiring pending
    extendedHours?: boolean                 // persisted only
    extendedHoursColor?: string
    earnings?: boolean; dividends?: boolean; splits?: boolean; economic?: boolean
  }

  recentIndicatorTemplates?: string[]       // ring buffer, most-recent first, capped at 5 (1915.11)
  autoSaveDelay?: number                    // ms; persists the Preferences-tab slider across reloads
}
```

> **SC API gap — a host cannot read or write these.** `ChartPreferences` is
> mutated only through `useChartState().setPreference(path, value)` /
> `getPreferences()`, and `useChartState` is **not exported** from
> `src/lib/index.ts` nor surfaced on `SuperchartApi`. SC's own Settings modal is
> the only writer. The only host-facing slices are `setAlerts()`/`setEvents()`
> (which cover the *data*, not these style prefs) and the pre-existing
> `setStyles()` / `setPaneOptions()` / `setSymbol()`. If Altrady needs
> programmatic control of any preference above, that is a feature request to the
> SC author.
>
> For reference, `setPreference(path, value)`'s `path` is dot-separated and
> **relative to `preferences`**, not to `ChartState` — e.g.
> `"symbolOverrides.BTCUSDT.pricePrecision"`, `"alerts.lineColor"`. It writes
> immutably and persists through the normal `enqueueMutation` →
> `StorageAdapter` path (immediate when `autoSaveDelay <= 0`, debounced above
> that, cache-only when `auto_save_state` is off).

> **Magnet snap rewritten (coinray-chart `174b3244` — ALTD-1898).** No type or config-key change —
> `magnetMode` values are the same. The snap *algorithm* changed: it now picks the nearest of
> {open, high, low, close} by **pixel distance**. `strong` always snaps; `weak` only snaps within
> `Overlay.modeSensitivity`, whose default went **8px → 60px** (a much wider, more forgiving halo).
> The old asymmetric behaviour (hard-snap anywhere inside the candle body regardless of mode) is gone.
> Feel-only change — no code action needed unless you read or hardcode `modeSensitivity`.

> **Two unrelated things are called "magnet" — do not conflate them when wiring UI toggles.**
> 1. **Overlay drag-magnet** (pre-existing): `OverlayImp.mode: 'normal' | 'weak_magnet' | 'strong_magnet'`
>    with a `modeSensitivity` pixel radius. Governs how a *dragged overlay point* snaps to OHLC
>    while drawing/editing. This is what `ChartPreferences.magnetMode` above feeds.
> 2. **Global crosshair magnet** (NEW, coinray-chart `bd92b49e`): `chart.setMagnetMode(mode)` /
>    `getMagnetMode()`. Snaps the *crosshair itself*. `weak` snaps X to the nearest bar centre;
>    `strong` additionally snaps Y to the nearest OHLC pixel, and only on the candle pane
>    (`crosshair.paneId === CANDLE`); `normal` disables. Applied inside `Store.setCrosshair`
>    before the crosshair snapshot, so tooltip and crosshair-line views see the snapped
>    coordinates. `setMagnetMode()` immediately re-invokes `setCrosshair({forceInvalidate: true})`.
>    Related but distinct from the `crosshair_magnet` feature flag (which gates availability).

### SavedIndicator
```typescript
interface SavedIndicator {
  id: string
  name: string           // indicator type name e.g. "RSI", "MACD"
  paneId: string
  calcParams?: unknown[] // built-in indicators
  settings?: Record<string, SettingValue>  // backend indicators only
  visible: boolean
  isStack?: boolean
  paneOptions?: PaneOptions
  styles?: Record<string, unknown>
}
// type SettingValue = number | boolean | string
```
Backend indicators are identified by having `settings` and no `calcParams`.

### StudyTemplateMeta / StudyTemplate
```typescript
interface StudyTemplateMeta {
  name: string
  indicatorName: string
  system?: boolean     // true = bundled read-only preset
  savedAt?: number
}
interface StudyTemplate extends StudyTemplateMeta {
  calcParams?: unknown[]
  settings?: Record<string, SettingValue>
  styles?: Record<string, unknown>
}
```
`SYSTEM_STUDY_TEMPLATES`: 5 bundled presets (RSI 14, MACD 12/26/9, EMA 50, EMA 200, BOLL 20).
UI shown when: `study_templates` feature flag is `true` AND adapter implements all 4 study-template methods.

### DrawingTemplateMeta / DrawingTemplate
```typescript
interface DrawingTemplateMeta {
  name: string
  toolName: string    // e.g. 'trendLine', 'fibSegment', 'horizontalRayLine'
  system?: boolean
  savedAt?: number
}
interface DrawingTemplate extends DrawingTemplateMeta {
  properties?: Record<string, unknown>
  figureStyles?: Record<string, Record<string, unknown>>
}
```
Composite key is `(toolName, name)` — independent per tool.
`SYSTEM_DRAWING_TEMPLATES`: 4 presets (Bullish trendline, Bearish trendline, Support line, Resistance line).
UI shown when: `drawing_templates` feature flag is `true` AND adapter implements all 4 drawing-template methods.

### ExtractedDrawingTemplate (new in 8ea9d2c / 6d68fbb)
```typescript
interface ExtractedDrawingTemplate {
  toolName: string           // overlay.name, e.g. "segment", "fibonacciLine"
  template: DrawingTemplate  // template.name is empty; consumer fills it before calling saveDrawingTemplate
}
```
Returned by `sc.getDrawingTemplate(id)`. Use `toolName` as the first argument to `StorageAdapter.saveDrawingTemplate(toolName, name, template)`.

### ChartTemplateMeta / ChartTemplate (new in 69a41cf)
```typescript
interface ChartTemplateMeta {
  name: string
  savedAt?: number
  symbol?: string          // ticker — shown in the dropdown
  period?: string          // period.text — shown in the dropdown
}

interface ChartTemplate {
  name: string
  savedAt?: number
  indicators: SavedIndicator[]
  overlays: SavedOverlay[]
  styles: DeepPartial<Styles>
  paneLayout: PaneLayout[]
  preferences: ChartPreferences
  overlayDefaults?: Record<string, DeepPartial<OverlayProperties>>
  symbol?: SymbolInfo                                // restored via setSymbol() on apply
  period?: Period                                    // restored via setPeriod() on apply
}
```
A `ChartTemplate` is a complete snapshot of a chart (TV "Chart Layout" semantics). Applying one swaps everything including symbol+period. SC tracks the active template in `ChartState.activeChartTemplate` and re-saves into it on overlay/indicator/symbol/period changes when auto-save is on (`ea1dd96`). UI shown when: `chart_templates` feature flag is `true` AND adapter implements `list/load/save/deleteChartTemplate`.

### OverlayProperties
```typescript
{ style, text, textColor, textFont, textFontSize, textFontWeight, textBackgroundColor,
  textPaddingLeft/Right/Top/Bottom, lineColor, lineWidth, lineStyle, lineLength,
  lineDashedValue, tooltip, backgroundColor, borderStyle, borderColor, borderWidth }
```

### OverlayTextChangeEvent (`committed` new in coinray-chart `174b3244`)
Fired by the engine while the user inline-edits text on a text-bearing overlay
(`text`, `note`, `callout`, `comment`, `priceNote`, `signpost`, `pin`, `table` cells,
and — new in `174b3244` — `arrow` and `circle`).

```typescript
interface OverlayTextChangeEvent<E> {
  overlay: Overlay<E>
  chart: Chart
  text: string
  committed: boolean   // NEW in 174b3244
}
```

`committed: false` fires on **every keystroke** (live re-render); `committed: true` fires
once on blur/Escape (edit finalised). **Anything that persists or reacts expensively must
gate on `committed === true`** or it will run on every keypress.

**There is no `SuperchartApi` callback for this event.** `Superchart` exposes no
`onOverlayTextChange` method or constructor option. The only way to receive it is the generic
engine hook — pass your own `onTextChange` in the object handed to `createOverlay()`:

```typescript
sc.createOverlay({
  name: "note",
  points: [...],
  onTextChange: (e: OverlayTextChangeEvent) => { if (e.committed) persist(e.text) },
})
```

SC's own `useChartState` consumes the hook internally (chains it, then syncs to storage on
`committed`) and does **not** forward it. Net effect: inline overlay text now survives a
reload, where before it silently reverted. Altrady doesn't use `onTextChange` today — this
is informational, not a required migration.

### IndicatorProvider
```typescript
{ getAvailableIndicators(), subscribe(params), updateSettings(id, settings),
  unsubscribe(id), onSymbolPeriodChange?(symbol, period, active), dispose?() }
```

### ScriptProvider

Passed as `new Superchart({ scriptProvider })`. Verified against
`src/lib/types/script.ts` at `4bd96aaf` (matches `$SUPERCHART_DIR/docs/scripts.md`).

> **⛔ BLOCKER — `main` cannot run `@coinrayio/superchart-script` today**
>
> The npm package `@coinrayio/superchart-script@0.1.7` (the one the app installs)
> was compiled against a **different, unmerged** Superchart. Its
> `WasmScriptProvider` declares `language`, `defaultScript` and `EditorComponent`
> on `ScriptProvider`, and its `reducePrimitives()` returns `PrimitiveSnapshot`.
>
> **None of that exists on `main`.** Those types were introduced by commit
> `12b80231c53ce69c14fd5231113f41c4b80349de` ("feat: pluggable scripting —
> primitive overlays + editor slot", 2026-06-16), which lives only on
> `origin/feat/wasm-script-provider-example`. That branch also adds
> `src/lib/types/primitive.ts` (`ScriptPrimitive`, `MarkerShape`,
> `PrimitivePoint`, `PrimitiveSnapshot`), `IndicatorSubscription.onPrimitives?()`,
> and a `ScriptEditorComponentProps` contract — and deletes the in-tree
> `script-editor` widget.
>
> Divergence, not simple staleness: merge-base with `main` is `dcb4c417`
> (2026-06-12); `main` has since gained **203 commits** the branch never
> absorbed, and the branch's 2 commits have no equivalent on `main`
> (`git cherry main origin/feat/wasm-script-provider-example` marks both `+`).
> The locally built `dist-enterprise/` matches `main`, not the branch.
>
> **Consequences:** `WasmScriptProvider` fails to typecheck against the linked
> SC (`PrimitiveSnapshot` and the three `ScriptProvider` members don't exist),
> and at runtime `main`'s `SuperchartComponent` has no `onPrimitives` wiring and
> no editor slot. Script-drawn primitives (`draw.*`) have **no rendering path on
> `main` at all** — everything must go through `IndicatorMetadata.plots`.
>
> **Unblocking is the SC author's call, not ours:** either rebase and merge
> `feat/wasm-script-provider-example` onto current `main`, or re-port the feature.
> Re-verify this section before designing the SC scripting port.

The contract below is `main`'s — i.e. what is actually available today.

```typescript
interface ScriptProvider {
  compile(code: string, language: string): Promise<ScriptCompileResult>
  executeAsIndicator(params: ScriptExecuteParams): Promise<IndicatorSubscription>
  executeAsBot?(params: ScriptExecuteParams): Promise<BotSubscription>
  stop(scriptId: string): Promise<void>
  listScripts?(): Promise<ScriptInfo[]>
  saveScript?(script: ScriptSaveParams): Promise<ScriptInfo>
  deleteScript?(scriptId: string): Promise<void>
  dispose?(): void
}

interface ScriptExecuteParams {
  code: string
  language: string                            // matched against ScriptLanguageDefinition.name
  symbol: SymbolInfo
  period: Period
  settings?: Record<string, SettingValue>     // SettingValue = number | boolean | string
}

interface ScriptCompileResult {
  success: boolean
  errors?: ScriptDiagnostic[]
  warnings?: ScriptDiagnostic[]
  metadata?: IndicatorMetadata                // reuses the indicator metadata shape
}

interface ScriptDiagnostic {
  line: number; column: number                // 1-based
  endLine?: number; endColumn?: number
  message: string
  severity: 'error' | 'warning' | 'info'
}

interface ScriptInfo {
  id: string; name: string; code: string; language: string
  createdAt: number; updatedAt: number        // unix ms
  description?: string
}
interface ScriptSaveParams { name: string; code: string; language: string; description?: string }

interface BotSubscription {
  botId: string
  onSignal(handler: (signal: BotSignal) => void): void
  onError?(handler: (error: Error) => void): void
  dispose(): void
}
interface BotSignal {
  type: 'buy' | 'sell' | 'close' | 'modify'
  timestamp: number; price?: number; quantity?: number
  stopLoss?: number; takeProfit?: number; metadata?: Record<string, unknown>
}

interface ScriptLanguageDefinition {
  name: string
  extension?: string
  keywords: string[]
  typeKeywords?: string[]
  builtinFunctions: ScriptBuiltinFunction[]
  builtinVariables?: ScriptBuiltinVariable[]
  comments: { line?: string; blockStart?: string; blockEnd?: string }
  operators?: string[]
  stringDelimiters?: string[]
}
interface ScriptBuiltinFunction { name: string; description?: string; parameters?: ScriptFunctionParameter[]; returnType?: string }
interface ScriptFunctionParameter { name: string; type: string; description?: string; optional?: boolean }
interface ScriptBuiltinVariable { name: string; description?: string; type?: string }
```

### IndicatorSubscription / IndicatorMetadata / IndicatorDataPoint

Shared by `IndicatorProvider` and `ScriptProvider` — `executeAsIndicator()` returns this.

```typescript
interface IndicatorSubscription {
  indicatorId: string
  metadata: IndicatorMetadata
  onData(handler: (data: IndicatorDataPoint[]) => void): void      // full/initial dataset
  onTick(handler: (data: IndicatorDataPoint) => void): void        // single real-time point
  onHistory?(handler: (data: IndicatorDataPoint[]) => void): void  // backfill — MERGED, not replaced
  onError?(handler: (error: Error) => void): void
}

interface IndicatorMetadata {
  name: string; shortName: string; precision: number
  paneId: string          // 'candle_pane' = overlay on price; any other string = its own pane
  plots: IndicatorPlot[]
  settings: IndicatorSettingDef[]
  minValue?: number; maxValue?: number; logarithmic?: boolean
}

interface IndicatorDataPoint {
  timestamp: number                             // unix MILLISECONDS
  values: Record<string, number | null>         // plotId → value
  colors?: Record<string, string>               // plotId → per-bar colour
  shapes?: Record<string, boolean>              // plotId → show
  texts?: Record<string, string>                // plotId → label
  ohlc?: Record<string, {open: number; high: number; low: number; close: number}>  // plotcandle
  bgcolor?: string
}

interface IndicatorSettingDef {
  id: string; name: string
  type: 'number' | 'boolean' | 'string' | 'color' | 'select'
  defaultValue: SettingValue
  min?: number; max?: number; step?: number
  options?: {value: string; label: string}[]
  group?: string
}
```

### IndicatorPlot (all 9 variants)

```typescript
type IndicatorPlot = PlotLine | PlotHistogram | PlotHLine | PlotShape | PlotChar
                   | PlotFill | PlotBgColor | PlotCandle | PlotArrow

interface PlotLine      { type: 'plot'; id: string; title: string
                          style: 'line'|'stepline'|'stepline_diamond'|'circles'|'cross'|'area'
                          color: string; lineWidth?: number; offset?: number; transparency?: number }
interface PlotHistogram { type: 'histogram'; id: string; title: string; color: string; histBase?: number }
interface PlotHLine     { type: 'hline'; id: string; price: number; color: string
                          lineStyle?: 'solid'|'dashed'|'dotted'; lineWidth?: number; title?: string }
interface PlotShape     { type: 'plotshape'; id: string
                          style: 'triangleup'|'triangledown'|'circle'|'cross'|'xcross'|'diamond'|'flag'
                               | 'label_up'|'label_down'|'arrowup'|'arrowdown'|'square'
                          location: 'abovebar'|'belowbar'|'top'|'bottom'|'absolute'
                          color: string; size?: 'tiny'|'small'|'normal'|'large'|'huge'
                          text?: string; textColor?: string; offset?: number }
interface PlotChar      { type: 'plotchar'; id: string; char: string
                          location: PlotShapeLocation; color: string; size?: PlotShapeSize; offset?: number }
interface PlotFill      { type: 'fill'; id: string; plot1: string; plot2: string
                          color: string; transparency?: number; title?: string }
interface PlotBgColor   { type: 'bgcolor'; id: string; color: string; transparency?: number; title?: string }
interface PlotCandle    { type: 'plotcandle'; id: string; colorUp: string; colorDown: string
                          borderUp?: string; borderDown?: string; wickUp?: string; wickDown?: string; title?: string }
interface PlotArrow     { type: 'plotarrow'; id: string; colorUp: string; colorDown: string
                          offset?: number; minHeight?: number; maxHeight?: number }
```

SC converts these into a klinecharts custom indicator (`registerIndicator({figures, calc, draw})`)
and paints the awkward kinds (`fill`, `plotshape`/`plotchar`, gap-connected sparse `plot`) with a
hand-rolled canvas `draw` callback internal to `SuperchartComponent`. **A host never reimplements
that** — it only has to produce correct `IndicatorMetadata` + `IndicatorDataPoint`.

### SetVisibleRangeError (new in 12e80de)
```typescript
type SetVisibleRangeErrorCode = 'no_data_at_time' | 'unsupported_resolution' | 'aborted'

interface SetVisibleRangeError extends Error {
  name: 'SetVisibleRangeError'
  code: SetVisibleRangeErrorCode
  detail: unknown
}

function isSetVisibleRangeError(e: unknown): e is SetVisibleRangeError
```

Error codes:
- `'no_data_at_time'` — `range.from` is before symbol's first candle. `detail: { timestamp, firstCandleTime, period }`.
- `'unsupported_resolution'` — second-resolution or unsupported period. `detail: { period }`.
- `'aborted'` — pending queued call cancelled because chart was destroyed. `detail: { reason: 'chart_destroyed' }`. Safe to ignore on unmount.

### FeatureFlag
```typescript
type FeatureFlag =
  | 'drawing_bar'         // default true
  | 'period_bar'          // default true
  | 'screenshot_button'   // default true
  | 'fullscreen_button'   // default true
  | 'symbol_search'       // default true
  | 'period_picker'       // default true
  | 'indicator_picker'    // default true
  | 'right_click_menu'    // default true
  | 'longpress_menu'      // default true
  | 'crosshair_magnet'    // default false
  | 'auto_save_state'     // default true — when false, no adapter writes; must call saveState() manually
  | 'study_templates'     // default true — UI shown when adapter also implements all 4 study template methods
  | 'drawing_templates'   // default true — UI shown when adapter also implements all 4 drawing template methods
  | 'chart_templates'     // default true — UI shown when adapter implements list/load/save/deleteChartTemplate
  | 'multi_chart_browser' // default true (reserved)
  | 'volume_in_legend'    // default true — DEPRECATED in 9a8dc80, see below
  | 'last_close_price_line' // default true
  | 'settings_button'     // default true — gear/settings button in the period bar
  | 'timezone_button'     // default FALSE since 9a8dc80 (was true) — see below
```

> **BREAKING (SC `9a8dc80`): `timezone_button` now defaults to `false`.** The
> period-bar timezone button was replaced by the new bottom-right
> `TimezoneLauncher` widget. A host that wants the old button back must pass
> `enabledFeatures: ['timezone_button']` explicitly.
>
> **`volume_in_legend` is deprecated.** It still works, but `resolveFeatures`
> emits a one-time `console.warn` pointing at `preferences.statusLine.volume`
> as the replacement.

`disabledFeatures` wins over `enabledFeatures` when a flag appears in both.
`drawing_bar` / `period_bar` flags control availability (binary); `drawingBarVisible` / `periodBarVisible` options control current visibility state (user-toggleable). Toolbar shows only when flag is `true` AND visibility is `true`.

### FEATURE_DEFAULTS
`Record<FeatureFlag, boolean>` — complete defaults map. Import to inspect defaults without constructing a chart.

### useFeature (React hook)
```typescript
import { useFeature } from 'superchart'
const enabled: boolean = useFeature('drawing_bar')
```
Re-renders the consuming component when `setFeatureEnabled` toggles the flag.

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

// Panes
getPaneOptions(): PaneOptions[]                    // includes the 'x_axis_pane' entry
setPaneOptions(options: PaneOptions): void         // PaneOptions: { id, state?: 'normal'|'maximize'|'minimize', height?, ... }

// Coordinate conversion
convertToPixel(points, filter?): Partial<Coordinate> | Array<...>
convertFromPixel(coordinates, filter?): Partial<Point> | Array<...>

// Actions
subscribeAction(type: ActionType, callback): void
unsubscribeAction(type: ActionType, callback?): void
// ActionType: 'onZoom' | 'onScroll' | 'onVisibleRangeChange' | 'onCandleTooltipFeatureClick'
//           | 'onIndicatorTooltipFeatureClick' | 'onCrosshairFeatureClick' | 'onCrosshairChange'
//           | 'onCandleBarClick' | 'onChartClick' | 'onChartRightClick' | 'onChartDoubleClick' | 'onPaneDrag'
//           | 'onInitLoadComplete'   ← fires when the initial getBars load finishes; drains setVisibleRange queue
// onChartClick / onChartRightClick / onChartDoubleClick only fire on MAIN widget clicks
// that were NOT consumed by an overlay. Payload: { x, y, timestamp, ...crosshair }

// Style & config
setStyles(value: string | DeepPartial<Styles>): void
getStyles(): Styles
setSymbol(symbol): void
setPeriod(period): void
setZoomEnabled(enabled: boolean): void
setScrollEnabled(enabled: boolean): void

// Global crosshair magnet (new in coinray-chart bd92b49e) — NOT the overlay drag-magnet
setMagnetMode(mode: 'normal' | 'weak' | 'strong'): void
getMagnetMode(): 'normal' | 'weak' | 'strong'

// X-axis seconds (new in coinray-chart 7d3cc38a)
setShowSeconds(show: boolean): void   // call this one, not the Store-level setter — it repaints
getShowSeconds(): boolean

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

## Small-price fold notation (coinray-chart `174b3244` — ALTD-1896)

`formatFoldDecimal` (the engine's compact rendering of tiny prices on axis labels, tooltips and
overlay labels) changed its **output string shape**:

| | example input | old output | new output |
|---|---|---|---|
| leading `0` dropped | `0.00012` | `0.0{3}12` | `0.{4}12` |
| trailing zeros trimmed | `0.00012000` | `0.0{3}1200` | `0.{4}12` |

So the notation is now `0.{n}sig` (was `0.0{n}sig`), and the significand no longer carries
trailing zeros. **Breaking for any code that regex-parses SC's folded-price display strings**
(e.g. a custom price-label renderer or a screenshot/text assertion). Altrady does not parse these
strings — grep for `formatFoldDecimal` / fold-notation regexes found nothing — so we're unaffected.

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

### Drawing-tool overlays (new in coinray-chart `2b25f9fb`)

A batch of TV-style annotation/drawing overlays registered as `proExtensions` in
coinray-chart, available through `chart.createOverlay({name: "...", ...})` like the
primitives above. None export a TS interface — configure via `extendData` (same
hand-documented pattern as the entries above). `totalStep` is klinecharts' internal
point-count (clicks = `totalStep − 1`).

| name | clicks | key `extendData` fields |
|---|---|---|
| `text` | 1 | `text, fontSize, textColor, fontWeight, align` |
| `note` | 2 | `text, fontSize, textColor, fontWeight, fontFamily, lineColor, backgroundColor, borderColor, borderWidth` |
| `callout` | 2 | `text, fontSize, textColor, fontWeight, fontFamily, backgroundColor, borderColor` + tail-attachment geometry |
| `comment` | 1 | `text, fontSize, textColor, fontWeight, fontFamily, backgroundColor` |
| `priceLabel` | 1 | `fontSize, textColor, fontWeight, fontFamily, backgroundColor, borderColor` |
| `priceNote` | 2 | `lineText, fontSize, textColor, fontWeight, fontFamily, lineColor, backgroundColor, borderColor, borderWidth` |
| `signpost` | 1 | `text, fontSize, textColor, fontWeight, fontFamily, backgroundColor, borderColor, borderWidth, emojiEnabled, emoji, emojiRingColor` (always-on x-axis date label) |
| `flagMark` | 1 | `backgroundColor` |
| `pin` | 1 | `backgroundColor, text, anchorDrawing` |
| `table` | 1 (then resize) | `rows, cols, cells: string[][], colWidths: number[], rowHeights: number[], textAlign` |
| `image` | 1 (drop-anywhere) | `src` (data URI), `opacity, width, height` — upload flow via internal `imageUploadTarget` store signal, not a public API |
| `measure` | 2 | none persisted — self-removing, always created with `save: false` (TV-style drag-box price/percent/bar-count readout); internal use |

> **`horizontalRayLine` is now single-click (breaking-ish, `2b25f9fb`).** `totalStep`
> went `3 → 2`; direction (`'left' | 'right'`, default `'right'`) now comes from
> `extendData.direction` instead of a second click. Any Altrady drawing-bar wiring that
> assumed 2-click placement will now complete after one click.
>
> **Fibonacci label format flipped (`2b25f9fb` / SC `5a304c3`):** retracement / extension /
> segment level labels render `"{pct}% ({price})"` (was `"{price} ({pct}%)"`).

### Fibonacci family rework (coinray-chart `174b3244` — ALTD-1894)

The whole fib family was reworked for TV parity. No overlay **names** were added, removed or
renamed, so the registry and any `createOverlay({name: "fibonacci…"})` call still resolves —
but geometry, defaults and click-counts changed:

> **`fibonacciLine` ("Fibonacci Channel") is now 3-click (was 2).** `totalStep` went `3 → 4`.
> Backward-safe, not a crash: an overlay persisted with only 2 points renders just the diagonal
> line and no channel bands until a 3rd point is added (`if (coordinates.length < 3) return figures`).
> **Anything that creates `fibonacciLine` programmatically with 2 points now draws an incomplete
> overlay.** Altrady's MCP chart-bridge lists `fibonacciLine` as a valid name but never constructs
> one (it maps canonical `fib_retracement` → `fibonacciSegment`), so we are not affected today.

- `fibonacciCircle` — circle → **ellipse**, √2-based geometry, trendline defaults, bespoke Style tab.
- `fibonacciSpiral` — now a true **log spiral**; `counterclockwise` direction flag.
- `fibonacciSpeedResistanceFan` — bespoke geometry rewrite + separate `fanPriceLevels` /
  `fanTimeLevels`, bespoke Style tab.
- `fibonacciSegment` / `fibonacciExtension` — retracement-first ordering, colour cascade, alpha norm.
- Line-based fibs gained shared defaults parity: colours, background fill, label toggles.

**New `extendData` keys** (persisted) on the reworked fibs — SC's `EXTEND_DATA_PROPERTY_KEYS` grew:
`diagonalWidth`, `diagonalStyle`, `diagonalDashedValue`, `counterclockwise`, `fanPriceLevels`,
`fanTimeLevels`, `showLeftLabels`, `showRightLabels`, `showTopLabels`, `showBottomLabels`,
`showGrid`, `gridColor`. The `SavedOverlay` shape is unchanged (`{ properties, extendData, … }`) —
older saved states simply lack these keys and fall back to defaults. No migration needed.

> **`arrow` and `circle` now persist inline text.** Their inline-edited text is written into
> `extendData.text` (previously it lived only in a volatile in-memory properties Map and was lost
> on reload). Persisted `extendData` for these two types may now carry a `text` key it never had before.

### Overlay drag constraints via `extendData` (coinray-chart `2633ab04` / `3dbccb91` / `9228235a`)

These are read off `overlay.extendData` with an **untyped cast** — they are NOT on the
typed `OverlayTemplate`/`OverlayCreate` interface, so TS will not help you. Set them with
`chart.overrideOverlay({ id, extendData: { ... } })`.

```typescript
// Coordinate lock (2633ab04) — suppresses axis updates during per-point and whole-overlay drag
{ lockPrice?: boolean, lockTime?: boolean }

// Aspect-ratio drag (3dbccb91, 9228235a) — requires !lockPrice && !lockTime
{
  lockAspectRatio?: boolean
  aspectRatio?: number                                   // > 0; required for 'boundingBox'
  aspectRatioMode?: 'boundingBox' | 'similar' | 'angleAtVertex'
  aspectRatioOffsets?: Array<{x: number, y: number}>     // 'similar' only; length === points.length
  aspectRatioCentroid?: {x: number, y: number}           // 'similar' only
  aspectRatioAngles?: number[]                           // 'angleAtVertex' only; triangles (points.length === 3)
}
```

Modes:
- `boundingBox` (default) — only the dragged vertex moves, anchored to the centroid of the
  remaining points and scaled by `aspectRatio`.
- `similar` — rotates + scales the whole shape around a captured centroid so it stays
  geometrically similar.
- `angleAtVertex` — triangle-only; constrains the dragged vertex to the arc on which it
  subtends the stored interior angle (inscribed-angle theorem).

> **The consumer owns the bookkeeping.** SC only *consumes* these fields. The host must
> compute and stash `aspectRatioOffsets` / `aspectRatioCentroid` / `aspectRatioAngles`
> itself (e.g. on flag-flip in a Coordinates tab) *before* setting `lockAspectRatio: true`.

### emojiMarker (now a real overlay, `2b25f9fb`)
Single emoji (or `'svg:<path>'` glyph) at a point. **Moved** from Superchart's storybook-only
`src/lib/extension/emojiMarker.ts` into coinray-chart as a registered `proExtensions` overlay —
it is now always available, and per-instance (previously properties were shared across overlays).
`extendData`: `text` (unicode emoji or `'svg:<path>'`), `textFontSize` (was `fontSize`),
`textColor` (was `color`). `totalStep: 2` (1 click).

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

## setVisibleRange / resetView Notes (12e80de)

- Both methods are now `async` and return `Promise<void>`. Always `await` them or handle the rejection.
- `setVisibleRange` uses `VisibleTimeRange` (unix **seconds**). The coinray-chart layer takes ms — the Superchart wrapper multiplies by 1000 automatically.
- Both are safe to call before the chart is ready — they wait for the API-ready signal internally (the same one `onApiReady` exposes).
- Both are queued during an in-flight init load. Only the latest queued call is applied when the load completes; earlier queued calls resolve without effect.
- `setVisibleRange` fetches missing history backward via `dataLoader.getRange` if `range.from` is before the loaded buffer. Requires `getRange` to be present on the DataLoader (see `SuperchartDataLoader` above).
- The `last_bar` zoom anchor is now clamped to the viewport — zooming while scrolled left no longer jumps the viewport. No API change, just a behavioral fix.
- **`SuperchartApi` interface gap**: `setVisibleRange` and `resetView` exist on the `Superchart` class but are not yet declared on the `SuperchartApi` interface. Code that holds a `SuperchartApi`-typed reference cannot call them without a cast. Reported to SC dev.

## useBackendIndicators — New Methods (8c245a1)

### `getActiveIndicatorByKlinechartsName`
```typescript
getActiveIndicatorByKlinechartsName(klineName: string): ActiveIndicator | undefined
```
Reverse-lookup from a klinecharts template name (format `BACKEND_<indicatorId>`) to the `ActiveIndicator`. Needed when klinecharts tooltip events report only the template name and you need the original backend indicator.

### `onHistory` on `IndicatorSubscription`
```typescript
subscription.onHistory?.((points: IndicatorDataPoint[]) => void)
```
Optional handler. Fires with historical backfill data. Unlike `onData` (which clears the store first), `onHistory` merges into the existing data store — preserving live data received before the backfill arrives.

Full `IndicatorSubscription` / `IndicatorMetadata` / `IndicatorDataPoint` / `IndicatorPlot` shapes are under "ScriptProvider" above — the same types serve `IndicatorProvider` and `ScriptProvider`.

## Overlay `save` field (8c245a1)

`createOverlay` now accepts `save?: boolean` (default `true`). Set `save: false` for transient overlays that should render on the chart but never be written to the `StorageAdapter` or restored on reload. Mirrors TradingView's `disableSave`.

Altrady note: All fluent-factory overlays (`createOrderLine`, `createPriceLine`, `createTradeLine`) never save by design — they bypass SC's overlay lifecycle entirely. Any new `superchart.createOverlay(...)` calls for app-driven transient overlays (e.g. replay cursor, measurement tool) should pass `{ save: false }`.

## Chart-Ready Milestones (69a41cf — `6bc991c`)

The single pre-69a41cf `onReady` callback was split into two milestones, both available as options and as instance methods:

| Milestone | When it fires | Safe to do |
|---|---|---|
| `onApiReady` | React API mounts; `getChart()` becomes non-null | subscribe to events, `createButton`/`createDropdown`, read/write feature flags, call `setSymbol`/`setPeriod`, access `sc.replay` |
| `onDataLoaded` | first dataset resolves and is in `getDataList()` | read concrete bars, place overlays at specific timestamps, snapshot via `getScreenshotUrl`, call `setVisibleRange` against known data |

Both forms (option and method) fire immediately if the milestone has already been reached, and the method form returns an unsubscribe function. Migration: replace every `onReady` with `onApiReady` unless the next step needs bar data — in which case use `onDataLoaded`.

## Chart Templates (69a41cf — `f43f048`, `98c1446`, `ea1dd96`)

Chart templates are named full-chart snapshots persisted via `StorageAdapter.*ChartTemplate` (TV "Chart Layout" semantics — distinct from study/drawing templates which act per-overlay/per-indicator).

- Six imperative methods on `SuperchartApi`: `list/save/apply/rename/duplicate/deleteChartTemplate` — see SuperchartApi block above.
- `applyChartTemplate` is a full chart swap: indicators, overlays, styles, pane layout, preferences, symbol, period.
- `saveChartTemplate(name)` snapshots the current chart (including `symbol`+`period`).
- `rename`/`duplicate` use adapter atomic methods if implemented; otherwise SC falls back to a load+save (+delete) sequence.
- Active template is tracked in `ChartState.activeChartTemplate`. When auto-save is on and `activeChartTemplate` is set, symbol/period/overlay/indicator edits dirty the template and re-save it (`ea1dd96`).
- UI is gated on the `chart_templates` feature flag AND `list/load/save/deleteChartTemplate` being present on the adapter.

## Indicator/Overlay Removal API (69a41cf — `1c05e9e`)

`sc.removeIndicator(name)` and `sc.removeOverlay(id)` are the canonical removal APIs. They route through the persistence pipeline so canvas, `StorageAdapter`, and the open indicator/overlay modal all update together. Direct `sc.getChart().removeOverlay(...)` still works but bypasses SC's lifecycle (no autosave, no modal sync) — use only for klinecharts-native overlays that SC doesn't track.

## Known Limitations

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

### Replay init no longer flashes future price (coinray-chart `52332ceb`)

Behaviour fix, no API change. Previously, during an engine-driven init load while in
playback mode, the raw candle straddling the replay cursor was painted briefly before the
sub-resolution partial replaced it — flashing price action from *past* the cursor onto the
screen. Now `Store._addData` checks `ReplayEngine.isAwaitingInit()` and skips its own paint;
`ReplayEngine._triggerDeferredLayout` does the full paint instead (visible range, crosshair,
indicators via `_recalcIndicators`, layout). Boundary-fetch also now runs *before*
buffer-fetch and merges into rather than overwrites the buffer, so the boundary candle
survives. Affects replay init and period-change flows only.

### Datafeed prerequisites for replay

| Requirement | Purpose |
|---|---|
| `Datafeed.getBars` must honour `from` when `countBack === 0` | `SuperchartDataLoader.getRange` (replay's only data-fetch path) always passes `countBack: 0`. A `getBars` that derives `from` from `countBack` will return wrong data here. |
| `Datafeed.getFirstCandleTime?` (optional) | Validates the cursor timestamp against data availability. Without it, cursors before data silently yield an empty chart instead of `no_data_at_time`. |

Append to the Type Glossary table:

| `ReplayEngine` | superchart / klinecharts | Replay playback controller (`sc.replay`) |
| `ReplayStatus` | superchart / klinecharts | `'idle' \| 'loading' \| 'ready' \| 'playing' \| 'paused' \| 'finished'` |
