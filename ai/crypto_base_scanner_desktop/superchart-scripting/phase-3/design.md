---
id: sc-script-trimmings
repo: crypto_base_scanner_desktop
---

# Phase 3 design — trimmings (cbsd) [sc-script-trimmings]

Host design for [prd.md](prd.md), plus the **cross-repo contract**. SC's
internals are in [sc-design.md](sc-design.md), written by that repo's own
session, as `~/ai/workflow.md` -> "Multi-repo work" requires.

**`coinray_rest` has no design doc this phase.** Confirmed by that session,
2026-09-01: the backtest's server side lives there and already works
(`packages/coinray_script`, `src/web/ta/mod.rs:874`), but nothing in
`packages/superchart-script` participates in a backtest — the browser package is
execute-and-render only. No `0.1.10` is expected.

## Shape of the solution

Phase 2 was mostly other repos filling in the seam. Phase 3 inverts that:
**cbsd does nearly all of it**, SC contributes one feature flag and one
persistence fix, and `superchart-script` contributes nothing.

| Requirement | cbsd's part |
|---|---|
| R1 backtest trades | A neutral policy hook + an SC drawing module. The report is untouched. |
| R2 add to charts | A neutral resolver (list → runnable payloads) + an SC renderer. TV moves onto the resolver. |
| R3 Script button | One line: `disabledFeatures: ["script_button"]` where the provider is created. |
| R4 `BACKEND_` leak | **Nothing.** SC-side. |

One consequence of SC's R4 fix reaches the host and is accepted: after it, a
backend indicator's eye-toggle and settings no longer persist `visible` into
chart state. It never actually restored — it only ever produced the warning — so
nothing regresses. Real backend-visibility persistence would belong in SC's
`syncToStorage` and is not built.

Neither requirement introduces a new *mechanism*. Both are the third and fourth
uses of shapes phase 1 and 2 established: a neutral hook owning policy while
providers supply mechanism (`useScriptRun`), and a provider renderer mounted
structurally inside its own chart tree.

## R1 — backtest trades: policy in the bridge, drawing in the trees

### The problem with what exists

`tradingview/script-backtest-trades-bridge.js` does the whole job in one file
inside the TV tree: it reads `useScripts()` directly for
`scripts.backtest.trades`, decides when trades are active, hides the user's real
trades, and draws. Copying that file into `super-chart/` would satisfy R1 and
violate principle 2 in the same commit — the *policy* half is identical on both
providers and only the drawing differs.

It is also the last place in the scripting path where chart code imports the
IDE. Phase 2 removed that from `tradingview.js` on the grounds that "the widget
has no business importing the Scripts IDE"; this file was simply not in that
phase's scope. R1 is the occasion to finish it (PRD R6).

### The split

- **The bridge carries the trades.** Same direction as `currentRun` (IDE →
  chart), same discipline: the IDE publishes the current backtest's trades, a
  renderer consumes them, and nothing in the bridge names a provider. A cleared
  result publishes empty, so "no trades" is a value, not an absence.
- **A neutral hook owns policy** — `useBacktestTrades({draw, clear, deps})`,
  a deliberate sibling of `useScriptRun({apply, clear, deps})`, with the same
  contract: providers supply mechanism, the hook decides *when*. What it owns:
  - when trades are considered active,
  - hiding the user's real account trades while they are, and restoring them on
    clear and on unmount — and **only if they were on when we hid them**,
  - redraw on a dep change, teardown on unmount,
  - the async-cleanup race, exactly as `useScriptRun` handles it.
- **Each tree draws.** TV keeps `chartFunctions.drawTrade` +
  `createMultipointShape`. Both reduce to a `draw(trades) -> handles` and a
  `clear(handles)`.

### The SC drawing side is already written, nearly

`createTradeLine` is not new surface for cbsd: `controllers/trades-controller.js`
already draws every real account trade with it, resolving arrow type, colour and
label text from `chartSettings` and registering each handle under
`OverlayGroups.trades`. The backtest markers are the same object with different
inputs, so the SC side reuses that controller's shape rather than calling the SC
API raw.

Two deltas from it:

- **Its own overlay group** — `OverlayGroups.backtestTrades`. Not
  `OverlayGroups.trades`: `clearAllTrades()` would then tear down both sets, and
  the two have independent lifetimes. A separate group also gives batch teardown
  for free, which is the phase-2 `groupId` lesson applied on a different path.
- **The connecting line.** TV draws it with `createMultipointShape("trend_line")`
  coloured by win/loss. SC's equivalent is a segment overlay registered in the
  same group, styled through `extendData` — the pattern phase 2 settled on after
  the figure-`styles`-as-a-thunk bug (a thunk is spread, never called, so
  everything renders klinecharts default blue). Colour is decided in the
  controller, not the component: `feedback_sc_overlay_colors`.

### Why the hide/restore policy is genuinely neutral

It is a redux dispatch on `chartSettings.closedOrdersShow`, and **both**
providers' trade overlays already gate on that flag — TV's `trades.js` and SC's
`super-chart/overlays/trades.js:31`. So the setting is the shared mechanism and
the hook is just deciding when to flip it. Nothing provider-shaped is involved.

The one subtlety to preserve verbatim: the existing effect is driven by
`hasTrades` **only**, not by chart readiness, because dispatching the setting
recreates `chartFunctions` and depending on it would loop and flicker. That is a
hard-won constraint, documented at the site. The neutral hook must keep the two
effects separate for the same reason: one for the setting, one for the drawing.

### Scale

`createTradeLine` is one handle per marker with no batch route. The row-12
reference run was 48 trades — roughly 150 handles including the connecting
lines — so per-marker calls are the right choice. Phase 2's overlay batching
does **not** cover this path. If a real backtest ever produces thousands of
trades, raise it rather than absorbing the stall; the PRD says the same.

## R2 — "add to charts": one resolver, two renderers

### What is already neutral

`~/actions/coinray-chart-scripts.js` — the localStorage list, its change
event, and the toggle — is provider-agnostic today and is reused unchanged. The
IDE's toggle button and `scripts-context`'s delete-drops-it-from-the-list are
likewise untouched.

### What is duplicated if nothing is extracted

Turning an enabled *id* into something a chart can run is four steps:
`getScript(externalId)` → filter `version.resolvedDependencies` → `buildModules`
→ compile. TV does all four inline in `use-trading-view.js:324-347`. SC needs
the first three and **not** the fourth: SC compiles from source, so its add
takes `{code, modules}` while TV's custom indicator takes `{wasm, meta}`.

So the seam is exactly there: **the first three steps are neutral, the compile
is provider-specific.**

- A neutral resolver — `loadChartScripts()` beside the list it reads — returns
  `{externalId, name, source, modules}[]`. It is a plain async function, not a
  hook: TV's call site is a non-React async provider, and forcing a hook shape
  on it would be the tail wagging the dog.
- TV's `chartEnabledProvider` becomes *resolver + its existing compile*. This
  changes TV code under an R5 gate; it is behaviour-preserving by construction
  (the same four steps in the same order, three of them moved) and it is the
  only way to avoid the duplication. Same reasoning phase 2 used to move TV onto
  the shared log sink, and it is called out here so the review can check it
  rather than discover it.
- The `script.modules` trap stays fixed on both paths: helpers come from
  `version.resolvedDependencies`, which is the only place the API returns them.
  This was already a bug once (matrix row 15).

### The SC renderer

A new `super-chart/scripts/sc-chart-scripts-renderer.js`, mounted in
`charts/trading-terminal-chart.js` beside `ScScriptRenderer`.

- **Main chart only, structurally.** That file is the terminal's main chart;
  `/charts`, grid-bot, preview and quiz mount neither renderer. No `mainChart`
  boolean is needed — TV needs one because its widget is shared; SC's tree
  already separates them. This is principle 4 paying out.
- **Keyed by `externalId`, reconciled as a set.** On the list changing, add what
  is new and remove what is gone; do not tear down and re-add the survivors.
  The list changes on every toggle, and a user toggling a second script must not
  make the first one flicker.
- **Lifetime matches `useScriptRun`'s**: re-applied when the controller,
  symbol or resolution changes, cleared on unmount, and every value the apply
  path reads is named in the deps. The controller resolves asynchronously
  through `ChartRegistry` and is undefined on a remounted chart's first render —
  the phase-1 bug this hook's dep list exists to prevent.
- **When to add.** No new SC event is needed. `useScriptRun` already adds the
  preview as soon as the controller exists, which proves `addScriptIndicator`
  does not need to wait for data. SC's session suggested `onDataLoaded` and
  warned off `onApiReady` (it races the restore mirror write); that warning does
  not bind here, because restore never touches `SCRIPT_*` — which is precisely
  why phase 2 took them out of saved state. If ordering ever does bite, cbsd's
  existing `subscribeBarsLoaded` is the equivalent signal and is already used by
  the paging effect in the same folder. **Recorded so the review can challenge
  it**: this is the one place where I am deliberately not taking the peer's
  suggested hook.

### Dedupe against the preview

A script that is both previewed and enabled is added once. The renderer needs
the previewed script's identity to do that, so **`currentRun` gains
`externalId`** — a one-field addition to the bridge payload, null for an unsaved
draft. Matching on source text instead was rejected: two saved scripts can share
a source, and an unsaved edit of an enabled script would stop matching exactly
when the user most expects the preview to win.

Precedence when both are present: **the preview wins.** It is the version the
user is looking at, and it may be edited but unsaved. When the preview ends, the
enabled copy is added.

### What the bridge does *not* carry

The enabled list itself. It is not IDE → chart run data — it is app state that
outlives any run and is read with the Scripts panel closed. TV reads the module
directly from inside its tree; SC does the same. Putting it in the bridge would
widen the seam to carry something neither end is a party to.

## R3 — suppressing SC's Script button

One line, in `charts/market-tab-chart.js` where the provider is built: the same
call site that already decides *whether there is a provider at all*, and whose
comment already says "Charts without one get no provider — and so no Script
button either". After R3 the main chart keeps the provider and loses the button;
every other chart is unchanged.

Depends on SC shipping the `script_button` feature flag (default `true`). Until
it does, passing the name is inert, not broken — SC ignores unknown flags — so
the ordering between the repos is soft.

## The contract — what the host needs from the other repos

### From SuperChart

1. **A `script_button` feature flag**, default `true`, so a host can pass
   `disabledFeatures: ["script_button"]` and keep its `scriptProvider`. Shape is
   SC's call; the flag system is already the established pattern for every other
   top-bar button.
2. **`createTradeLine(chart, options)` stays a public, host-callable API** with
   per-handle `remove()`, usable for a few hundred markers created and torn down
   repeatedly as backtests are run and cleared. cbsd is not asking for a batch
   route; it is asking for the guarantee that repeated create/remove cycles do
   not accumulate.
3. **Backtest trade lines follow the same object-tree treatment as real
   account trades** — i.e. none. SC's session raised this as an open default:
   trade lines are host-owned and, unlike script primitives, are not filtered
   out of the object tree or a drawings export. cbsd is **not** asking for a
   filter. Real account trades already draw through the same API with the same
   exposure, TV behaves the same way, and a backtest's markers are the same kind
   of object. Consistency with the neighbouring feature beats consistency with
   script primitives here: primitives are *script output*, trade markers are
   chart furniture.
4. **`SCRIPT_*` indicators stay out of saved chart state.** Phase 2 established
   it; R2 now *depends* on it, because the enabled list is the sole source of
   truth. If restore ever starts replaying script indicators, R2 double-adds.
   This is the invariant most likely to be broken by accident, so it is written
   down as a promise rather than assumed.

### Invariants

- **Nothing script-shaped enters persistence.** Both directions: cbsd persists
  no provider-side script id (SC's are session-local and non-deterministic —
  `SCRIPT_${++idCounter}`), and SC persists no script indicator.
- **No new host-visible behaviour on the TV side.** R5 is a hard gate. R1 and
  R2 both refactor TV code; both must be observably identical.

## Conformance to the architecture principle

Audited against plan.md -> "Architecture principle".

| # | Principle | Verdict |
|---|---|---|
| 1 | One flow, not two | **Holds, and improves.** Backtest-trade policy and chart-script resolution each become one implementation where R1/R2 could each have been two. |
| 2 | Minimum duplicated code | Holds. The only per-provider code is drawing (TV shapes vs `createTradeLine`) and compiling (wasm vs source), both genuinely provider-specific. |
| 3 | Provider code in provider modules | Holds, and repairs a violation: the TV backtest bridge stops importing the IDE. |
| 4 | No branching outside those modules | Holds. No `chartProvider` test. "Main chart only" is structural on SC — the renderer is mounted only by the terminal's chart. |
| 5 | Symmetry | Holds. Both trees end with a script renderer, a chart-scripts renderer and a backtest-trades module at mirrored paths. |
| 6 | Third provider is additive | Holds. A third provider writes three small modules and touches neither the IDE nor the bridge. |

## Phase-1 and phase-2 lessons applied

The two reviews' findings cluster into the same three shapes, and phase 3's
new state sits on all three axes:

- **Lifetime — the dominant failure mode in both phases.** A captured endpoint,
  an `earliest` high-water mark surviving a re-run, a dep array missing an
  asynchronously-resolved controller. Phase 3's new state is a set of chart
  script handles and a set of trade handles. Both are owned by the effect that
  created them, reconciled rather than accumulated, and torn down on symbol,
  resolution and unmount. The `closedOrdersShow` restore is the sharpest case:
  it must restore the value that was true *when it hid it*, which is why the
  existing code keeps it in a ref, and why the neutral hook must too.
- **Dep arrays.** `useScriptRun` spreads its deps and so opts out of
  `exhaustive-deps` — the exact hole the phase-1 `chartController` bug came
  through. `useBacktestTrades` inherits that hazard by construction. Everything
  its callbacks read is named in `deps`, with the reason stated at the call
  site, and the same applies to the chart-scripts renderer.
- **No dead paths.** Phase 1 shipped a memoized, documented, never-called
  `clear()`. Every channel added here has both ends written in this phase.
- **Verify against the artifact, not the pixels.** From the phase-2 review: an
  item was marked passed off a screenshot while the app ran a stale bundle. R2
  is especially exposed — "the script is on the chart" looks the same whether it
  came from the enabled list or a leftover run — so acceptance for R2 must
  identify *which* path put it there (IDE closed, fresh reload), not merely that
  something is drawn.
- **Silent-nothing is the expensive failure mode.** `buildMetadata` returning
  `plots: []` cost a wrong diagnosis because the add resolved normally and drew
  nothing. R2 has the same shape available to it: a script that fails to resolve
  (deleted server-side, helpers missing) must report, not vanish. TV logs and
  continues; SC should surface the failure through the bridge's existing failure
  channel where a run is involved, and log where one is not.

## Accepted gaps

- **No picker entry for enabled scripts on SC.** PRD non-requirement, agreed
  with the SC session: SC has register-vs-place only on the backend-indicator
  path. The user-visible part — the script is on the chart — is reproduced.
- **The enabled list stays per-device.** Same as TV.
- **The ta-v2 redeploy is not a phase-3 deliverable**, though the phase would
  like it: it closes matrix row 3's remaining ⚠ and `buildMetadata`'s SDK layer
  in one step. Human, credentialed, scheduled separately.

## Decisions taken during design

- **Backtest trades go through the bridge; the enabled list does not.** The
  trades belong to a run the IDE is showing — the bridge's existing subject. The
  enabled list is app state read with the IDE closed, and putting it in the
  bridge would make the seam carry something neither end owns.
- **Policy goes in a neutral hook, not in a shared component.** A component
  would have to be mounted by both trees and would drag React structure across
  the seam; a hook lets each tree keep its own mount point and supply only
  mechanism. This is `useScriptRun`'s shape, reused rather than reinvented.
- **TV moves onto the shared resolver despite R5**, for the same reason phase 2
  moved TV onto the shared log sink: the alternative is two copies of the
  fetch-and-rebuild-modules logic, which principle 2 exists to prevent. The move
  is behaviour-preserving by construction and is flagged for the review.
- **The preview wins over an enabled copy of the same script.** It is what the
  user is looking at, and it may be unsaved.
- **`currentRun` gains `externalId`** rather than dedupe-by-source. Source
  matching breaks precisely when a user edits an enabled script.
- **No new SC event for "safe to add indicators".** `useScriptRun` already
  proves the controller's existence is sufficient. Recorded as a deliberate
  divergence from the SC session's suggestion, with `subscribeBarsLoaded` named
  as the fallback if it proves wrong.
