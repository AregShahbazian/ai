# MCP chart tools → SuperChart parity — Review

PRD `mcp-sc-bridge`. Code lives in `crypto_base_scanner_desktop` (branch
`feature/superchart-integration`), left **uncommitted** for live testing.

Legend: ☐ unverified · ✅ verified by user · 🔶 `(agent-verified)` self/subagent only.

## Round 0 — implementation

### Files
- **New** `src/mcp/chart-bridge/superchart-adapter.js` — canonical drawing ↔ SC
  overlay, user-drawing whitelist, indicator catalog.
- **New** `src/mcp/chart-bridge/chart-handle.js` — union `listCharts(ctx)`,
  `hasChart`, `resolveHandle`, `tvHandle`, `scHandle`.
- **Edit** `widget-registry.js` (TV-only store; `listCharts→listTvCharts`,
  `getChart→getTvChart`), `tools/charts.js`, `tools/context.js`, `tools/notes.js`,
  `super-chart/chart-controller.js`, `super-chart/charts/market-tab-chart.js`,
  `super-chart/charts/trading-terminal-chart.js`.

### Checklist (numbers referenced by the chat "What to test")

**R1 — discovery/resolution**
1. ☐ SC active, on `/trade`: `list_open_charts` → each rendered trading tab has
   `rendered:true` + a real `chartId` (not null).
2. ☐ `list_chart_panels` lists one entry per mounted SC chart widget; grid layout
   with 2+ chart cells → 2+ entries, exactly one `mainChart:true`.
3. ☐ `resolve_active_chart` returns the focused SC chart with `chartId`.

**R2 — provider dispatch**
4. ☐ A `chartId` from list resolves and every tool acts on that specific chart.
5. 🔶 TV and SC ids are disjoint namespaces (TV widget id vs `marketTabId||"main"`);
   `resolveHandle` checks TV registry then `ChartRegistry` — no cross-talk. *(reasoned)*

**R3 — timeframe**
6. ☐ `set_chart_timeframe {timeframe:"15"}` changes the SC chart's timeframe;
   subsequent `list_chart_panels` shows `resolution:"15"`.

**R4 — drawings**
7. ☐ `add_chart_drawing` for each kind on an SC chart renders:
   line (horizontal/vertical/trend/ray), rectangle, fib_retracement, label, arrow.
8. ☐ `list_chart_drawings` returns them with ISO-time+price points and a stable id;
   app overlays (orders/alerts/bid-ask) are NOT listed.
9. ☐ id round-trip: an id from add/list is accepted by `remove_chart_drawing`.
10. ☐ `add_chart_drawings` (batch) + `remove_chart_drawings` (batch) best-effort.
11. ☐ `clear_chart_drawings` removes user drawings and LEAVES order/alert overlays intact.
12. 🔶 fib_retracement maps to `fibonacciSegment` (not `fibonacciLine`); trend→`segment`,
    ray→`rayLine` — naming traps handled. *(agent-verified via SC-API investigation)*
13. 🔶 color/width/line-style applied on Pro overlays (`segment`, `rect`,
    `fibonacciSegment`) via the create `properties` field. **Verified:**
    `controller.createUserOverlay` → `_superchart.createOverlay` (the Superchart
    wrapper), which strips + re-applies `properties` via `setProperties`/
    `overrideOverlay` — NOT the raw engine `chart.createOverlay` (which drops
    them). Keys `lineColor`/`lineWidth`/`lineStyle` are correct. *(agent-verified)*
14. 🔶 `arrow` fixed to a **2-point** overlay (direction is geometric — a 1-point
    arrow renders nothing; synthesized a vertical head ±1% of price). ☐ rectangle
    fill fidelity still best-effort. Verify arrow renders up/down live.

**R5 — indicators (full parity)**
15. ☐ `list_available_indicators` returns the catalog; with a name returns inputs.
16. ☐ `toggle_chart_indicator {enabled:true}` adds (e.g. RSI); appears in `list_chart_indicators`.
17. ☐ `toggle_chart_indicator {enabled:false}` removes all of that name.
18. ☐ `remove_chart_indicator {studyId}` removes one by id (id from list round-trips).

**R6 — screenshot**
19. ☐ `take_chart_screenshot` on an SC chart returns a hosted image URL (no in-app
    share modal pops); URL opens the chart image incl. drawings/indicators.

**R7 — open_market / auto-switch**
20. ☐ `open_market {exchange, marketSymbol, timeframe}` under SC switches the active
    tab, applies the timeframe, and the chart is then discoverable via `list_open_charts`.

**R8 — readyToDraw**
21. ☐ Fresh onboarding (or force intro) on `/trade` under SC: the smart-trading
    intro-modal **Start/Resume** button un-disables once the chart loads.
    Console: `store.getState().replay.chartReadyToDraw === true`.
22. 🔶 Only the main chart drives the flag (grid charts pass `isMainChart:false`);
    dispatched inside the controller (no external dispatch/getState). *(reasoned)*

**R9 — multi-chart (TV parity)**
23. 🔶 One entry per grid chart widget; no per-pane addressing added. `mainChart`
    derived from active-tab id. *(reasoned — same granularity as TV registration)*

**Regression — TV byte-compatibility**
24. ☐ Switch provider to TV: every chart tool (1–20) behaves exactly as before the
    change (`tvHandle` wraps the identical prior calls; screenshot returns `<url>.png`).

### Self-review notes (Phase 4)

- **Coupling points reasoned:** *TradingTab change* — TT chart re-registers its
  controller under the new marketTabId (`trading-terminal-chart.js:57`), `_isMainChart`
  preserved. *coinraySymbol change* — no controller dispose; `readyToDraw` correctly
  stays true (SC keeps the same chart instance, unlike TV re-init). *resolution
  change* — `set/getResolution` proxy `_superchart.setPeriod/getPeriod`.
  *exchangeApiKeyId change* — not touched by this work (chart tools are market/tab
  scoped, not account scoped).
- **Cleanup:** `dispose()` dispatches `setChartReadyToDraw(false)` for the main
  chart before teardown; `useMarketTabChart` unchanged unmount path. No new
  listeners/subscriptions added (handles are stateless per-call).
- **No second registry:** `chart-handle` reads `ChartRegistry`; SC registration
  untouched (PRD non-req satisfied).

### Verification round (subagent, agent-verified)

Confirmed against SC source: (1) `properties` IS applied through the
`sc.createOverlay` wrapper we use — #13 resolved, no code change needed;
(2) Pro-overlay keys `lineColor/lineWidth/lineStyle` correct; (3) `arrow` needs
2 points, direction geometric → **fixed**; (4) `text` content is `extendData.text`
only (color/size via `styles.text.*`) → adapter matches; (5) indicator
signatures `createIndicator/getIndicators/removeIndicator` correct, ids stable.
**No open correctness risks remain from the SC API assumptions.**

### Follow-ups (non-blocking)

- `deps/SUPERCHART_API.md` is stale (recorded `00b4c49`/`a9a761a` vs HEAD
  `f51001b`/`2b25f9f`) and worth a note that `properties` requires the
  Superchart-level `createOverlay` wrapper (raw engine drops it). Separate doc task.
- **Indicator catalog** is a static list (SC does not re-export `getSupportedIndicators`).
  Operational tools are full parity; the catalog completeness is an SC feature
  request (export `getSupportedIndicators`), not a desktop-side workaround.
- **arrow/text** style + direction are best-effort (SC `arrow`/`text` overlay
  internals) — flagged, not blocking.
