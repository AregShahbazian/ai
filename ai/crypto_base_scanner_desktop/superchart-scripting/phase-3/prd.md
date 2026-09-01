---
id: sc-script-trimmings
---

# Phase 3 — Trimmings: the last things that make scripting feel finished on SuperChart

Part of the [SuperChart scripting port](../plan.md). Background and
terminology: [guide.md](../guide.md). Gotchas: [notes.md](../notes.md).
Builds on [phase 1](../phase-1/prd.md) (the spine) and
[phase 2](../phase-2/prd.md) (parity of everything a script *computes and
draws*).

After phase 2, a script that runs on TradingView produces the same picture on
SuperChart. What is still missing is everything *around* the script: its
backtest cannot draw its trades on an SC chart, a script the user added to
their charts never appears on one, and SC's own Script button still sits in the
toolbar offering a second, competing editor. None of it is new capability —
it is the port catching up with the surfaces TV already has.

This is the last phase before orders. It is deliberately small.

## Goal

The two capability-matrix rows that phase 2 left out — **12** (backtest run +
trade markers) and **15** ("Add to charts", the non-preview path) — behave on
SuperChart the way they behave on TradingView, and a user on an SC chart is
never offered a scripting UI that isn't Altrady's.

## Requirements

### R1 — Backtest trades render on an SC chart
- Matrix row **12**: running a backtest from the Scripts IDE while the terminal
  is on a SuperChart chart produces the same result as on TV — the report and
  equity curve in the panel, and the run's trades drawn on the chart.
- Per trade: an entry marker, an exit marker on the opposite side, and a
  connecting line coloured by win/loss. The TV implementation
  (`tradingview/script-backtest-trades-bridge.js`) is the reference for what
  "the same" means.
- While a backtest's trades are shown, the user's real account trades are
  hidden, and restored when the result is cleared — including on unmount, and
  only if they were on to begin with.
- The report itself needs no work. It is a REST call to the `coinray_script`
  service (`ta-v2`) rendered with Highcharts; it is chart-agnostic and already
  passes. **The only coupling is the trade markers.**
- The trades themselves are neutral data. They reach the chart the way
  `currentRun` does — through the chart bridge — and each provider's own tree
  renders them. A second copy of the drawing logic in the SC tree is expected;
  a second copy of the *policy* (when to draw, when to hide real trades) is a
  defect.
- **SC's drawing API is `createTradeLine(chart, options)`** (package root
  `index.ts:37`, impl `tradeLineApi.ts:83`) — one imperative handle per marker,
  with `remove()`, and not persisted, so it is re-created on reload. There is no
  batch API. A typical script backtest is a few hundred markers at most (the
  row-12 reference run was 48 trades), so per-marker calls are fine; if a real
  run ever reaches thousands, note that phase 2's batching does **not** cover
  this path — it is a different overlay route — and raise it rather than
  absorbing the stall.

### R2 — "Add to charts" works on SC, replicating TV
- Matrix row **15**: a saved script toggled "Add to charts" appears on the main
  SuperChart chart, with no Scripts IDE open and without "Run on chart".
- **TV is the specification** (Areg, 2026-09-01). What TV does today, and what
  SC must match:
  - The enabled set is a **per-device list of script externalIds** in
    localStorage (`scripts.chartEnabled`, `~/actions/coinray-chart-scripts`).
    It does not follow the account. That module is already provider-neutral and
    is reused as-is.
  - On chart load, each enabled id is fetched, its helper modules rebuilt from
    `version.resolvedDependencies` (the API never returns `script.modules` —
    this was a bug once already), compiled, and added to the chart.
  - Enabled scripts and the IDE's current preview coexist on the same chart;
    both are added.
  - **Main chart only.** Grid-bot, preview and quiz charts never carry script
    indicators.
  - Toggling the list takes effect **immediately** on charts already on screen,
    not at the next reload. On TV that costs a widget rebuild; on SC it should
    not need one.
  - Deleting a script removes it from the list, so no chart tries to load it.
- **The list is the only source of truth.** Script indicators must stay out of
  SC's saved chart state — phase 2 removed them from it deliberately, after
  they leaked in through `modifyIndicator`'s backfill and produced a klinecharts
  warning at every app load. Nothing in phase 3 may put them back.
- For the same reason, **no provider-side script id is ever persisted**. SC's
  ids are session-local and non-deterministic (`SCRIPT_${++idCounter}`); what
  persists is the externalId, resolved to source on load.
- A script that is both previewed and enabled is added **once**, not twice.
  This is a deliberate, minor deviation from TV, which registers it through
  both providers and shows two identical studies. No user wants the duplicate.
- **Where TV parity stops, and why that is acceptable.** On TV an enabled script
  is both *registered* as a custom indicator (so it is listed in the Indicators
  picker) and *auto-placed* on the chart — `custom_indicators_getter` builds it,
  `onStrategyIndicatorsBuilt` reports every built indicator, and
  `TvScriptRenderer` `createStudy`s each one. SC has the register-vs-place
  distinction only on the **backend-indicator** path
  (`IndicatorProvider.getAvailableIndicators()` → the picker's second list);
  scripts have no listing hook, and `addScriptIndicator` is add-equals-place.
  So SC reproduces the part the user actually sees — the script is on the chart
  — and loses only the picker entry. Confirmed with the SC session,
  2026-09-01. Adding a real script-listing API to SC is the alternative and is
  **out of scope** (see non-requirements).
- **When to re-add on load.** SC has no public restore-complete event;
  `restoreChartState` does its indicator pass on an untracked `setTimeout` with
  a +500 ms mirror write. The hook to use is **`onDataLoaded`** (fires on the
  engine's `onInitLoadComplete`), which is safe here precisely because restore
  never touches `SCRIPT_*`. Do not use `onApiReady` — it races the mirror
  write.

### R3 — SuperChart's own Script button is suppressed
- SC renders its Script/`fx` toolbar button whenever a `scriptProvider` is set.
  Altrady sets one, and keeps its own IDE — so the button opens a second,
  competing editor over the chart.
- After this phase the button is not there, while the provider still is.
- This is new SC surface; it does not exist today. In scope for phase 3
  (Areg, 2026-09-01).
- **The shape is already settled**: SC's top-bar buttons gate on its feature-flag
  system (`useFeature('settings_button' | 'indicator_picker' | …)`), not on
  options booleans. Adding a `script_button` flag (default `true`) is ~8 lines
  across three files plus a docs row; the host then passes
  `disabledFeatures: ['script_button']`. Confirmed with the SC session,
  2026-09-01.

### R4 — The `BACKEND_<id>` state leak, carried from the phase-2 review
- SC's settings modal reaches `modifyIndicator` with raw `BACKEND_<id>` names,
  so a backend indicator can be snapshotted into saved chart state — the same
  structural leak phase 2 fixed for `SCRIPT_`, on the other prefix.
- Phase 2 fixed only the scripting half at the chokepoint, on Areg's call, to
  avoid widening the phase. Phase 3 closes the other half.
- Not user-reported, and outside scripting. It is here because it is the same
  bug and the fix is in the same place.

### R5 — TradingView keeps working, unchanged
- All 15 matrix rows still pass on TV, with no behavioural change. A hard
  acceptance gate, as in phases 1 and 2.
- R1 and R2 both touch code the TV path uses today (the backtest trades bridge,
  the chart-enabled list). Moving policy into the neutral layer must leave TV's
  observable behaviour identical.

### R6 — The seam stays provider-agnostic
- No new `chartProvider` test anywhere in the scripting path. Selection stays
  structural: each renderer mounts inside its own chart tree.
- New provider-specific code lives in that provider's module
  (`super-chart/scripts/`, `tradingview/scripts/`), never in the IDE.
- `script-backtest-trades-bridge.js` currently reads `useScripts()` directly
  from inside the TV tree — a leftover from before the bridge existed. R1 is
  the occasion to route it through the bridge, as `tradingview.js` already was
  in phase 2.

## Non-requirements (explicitly out of scope for phase 3)

- **`strategy.long/short/close` and order rendering** — phase 4, and still an
  open design question rather than a port.
- **Pane-routed primitives.** Unchanged from phase 2: needs an SDK + ABI change
  and both hosts.
- **An alert picker.** `declareAlert()` works, but `compileClient.ts` drops the
  server's `alerts` array from the compile response, so a picker would need
  either `host.declaredAlerts` after `load()` or a ~5-line `0.1.10` change.
  Neither is phase 3 unless a picker is actually asked for.
- **A script-listing API in SC's indicator picker.** It would be the last piece
  of literal TV parity for R2 — enabled scripts appearing in the picker as
  *available but not placed*, with placement routed through the script pipeline.
  It is real SC work (medium), and the alternative of wrapping scripts in an
  `IndicatorProvider` to reuse the backend-indicator listing is a dead end: that
  pipeline loses primitives. Deferred until someone actually wants the picker
  entry.
- **A restore-complete event in SC.** `onDataLoaded` is sufficient here. A hard
  ordering guarantee would be new SC surface (small); not needed while
  `SCRIPT_*` stays out of saved state.
- **Making the enabled list follow the account.** It is per-device on TV; it
  stays per-device on SC. Changing that is a product decision, not a port.
- **Publishing a helper module** — phase-2 review item 31, still ⛔ blocked on a
  backend 422 (`"A username is required to publish a module"`) in
  `crypto_base_scanner`, a fourth repo outside this port. Re-test when that
  endpoint is fixed; do not carry it as phase-3 scope.
- Any change to the Scripts IDE's look or layout.

## Constraints

- **Which repos change** — to be confirmed by each repo's own session before
  design, but expected:
  - **`crypto_base_scanner_desktop`** — the bulk. The SC backtest-trades
    bridge, the SC chart-enabled renderer, routing backtest trades through the
    chart bridge.
  - **`Superchart`** — R3 (the `script_button` feature flag) and R4 (the
    `BACKEND_` half of the `modifyIndicator` chokepoint). Small; scoped with
    that session on 2026-09-01.
  - **`coinray_rest`** — **none expected.** Confirmed by that session,
    2026-09-01: the backtest's server side lives there
    (`packages/coinray_script`, `src/web/ta/mod.rs:874`) and already works, but
    nothing in `packages/superchart-script` participates in a backtest — the
    browser package is execute-and-render only. No `0.1.10` unless something
    unforeseen turns up.
- **`from`/`to` on the backtest endpoint must be RFC 3339 strings.** Unix ints
  return a **500**, not a 422, with `Json deserialize error … expected an
  RFC 3339 formatted date`. Recorded in guide.md row 12; repeated here because
  it is the kind of thing a port re-discovers the hard way.
- **The ta-v2 compiler redeploy is a human step, and a phase-3 dependency worth
  taking.** It is not a code deliverable, but one redeploy closes two things at
  once: `buildMetadata`'s SDK layer (so a `plot()` of an all-NaN warmup window
  renders without the script having to set `config.warmup`), and matrix row 3's
  remaining ⚠ — the deployed compiler still rejects `options` inputs. Artefacts
  are in `coinray_rest` (`packages/strategy_compiler/build.sh`, `k8s.yml`);
  the trigger needs DO registry + `admin@coinray-ovh` credentials that Areg or
  Benoist holds. Treat it like the 0.1.9 publish was treated: a human step,
  scheduled, not assumed.
- **Per-repo sessions.** Each repo's work is done by a Claude session started
  in that repo's root; the cbsd session coordinates and delegates by message.
  Permissions do not transfer between sessions. See "Multi-repo work" in
  `~/ai/workflow.md`.
- **WIP commits, squashed at the end.** Each repo commits work as WIP commits
  (fixes get their own, not amends) and squashes to one commit per repo,
  tagged `[sc-script-trimmings]`, when the phase is verified. WIP commits are
  never pushed.
- **Local links while iterating**, if `superchart-script` turns out to need a
  change after all.

## Acceptance

Phase 3 is done when, on a SuperChart chart:

1. A backtest run from the Scripts IDE draws its entry/exit markers and
   win/loss lines on the chart, hides the user's real trades while they are
   shown, and restores them on clear.
2. A script toggled "Add to charts" appears on the main SC chart with the
   Scripts IDE closed, survives a reload and a layout switch, and disappears
   when toggled off — without a chart rebuild in either direction.
3. Multi-file scripts work through that path: helpers come from
   `resolvedDependencies`, not from `script.modules`.
4. Nothing script-shaped appears in SC's saved chart state, and no klinecharts
   warning is logged at app load — for `SCRIPT_` or `BACKEND_`.
5. SC's Script button is gone from the toolbar while the provider is still set.
6. All 15 matrix rows still pass on TradingView.
7. The Scripts IDE still contains no provider-specific branching, and the
   backtest trades path goes through the chart bridge on both providers.
