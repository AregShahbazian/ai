---
id: sc-script-trimmings
repo: crypto_base_scanner_desktop
---

# Phase 3 tasks — trimmings (cbsd) [sc-script-trimmings]

From [design.md](design.md). SC's tasks are in [sc-tasks.md](sc-tasks.md),
owned by that repo's session. `coinray_rest` has no tasks this phase.

Unlike phase 2, **cbsd owns nearly all of the work and almost none of the
dependencies**. Only part D needs SC, and it is one line that is inert until
SC's flag lands.

## Part A — the neutral backtest-trades channel (no dependency)

- [x] A1. `chart-bridge/context.js`: carry `backtestTrades` alongside
      `currentRun`, with a `publishBacktestTrades(trades)` setter. Same
      direction (IDE → chart), same rule as `currentRun`: a cleared result
      publishes `null`, so "no trades" is a value rather than an absence.
- [x] A2. `scripts-context.js`: publish `backtest?.trades` to the bridge as it
      changes, and `null` when the result is cleared. The IDE keeps owning the
      backtest; the bridge only carries what a chart needs.
- [x] A3. New `chart-bridge/use-backtest-trades.js` — the neutral policy hook,
      a deliberate sibling of `useScriptRun`:
      `useBacktestTrades({draw, clear, deps})`. It owns *when*; providers own
      *how*. Two separate effects:
      - **hide/restore**, driven by `hasTrades` **only** — never by chart
        readiness. Dispatching `closedOrdersShow` recreates the TV chart
        functions, so depending on them loops and flickers. Restore only if the
        setting was on when we hid it, read from a ref.
      - **draw/clear**, keyed on the trades and the caller's `deps`, with the
        same async-cleanup race handling `useScriptRun` already has.
- [x] A4. Export it from `chart-bridge/index.js`.

## Part B — TV moves onto the hook (R5 gate)

- [x] B1. Move `tradingview/script-backtest-trades-bridge.js` →
      `tradingview/scripts/tv-backtest-trades.js`, so both providers' script
      modules sit at mirrored paths (principle 5). Pure move plus the import in
      `tradingview.js`.
- [x] B2. Rewrite it as `draw`/`clear` over the neutral hook. It stops importing
      `useScripts` — the last place chart code reaches into the IDE, and the
      violation phase 2 removed from `tradingview.js` but did not chase here.
- [x] B3. Confirm the drawing is byte-for-byte the same decisions as before:
      `drawTrade` for entry and exit, `createMultipointShape("trend_line")`
      coloured by `pnl >= 0`, and the same cleanup shape (execution shapes have
      `.remove()`, multipoint shapes are ids for `removeEntity`).

## Part C — the SC side of backtest trades

- [x] C1. `overlay-helpers.js`: add `OverlayGroups.backtestTrades`. Its own
      group, not `trades` — `clearAllTrades()` would otherwise tear down both
      sets, and it buys batch teardown (the phase-2 `groupId` lesson on a
      different path).
- [x] C2. New `controllers/backtest-trades-controller.js`, mirroring
      `TradesController`: entry and exit markers via `createTradeLine`, and the
      connecting line as a `styledSegment` through `_createTrendlineLine`,
      coloured by win/loss. **Colour is decided in the controller, never in the
      component** (`feedback_sc_overlay_colors`).
- [x] C3. Attach it in `tt-chart-controller.js` beside the other
      sub-controllers, and dispose it with them.
- [x] C4. New `super-chart/scripts/sc-backtest-trades.js` — the renderer: the
      neutral hook plus `draw`/`clear` delegating to the controller. Mount it in
      `charts/trading-terminal-chart.js` beside `ScScriptRenderer`.

## Part D — "add to charts" on SC

- [x] D1. `actions/coinray-chart-scripts.js`: add `loadChartScripts()` —
      `getScript` → filter `version.resolvedDependencies` → `buildModules`,
      returning `{externalId, name, source, modules}[]`. A plain async
      function, not a hook: TV's caller is a non-React async provider. Helpers
      come from `resolvedDependencies`, never `script.modules` — the API does
      not return the latter, and that was already a bug once (matrix row 15).
      One script failing to resolve must not take the others down.
- [x] D2. `use-trading-view.js`: `chartEnabledProvider` becomes
      *resolver + its existing compile*. **R5 gate** — behaviour-preserving by
      construction (same four steps, same order, three of them moved), but it is
      TV code and the review must check it rather than discover it.
- [x] D3. `chart-bridge/context.js`: `currentRun` gains `externalId` (null for
      an unsaved draft), so a renderer can tell the previewed script from an
      enabled one. Rejected alternative: matching on source text, which breaks
      exactly when a user edits an enabled script.
- [x] D4. `scripts-context.js`: pass `selected.externalId` into `run()`.
- [x] D5. New `super-chart/scripts/sc-chart-scripts-renderer.js`:
      - resolve the enabled list, add each via `addScriptIndicator`, keyed by
        `externalId`;
      - **reconcile as a set** — add what is new, remove what is gone, leave
        survivors alone. A user toggling a second script must not make the
        first flicker;
      - skip an enabled script that is currently the preview (**the preview
        wins** — it is what the user is looking at, and may be unsaved);
      - re-subscribe on `onChartScriptsChanged` so a toggle takes effect
        immediately, with no chart rebuild;
      - re-apply on controller / symbol / resolution change and clear on
        unmount, with **every value the apply path reads named in the deps** —
        the controller resolves late through `ChartRegistry` and is undefined on
        a remounted chart's first render (the phase-1 bug);
      - a script that fails to resolve **reports** — never silently draws
        nothing (the `buildMetadata` lesson).
- [x] D6. Mount it in `charts/trading-terminal-chart.js`. Main-chart-only comes
      free from *where* it is mounted; no `mainChart` boolean.

## Part E — suppress SC's Script button (needs SC's flag)

- [x] E1. `charts/market-tab-chart.js`: pass
      `disabledFeatures: ["script_button"]` alongside the provider, at the call
      site that already decides whether there is a provider at all. Inert until
      SC's flag exists — confirmed with that session: `disabledFeatures`
      resolves into a flag set only declared `useFeature()` calls read, so an
      unknown name is a no-op, not a throw.

## Verification

Run [review.md](review.md), all items, in the browser against the dev server —
Playwright driving console globals (`window.DEBUG.scripts`,
`window.chartController`), screenshots read visually.

**Verify against the artifact, not the pixels.** Phase 2's review marked an item
passed off a screenshot while the app was running a `dist-enterprise` that
predated the fix. Anything depending on SC's part (E, and the object-tree
behaviour in C) is checked against the built bundle before it is called passed.

Part D has a specific version of the same trap: "the script is on the chart"
looks identical whether the enabled list put it there or a leftover run did. Its
items are only passed with the Scripts panel closed after a fresh reload.

## Status (2026-09-01)

All parts implemented; ESLint clean on every new file. Committed as two WIP
commits (`537c5b0b0`, `ee1f88d8a`), unpushed.

Round 1 of [review.md](review.md) run by me: **31 of 40 verified**, two bugs
found and fixed (a preview change re-adding every enabled script; backtest
trades not redrawing on symbol/resolution). The nine remaining items are marked
in place with why — one deletes a saved script, four need SC's indicator picker,
one is the full TradingView 15-row suite.
