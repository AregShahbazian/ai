---
id: mcp-sc-bridge
---

# MCP chart tools → SuperChart parity — PRD

## Problem

The MCP server (merged from 5.4.x) exposes 13 chart-scoped tools. They are
**TV-only**: under the SuperChart (SC) provider `list_open_charts` returns
`chartId: null, rendered: false` for every tab and every chart tool fails with
`chart_panel_not_open`. Verified live on `feature/superchart-integration`
(2026-07-06) with the desktop app running SC.

Non-chart MCP tools (positions, bots, alerts, watchlists, markets, notes)
already work under SC and are out of scope.

## Background (current architecture)

- `src/mcp/chart-bridge/widget-registry.js` — a private `Map` of TV state
  objects. `registerChart(id, tv)` is called ONLY from the TV context provider
  (`.../center-view/tradingview/context/context-provider.js:74`). The SC widget
  never registers, so the map is empty under SC.
- Registry helpers `withActiveChart` / `withTvWidget` assume `tv.tvWidget` and
  `tvWidget.activeChart()` (TV API).
- `src/mcp/tools/charts.js` — the 13 tools, built on those helpers plus
  TV-specific calls (`setResolution`, study APIs, shape APIs).
- `src/mcp/tools/context.js` — `list_open_charts`, `resolve_active_chart`,
  `get_session_context`; all read `listCharts()` from the TV registry.
- `src/mcp/drawings/adapters/tradingview.js` — canonical drawing schema ↔ TV
  shape conversion. No SC adapter exists.
- `take_chart_screenshot` imports the TV screenshot module directly.

The SC branch already provides the pieces the SC path must build on:

- `ChartRegistry` (`src/models/chart-registry.js`) — the branch's canonical
  registry. `ChartRegistry.getActive()` / `.get(id)` return the live
  `ChartController`. Registration already happens per chart widget
  (`super-chart.js:120`, `trading-terminal-chart.js:66`).
- SC screenshot: `widgets/super-chart/screenshot.js` — `takeScreenshot(chartId, cb)`
  (already provider-switched in notes-form).
- Chart provider switch: `widgets/chart-provider.js` (`CHART_PROVIDER`, redux
  `state.chartSettings.chartProvider`).

## Goal

All 13 chart tools work under BOTH providers, dispatching on the active chart
provider. The TV path stays byte-compatible (it ships in 5.4.x). The SC path
resolves charts through `ChartRegistry` and produces identical tool output
shapes.

## Requirements

Tools are grouped by capability. For every tool, the SC result shape (JSON
returned to the MCP client) MUST match the TV result shape — same keys, same
`chartId` semantics, same error codes (`chart_panel_not_open`, etc.). Callers
must not need to know which provider is active.

### R1 — Chart discovery & resolution

- `list_open_charts`, `list_chart_panels`, `resolve_active_chart`, and the
  chart portion of `get_session_context` MUST enumerate live SC charts:
  `rendered: true`, a real `chartId`, `coinraySymbol`, current `resolution`,
  `ready`, and `mainChart` — one entry per rendered SC chart widget.
- Resolution MUST go through `ChartRegistry` (the branch's canonical registry).
  Do NOT grow the MCP widget-registry into a second parallel registry for SC.
- `resolve_active_chart` MUST return the active SC chart
  (`ChartRegistry.getActive()`).

### R2 — Provider-dispatched execution

- Every chart tool MUST dispatch on the active chart provider
  (`state.chartSettings.chartProvider`). TV charts continue through the existing
  TV path unchanged; SC charts route through the SC path.
- A single `chartId` unambiguously identifies its provider, so tools invoked
  with an explicit id MUST resolve to the correct provider without a global
  mode read.

### R3 — Timeframe

- `set_chart_timeframe` MUST change the timeframe of the target SC chart and
  reflect the new resolution in subsequent `list_*` calls. TV resolution
  strings continue to be accepted; document any SC translation in design.

### R4 — Drawings

- `list_chart_drawings`, `add_chart_drawing`, `add_chart_drawings`,
  `remove_chart_drawing`, `remove_chart_drawings`, `clear_chart_drawings` MUST
  all work on SC charts.
- Drawings MUST be expressed in the same canonical drawing schema the TV adapter
  uses (neutral `kind`, ISO-time + price points, style/fill/label). A new SC
  adapter maps canonical schema ↔ SC overlay API.
- Drawing ids MUST round-trip: an id returned by `list_chart_drawings` /
  `add_chart_drawing[s]` MUST be accepted by `remove_chart_drawing[s]` for the
  same chart, stable for the lifetime of the drawing.
- No SC source changes are expected. If the SC overlay API cannot express a
  canonical drawing kind or style, that gap is recorded as an SC feature request
  — not worked around in the desktop repo.

### R5 — Indicators (full parity)

- `list_chart_indicators`, `toggle_chart_indicator`, `remove_chart_indicator`,
  and `list_available_indicators` MUST all work on SC charts, at full parity
  with the TV path — no `unsupported_under_superchart` stubs in v1.
- Indicator results MUST use the same shape (id + name per study) so callers are
  provider-agnostic.
- Design MUST map each TV study/panel operation to its SC equivalent (see Open
  questions).

### R6 — Screenshot

- `take_chart_screenshot` MUST capture the target SC chart — including its
  drawings and indicators — and return a hosted image URL, dispatching to
  `widgets/super-chart/screenshot.js` (`takeScreenshot(chartId, cb)`) the same
  way notes-form already does.

### R7 — open_market / tab auto-switch

- `open_market` MUST open/activate the requested market and auto-switch the
  active trading tab when the center view is SC (`CandleChart` component), not
  only under the TV `CenterView`.
- After `open_market` resolves, the opened chart MUST be discoverable via R1
  (`rendered: true` with a `chartId`).

### R8 — readyToDraw

- The SC path MUST dispatch `setChartReadyToDraw` so a chart reports
  `ready: true` once drawable, unblocking the intro-modal "Start" buttons that
  are currently stuck under SC. Drawing tools (R4) MUST refuse a not-yet-ready
  chart with the same error semantics as TV.

### R9 — Multi-chart (TV parity only)

- Under SC, tools MUST resolve one `chartId` per rendered chart **widget** in
  Altrady's flex-grid layout, `mainChart`-tagged — matching what TV already
  does (each `DefaultTradingWidget` registers separately).
- TV's MCP path only ever touches `tvWidget.activeChart()`; TV-internal split
  panes within a single widget were never exposed. The SC path MUST NOT add
  per-pane addressing. Parity with TV, no more.

## Acceptance criteria

Desktop dev app + `claude mcp` session against `http://127.0.0.1:6850/mcp`:

1. With SC active, `list_open_charts` shows `rendered: true` and real
   `chartId`s, one per grid chart widget, `mainChart`-tagged.
2. Each of the 13 chart tools succeeds against a live SC chart with the same
   result shape as TV: timeframe change, list/add/remove/clear drawings
   (ids round-trip), list/toggle/remove/list-available indicators, screenshot
   returns a URL, `open_market` switches tabs and the new chart is discoverable.
3. Intro-modal "Start" buttons work under SC (R8).
4. Full regression pass under TV: every chart tool behaves byte-for-byte as
   before the change.

## Non-requirements / scope boundaries

- Non-chart MCP tools (positions, bots, alerts, watchlists, markets, notes) —
  already work under SC, untouched.
- TV-internal split-pane addressing — never existed; not added (R9).
- SC source changes — none expected; API gaps become SC feature requests (R4).
- No new second registry for SC (R1).

## Decisions (locked by user 2026-07-06)

- Indicators: **full parity** under SC in v1 (R5).
- `setChartReadyToDraw`: **in scope** (R8).
- Multi-chart: **TV parity only** — one `chartId` per grid chart widget; no
  per-pane support (R9).
- Registration: **reuse `ChartRegistry`**, no parallel MCP registry for SC (R1).

## Open questions for design (agent-investigable, no user input needed)

- SC indicator/panel API surface required for R5 full parity: map each TV
  study/panel MCP operation to its SC equivalent. Consult
  `~/ai/crypto_base_scanner_desktop/deps/SUPERCHART_API.md` FIRST (hard rule);
  SC just shipped trend-line/fib/h-ray overhauls (ALTD-1891/2/4) so the drawing
  and settings surface is fresh.
- Drawing id round-tripping (R4): how SC overlay ids map to the canonical
  schema's ids, and their lifetime/stability.
- Provider-agnostic chart handle: the exact interface wrapping TV state vs SC
  `ChartController` (`getTimeframe/setTimeframe`, `listDrawings/addDrawing/
  removeDrawing/clearDrawings`, `listIndicators/toggleIndicator/
  removeIndicator`, `listPanels`, `screenshot`, `readyToDraw`) — or whether the
  bridge reads `ChartRegistry` directly per tool.
