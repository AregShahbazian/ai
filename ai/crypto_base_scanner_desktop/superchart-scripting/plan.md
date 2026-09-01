# SuperChart scripting port — plan

Scripting works on TradingView today. This plans the port to SuperChart.
Background and terminology: [guide.md](guide.md). Running observations and
gotchas: [notes.md](notes.md).

**Hard constraint (Areg, 2026-08-28):** TV and SC coexist. All functionality
keeps working on both; nothing may break for either. The SC path is additive
code beside the TV path.

**Phase PRDs** land in this folder as each phase starts.

## Scope (surveyed 2026-08-28)

Scopes the actual work. Verified against
SC `main` `d5298aa`, coinray_rest `master` `87ba31b6`,
`@coinrayio/superchart-script@0.1.8`.

### Not greenfield — but not wired either
The package is named for SC because that is what it was built for
(`package.json`: "Execute-only scripting **ScriptProvider for
@coinrayio/superchart**"). Roughly 15% of it is SC-coupled and dormant today:
`WasmScriptProvider.ts` (329 lines), `subscriptionAdapter.ts` (135),
`candleSource.ts` (91) — ~555 of ~3,744. Altrady uses only the `/engine`
subpath (`StrategyHost`, `TaEngine`, `compileStrategy`) plus `CodeEditor` +
`COINRAY_STRATEGY_LANGUAGE`; SC's own `ScriptEditor` widget stays unused
because Altrady keeps its own IDE.

`subscriptionAdapter.ts` already maps engine events → `IndicatorDataPoint[]` +
primitives — the SC-flavoured equivalent of the TV shim in
`…/tradingview/controllers/ci/coinray-strategy.js`. **Read `WasmScriptProvider.ts`
before designing anything.**

Nothing in `src/containers/trade/trading-terminal/widgets/super-chart/` passes a
`scriptProvider` to `new Superchart()` today. Zero wiring.

### The four real gaps
1. ~~**Editor-slot vs bypass**~~ — **DECIDED 2026-08-28: option B, a public
   entry point.** SC `main` already renders plots, panes, settings and
   primitives, but that pipeline (figures, `reconcilePrimitives`, pane grouping)
   only fires from `SuperchartComponent`'s internal script-editor handler
   (`SuperchartComponent.tsx:1238`); there is no public
   `chart.addScriptIndicator()`.
   **Rejected (A):** mounting Altrady's IDE as `ScriptProvider.EditorComponent`.
   TV and SC coexist, so the one FlexLayout Scripts panel would have to mount
   twice — two component instances, split `ScriptsProvider` state, and inside SC
   it becomes an SC-rendered overlay rather than a docked panel.
   **Chosen (B):** add a public method to SC that does what the internal handler
   does, and call it from Altrady the way `createStudy` is called today. The
   editor slot stays unused and the Script button is suppressed. Costs SC code —
   Areg has push access to SC and will write it.
2. **`param.*` cannot reach a running script.** `settings` is never passed to
   `executeAsIndicator`, and there is no `updateSettings`. Upstream fix.
3. **No `onSymbolPeriodChange`, and no way to hide SC's `fx`/Script button** —
   the editor chrome renders unconditionally whenever `scriptProvider` is set,
   colliding with Altrady's own toolbar. Upstream fix.
4. **Orders are architecturally undecided.** SC has no order concept;
   `executeAsBot` exists but nothing maps `strategy.long/short/close` onto it.

**Coexistence is a hard constraint (Areg, 2026-08-28):** TV and SC both keep
working; nothing may break for either. Consequences: the SC path is additive
code beside the TV path, `src/containers/scripts/**` must become
provider-agnostic (today `loadOnChart` hardcodes the TV route through
`use-trading-view.js`), and the 15-row capability matrix becomes a regression
checklist run once per provider.

Gaps 1–3 largely collapse if the SC author exports an entry point and adds a
suppress flag — worth settling with Benoist *before* writing code.

### Near-zero work
- **Backtest.** It is a REST call to `ta-v2` (`coinray-script-backtest.js`) with
  a Highcharts report — chart-agnostic. The only chart coupling is feeding
  backtest trades into the existing trades overlay (`backtest-panel.js:179`),
  which SC already renders.
- **Re-run / hot-swap.** `executeAsIndicator` is simply called again. TV's
  `getLiveWasm` hack and widget reload have no SC equivalent; several bugs fixed
  during Part 1 do not exist on SC.
- **`declareAlert()`.** Safe from 0.1.8 onward. Caveat: `compileStrategy()`
  discards the server's `alerts` array, so an alert picker must read
  `host.declaredAlerts` after `load()`.

### Architecture principle — provider-agnostic by default (binding, all phases)

Scripting is a **chart-agnostic feature**. TradingView and SuperChart are two
renderings of the same thing, and the code must say so. This holds for every
phase, not just phase 1 — re-read it before designing each one.

1. **One flow, not two.** Compile, run, re-run, stop, symbol change, cleanup —
   the *policy* is provider-neutral and written once. Only the *mechanism*
   differs per provider.
2. **Minimum duplicated code.** If both providers need the same logic, it lives
   in the neutral layer. Two near-identical blocks in two adapters is a defect,
   not a coincidence.
3. **Provider-specific code lives in provider-specific modules.** TV code under
   the TV chart tree, SC code under the SC chart tree. Nothing provider-specific
   in the shared scripts modules — no TV concepts leaking into neutral names,
   no SC concepts either.
4. **No provider branching outside those modules.** Prefer *structural*
   selection — a module mounts only under its own provider — over
   `if (chartProvider === …)`. A branch is a last resort, and it belongs in the
   bridge, never in the IDE or a feature module.
5. **Symmetry.** The two adapters expose the same surface to the bridge, and sit
   at mirrored paths. Asymmetry is the early warning that something neutral has
   drifted into one side.
6. **A third provider is additive.** Adding one should mean writing one adapter
   and one renderer — touching no IDE code, and ideally no bridge code either.

The payoff is that a future fix is either "neutral, fixes both" or "this
provider only", and you can tell which from where the file lives.

### Phases
Agreed 2026-08-28. Each phase gets its own PRD in this folder when it starts.
All 15 capability-matrix rows must work eventually; the split is about ordering,
not scope. Every phase keeps TV working — coexistence is a hard constraint.

**Phase 1 — Spine.** The public entry point in SC (decision B), the
provider seam in `src/containers/scripts/**`, and plots + panes rendering.
Done when "Run on chart" puts a working indicator on an SC chart. Proves the
architecture; everything after is additive.

**Phase 2 — Parity. DONE 2026-09-01.** `param.*` settings (needs the SC +
`superchart-script` changes both), console logs, helper modules on the compile
path, real compiler diagnostics, and making `draw.*` primitives scale. Scoped in
[phase-2/prd.md](phase-2/prd.md) (`sc-script-parity`); verified in
[phase-2/review.md](phase-2/review.md) — 52 of 53 items pass, item 31 blocked
(below).
**Correction, 2026-08-31:** primitives were listed here as missing. They are
not — `draw.*` already renders end to end on SC (verified in-browser; see
phase-1/review.md item 37). What phase 2 owed them is batching: 8k overlays
were O(n²) through SC's engine, and 663 ms to tear down — now 6 ms, via one
`groupId: 'script:<hostId>'` per run.

**Phase 3 — Trimmings. DONE 2026-09-01.** Backtest wiring (near-zero — the report is
chart-agnostic; only the trades overlay is coupled), "add to charts"
persistence across layouts, and suppressing SC's Script button. Scoped in
[phase-3/prd.md](phase-3/prd.md) (`sc-script-trimmings`); matrix rows 12 and
15. Expected to touch cbsd and SC only — `superchart-script` takes no part in
a backtest, confirmed 2026-09-01.

**Carried into phase 3 (found 2026-08-31, during phase-2 review):** SC's
settings modal reaches `modifyIndicator` with raw `BACKEND_<id>` names, so a
backend indicator can be snapshotted into saved chart state the same way script
indicators were. Same structural leak, different prefix; unreported by users so
far and outside scripting, so phase 2 fixed only the `SCRIPT_` half at the
chokepoint. Areg's call, 2026-08-31: note it for phase 3 rather than widen
phase 2.

### Shipped — phase 3 (2026-09-01)

One squashed commit per repo. `coinray_rest` took no part, so there is **no new
package version and no CI change** — the alpha picks up SC's new branch head
through the phase-2 repoints.

| repo | branch | commit |
| --- | --- | --- |
| crypto_base_scanner_desktop | `feature/superchart-scripting` | `93e644217` |
| Superchart | `feat/superchart-scripting` | `b586329` |

Review: **36 of 40 pass, 4 blocked** ([phase-3/review.md](phase-3/review.md)).
Four bugs were found and fixed during it, one of them a lifetime bug in phase-1's
`useScriptRun` that affected both providers.

**Open after phase 3:**
- **Items 28-31 are ⛔ blocked, not deferred.** Altrady wires no
  `indicatorProvider`, so no `BACKEND_` indicator can exist to test the
  persistence fix against. SC's half ships on its unit coverage. Revisit only if
  Altrady ever wires a provider.
- **The ta-v2 compiler redeploy is still pending**, and phase 3 gave it a second
  reason: whether a `plot()` registers depends on how much history happens to be
  loaded when a script is added, so the same script can render from the enabled
  list and draw nothing when previewed. Human step; closes matrix row 3's
  `options` gap in the same deploy.
- **The backtest engine's `pnl` sign is worth a look** — a 90-day run returned 81
  trades and zero winners, including longs exiting above their entry with a large
  negative pnl. Server-side in `coinray_script`, and it predates the port: the
  TradingView path has always coloured from the same field.
- **The three CI repoints from phase 2 still stand** and revert together when
  `feat/superchart-scripting` and `feat/overlay-store-scaling` reach their mains.

**Phase 4 — Orders.** `strategy.long/short/close` → `executeAsBot`. Split out
because SC has no order concept today and the mapping is an open design
question, not a port.

### Repos touched
- **SC** — public entry point, Script-button suppression, pass `settings` to
  `executeAsIndicator` + an `updateSettings`. Smallest diff, highest leverage.
- **coinray_rest** (`packages/superchart-script`) — `settings` in
  `buildMetadata` (hardcoded `[]` today), `modules` on `compileStrategy`, real
  diagnostics (currently every error is reported at line `i+1`, col 1), an
  `onLog` channel. Then publish 0.1.9.
- **crypto_base_scanner_desktop** — the provider seam, wiring
  `WasmScriptProvider` into `super-chart/`, TV path untouched.

**Phase 1 touches only two of them**: SC (the public entry point) and
crypto_base_scanner_desktop (the bridge + wiring). `superchart-script` is
expected to need no changes in phase 1 — `WasmScriptProvider` and
`subscriptionAdapter` already cover plots, `plotPane`, history, live ticks and
`stop()`; its known holes are all phase 2 work.

While iterating, link a local build of `superchart-script` rather than
republishing per change (as was done for the `declare_alert` fix).

### Cross-repo agent delegation (agreed 2026-08-28)

Generalised since — this is now the standing method for any multi-repo PRD;
see `~/ai/workflow.md` -> "Multi-repo work". The port spans three repos. Rather than one session editing all of them,
**each repo gets its own Claude session, started in that repo's root.** The
session working in `crypto_base_scanner_desktop` coordinates; it delegates the
SC and coinray_rest work to those sessions by message.

- **Areg starts the sessions.** The coordinating session never spawns a
  sub-agent to edit another repo — it waits until Areg confirms a session is
  running there.
- **Why:** each session gets the correct working directory, that repo's own
  `CLAUDE.md`, and its own git context and branch. No cross-repo working-tree
  entanglement, and no worktree confusion.
- **Delegation carries context, not just a task**: which phase and PRD id, the
  contract being added or consumed, and what the calling side expects. Peer
  sessions have none of this conversation's history.
- **Permissions do not transfer between sessions.** A peer session cannot grant
  another one an escalation. If a peer reports it was denied something and asks
  the coordinator to do it instead, the coordinator refuses and surfaces it to
  Areg.
- **Nothing is pushed by any session** unless Areg says so explicitly, in that
  repo, for that push.

### Effort
Multi-day integration, not a glue task. Phase 1 carries the architectural risk;
2-4 are additive.


## Phase tracker

`[ ]` not started · `[~]` in progress · `[x]` done. Each phase gets its own PRD
in this folder when it starts.

- [x] Phase 1 — Spine (SC entry point, provider seam, plots + panes) — [prd](phase-1/prd.md) `sc-script-spine`
- [x] Phase 2 — Parity (params, logs, modules, diagnostics, primitive scaling) — [prd](phase-2/prd.md) `sc-script-parity`
- [x] Phase 3 — Trimmings (backtest, add-to-charts, hide Script button) — [prd](phase-3/prd.md) `sc-script-trimmings`
- [ ] Phase 4 — Orders (`strategy.*` → `executeAsBot`)

### Shipped — phase 2 (2026-09-01)

One squashed commit per repo, all pushed:

| repo | branch | commit |
| --- | --- | --- |
| crypto_base_scanner_desktop | `feature/superchart-scripting` | `f6d99e239` + `dc4a13cbc` (CI/version) |
| Superchart | `feat/superchart-scripting` | `5986d63` |
| coinray-chart (SC submodule) | `feat/overlay-store-scaling` | `e5f19660` (new branch) |
| coinray_rest | `master` | `8ab06cdf` + `155723a3`, published as `@coinrayio/superchart-script@0.1.9` |

**Open after phase 2:**
- **Item 31 (publish a helper module) is ⛔ blocked**, not failed: the backend
  returns 422 `{"error": ["A username is required to publish a module"]}` even
  with the profile username set. The endpoint lives in `crypto_base_scanner` —
  a fourth repo, outside this port. Re-test once it accepts module creation.
- **ta-v2 compiler redeploy pending.** `buildMetadata` was fixed in three
  layers; the SDK layer only reaches scripts compiled by an updated ta-v2. Until
  that deploys, a `plot()` of an all-NaN warmup window can still render nothing
  unless the script sets `config.warmup`.
- **Three CI repoints must be reverted on merge** (all marked TEMPORARY):
  SC branch in `d1f7d4943`, and the coinray-chart submodule branch plus the
  `0.1.9` pin in `dc4a13cbc`. Revert when `feat/superchart-scripting` and
  `feat/overlay-store-scaling` reach their mains.

### Decisions taken
- **2026-08-28 — Option B, a public entry point in SC** (not SC's editor slot).
  Reasoning under "The four real gaps" #1.
- **2026-08-28 — TV and SC coexist.** All 15 capability-matrix rows must work on
  both, eventually; the phases order the work, they do not reduce scope.
- **2026-08-31 — the seam stays structural.** Phase 2 added a second, opposite
  direction to the bridge (chart → IDE: `registerConsumer` / `publishLogs` /
  `publishFailure`) without a single `chartProvider` test anywhere in the
  scripting path. Selection is still "which chart tree mounted this renderer",
  per principle #4 above. A third provider remains one adapter + one renderer.
- **2026-08-31 — fixes get their own WIP commits, squashed at phase end.** One
  commit per repo per phase; WIP commits are never pushed.
