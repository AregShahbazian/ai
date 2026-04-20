# SuperChart Integration Analysis

## Package Relationships

```
klinecharts (packages/coinray-chart/)
  ^ git submodule — a Coinray fork of KLineChart (canvas engine)
  |
superchart (root: src/lib/)
  ^ depends on klinecharts via workspace:*
  | adds: React UI (toolbars, modals, drawing bar), class API,
  |       DataLoader bridge, StorageAdapter, IndicatorProvider, ScriptProvider
  |
examples/client
  ^ demo app that uses superchart + coinrayjs for data
```

**In the desktop app, imports would look like:**
```js
import { Superchart, createDataLoader } from "superchart"
import "superchart/styles"
```

You'd never import `klinecharts` directly — `superchart` re-exports what you need (`createOrderLine`, `DEFAULT_OVERLAY_PROPERTIES`). The underlying klinecharts `Chart` instance is accessible via `chart.getChart()` when needed for low-level operations (overlays, scrolling, coordinate conversion).

---

## How SuperChart Compares to TradingView in This App

| Concern | Current (TradingView) | SuperChart |
|---|---|---|
| **Init** | `new TradingView.widget({datafeed, ...})` | `new Superchart({dataLoader, ...})` |
| **Data feed** | `DataProvider` (TV Datafeed interface) | `createDataLoader(datafeed)` — **accepts the same TV-compatible interface** |
| **Candle source** | `getCoinrayCache().fetchCandles()` | Same — wired through the datafeed adapter |
| **Real-time updates** | `datafeed.subscribeBars()` -> `onRealtimeCallback` | `dataLoader.subscribeBar()` -> callback — same concept |
| **Drawing candles programmatically** | `datafeed.onRealtimeCallback(candle)` | Call the `subscribeBar` callback with a candle |
| **Chart object** | `tvWidget.chart()` | `chart.getChart()` (klinecharts instance) |
| **Order/alert lines** | `chart.createOrderLine()` | `createOrderLine()` + `chart.createOverlay()` |
| **Drawings** | `chart.createShape()`, Save/Load adapter | `chart.createOverlay()`, `StorageAdapter` |
| **Indicators** | `custom_indicators_getter`, TV built-ins | klinecharts built-ins + `IndicatorProvider` (backend) |
| **Persistence** | `SaveLoadAdapter` (cloud API) | `StorageAdapter` interface (pluggable) |
| **Replay/playback** | Custom `ReplayController` | **No built-in** — must be built the same way |
| **Multi-chart** | Each widget gets its own TV instance | Each `new Superchart()` is fully independent |
| **Theme** | Color overrides object | `chart.setTheme('dark'/'light')` + `chart.setStyles()` |

---

## The Current Controller Architecture & Its Problems

### How it works today

1. **ReplayController** — created inside `useReplay()` hook, scoped to each chart's React tree via `ReplayContext`. Only the main Trading Terminal chart mirrors its controller to Redux (`state.replay.replayContextGlobal`) for access from thunks.

2. **DrawController** (quizzes) — uses a promise-based `loadTv()` pattern to wait for the TV widget to be ready, then stores `{chart, tvWidget, datafeed}` references. Draws candles by calling `datafeed.onRealtimeCallback(candle)`.

3. **DataProvider** — the datafeed that conditionally routes `getBars()` calls through ReplayController (replay mode), QuizController (quiz mode), or CoinrayCache (live mode). Holds bidirectional references to controllers.

### The problems

- **Controllers need chart access, but chart lives in React context** — ReplayController needs `datafeed.onRealtimeCallback` to draw candles. DrawController needs `{chart, tvWidget, datafeed}`. Both are wired ad-hoc with bidirectional references and promise hacks.

- **Redux mirroring is main-chart-only** — secondary charts (in /charts) have their own ReplayContext but there's no way to reach those controllers from outside their React tree.

- **DrawController and ReplayController duplicate candle-drawing logic** — both call `onRealtimeCallback(candle)` to push candles, but through different paths. No shared abstraction.

---

## What SuperChart Changes About This

**The key constraint:** SuperChart has **no public method to push candles directly**. All data must flow through the `DataLoader` interface — specifically the `subscribeBar` callback. This is actually architecturally cleaner than the current approach.

**What this means for the integration:**

The `subscribeBar` callback becomes the **single control point** for drawing candles. Whether it's live data, replay, or quiz playback, the pattern is the same: call the callback with a `KLineData` object. This naturally unifies what ReplayController and DrawController do today.

---

## Recommended Architecture for Integration

Given the challenges described above, here's what works best:

### 1. ChartController — a unified controller object per chart instance

Instead of scattering chart control across ReplayContext, DrawController, DataProvider, and ChartContext, introduce one object that wraps the Superchart instance and its datafeed:

```
ChartController {
  superchart: Superchart          // the lib instance
  datafeed: CoinrayDatafeed       // the datafeed adapter
  drawCandle(candle)              // calls subscribeBar callback
  setMode(live | replay | quiz)   // switches datafeed routing
  getChart()                      // klinecharts instance for overlays
  dispose()
}
```

This is the object that ReplayController, quiz code, trading overlays, and external components all interact with. It replaces `chartFunctions` and the `{chart, tvWidget, datafeed}` triple from the current ChartContext. Reactive UI state (readyToDraw, mainChart, chartSettings, etc.) stays in a React context (`SuperChartContext`) — ChartController only handles imperative chart access.

### 2. ChartController registry — solves multi-chart global access

```
ChartRegistry {
  main: ChartController               // Trading Terminal chart
  charts: Map<tabId, ChartController> // /charts page, keyed by ChartTab ID

  getMain()
  getByTabId(tabId)
}
```

This lives outside React (plain JS singleton or redux-accessible). Any controller, thunk, or component can access any chart's controller. No more "only main chart mirrors to redux" limitation.

### 3. Datafeed adapter with mode switching

The current DataProvider's conditional routing (`if replayMode... else if quiz...`) stays conceptually the same, but lives inside ChartHandle. The datafeed adapter:
- In **live mode**: routes `getBars`/`subscribeBar` to CoinrayCache
- In **replay mode**: routes `getBars` to ReplayController's candle buffer, `subscribeBar` callback is captured for ReplayController to call
- In **quiz mode**: routes `getBars` to QuizController's candle set, callback captured for DrawController

### 4. Candle drawing unification

Both ReplayController and DrawController converge on the same operation: calling `chartController.drawCandle(candle)`, which internally calls the captured `subscribeBar` callback. No more separate paths.

---

## Superchart Storybook — Overlay Development Environment

The Superchart repo (`$SUPERCHART_DIR/`) has a Storybook instance
for staging and proving overlay APIs in isolation before porting them to Altrady.

### Why

Direct overlay integration into Altrady proved difficult to debug — issues with the
klinecharts API (missing text labels, unknown overlay props, broken interactions)
are tangled with Altrady's Redux/context layers. Storybook isolates the chart API
question from the app integration question.

### Workflow

For each overlay type across phases:

1. **Stage in Storybook** — create a story with controls (toggles, number inputs)
   that exercises the overlay API. Fix any Superchart/klinecharts issues here.
2. **Port to Altrady** — use the working story as a copy-paste template for the
   corresponding `super-chart/overlays/*.js` file.

### Where it's used

| Phase | Overlay Stories |
|---|---|
| **3c** Market data | Break-even (priceLine + label), PNL handle (orderLine), Bid/Ask (priceLine pair), Trade markers (annotations) |
| **3a** Orders | Order lines (draggable orderLine), Edit orders (drag-to-modify) |
| **3b** Alerts | Price alerts (orderLine), Time alerts (verticalStraightLine), Trendline alerts (segment) |
| **3d** Grid bot | Grid levels (read-only lines), Draggable bounds |
| **3e** Scanner | Base shapes (multi-style overlays) |
| **3f** Custom shapes | Callouts, multipoint drawings |
| **5** Replay | Candle-by-candle drawing via DataLoader control |

### Location

```
$SUPERCHART_DIR/
├── .storybook/
│   ├── main.ts, preview.ts   # Storybook config
│   ├── helpers/               # SuperchartCanvas shared wrapper
│   ├── api-stories/           # API behavior stories
│   └── overlay-stories/       # one story per overlay type
├── examples/
│   └── client/                # existing demo app (unchanged)
```

### Running

```bash
cd $SUPERCHART_DIR
pnpm storybook   # port 6007
```

Requires `VITE_COINRAY_TOKEN` in `$SUPERCHART_DIR/.storybook/.env`.

---

## Phases

### Phase 1: Core Chart in Trading Terminal ✅ Done

Live SuperChart rendering in the widget slot — same market as the TT, live candles, theme support, bidirectional sync with Market Tab.

**Done:**
- `coinray-datafeed.js` — Datafeed adapter wrapping `getCoinrayCache()`
- `helpers.js` — `toSymbolInfo()`, `toPeriod()`, `periodToResolution()`, `SUPPORTED_PERIODS`
- `super-chart.js` — Widget component with Superchart init, symbol/resolution/theme sync (MarketTab → chart), resize handling
- `superchart` and `klinecharts` added as `link:` deps in `package.json` (symlinks to sibling repo)
- `onSymbolChange(callback)` — wired in `ChartController` to sync chart UI symbol changes back to MarketTab via `TradingTabsController`
- `onPeriodChange(callback)` — wired in `ChartController` to sync chart UI period changes back to MarketTab
- `onVisibleRangeChange(callback)` — wired in `ChartController` to persist viewport to MarketTab when `miscRememberVisibleRange` enabled

**Remaining:**
- **`onReady` migration** — Replace `requestAnimationFrame` polling in `super-chart.js` and `setInterval` polling in `replay-controller.js` with `superchart.onReady(callback)`. The SC library now provides `onReady` (constructor option and instance method) that fires when `getChart()` is guaranteed non-null. If already ready, fires immediately. Returns unsubscribe function. See `$SUPERCHART_DIR/.storybook/api-stories/OnReady.stories.tsx` and `$SUPERCHART_DIR/.storybook/overlay-stories/overlays/on-ready.ts` for the pattern.
- **Search symbol in SC** — SC's symbol search bar needs a search implementation. Currently no symbol search/resolution is wired — the search input exists in the SC UI but doesn't query Coinray markets. Needs a search adapter that queries the app's market data.

---

### Phase 2: ChartController + SuperChartContext Foundation

Before overlays can be built, we need the foundation they all depend on.

**Architecture decision: ChartController replaces ChartFunctions (not ChartContext)**

The current TV integration has two separate concerns mixed in `ChartContext`:
1. **Reactive UI state** — `mainChart`, `readyToDraw`, `chartSettings`, `replayMode`, `customIndicators`, etc. — consumed by components to conditionally render UI. This triggers re-renders.
2. **Imperative chart access** — `tvWidget`, `chart`, `datafeed`, `chartFunctions` — used to call methods on the TV instance. This should NOT trigger re-renders.

For SuperChart, we split these cleanly:

- **ChartController** is a thin plain-JS object (not a React component) that holds the imperative references overlays need: `superchart` instance, `datafeed`, and `getChart()` (klinecharts). It replaces `chartFunctions` + the `{tvWidget, chart, datafeed}` triple from the current ChartContext. It does NOT re-wrap every klinecharts method — overlays call the SuperChart/klinecharts APIs directly through it. Only add convenience methods where the raw API is awkward (e.g. `drawPriceLine()` combining `createOrderLine()` + styling in one call).
- **ChartController lives at `super-chart/chart-controller.js`** — colocated with the rest of the SuperChart integration, not in `src/models/`. It's chart-internal, not an app-wide model.
- **SuperChartContext** is a React context that provides both:
  - **Reactive state** (triggers re-renders): `readyToDraw`, `mainChart`, `chartSettings`, `replayMode`, etc.
  - **ChartController** (stable ref, does NOT trigger re-renders): created once, identity never changes. Components grab it from context and call methods imperatively.
- **ChartRegistry** (for multi-chart access in Phase 9) can go in `src/models/` later when needed. Not needed for Phase 2.

SuperChart already exposes much of what overlays need:
- `superchart.createOverlay()`, `superchart.setOverlayMode()` — overlay management
- `createOrderLine()` — exported from superchart package
- `superchart.getChart()` — klinecharts instance for visible range, candle data, coordinate conversion, etc.

**Do NOT mirror the TV hook structure.** The current TV `ChartContextProvider` is built on three hooks (`useTradingView`, `useTradingViewMarket`, `useVisibleRange`). These should not be copied for SuperChart:

- `useTradingViewMarket` — resolves coinraySymbol/currentMarket from props or MarketTabContext. Our widget already reads MarketTabContext directly. The prop-override logic (for grid bot, quiz) is Phase 9 — add it then, no hook needed.
- `useVisibleRange` — generic debounced range tracker, nothing TV-specific. But depends on `onVisibleRangeChange` callback (blocked). When it ships, the logic is ~15 lines, inline or reuse directly.
- `useTradingView` — 500 lines fighting TV's async iframe lifecycle: promise-based `loadTv()`/`resolveLoaded`, `headerReady` 5s timeout hack, `tvWidget.save()` color extraction, `reloadTradingView()` full destroy+recreate. None of this applies — SuperChart init is synchronous, setters work without reload, there's no iframe.

The current `super-chart.js` with its simple `useEffect` hooks is already closer to the right shape. It evolves into the `SuperChartContextProvider` in this phase — create ChartController on mount, wrap children in context, expose `readyToDraw`.

**Key tasks:**

1. **Create `ChartController`** — plain JS object created per chart instance:
   ```
   ChartController {
     superchart: Superchart          // the lib instance
     datafeed: CoinrayDatafeed       // the datafeed adapter
     getChart()                      // klinecharts instance for direct access
     drawCandle(candle)              // calls subscribeBar callback (for replay/quiz)
     setMode(live | replay | quiz)   // switches datafeed routing (for replay/quiz)
     dispose()
   }
   ```
   Convenience methods added as needed when implementing overlays — not upfront.

2. **Create `SuperChartContext`** — React context providing both reactive state and ChartController:
   ```
   SuperChartContext {
     // Reactive state (triggers re-renders)
     readyToDraw: boolean
     mainChart: boolean
     chartSettings: object           // from Redux
     replayMode: ...                 // later phases

     // Imperative access (stable ref, no re-renders)
     chartController: ChartController
   }
   ```

3. **`readyToDraw` gating** — gate overlay rendering on `getChart() !== null`, set via `superchart.onReady()` callback (replaces TV's multi-condition `readyToDraw`).

4. **Refactor SuperChart widget** to create ChartController on mount, provide via context.

**Files:**
- New: `super-chart/chart-controller.js`
- New: `super-chart/context.js`
- Modify: `super-chart/super-chart.js`

**Reference (current implementation):**
- `tradingview/controllers/chart-functions.js` — 200+ lines, all the drawing APIs (don't replicate 1:1, use as reference for what overlays need)
- `tradingview/context/chart-context.js` — current context shape (reactive state we need to carry over)
- `tradingview/context/context-provider.js` — how ChartContext is wired up (pattern for SuperChartContext provider)

---

### Phase 3: Overlays (All Types) ✅ Done

Migrate ALL chart overlay components from TV APIs to SuperChart. Each overlay component currently reads from `ChartContext` and calls `tv.chartFunctions.*` — they'll instead get `chartController` from `SuperChartContext` and call SuperChart/klinecharts APIs through it.

**3a. Order overlays (trading core)**
- **Orders** (`orders.js`) — pending order lines with price labels, color-coded buy/sell
- **Edit Orders** (`edit-orders.js`) — drag-to-modify order price with validation
- **Edit Entry Conditions** — entry condition price lines
- **Edit Entry Expirations** — expiration time markers

**3b. Alert overlays**
- **Alerts** (`alerts.js`) — price alert + time alert lines with edit/delete
- **Edit Alerts** (`edit-alerts.js`) — interactive alert creation/modification

**3c. Market data overlays**
- **Bid/Ask** (`bid-ask.js`) — live bid/ask price lines from market data stream
- **Break-even** (`break-even.js`) — position break-even point with PnL visualization
- **Trade markers** (`trades.js`) — closed trade entry/exit visualization

**3d. Grid bot overlays**
- **Grid Bot Orders** (`grid-bot-orders.js`) — read-only order lines for grid levels
- **Grid Bot Prices** (`grid-bot-prices.js`) — draggable handles for upper/lower bounds, stop-loss, take-profit with `onMove` callbacks

**3e. Scanner overlays**
- **Bases** (`bases.js`) — base scanner visualization with multiple shape types (respected/not respected/not cracked)

**3f. Custom shapes**
- **Callouts** (`callout.js`) — text annotations on chart
- **Multipoint drawings** (`multipoint-drawings.js`) — multi-point shape support
- **Custom indicator shapes** (`custom-indicators.js`) — shapes drawn by custom indicator logic

**Files:**
- New: `super-chart/overlays/` directory with one file per overlay type
- Modify: `super-chart/super-chart.js` — compose overlay components

**Reference (current TV implementation):**
- All files in `tradingview/overlays/` — direct 1:1 migration targets
- `tradingview/controllers/chart-functions.js` — the API they all call

---

### Phase 4: Chart Interaction (Context Menu, Hotkeys, Screenshot, Header Buttons)

Features that let users interact with the chart beyond just viewing candles.

**4a-1. Chart context menu** (right-click on chart background)
Current implementation: `context/use-on-context-menu.js`

Context-dependent menu items:
- Trading mode: Create Buy/Sell Order at price, Set Break-even Start/End
- Alert mode: Create New Alert at price
- Replay mode: Start Replay, Go Back, Play/Pause, Speed Up/Down, Stop
- Quiz mode: Set Solution Start/End time
- Grid bot backtest: "Set Backtest Start" / "Set Backtest End" at clicked time (`sc-grid-bot-backtest`)

The context menu UI will be implemented in Altrady with React. ✅ Plumbing landed in `[sc-chart-ctx-menu]` — right-click on the chart background opens an empty `ContextMenuPopup`, consumed through `InteractionController`'s `onRightSelect` in persistent mode. Concrete entries (trading, alerts, replay start, step-back jump, etc.) are delivered in the follow-up `[sc-chart-ctx-menu-options]`.

**4a-2. Overlay context menu** (right-click on overlays)
TV had per-overlay right-click menus (e.g. Delete on trendline/time alert shapes). SC overlays don't have built-in context menus but do expose `onRightClick` callbacks. The overlay context menu UI will be implemented in Altrady with React, triggered by overlay `onRightClick` callbacks. See risk #8.

**4b. Hotkeys**
Current implementations:
- `tradingview-hotkeys.js` — chart-specific shortcuts
- `charts-hotkeys.js` — global chart shortcuts (/charts page)
- `replay/replay-hotkeys.js` — replay-specific shortcuts

**4c. Screenshot**
Current: `screenshot.js` — calls `tvWidget.onScreenshotReady`, shows modal for sharing.
SuperChart: `chart.getScreenshotUrl()` already exists — wire to the existing screenshot sharing modal/UI.

**4d. Custom header buttons**
Current: `header.js` — uses `chartFunctions.createButton()` (which calls `tvWidget.createButton()`) to inject custom buttons into the TV header bar:
- **Alert** — create price alert at current price
- **Buy / Sell** — start buy/sell order (main chart only, hidden during quiz)
- **Replay** — pick replay start time (hidden during certain quiz modes)
- **Settings** — open chart settings modal

Also: `action-buttons.js` — trading action buttons (Submit, Reset, Cancel).

Buttons are conditionally shown/hidden based on `mainChart`, `gridBotChart`, `replayMode`, `questionController.active`, and `backtestIsFinished`. The Replay button text is highlighted when `selectingStartTime` is active.

SuperChart has `superchart.createButton()` — wire the same button set through ChartController. The conditional visibility/highlight logic carries over.

**Files:**
- New: `super-chart/context-menu.js`
- New: `super-chart/hotkeys.js`
- New: `super-chart/screenshot.js`
- New: `super-chart/header-buttons.js`
- Modify: `super-chart/super-chart.js`

**Blocked by SuperChart library:**
- `onTimezoneChange(callback)` — sync timezone changes from chart UI back to Redux `chartSettings.timezone`

---

### Phase 5: Replay System

The app has a sophisticated replay/backtest system. SuperChart has no built-in replay — it must be built on top via DataLoader control.

**5a. Datafeed mode switching**
Add mode routing to CoinrayDatafeed: `setMode('live' | 'replay' | 'quiz')`.
- Live: routes to CoinrayCache (current behavior)
- Replay: routes `getBars` to ReplayController's candle buffer, captures `subscribeBars` callback
- Quiz: routes `getBars` to QuizController's candle set, captures callback

**5b. Port ReplayController**
Current: `controllers/replay/replay-controller.js`
- `REPLAY_MODE.DEFAULT` — time-based candle-by-candle replay
- `REPLAY_MODE.SMART` — smart trading replay with live order execution
- Play/pause/stop controls, speed adjustment
- Currently calls `chart.chartModel().mainSeries().bars()` — needs klinecharts equivalent

**5c. Port Replay UI**
- `replay/replay-controls.js` — play/pause/speed controls
- `replay/replay-timelines.js` — visual timeline
- `replay/replay-position.js` — current position indicator
- `replay/replay-hotkeys.js` — keyboard shortcuts
- `replay/replay-mode-dialog.js` — mode selection

**5d. Port Replay Trading**
- `ReplayTradingController` — trade execution during replay
- `SmartReplayController` — advanced replay scenarios
- `ReplaySmartTradingController` — smart position management
- `ReplayBacktests` widget — backtest results display

**Files:**
- Modify: `coinray-datafeed.js` — add mode routing
- Modify: `super-chart/chart-controller.js` — expose drawCandle(), setMode()
- New/Modify: `super-chart/replay/` directory
- Modify: replay controllers to target ChartController instead of TV widget

---

### Phase 6: Persistence (StorageAdapter)

Save and restore chart state (indicators, drawings, user preferences). **Must come before Quiz (Phase 7)** — the quiz system depends on `SaveLoadAdapter` to persist drawings on quiz questions (`QuestionSaveLoadAdapter`, `EditQuestionSaveLoadAdapter` both extend `LocalSaveLoadAdapter`).

**Current system:**
- `SaveLoadAdapter` (`controllers/save-load-adapter.js`) — server-side via `/api/v2/tradingview_charts`
  - Chart layouts, study templates, chart templates, drawing templates
  - `saveLineToolsAndGroups()` — separate drawings storage
- `LocalSaveLoadAdapter` (`controllers/local-save-load-adapter.js`) — offline/non-trading users
- `QuestionSaveLoadAdapter` / `EditQuestionSaveLoadAdapter` (`models/quiz/question-save-load-adapters.js`) — quiz-specific, extend `LocalSaveLoadAdapter`
- Redux: `actions/chart-settings.js` — `getTvStorage()`, `updateTvStorage()`, `deleteTvStorage()`

**SuperChart approach:**
1. Implement `StorageAdapter` interface — route save/load to the existing API endpoints or Dexie (IndexedDB)
2. Wire to Superchart constructor via `storageAdapter` + `storageKey` (per market or per tab)
3. Create quiz-specific StorageAdapter variants that mirror `QuestionSaveLoadAdapter` / `EditQuestionSaveLoadAdapter`
4. Decide: migrate existing saved TV layouts, or clean start for SuperChart state

**Files:**
- New: `super-chart/storage-adapter.js`
- New: `super-chart/quiz-storage-adapter.js`
- Modify: `super-chart/super-chart.js` — pass storageAdapter to constructor

---

### Phase 7: Quiz System

The quiz/training system uses the chart for interactive questions. Separate from replay because it has its own controllers, drawing modes, and UI. **Depends on Phase 6 (Persistence)** — quiz controllers create `QuestionSaveLoadAdapter` / `EditQuestionSaveLoadAdapter` instances for drawing persistence.

**Key components to port:**
- **DrawController** (`models/quiz/draw-controller.js`) — candle-by-candle animation via `datafeed.getDrawCandleCallback()`
- **Edit drawings** (`quiz/edit-drawings.js`) — drawing mode for quiz question creation
- **Play drawings** (`quiz/play-drawings.js`) — animated quiz playback
- **Preview drawings** (`quiz/preview-drawings.js`) — preview mode
- **Decision point arrow** (`quiz/decision-point-arrow.js`) — arrow markers
- **Question timelines** (`quiz/questions-timelines.js`) — timeline visualization
- **Quiz controls** (`quiz/quiz-controls.js`) — UI controls
- **Quiz question chart** (`containers/quizzes/edit/quiz-question-chart.js`) — chart used in quiz editor
- **Question save/load adapters** (`models/quiz/question-save-load-adapters.js`) — rewire to use SuperChart StorageAdapter from Phase 6

**Files:**
- Modify: `models/quiz/draw-controller.js` — target ChartController
- Modify: `models/quiz/question-save-load-adapters.js` — use SuperChart StorageAdapter
- New: `super-chart/quiz/` directory for quiz-specific chart components

---

### Phase 8: Custom Indicators

Migrate the app's custom TradingView indicators to klinecharts.

**Current custom indicators** (`controllers/ci.js`):
- `rsiStoch` — RSI + Stochastic oscillator (PineJS study definition)
- `previousCandleOutliers` — previous candle outlier detection with custom shapes
- `smartMoney` — smart money flows (feature-gated: "essential_indicators")
- `Willams21EMA13` — Williams EMA study

**klinecharts built-in indicators** cover standard TA (MA, EMA, MACD, RSI, Bollinger, etc.) so most TV built-in studies have direct equivalents. The 4 custom indicators above need to be rewritten using `registerIndicator()`.

**Chart color overrides & settings integration:**
- Map `chartSettings.chartColors[theme]` to `setStyles()` on init and theme change — requires investigating compatibility between our color keys and klinecharts' `Styles` type
- `reducers/chart-settings.js` — Redux state for chart colors, overlay visibility toggles
- `actions/chart-settings.js` — mutations, TV storage get/update/delete
- Map relevant settings to SuperChart's `setStyles()` API

**Files:**
- New: `super-chart/indicators/` directory
- Modify: chart settings actions/reducers where they reference TV-specific APIs

---

### Phase 9: Secondary Chart Instances

The app uses TradingView charts in multiple places beyond the main Trading Terminal. Each needs SuperChart equivalents.

**Blocker:** SC's global singleton store (`chartStore.ts`) prevents multiple SC instances from coexisting — the second instance overwrites the first's state. This phase (especially 9a /charts) is the most impacted by this limitation, since the charts page mounts multiple independent chart instances simultaneously. Blocked on SC library multi-instance support (reported with reproduction story `API/MultiChart`).

**9a. /charts page** — multi-tab chart-only view
- Currently uses `DefaultTradingWidget` (orders, alerts, trades, bid/ask, break-even, bases, enhancements)
- Each tab is an independent chart instance with its own `ChartLayoutsController`
- Managed by: `containers/charts.js`, `models/flex-layout/chart-layouts-controller.js`, `models/market-tabs/chart-tab.js`

**9b. Grid bot chart** — SC integration done (`sc-grid-bot`, `sc-grid-bot-backtest`)
- `GridBotSuperChartWidget` in `super-chart/grid-bot-super-chart.js`
- TV fully replaced by SC in overview, settings, and backtest pages
- Overlays: grid bot prices (draggable), grid bot orders, trades, backtest time markers
- **Known issue:** SC global singleton store prevents two SC instances from coexisting. When backtest modal opens over settings page, both SC charts conflict (overlays leak between instances). Blocked on SC library multi-instance support. Reproduction story: `API/MultiChart` in SC storybook. Temporary toggle `SHOW_SETTINGS_CHART` in `grid-bot-settings.js` can disable the settings chart to test backtest in isolation.

**9c. Trading preview — chart settings modal preview** ✅ done (`sc-settings-preview`)
- SC variant `PreviewSuperChartWidget` (`super-chart/preview-super-chart.js`) replaces
  the TV `tradingpreview.js` at the top of the chart settings modal. Fixed symbol
  (`BINA_USDT_BTC`), fixed resolution (`60`), hardcoded candles in `preview-candles.js`.
- Per-tab overlay configs in `super-chart/preview-tab-configs.js`: Open Orders / Closed
  Orders / Positions / Alerts / Bases / Quiz+Replay / Misc each declare `rightOffsetPx`,
  `priceRange`, and a `renderOverlays()` JSX with the relevant live overlay components
  fed hardcoded dummy data (`preview-trading-data.js`).
- Live setting/color changes flow through without Save: modal passes merged
  `{...chartSettings, ...previewSetting}` to the preview. `ChartController` gets
  `setChartSettingsOverride()` + `setColorsOverride()` (both applied during render, not
  in a post-commit effect, so child overlay useDrawOverlayEffects see fresh values).
  Overlays read chartSettings from `useSuperChart().chartSettings` (was Redux).
- Interaction is disabled globally: `ChartController({nonInteractive: true})` scrubs
  callbacks on every overlay/order-line at the base-controller chokepoint.
- SC's single-instance limitation (see 9b) handled the same way as grid-bot settings:
  TT main chart unmounts via `GridItemSettingsContext.previewShown` while the preview
  is up. `tradingpreview.js` / `DummyDataProvider` untouched (kept until Phase 9c
  cleanup; safe since no consumer imports them anymore).

**9d. Quiz question chart** — chart in quiz editor
- `containers/quizzes/edit/quiz-question-chart.js`
- Uses `DefaultTradingWidget` with quiz-specific overlays

**9e. Other chart consumers**
- `containers/training/chart.js` — training module (read-only)
- `containers/customer-service/account/position.js` — CS position analysis
- `containers/market-explorer/currency/currency-overview/currency-overview-chart.js` — market overview

**Files:**
- Modify: each consumer to use SuperChart widget variant instead of TV widget
- New: `super-chart/variants/` — DefaultSuperChart, GridBotSuperChart, PreviewSuperChart

---

### Phase 10: CandleChart Migration ✅ (coexistence removed)

**History:** Phase 10 originally introduced a TV/SC coexistence layer — a
toggleable `CandleChart` widget, a dev-widget guard, and a layout migration
from `CenterView` to `CandleChart`. The coexistence pieces (toggle UI,
`useSuperChart` Redux state, `DevWidgetGuard`) were removed in Phase 5 when
the Trading Terminal switched to SC-only. What remains from Phase 10 is
the layout migration and the `CandleChart` wrapper, which now renders SC
for the Trading Terminal and TV for the Charts page pending that page's
own SC migration.

See `phase-10/review.md` for the full list of Phase-10 pieces that were
undone.

#### 10a. CandleChart wrapper ✅ (toggle removed)

`CandleChart` is a thin wrapper that renders SC in the Trading Terminal
and TV in the Charts page, gated by the `toggleable` prop passed by the
grid item:

- **TT (`toggleable=true`):** always renders `SuperChartWidgetWithProvider`.
  No toggle UI, no Redux state read.
- **Charts page (`toggleable=false`):** always renders `DefaultTradingWidget`
  (TV). Will be replaced by SC when the Charts page migrates.
- **Other pages** (quiz, customer service, shared bots, grid bots) mount
  their chart widgets directly — no `CandleChart` indirection.

#### 10b. ~~SC Single-Instance Guard~~ (removed)

The `DevWidgetGuard` and standalone `SuperChart` dev widget were removed
from the grid layout. The Trading Terminal now has exactly one SC instance
(inside `CandleChart`); legacy layouts with `SuperChart` nodes resolve to
`UnknownWidget`.

#### 10c. Layout Migration ✅

`CenterView` → `CandleChart` in all layout types:
- **TT + Charts page:** `FlexLayoutsController.migrateCenterViewToCandleChart` runs
  in `loadLayouts`, saves migrated layouts to backend immediately. Idempotent.
- **Mobile:** `stateMergeAndReset` in layout reducer renames `CenterView` →
  `CandleChart` and removes `SuperChart` from `widgetTabs` on rehydrate.
- **Default layouts:** updated in code (`default-trading-layouts.js`,
  `default-chart-layouts.js`).
- **Legacy grid-to-flex migration:** creates `CandleChart` nodes directly.
- **CenterView removal:** removed from `WIDGET_SETTINGS`, `grid-content.js`,
  `grid-item-settings.js`, `grid-item-refresh.js`, translations. Only remains
  in migration/legacy code.

#### 10d. Screenshots ✅

Notes screenshots are SC-only via `ChartRegistry.getActive()`. In the
Trading Terminal this always succeeds since `CandleChart` always renders
SC. The "Toggle to SuperChart" fallback path no longer triggers in TT.
Warning when no SC is active (no CandleChart in layout): yellow warning
"Activate the Chart widget" with widget dropdown highlight.

#### 10e. ~~TV Feature Restoration~~ (no longer applicable)

The TV feature restoration table (grid bot pages, screenshots, hotkeys)
was relevant only while TV and SC coexisted in the TT. Since Phase 5
decommissioned TV from the TT entirely, these items are either resolved
(grid bots are SC-only, screenshots are SC-only, hotkeys migrated in
Phase 4) or moot.

#### 10f. TV Removal (in progress, pre-release)

Trading Terminal: ✅ done (Phase 5 decommission). Remaining TV consumers
are the Charts page and non-TT contexts (quizzes, customer service,
training, market explorer). Full removal before release:

1. ✅ `chartSettings.useSuperChart` Redux state removed
2. ✅ `DevWidgetGuard` and standalone `SuperChart` dev widget removed
3. Migrate Charts page: `CandleChart` drops the `toggleable` prop and
   always renders SC
4. Migrate remaining TV consumers (quiz, CS, training, market explorer)
5. Delete `vendor/tradingview/` (6 vendored builds)
6. Remove CopyWebpackPlugin entry for tradingview
7. Delete `center-view/tradingview/` widget directory and all sub-files
8. Delete `DataProvider`, `SymbolsStorage`, `SaveLoadAdapter`, `ChartFunctions`
9. Clean up `ChartContext`, `VisibleRangeContext` if no longer needed
10. Remove TV chart version management from `actions/chart-settings.js`
11. Remove old `visibleRange` (duration-in-seconds) from market tab state and rename
    `visibleRangeFromTo` to `visibleRange` — SC stores `{from, to}` which replaces TV's
    duration format

---

### Phase 11 (Future): Server-Side Features

Optional — requires deploying the SuperChart WebSocket server alongside the app.

**11a. IndicatorProvider** — backend-computed indicators
- Server subscribes to Coinray candles, executes TA-Lib computations
- Pushes `indicatorTick` updates via WebSocket
- History backfill when chart scrolls left
- Preset indicators: TDI, Stochastic, RSI, MACD, etc. stored in SQLite

**11b. ScriptProvider** — Pine Script editor
- Server-side Pine Script parser, compiler, and executor
- Real-time script re-execution on new candles
- Script save/load from server

**11c. Deployment**
- Sidecar process in Electron, or hosted WebSocket server for web builds
- Feature-gated: only enable if server connection available

---

## TradingView Integration Audit (Complete File List)

For reference, here is every file in the codebase that touches TradingView APIs:

**Core chart system** (`widgets/center-view/tradingview/`):
- `tradingview.js` — entry points: `MainChartTradingWidget`, `DefaultTradingWidget`, `GridBotTradingWidget`
- `tradingview-component.js` — TV widget mounting/lifecycle
- `tradingview-enhancements.js` — UI tweaks
- `tradingview-hotkeys.js` — chart keyboard shortcuts
- `screenshot.js` — chart screenshot capture
- `price-time-select.js` — price/time selection UI
- `action-buttons.js` — trading action buttons (Submit, Reset, Cancel) → **Phase 4e**
- `header.js` — chart header custom buttons (Alert, Buy/Sell, Replay, Settings) → **Phase 4e**
- `settings.js` — chart appearance settings modal

**Controllers:**
- `controllers/setup.js` — `setupTradingview()`, TV widget creation
- `controllers/data-provider.js` — `DataProvider` (Datafeed implementation)
- `controllers/symbol-storage.js` — `SymbolsStorage` for symbol resolution
- `controllers/chart-functions.js` — drawing API wrapper (used by ALL overlays)
- `controllers/save-load-adapter.js` — server-side persistence
- `controllers/local-save-load-adapter.js` — offline persistence
- `controllers/ci.js` — custom indicators registry
- `controllers/ci/rsi-stoch.js`, `previous-candle-outliers.js`, `smart-money.js` — custom indicator implementations

**Context:**
- `context/chart-context.js` — ChartContext definition
- `context/context-provider.js` — ChartContextProvider
- `context/use-trading-view.js` — core TV setup hook
- `context/use-trading-view-market.js` — market sync hook
- `context/use-on-context-menu.js` — right-click menu
- `context/use-visible-range.js` — viewport range tracking
- `context/use-replay.js` — replay hook

**Overlays:**
- `orders.js`, `alerts.js`, `trades.js`, `bid-ask.js`, `break-even.js`
- `grid-bot-orders.js`, `grid-bot-prices.js`, `bases.js`
- `callout.js`, `multipoint-drawings.js`, `custom-indicators.js`
- `edit-orders.js`, `edit-alerts.js`

**Replay:**
- `replay/replay-controller.js`, `replay-controls.js`, `replay-timelines.js`
- `replay/replay-position.js`, `replay-hotkeys.js`, `replay-mode-dialog.js`
- Related: `ReplayTradingController`, `SmartReplayController`, `ReplaySmartTradingController`

**Quiz:**
- `quiz/edit-drawings.js`, `play-drawings.js`, `preview-drawings.js`
- `quiz/decision-point-arrow.js`, `questions-drawings.js`, `questions-timelines.js`, `quiz-controls.js`

**Outside tradingview/ dir:**
- `containers/charts.js` — /charts page (multi-tab charts)
- `containers/trade/trading-terminal/widgets/center-view/tradingpreview.js` — demo chart
- `containers/bots/grid-bot/backtest/backtest-content.js` — grid bot backtest chart
- `containers/bots/grid-bot/grid-bot-overview.js` — grid bot overview chart
- `containers/quizzes/edit/quiz-question-chart.js` — quiz editor chart
- `containers/training/chart.js` — training chart
- `containers/customer-service/account/position.js` — CS position chart
- `containers/market-explorer/currency/currency-overview/currency-overview-chart.js` — market overview
- `containers/trade/charts-hotkeys.js` — global chart hotkeys
- `actions/chart-settings.js` — chart settings + TV storage API
- `reducers/chart-settings.js` — chart settings Redux state
- `actions/customer_service/tradingview-charts.js` — CS chart data API

---

## SuperChart API Requests (for SuperChart dev)

Callback methods needed on `SuperchartApi`. Each should return an unsubscribe function.

| Method | Needed by | Description |
|---|---|---|
| `onSymbolChange(callback)` | Phase 1 | Fires when user picks a symbol from the chart UI. Callback receives `SymbolInfo`. |
| `onPeriodChange(callback)` | Phase 1 | Fires when user picks a period from the chart UI. Callback receives `Period`. |
| `onVisibleRangeChange(callback)` | Phase 1 | Fires on scroll/zoom. Callback receives `{from, to}` timestamps. |
| `onTimezoneChange(callback)` | Phase 4 | Fires when user changes timezone from the chart UI. Callback receives timezone string. |

The internal store already has `subscribeSymbol`, `subscribePeriod`, etc. — these callbacks would be thin wrappers exposing them via the public `SuperchartApi` interface.

Note: `onReady` is now available — constructor option and instance method. The instance method returns an unsubscribe function and fires immediately if the chart is already ready. Used to gate operations that need `getChart()` (overlay init, replay engine access). Replaces the polling hacks in `super-chart.js` and `replay-controller.js`.

---

## Backlog

Non-blocking items that don't fit neatly into a phase and are best tackled after core migration is complete.

- **Drawing selection toolbar (TV "Chart Enhancements")** — `tradingview-enhancements.js` injects custom buttons into TV's floating drawing toolbar via iframe DOM manipulation: drawing template save/load/apply, and trendline-to-alert conversion (bell icon on trendline/ray selection). Deeply TV-specific (reaches into `_iFrame.contentDocument`, `_selection._items`, `_undoModel`). Needs SC dev input on whether SC exposes a drawing selection toolbar, selected overlay properties, and an extension point for custom buttons. Was Phase 4d.

---

## Key Risks

1. **Overlay migration is the biggest cost** — 25+ components using TV-specific APIs (`createOrderLine`, `createShape`, `createStudy`). Each needs translation to klinecharts overlay API. The `ChartFunctions` class alone is 200+ lines of drawing API that must be re-implemented.

2. **Replay has no built-in support** — must be reimplemented via DataLoader control. The architecture is actually cleaner (single callback), but the replay trading simulation, smart replay, and backtest features on top are significant. The current ReplayController uses `chart.chartModel().mainSeries().bars()` which has no klinecharts equivalent.

3. **No `_addData()` escape hatch** — klinecharts' data store is private. If you hit a case where the DataLoader pattern doesn't work (e.g., inserting candles mid-history for quiz), you'd need to fork klinecharts further or reload the chart.

4. **Two React roots** — SuperChart creates its own React root internally. The desktop app has its own React tree. They won't share context. Communication must go through the `Superchart` class API, not React context.

5. **6 chart consumer sites** — beyond the main TT, charts are used in /charts page, grid bots, quiz editor, training, CS tools, and market explorer. Each has different overlay requirements and may need its own SuperChart variant.

6. **Custom indicators use PineJS** — the 4 custom indicators (rsiStoch, previousCandleOutliers, smartMoney, Willams21EMA13) are written as PineJS study definitions. They must be rewritten as klinecharts `registerIndicator()` calls — different API shape entirely.

7. **Persistence schema mismatch** — TV's SaveLoadAdapter stores drawings/studies/templates in a TV-specific format via `/api/v2/tradingview_charts`. SuperChart's `StorageAdapter` has its own `ChartState` schema. Existing user data either needs migration or a clean break.

8. **No per-overlay interaction UI** — TV drawing entities have built-in interaction affordances: select highlight, right-click context menu with Delete, property dialogs. SC overlays have none of this — they support callbacks (`onClick`, `onPressedMoveEnd`, `onRightClick`) but no built-in UI. In practice this means delete/edit for overlays like trendline alerts and time alerts must be routed through the alert form UI rather than direct on-chart interaction. Affects Phase 3 overlays (alerts, drawings) and Phase 4a-2 (overlay context menu). Overlay `onRightClick` callbacks are available — the context menu UI will be built in Altrady with React (see §4a-2).

---

## Mobile View

The app has a mobile layout (`screen === SCREENS.MOBILE`) with chart-specific behavior that diverges from desktop. This is easy to forget during SC integration — every phase should be tested on mobile.

**Known mobile-specific behavior in the current TV integration:**

- **Action buttons bar** (`action-buttons.js`) — mobile-only bar below the chart replaces the desktop sidebar trade/alert forms. Shows contextual buttons: "Create Alert" + "Trade" (initiate mode), Reset + Place Order (trade form active), Reset + Save Alert (alert form active). Switches based on `state.layout.mobile.lastTouchedForm`.
- **Pick Replay Start button** (`pick-replay-start-button.js`) — different UI on mobile (appears in action buttons bar instead of header).
- **Replay start** (`header.js`) — passes `screen === SCREENS.MOBILE` flag to `handleSelectReplayStartTimeClick`, which changes the selection flow.
- **Chart container styling** (`tradingview-component.js`) — mobile gets extra `box-shadow` dividers on the controls bar.
- **TV widget preset** — there's a commented-out mobile preset (`"mobile"`) in `use-trading-view.js` for tablet/mobile device types.

**Rule:** When implementing any SC feature that has UI below or around the chart (buttons, controls, toolbars), check `ScreenContext` for mobile-specific rendering in the TV version.

---

## Pending / Needs Investigation

Items that were attempted or considered but need more work. Check back on these periodically.

- **Timezone init** — Attempted reading from Redux `chartSettings.timezone` (never actually set — TV's `editChartSettings(timezone)` call passes a string instead of an object) and from TV's `localStorage["tradingview.chartproperties"]` (didn't work). SuperChart's `timezone` constructor option needs investigation — may need SuperChart dev input on how timezone is applied internally, or the value format may differ from what TV stores. Revisit when `onTimezoneChange` callback ships (Phase 4).
- **Timezone sync between TV and SuperChart** — blocked on `onTimezoneChange` callback + fixing the TV Redux bug (`editChartSettings` should be called with `{timezone}` object, not bare string).
- ~~**Locale**~~ — RESOLVED: no longer crashes. SC labels stay in English for non-en locales, which is acceptable — Altrady's own overlays/buttons/modals are translated via i18n yaml files.
- **Replay session persistence across remount** — when SC chart remounts (mobile↔desktop toggle, page navigation), the replay session is lost. Redux state (startTime, time, trades) survives, and the SC engine has `restoreSession(startTime, currentTime, endTime)` to re-enter at the exact position. Implementation needs: `destroy()` stops clearing Redux, `init()` detects existing session and restores, symbol mismatch check on restore. See `ai/superchart-integration/phase-5/deferred.md` and `Superchart/ai/features/replay-restore-session.md`.
