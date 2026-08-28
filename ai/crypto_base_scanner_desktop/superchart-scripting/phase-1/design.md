# Phase 1 design — spine [sc-script-spine]

Implements [prd.md](prd.md). Verification lives in [review.md](review.md).

## Shape of the solution

Three moving parts:

1. **SuperChart** gains a *public* way to put a script indicator on a chart.
   Today the only caller of `scriptProvider.executeAsIndicator()` is SC's own
   internal `handleAddToChart`, reachable solely through the editor slot.
2. **cbsd** constructs a `ScriptProvider` per SC chart and mounts a small
   renderer component beside the existing SC overlays.
3. **A chart-bridge module** holds the provider-neutral "run this script"
   state. The IDE writes to it; each provider's renderer reads from it.

The provider decision is **structural, not a branch**: the TV renderer only
mounts under the TV chart tree, the SC renderer only under the SC chart tree.
Neither the IDE nor the bridge ever tests `chartProvider`.

## The seam

```
Scripts IDE  ──loadOnChart()──►  chart-bridge (context)
                                   currentRun = {runId, name, source,
                                                 modules, wasm, meta}
                                         │
              ┌──────────────────────────┴──────────────────────────┐
              ▼ (mounted in TV chart tree)      (mounted in SC chart tree) ▼
      tv-script-renderer                         sc-script-renderer
      preview/nonce/structureKey                 addScriptIndicator(source)
      → custom_indicators_getter                 → provider.executeAsIndicator
```

`currentRun` carries **everything both adapters need**: `source` + `modules`
for SC (whose `executeAsIndicator` takes source), `wasm` + `meta` for TV
(whose shim instantiates bytes directly). One bump of `runId` per press of
**Run on chart**.

### Module layout (cbsd)

Neutral core, then one mirrored folder per provider — never provider code in
the neutral folder (plan.md principle 3 and 5):

```
src/containers/scripts/chart-bridge/          # neutral only
  index.js                 ScriptChartBridgeProvider + useScriptChart()
  use-script-run.js        the shared apply/re-apply/clear policy

…/center-view/tradingview/scripts/            # TV-only
  tv-script-renderer.js    the run-state machine moved out of scripts-context
                           (absorbs today's script-preview-bridge.js)

…/super-chart/scripts/                        # SC-only
  sc-script-renderer.js
```

Earlier drafts put a `tradingview-adapter.js` inside `chart-bridge/`. That is
exactly the asymmetry principle 5 warns about — TV code in the neutral folder,
SC code in the SC tree — so the TV state moves next to the TV chart instead, and
`chart-bridge/` holds nothing that names a provider.

`ScriptChartBridgeProvider` wraps the same subtree `ScriptsProvider` does, so a
single instance backs both chart trees (there is only ever one Scripts panel).

## What moves out of `scripts-context.js`

`preview`, `previewStudies`, `registeredPreviewKey`, `pushPreview` and the
`structureKey` computation are TradingView concepts. They move verbatim into
`chart-bridge/tradingview-adapter.js`; `scripts-context` keeps only:

```js
const loadOnChart = useCallback(async () => {
  const compiled = await ensureCompiled()        // unchanged — also the diagnostics path
  if (!compiled) return null
  return chartBridge.run({
    name: selected.name || "Preview script",
    source, modules, wasm: compiled.wasm, meta: compiled.meta,
  })
}, [ensureCompiled, chartBridge, selected, source, modules])
```

Everything downstream of `pushPreview` on the TV side keeps its current
behaviour byte-for-byte — the TV adapter still exposes `preview`,
`setPreviewStudies`, `setRegisteredPreviewKey` through the bridge context, and
`tradingview.js` and the renderer read them from there instead of from
`useScripts()`. That is the whole TV diff, and it is what R5 rides on.

## SuperChart change — what the host needs

**Capability requirements, not an interface.** The shape was the SC agent's to
design; what follows is only what the host must be able to do. **The agreed
shape is now settled in [sc-design.md](sc-design.md)** — on `SuperchartApi`,
beside `openScriptEditor`:

```ts
addScriptIndicator(params: {code, language?, settings?}): Promise<string>
removeScriptIndicator(scriptId: string): Promise<void>
onScriptIndicatorRemoved(cb: (scriptId: string) => void): () => void
```

Internals are a new `useScriptIndicators` hook mirroring `useBackendIndicators`;
the editor's `onAddToChart` calls the same `add()`, so there is one behaviour
with two entry points. `settings` is forwarded to `executeAsIndicator` from
phase 1 (there is still no update path — that is phase 2).

Today the only caller of `scriptProvider.executeAsIndicator()` is SC's internal
`handleAddToChart`, reachable solely through the editor slot. Phase 1 needs the
same capability reachable programmatically.

### The three capabilities

1. **Add.** Given script source (and, in future, a language and a settings
   map), put the resulting script indicator on the chart, and hand back an
   identifier the host can hold.
2. **Remove.** Given that identifier, take the script off the chart completely.
3. **Notice.** Learn when a script indicator was removed by the *user* rather
   than by the host.

### Invariants the host depends on

- **Add produces exactly what the editor's `onAddToChart` produces** — same
  plots, same panes, same primitive wiring. One behaviour, reachable two ways;
  no second implementation that can drift.
- **Remove is a complete teardown**, indistinguishable from the user clicking
  the ✕ on the indicator's pane legend: every `SCRIPT_<id>*` template gone,
  that script's primitives gone, `provider.stop(id)` awaited. R3 and R4 rest
  entirely on this.
- **Remove on an unknown or already-removed identifier is a no-op**, not a
  throw. The host can race the user.
- **The identifier is stable and opaque** to the host — held across renders,
  handed straight back to remove.
- **Reachable from whatever handle the host already has** for a mounted chart.
  If that means a new accessor, say so; the host will adapt.

The removal notice is a nice-to-have. Without it the host still works, thanks
to the no-op rule — it just holds a dead identifier until the next run.

### Deliberately not asked for

- **Symbol/period awareness inside `ScriptProvider`.** Altrady already knows
  symbol and resolution in React and drives the re-run itself (below). Cheaper
  than new SC surface.
- **Any way to hide the Script toolbar button.** Phase 3.
- **`settings` / `updateSettings` plumbing.** Phase 2. Worth *accepting* a
  settings argument now purely so adding it later is not a breaking change —
  but that is a suggestion, not a requirement.

## SC provider construction

`WasmScriptProvider` from `@coinrayio/superchart-script` is used as-is. It is
**per chart**, not a singleton, because its `datafeed` option must be the same
instance passed to `createDataLoader` for that chart. Built in the
`useChartLifecycle` `setup()` hook and passed through `superchartOptions`:

```js
const scriptProvider = new WasmScriptProvider({
  datafeed,
  compileEndpoint: `${taEndpointFrom(apiEndpoint)}/api/v1/ta/strategy/user/compile?exchange=BINA`,
  compileHeaders: {Authorization: `Bearer ${await coinrayToken()}`},
})
```

reusing `taEndpointFrom` / the token lookup already in
`src/actions/coinray-strategy.js:79-85`.

Two wrinkles:

- **Hide the package's editor.** `WasmScriptProvider` declares
  `EditorComponent = ScriptEditor`, and SC renders the Script toolbar button
  whenever `scriptProvider` is truthy. Wrap it in a thin object that forwards
  everything **except** `EditorComponent`, so the button is inert rather than
  opening a second, competing IDE. Removing the button itself is phase 3.
- **Double compile on first run.** The IDE compiles for diagnostics;
  `executeAsIndicator(code)` compiles again inside the provider. Both memoise
  by source, so it is one extra request per new source, not per run. Accepted
  for phase 1; the clean fix is an upstream `primeCompiled(code, {wasm, meta})`
  on `WasmScriptProvider`, which belongs with the phase-2 package work.

## Lifecycle — how R3 and R4 are satisfied

`sc-script-renderer` is the neutral `useScriptRun` hook over
`[runId, coinraySymbol, resolution]` holding one `scriptIdRef`:

```
cleanup:  if (scriptIdRef.current) <remove>(scriptIdRef.current)
effect:   if (!currentRun) return
          scriptIdRef.current = await <add>(currentRun.source)
```

That single effect covers every R3/R4 case:

| Requirement | Mechanism |
|---|---|
| Re-run replaces (R3) | `runId` changes → cleanup removes, effect re-adds |
| Plot-set / pane / warmup / name change | irrelevant — there is no `structureKey`; every run is a full remove-and-add. The TV bug class cannot occur here by construction. |
| Symbol / resolution change (R4) | in the dep array → same remove-and-add against the new series |
| Unmount / layout switch / widget close (R4) | React cleanup |
| User clicks ✕ (R4) | SC stops the script itself; the removal notice clears `scriptIdRef` |

`onScriptIndicatorRemoved` fires for host-initiated removals as well, so the
handler must ignore any id that is not the one currently held:

```js
onScriptIndicatorRemoved((id) => { if (id === scriptIdRef.current) scriptIdRef.current = null })
```

Without that guard a remove-then-add cycle can null out the *new* handle if the
notice for the old removal lands late.

Remove-and-add costs a re-execute on every edit, unlike TV's hot-swap. At
~500 history bars that is cheap, and correctness is the phase-1 goal.

## Conformance to the architecture principle

Audited against plan.md -> "Architecture principle". Honest verdict: mostly
compliant, two things fixed during this audit and one accepted compromise.

| # | Principle | Verdict |
|---|---|---|
| 1 | One flow, not two | **Fixed.** The re-apply policy (apply `currentRun`; re-apply when `runId`, symbol or resolution changes; clear on unmount) was written twice — once per renderer. It is now one neutral hook, `use-script-run.js`. Each renderer supplies only `apply` and `clear`. |
| 2 | Minimum duplicated code | Follows from 1. What remains per-provider is genuinely different mechanism: TV hot-swaps bytes and reloads on structural change; SC removes and re-adds. Not duplication. |
| 3 | Provider code in provider modules | **Fixed.** The TV adapter no longer lives in `chart-bridge/`. See the module layout above. |
| 4 | No branching outside those modules | Holds. There is no `chartProvider` test anywhere in this design — selection is structural, by mount site. `scripts-context.js` calls `chartBridge.run(...)` and knows nothing else. |
| 5 | Symmetry | Holds after the move: mirrored `…/tradingview/scripts/` and `…/super-chart/scripts/`, both consuming the same bridge + hook. |
| 6 | Third provider is additive | Holds. A third provider is one renderer folder plus its mount. No IDE change, and no bridge change either. |

**Accepted compromise — the neutral `currentRun` carries both payloads.** It
holds `source` + `modules` (what SC's `executeAsIndicator` takes) *and* `wasm` +
`meta` (what TV's shim instantiates). Strictly, that is two provider-shaped
fields in a neutral object. It stays because both are outputs of the *same*
compile the IDE already runs for diagnostics — the object is "the script and its
compiled artifact", which is a coherent neutral idea, and the alternative
(per-provider compile inside each adapter) duplicates the compile call and
splits the diagnostics path. Revisit if a third provider needs a third field.

**Deliberately partial — TV's migration onto the shared hook.** R5 forbids any
behavioural change on TV, and TV's state machine has reload guards that the
neutral hook does not model. Phase 1 writes the hook for SC and moves TV onto it
only where behaviour is provably identical; the rest of TV's machine stays as-is
inside `tv-script-renderer.js`. Full convergence is a phase-2 cleanup, once the
TV path is covered by the phase-1 regression pass. Recording it so it does not
quietly become permanent.

## Rejected alternatives

- **Mount Altrady's IDE as `ScriptProvider.EditorComponent`.** With TV
  coexisting, the one FlexLayout Scripts panel would have to mount twice,
  splitting `ScriptsProvider` state. (Decision B in ../plan.md.)
- **Teach `WasmScriptProvider` to accept pre-compiled wasm for phase 1.**
  Correct eventually, but it is a third-repo change for an efficiency gain, and
  the PRD scopes phase 1 to two repos.
- **Add symbol/period awareness to SC's `ScriptProvider`.** More SC surface for
  something the host can already do with the React deps it holds.
- **Keep the run state in `scripts-context.js` and branch on `chartProvider`.**
  Directly against R6.

## Accepted SC-side gaps

From [sc-design.md](sc-design.md) — known, not fixed in phase 1:

- **`registerIndicator` has no inverse.** Every run leaves a dead `SCRIPT_<id>`
  template in klinecharts' module-level registry. Invisible, no collision (ids
  are unique), no correctness impact. It does mean review.md's "ten re-runs"
  test reads as *no duplicates on the chart* — which is what it says. A real
  `unregisterIndicator` belongs in `packages/coinray-chart`, a repo boundary
  beyond this phase.
- **Template apply wipes script plots without stopping the script.** The host
  does not apply templates on the TT market chart, so phase 1 never hits it.
  Phase 3 ("Add to charts") will.
- **SC does nothing on symbol/period change.** By design — the host's
  remove-and-add effect is the only guard. If a dep is ever missed, SC will not
  catch it.
- **`add`/`remove` race on a fast double "Run on chart"** is guarded SC-side:
  `remove` on an in-flight id marks it, and `add` tears down and rejects with
  `'removed before start'` on resolve. The host must tolerate that rejection.

## Decisions taken during design

- **Scroll-back is in scope.** `WasmScriptProvider.loadHistoryBefore()` is wired
  to `DataLoader.setOnBarsLoaded`, which `useChartLifecycle` already exposes.
  Without it the script visibly stops mid-chart when you scroll left — that
  reads as a phase-1 defect, not a deferred feature.
- **Deps doc drift fixed.** `deps/COINRAY_REST_API.md` carried a stale "⛔
  Cannot be used against Superchart `main`" box on `WasmScriptProvider`; the
  blocker was resolved at `d5298aa`. Corrected — verified SC `main` is at
  `d5298aa` and cbsd pins `@coinrayio/superchart-script` 0.1.8.
- **Trading Terminal main chart only.** The renderer mounts on the TT market-tab
  chart and nowhere else — not `/charts`, not preview, grid-bot or
  customer-service charts. The Scripts IDE only exists in the Script Editor
  layout, so nothing else has a script to run. `/charts` gets scripts in phase 3
  with "Add to charts".
