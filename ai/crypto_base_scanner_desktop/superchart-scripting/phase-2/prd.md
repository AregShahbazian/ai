---
id: sc-script-parity
---

# Phase 2 — Parity: everything a script can do, on SuperChart

Part of the [SuperChart scripting port](../plan.md). Background and
terminology: [guide.md](../guide.md). Gotchas: [notes.md](../notes.md).
Builds on [phase 1](../phase-1/prd.md), which put a script's **plots** on a
SuperChart chart and left the rest deliberately absent.

Phase 1 proved the spine. This phase closes the capability gap between the two
providers: after it, a script that works on TradingView produces the same
result on SuperChart, and the reasons to prefer one provider over the other are
about the chart, not about scripting.

## What changed since the phase-1 non-requirements were written

Two of them turned out not to be gaps at all. Verified in the browser on
2026-08-31 (Altrady dev, SC `2250192`, published `@coinrayio/superchart-script`
0.1.8):

- **`draw.*` primitives already render on SC.** A script drawing all four kinds
  emitted three full snapshots of 8025 primitives; the chart ended with
  `scriptMarker` ×8022, `scriptBox`, `scriptLine`, `scriptLabel`, all visually
  correct, and `removeScriptIndicator` tore every one of them down. The
  emit side (`subscriptionAdapter.ts`) and the render side
  (`reconcilePrimitives` + the four overlay templates) were both already in
  place. Phase-1 review item 37 recorded the opposite and was wrong; it has
  been corrected.
- **A settings dialog does exist on SC** — the gear on a `SCRIPT_` legend. It
  opens *empty*, and applying it writes `calcParams: []` into autosave. So the
  phase-1 note "no settings dialog, no throw" understated it: this is a live
  defect reachable by Altrady users today, not an absence.

Both discoveries move work between repos but not out of the phase.

## Goal

Every row of the [capability matrix](../guide.md#capability-test-matrix) that
concerns *rendering and running a script* behaves the same on SuperChart as on
TradingView — primitives, inputs, logs, helper modules and compiler
diagnostics — with no regression to the TradingView path and no
provider-specific code in the Scripts IDE.

## Requirements

### R1 — `draw.*` primitives at realistic scale
- Matrix rows **4–8** (`line`, `marker`, `box`, `label`, `remove`) render on SC
  and keep rendering across re-runs, symbol changes and resolution changes.
- A script emitting thousands of primitives stays interactive: panning,
  zooming and crosshair movement remain smooth, and a re-run that replaces the
  whole set does not stall the chart.
  Today it does not. Individual create/remove per snapshot is O(n²) in SC's
  engine — `removeOverlay` does two full-store scans per call and
  `addOverlays` re-sorts each pane per call — so a full replace of 8k
  primitives is ~1e9 operations. Measured teardown of 8025 overlays: **663 ms**.
  There is also no visible-range culling: every paint walks all overlays and
  allocates per overlay, and hit-testing walks all of them on mousemove.
- Script-owned primitives stay invisible to the user as *objects*: they must
  not appear in the object tree and must not be included in a drawings export.
  They are script output, not user drawings.

### R2 — `param.*` inputs, editable on the chart
- Matrix row **3**: a script's declared inputs (`int`, `float`, `bool_`,
  `options`) reach the chart as real settings, with their names, defaults and
  min/max.
- Opening the settings dialog on a script indicator shows those inputs. It must
  never open empty, and must never be able to write an empty parameter set into
  the chart's saved state.
- Changing a value re-runs the script with the new values and updates what is
  on screen. The user does not have to remove and re-add the script.
- On TradingView this is TV's own study dialog; on SuperChart it is SC's own
  settings modal. **The Scripts IDE gains no parameter UI** — inputs are edited
  where the indicator lives, on both providers.

### R3 — `log.*` reaches the Console panel on SC
- Matrix row **9**: `log.debug/info/warn/error` from a script running on a SC
  chart appears in the Scripts IDE Console panel, with the same four levels and
  the same styling as on TV.
- Logs are gated to newly-confirmed bars. An ungated stream would emit on every
  intra-bar tick and flush the ring buffer (`LOG_CAP = 500`) of anything useful.
- A script running on SC with the IDE closed must not accumulate anything
  unbounded.

### R4 — Helper modules compile on the SC path
- Matrix row **13**: a multi-file script (entry plus sibling `./helper`
  imports, and linked modules) compiles and runs on SC exactly as it does on
  TV. The IDE's existing multi-file editor is unchanged — only the SC compile
  path currently drops the modules.
- A helper-only edit invalidates the compile cache and re-runs, as on TV.

### R5 — Compiler diagnostics are accurate and visible
- A compile error reports the **real line and column**, not `line i+1, col 1`.
- A failure on the SC path is visible in the IDE. Today a rejected compile is
  console-only: from the UI the indicator simply never appears (phase-1 review
  item 40).
- This applies to both providers — diagnostics come from the compiler, not from
  the chart.

### R6 — TradingView keeps working, unchanged
- All 15 matrix rows still pass on TV, with no behavioural change.
- A hard acceptance gate, as in phase 1 — not best-effort.

### R7 — The seam stays provider-agnostic
- No new `chartProvider` test anywhere in the scripting path. Provider
  selection stays structural: each renderer mounts inside its own chart tree.
- New provider-specific code lives in that provider's module
  (`super-chart/scripts/`, `tradingview/scripts/`), never in the IDE and never
  in the shared bridge.
- Anything both providers need (log level mapping, module passing) goes through
  the bridge in a shape neither provider's vocabulary leaks into.

## Non-requirements (explicitly out of scope for phase 2)

- **Pane-routed primitives.** SC pins every primitive to the candle pane; TV
  routes a `pane::id`-prefixed key to a named sub-pane. Closing this needs an
  SDK + ABI change plus both hosts (`draw.*` has no pane argument today). The
  agreed shape when it happens is an optional SC-owned `ScriptPrimitive.pane`,
  not key-prefix parsing. Deferred.
- **Collapsing a script's primitives into a single overlay** (tier (c) of the
  scaling plan) — it would lose per-primitive hover, tooltips and z-order.
  Deferred until a real script hits the wall that tiers (a) and (b) leave.
- **Marker shape fidelity on TV** (row 8: `square`→circle, `triangle`→arrow,
  `Shape.Circle` throwing). A TV-side defect; SC renders the shapes natively.
  Phase 2 must not make it worse and is not required to fix it.
- Backtest wiring and backtest trade markers on SC (phase 3).
- "Add to charts" persistence on SC (phase 3).
- Suppressing SuperChart's own Script button (phase 3).
- `strategy.long/short/close` and order rendering (phase 4).
- Any change to the Scripts IDE's look or layout.

## Constraints (already decided)

- **Three repos change.** Scope confirmed by each repo's own session,
  2026-08-31:
  - **`coinray_rest`** (`packages/superchart-script`) — map the compiler's
    `meta.inputs` to `IndicatorSettingDef` (`buildMetadata` hardcodes `[]`
    today); a `setParams` + re-run path behind SC's new contract member; thread
    `modules` through `compile()` / `ScriptExecuteParams` (the client and
    backend already accept them); parse the backend's
    `" in strategy.ts:L:C"` suffix into real diagnostics; emit `onLog`.
    **Primitives need no work.**
  - **`Superchart`** — `updateScriptIndicator(scriptId, settings)` plus a
    populated settings modal (and stop the empty one autosaving
    `calcParams: []`); define the optional `onLog` member; primitive batching,
    tiers (a) and (b); keep script overlays out of the object tree and the
    drawings export.
  - **`crypto_base_scanner_desktop`** — wiring only: map `onLog` to the
    existing `appendLog`, pass `modules` on the SC path, surface diagnostics in
    the IDE. The TV path is untouched.
- **Contract, settled between the three sessions before any code:**
  - `IndicatorSubscription.onLog?(handler: (entry: {level: 'debug' | 'info' |
    'warn' | 'error'; message: string; timestamp: number /* bar time, ms */})
    => void): void` — the type is SC's, `superchart-script` emits it, gating and
    dedupe are emit-side. Four levels, because the wasm host emits four
    (`LogEvent` 0–3) and Altrady's console already styles four; collapsing
    `debug` into `info` would regress against TV.
  - Altrady's console takes `{level: 0|1|2|3, message, time /* seconds */}`.
    The mapping is cbsd's job; SC's ms-everywhere convention wins in the
    contract.
  - `ScriptProvider.updateSettings?(id, settings)` — optional, mirroring
    `IndicatorProvider.updateSettings`, with a stop + re-execute fallback. The
    fallback changes the `scriptId`, so a host must re-read it.
  - Ordering: `superchart-script`'s settings metadata lands **before** SC's
    settings modal (the modal has nothing to render otherwise); SC's `onLog`
    and `updateSettings` type additions land **before** their emit sides.
- **Per-repo sessions.** Each repo's work is done by a Claude session started
  in that repo's root; the cbsd session coordinates and delegates by message.
  See "Multi-repo work" in `~/ai/workflow.md`.
- **Local links while iterating.** `superchart-script` and SC are consumed as
  local builds, not republished per change.
- **Publishing 0.1.9 is a human step.** The CI tag workflow is disabled
  (`87ba31b6` — the `link:` dependency on a local SC build breaks runners), so
  the publish is manual, from a machine with SC built, and needs a
  `write:packages` PAT. Only needed at the end of the phase.

## Acceptance

Phase 2 is done when, on a SuperChart chart:

1. Matrix rows **3**, **4–8**, **9** and **13** pass on SC — first run and
   re-run — to the same standard they pass on TV.
2. A script emitting several thousand primitives pans, zooms and re-runs
   without a visible stall, and its full teardown is fast enough not to be
   noticed.
3. Script primitives appear in neither the object tree nor a drawings export.
4. Editing an input in the chart's settings dialog re-runs the script and
   changes what is drawn, without removing and re-adding it.
5. A deliberate compile error names the right line and is visible in the IDE
   without opening the console.
6. All 15 matrix rows still pass on TradingView.
7. The Scripts IDE still contains no provider-specific branching.
