# MCP chart tools → SuperChart parity — Tasks

Ordered so the app stays working after each task. Verification is manual (dev
server is always running; no build commands). TV path must stay byte-compatible
throughout. IDs reference `design.md`.

---

## T1 — ChartController: MCP surface + readyToDraw (R3/R4/R8)

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`

- Import `{setChartReadyToDraw}` from `~/actions/replay`; `{toPeriod, periodToResolution}`
  from `~/models/chart-resolutions`.
- Constructor opts: destructure `isMainChart = false`; store `this._isMainChart = isMainChart`.
- In `onApiReady` handler: after `this._setReadyToDraw(true)`, add
  `if (this._isMainChart) this.dispatch(setChartReadyToDraw(true))`.
- In `dispose()`: `if (this._isMainChart) this.dispatch(setChartReadyToDraw(false))`.
- New methods:
  - `getResolution()` → `periodToResolution(this._superchart.getPeriod())` (guard null).
  - `setResolution(res)` → `this._superchart.setPeriod(toPeriod(res))`.
  - `createUserOverlay(create)` → `this._superchart.createOverlay(create)`.
  - `removeUserOverlay(id)` → `this._superchart.removeOverlay(id)`.
  - `listUserOverlays()` → `this.getChart()?.getOverlays() ?? []`.

**Verify:** app loads, main chart renders. In console:
`ChartRegistry.getActive().getResolution()` returns e.g. `"60"`;
`ChartRegistry.getActive().setResolution("15")` changes the timeframe.

## T2 — Thread `isMainChart` to the main TT chart (R8/R9)

**Files:** `.../super-chart/charts/market-tab-chart.js`,
`.../super-chart/charts/trading-terminal-chart.js`

- `useMarketTabChart`: accept `isMainChart` param; merge into the `controllerOptions`
  passed to `useChartLifecycle` (`controllerOptions: {...controllerOptions, isMainChart}`).
- `TradingTerminalChart` → `useMarketTabChart({..., isMainChart: true})`.
- Leave `charts-page-chart` / grid variants unset (default `false`).

**Verify:** fresh onboarding (or force intro modal) on `/trade` under SC — the
"Start"/"Resume" button un-disables once the chart finishes loading. In console
`store.getState().replay.chartReadyToDraw === true` on the main chart; grid charts
don't flip it.

## T3 — SC drawing/indicator adapter (R4/R5)

**File (new):** `src/mcp/chart-bridge/superchart-adapter.js`

- `toScPoint`/`fromScPoint` (ISO↔ms).
- `toSuperchart(drawing)` → `{name, points, styles?, properties?, save}` per the
  kind→name + style tables in design. Handle Pro vs standard style routing and the
  `fibonacciSegment` naming trap.
- `fromSuperchart(overlay)` → canonical `{id, name, kind, points, style?, fill?, label?}`.
- `USER_DRAWING_OVERLAY_NAMES` set; `AVAILABLE_INDICATORS` list; `indicatorInputs(name)`
  best-effort default calcParams.

**Verify:** unit-reason only here (pure module). Exercised via T5.

## T4 — Unified chart handle (R1/R2/R6/R7)

**Files:** `src/mcp/chart-bridge/chart-handle.js` (new);
`src/mcp/chart-bridge/widget-registry.js` (expose `listTvCharts`/`getTvChart`,
keep `withActiveChart`/`withTvWidget`).

- `scHandle(controller, {mainChart})` — implements the uniform interface via
  controller methods + `getChart()` + `superchart-adapter` + `header.captureScreenshotForNote`.
- `tvHandle(tvState)` — wraps the existing TV calls verbatim (moved out of
  `tools/charts.js`), incl. `captureScreenshot` + `.png`.
- `listCharts()` — union: `listTvCharts()` (tagged `tradingview`) + one entry per
  `ChartRegistry` controller (tagged `superchart`), with `mainChart` derived from
  the active trading-tab id (read via a passed-in `getState`, or accept an
  `activeTabId` arg from callers to avoid importing redux here — decide at impl:
  prefer callers passing `activeTabId`).
- `getHandle(id)` / `resolveHandle(id)` — look up TV registry first, then
  `ChartRegistry`; return the tagged handle or throw `chart_panel_not_open`.

**Verify:** via T5 (`list_open_charts`, chart tools).

## T5 — Rewrite MCP chart tools for provider dispatch (R1–R7)

**Files:** `src/mcp/tools/charts.js`, `src/mcp/tools/context.js`

- `charts.js`: replace `withActiveChart`/`withTvWidget`/direct TV calls with
  `resolveHandle(id)` + handle methods for every tool
  (`set_chart_timeframe`, `list/toggle/remove/list_available` indicators,
  `list/add/add_many/remove/remove_many/clear` drawings, `take_chart_screenshot`,
  `open_market`). `pickChartId`/`waitForChart`/`resolveProvidedChartId` use the
  unified `listCharts`/`getHandle`. `list_chart_panels` → `{charts: listCharts(activeTabId)}`.
- `context.js`: import `listCharts` from `chart-handle`; pass `activeTabId`;
  update chart-id wording (drop "TradingView widget id" → "chart id").

**Verify (live, `claude mcp` @ `127.0.0.1:6850/mcp`):**
1. SC active → `list_open_charts` shows `rendered:true` + chartIds, one per grid widget, `mainChart` set.
2. `set_chart_timeframe`, `add_chart_drawing` (each kind), `list_chart_drawings`
   (ids round-trip), `remove_chart_drawing`, `clear_chart_drawings`,
   `list/toggle/remove/list_available` indicators, `take_chart_screenshot` (URL),
   `open_market` (switches tab, chart discoverable) — all succeed on a live SC chart.
3. Intro-modal Start button works (T2).
4. Switch provider to TV → full regression: every tool behaves as before.

## T6 — Self-review + review.md

Per megaprompt Phase 4/5.

---

## Notes / risks

- **Style fidelity** (arrow direction, rect fill, Pro-overlay read-back) is
  best-effort in v1 — create/list/remove/round-trip are the acceptance bar.
- **Indicator catalog** is a static list (SC `getSupportedIndicators` not
  re-exported) — log as an SC feature request; operational tools are full parity.
- **`activeTabId` plumbing**: prefer callers (`tools/*`) passing the active
  trading-tab id into `chart-handle` so the bridge module stays redux-free.
