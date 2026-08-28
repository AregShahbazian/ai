---
id: sc-script-spine
---

# Phase 1 — Spine: run a script on a SuperChart chart

Part of the [SuperChart scripting port](../plan.md). Background and
terminology: [guide.md](../guide.md). Gotchas: [notes.md](../notes.md).

Scripting works end to end on TradingView today. This phase makes the same
"Run on chart" action work when the active chart provider is SuperChart,
rendering plots and panes — and nothing more. It exists to prove the
architecture; phases 2-4 are additive on top of it.

## Goal

From the Scripts IDE, with SuperChart as the chart provider, pressing
**Run on chart** puts the script's plots on the chart — correctly placed,
correctly re-runnable, and cleanly removable.

## Requirements

### R1 — Run on chart works on SuperChart
- With `chartSettings.chartProvider === "superchart"`, **Run on chart**
  compiles the current editor content and renders the result on the active
  SuperChart chart.
- The script runs against the chart's real candles for the chart's current
  symbol and resolution — not a synthetic or independently-chosen series.
- Historical bars and the live forming bar both produce values; the plot
  extends as new bars arrive.

### R2 — Plots render correctly
- A script with one `plot()` draws one line on the price pane.
- A script with several `plot()` calls draws one line per plot, each visually
  distinguishable.
- `plotPane("name", …)` places those plots in their own sub-pane; a script
  mixing main-pane and sub-pane plots renders both, in the right panes.
- Values match what the same script produces on TradingView for the same
  symbol, resolution and bar range. Matrix rows 1 and 2 must pass on SC.

### R3 — Re-run replaces, never accumulates
- Editing the script and pressing **Run on chart** again replaces the previous
  result. No duplicate indicators, no orphaned panes, no stale lines.
- This holds for an edit that changes the plot set, the pane layout, the
  warmup, or only the arithmetic. (On TV, `structureKey` misses the plot set
  and the script name — see notes.md. Phase 1 must not reproduce that class of
  bug.)
- Re-running does not require reloading the chart widget or the page.

### R4 — Lifecycle and cleanup
- Removing the indicator from the chart stops the script and releases its
  resources.
- Changing symbol or resolution leaves the chart in a correct state: either the
  script re-runs against the new series, or it is removed. It must never keep
  showing values computed from the previous symbol.
- Closing the Scripts widget, switching layouts, or unmounting the chart does
  not leak a running script or throw.

### R5 — TradingView keeps working, unchanged
- Every capability that works on TV today still works, with no behavioural
  change: all 15 matrix rows.
- Switching the chart provider back and forth leaves both paths functional.
- This is a hard acceptance gate, not a best-effort.

### R6 — One seam, both providers
- The Scripts IDE does not know which chart provider is active. It asks for
  "run this on the chart" and something else decides how.
- That decision lives in a **dedicated chart-bridge module**, not inside
  `scripts-context.js` (which is already large) and not scattered across the
  IDE panels.
- Adding a third provider later, or changing either existing one, touches the
  bridge and not the IDE.

### R7 — Reachable without SuperChart's script editor
- The SC path must be drivable from Altrady's own IDE. It must not require
  mounting the Scripts panel inside SuperChart's editor slot, and must not
  require SuperChart's built-in script UI to be visible or used.

## Non-requirements (explicitly out of scope for phase 1)

Deferred to later phases; each is expected to fail or be absent after phase 1,
and that is acceptable:

- `draw.*` primitives — line, marker, box, label, remove (phase 2)
- `param.*` inputs and any settings dialog on SC (phase 2)
- `log.*` reaching the Console panel on the SC path (phase 2)
- Multi-file scripts / helper modules on the SC compile path (phase 2)
- Accurate inline compiler diagnostics on the SC path (phase 2)
- Backtest wiring and backtest trade markers on SC (phase 3)
- "Add to charts" persistence — the `scripts.chartEnabled` list — on SC (phase 3)
- Suppressing SuperChart's own Script button (phase 3)
- `strategy.long/short/close` and any order rendering (phase 4)
- Alerts firing anywhere client-side (server-side concern, unchanged)
- Any change to the Scripts IDE's look or layout
- Any change to the TradingView rendering path beyond what R5 protects

## Constraints (already decided)

- **Coexistence.** TV and SC both remain fully functional. The SC path is
  additive code beside the TV path, never a replacement.
- **Entry point, not editor slot.** SuperChart gains a public way to add a
  script indicator to a chart, and Altrady calls it. Rejected alternative:
  mounting Altrady's IDE as `ScriptProvider.EditorComponent` — with TV
  coexisting, the single FlexLayout Scripts panel would have to mount twice,
  splitting its context state. (Decision log in ../plan.md.)
- **Two repos change in this phase**: `Superchart` (the public entry point)
  and `crypto_base_scanner_desktop` (the bridge and the wiring).
  `coinray_rest`'s `packages/superchart-script` is expected to need no change —
  its known holes are all phase 2 work.
- **Per-repo sessions.** Work in a repo is done by a Claude session started in
  that repo's root; the cbsd session coordinates and delegates by message.
  See "Cross-repo agent delegation" in ../plan.md.
- While iterating, `superchart-script` is consumed as a local link rather than
  a republished version.

## Acceptance

Phase 1 is done when, on a SuperChart chart:

1. Matrix rows **1** (`plot`) and **2** (`plotPane`) pass, first run and re-run.
2. A plots-only script survives an edit-and-re-run cycle ten times with no
   duplicate indicators and no page reload.
3. Symbol and resolution changes leave no stale or wrongly-attributed values.
4. All 15 matrix rows still pass on TradingView.
5. The Scripts IDE contains no provider-specific branching.
