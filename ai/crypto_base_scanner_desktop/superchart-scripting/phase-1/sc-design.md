# Phase 1 — SuperChart-side design [sc-script-spine]

Satisfies [design.md § SuperChart change — what the host needs](design.md#superchart-change--what-the-host-needs):
three capabilities (add / remove / removal notice), four invariants, reachable
from the handle the host already holds. The interface shape below is SC's
proposal; the host adopts it verbatim. Verified against SC `main` `d5298aa`
(2026-08-28).

## Proposed public interface

Three methods on `SuperchartApi` — i.e. on the `Superchart` instance the host
already holds — placed beside `openScriptEditor` / `closeScriptEditor`:

```ts
/** Execute `code` through the configured ScriptProvider and render it exactly
 *  as the editor's "Add to chart" does. Resolves an opaque, stable scriptId.
 *  Rejects if no scriptProvider is configured or execution fails. */
addScriptIndicator(params: ScriptIndicatorParams): Promise<string>
/** Complete teardown — same path as the pane-legend ✕. No-op for unknown ids. */
removeScriptIndicator(scriptId: string): Promise<void>
/** Fires after a script indicator is removed by any path (legend ✕, this API,
 *  chart dispose). Returns an unsubscribe. */
onScriptIndicatorRemoved(callback: (scriptId: string) => void): () => void

interface ScriptIndicatorParams {
  code: string
  language?: string                        // default: provider.language?.name ?? 'pine'
  settings?: Record<string, SettingValue>  // forwarded to executeAsIndicator; no update path yet
}
```

Why this shape, per SC convention:

- **On `SuperchartApi`, not a new accessor.** Every host-facing imperative
  operation lives there (`removeIndicator`, `createOverlay`, `setAlerts`,
  `openScriptEditor`); `getBackendIndicators()` returning a sub-API is the one
  exception and is not a pattern worth extending. No new handle for the host.
- **Options object for add** — matches `openScriptEditor(options)` and
  `createOverlay(overlay)`; lets `settings` land later without a signature
  change.
- **`on*` returning an unsubscribe** — identical to `onSymbolChange`,
  `onPeriodChange`, `onVisibleRangeChange`.
- **`scriptId` is the provider's `subscription.indicatorId`**, the same string
  `provider.stop()` takes. Opaque to the host; SC keys all bookkeeping on it.
- **Naming** parallels the existing `removeIndicator` / `removeOverlay` and the
  `SCRIPT_` prefix family.

The rest of this doc is how SC satisfies it.

## Where things are today (`SuperchartComponent.tsx`)

| Concern | Location today |
|---|---|
| The whole add pipeline (execute → figures → `registerIndicator` × N → `createIndicator` × N → `onData/onTick/onHistory` → `reconcilePrimitives`) | inline in the JSX `onAddToChart` prop of `<ScriptEditor>`, `SuperchartComponent.tsx:1226–1872` (~650 lines) |
| scriptId → primitives | `scriptOverlaysRef: Map<scriptId, Map<key, TrackedOverlay>>` (`:418`) |
| template name → owning scriptId | `scriptTemplateOwnerRef: Map<templateName, scriptId>` (`:422`) — added in `5aab82e` for `SCRIPT_<id>_<pane>` |
| Teardown | the `'close'` case of the indicator-tooltip feature handler, branch `name.startsWith('SCRIPT_')` (`:661–682`): `provider.stop(id)` (fire-and-forget), `removeIndicator` for the clicked template, loop the owner map to remove siblings, drop that script's overlays |
| API object | `useEffect` at `:720–967` building `SuperchartApi`, handed up via `onApiReady`; `Superchart.ts` forwards each method through `this._api?.x()` |
| Provider access | `store.scriptProvider()` signal; `Superchart.dispose()` calls `provider.dispose()` but nothing stops running scripts on unmount |

Two facts shape the design: the add pipeline is a closure over `store`,
`scriptProvider`, the two refs and the two `log` helpers — nothing else from the
component; and the teardown only needs the chart, the provider and the two refs.
Both can leave the component.

## Decision: one hook, `useScriptIndicators`

Extract everything script-related into `src/lib/hooks/useScriptIndicators.ts`,
mirroring `useBackendIndicators` (same file layout, same "hook returns an
imperative API object" shape, same `*Ref` bookkeeping). The component keeps only
JSX and wiring.

```ts
export interface UseScriptIndicatorsReturn {
  /** Execute + render. Resolves the scriptId (= subscription.indicatorId). */
  add: (params: { code: string; language?: string; settings?: Record<string, SettingValue> }) => Promise<string>
  /** Complete teardown. No-op for unknown ids. Awaits provider.stop(). */
  remove: (scriptId: string) => Promise<void>
  /** Reverse lookup used by the legend-✕ handler. */
  ownerOf: (templateName: string) => string | undefined
  /** Fires after any removal, whichever path triggered it. */
  onRemoved: (cb: (scriptId: string) => void) => () => void
  /** Unmount: remove everything, best-effort. */
  disposeAll: () => void
}
```

### Bookkeeping — one record per script

The two refs collapse into a single map so a script's whole footprint is one
object and can never half-exist:

```ts
interface ActiveScript {
  scriptId: string
  templates: string[]                     // SCRIPT_<id> and/or SCRIPT_<id>_<pane>
  primitives: Map<string, TrackedOverlay> // reconcilePrimitives' tracked set
  subscription: IndicatorSubscription
}
const activeRef = useRef<Map<string, ActiveScript>>(new Map())
```

`ownerOf(name)` is a linear scan over `activeRef` (a handful of entries) — the
separate `scriptTemplateOwnerRef` index goes away. The fallback
`name.slice('SCRIPT_'.length)` in the current ✕ handler is dropped: it is wrong
for `SCRIPT_<id>_<pane>` names and was only ever a pre-`5aab82e` safety net.

### `add(params)` — the editor pipeline, moved verbatim

The body of today's `onAddToChart` moves into `add` **unchanged** except for:

- `language` defaults to `provider.language?.name ?? 'pine'` (as now);
  `settings` is **forwarded** to `executeAsIndicator` as-is. `ScriptExecuteParams.settings`
  already exists (`types/script.ts:217`), so this is one line and not phase-2
  plumbing — there is no `updateSettings`, no settings modal, no re-execute on
  change. Forwarding now is strictly cheaper than a phase-2 diff.
- It **returns** `subscription.indicatorId` instead of closing the editor. The
  `setScriptEditorVisible(false)` and the `try/catch → console.error` stay in the
  component's `onAddToChart`, which becomes:
  ```ts
  onAddToChart={async (code) => {
    try { await scripts.add({ code }); setScriptEditorVisible(false) }
    catch (e) { console.error('Script execution failed:', e) }
  }}
  ```
  So the editor path and the public path are the same function; invariant (1)
  holds by construction, not by discipline.
- Errors **throw** out of `add` (chart not ready, `executeAsIndicator`
  rejection). The host awaits the promise; a rejection is the only honest signal
  it has. Today's "log and return undefined" would leave the host with a dead
  `scriptIdRef`.
- Ordering inside `add`: the `activeRef` entry is inserted **before** the
  subscription handlers are wired and **after** `executeAsIndicator` resolves,
  so a `remove` racing an in-flight `add` (host re-runs quickly) finds either
  nothing (no-op — but see the race note below) or a complete record.

### `remove(scriptId)` — the legend-✕ path, made the single teardown

```ts
const remove = async (scriptId) => {
  const rec = activeRef.current.get(scriptId)
  if (!rec) return                              // invariant (3)
  activeRef.current.delete(scriptId)            // first: re-entrancy guard
  const chart = store.instanceApi()
  for (const t of rec.templates) chart?.removeIndicator({ name: t })
  for (const o of rec.primitives.values()) chart?.removeOverlay({ id: o.id })
  try { await store.scriptProvider()?.stop(scriptId) } catch (e) { console.error(e) }
  emitRemoved(scriptId)
}
```

- `removeIndicator({ name })` without `paneId` removes that template from every
  pane it lives on — the same call the ✕ loop already makes for siblings. It is
  a no-op if the engine has already dropped the indicator (e.g. template apply
  wiped it — see "Known gaps"), which is what invariant (3) needs.
- `stop()` is **awaited** (contract) but its rejection is swallowed after
  logging: the chart-side teardown has already happened and the host must not
  be told the indicator is still there when it isn't.
- Chart-side removal happens **before** `stop()` so a slow provider cannot
  leave stale plots on screen during a re-run.

The legend ✕ handler in the component shrinks to:

```ts
} else if (data.indicator.name.startsWith('SCRIPT_')) {
  const id = scripts.ownerOf(data.indicator.name)
  if (id) void scripts.remove(id)
}
```

`ChartWidget`'s built-in `'close'` still runs after the external handler and
calls `removeIndicator` for the clicked template a second time plus a
`setMainIndicators/setSubIndicators` splice — both no-ops for `SCRIPT_*` names
(they are never in those signals). Unchanged, as today.

### `onRemoved` — how the host learns about ✕

A `Set<(id) => void>` inside the hook, fired at the end of `remove`, whichever
caller triggered it (✕, public API, `disposeAll`). Firing on API-initiated
removal too is deliberate: the host's `onScriptIndicatorRemoved` handler is
"drop the handle if it matches", which is idempotent, and it keeps the hook from
having to know who called. The design.md table only needs the ✕ case.

### `disposeAll` — unmount

`SuperchartComponent` gets a `useEffect(() => () => scripts.disposeAll(), [])`.
Today nothing stops scripts on unmount — `Superchart.dispose()` calls
`provider.dispose()` and hopes. This closes R4's "unmounting the chart does not
leak a running script": `disposeAll` iterates `activeRef` and calls `remove`
(not awaited; engine may already be gone, so chart calls are `?.`-guarded).

## Reaching it from `SuperchartApi` / `Superchart`

`SuperchartApi` (`Superchart.ts:248`) gains the three methods, placed next to
`openScriptEditor` / `closeScriptEditor` under the existing script section, with
the same "only functional when a `scriptProvider` was configured" doc note.

In the component's API `useEffect`:

```ts
addScriptIndicator: (p) => scripts.add(p),
removeScriptIndicator: (id) => scripts.remove(id),
onScriptIndicatorRemoved: (cb) => scripts.onRemoved(cb),
```

`scripts` is the hook's return object; its methods read refs and signals, not
closures over render-time state, so it does **not** need to join the effect's
dependency array (same reasoning `backendApi` already uses).

`Superchart` class forwarding follows the existing pattern, with one
difference for readiness. The other async methods do `this._api?.x() ?? Promise.resolve()`
before mount. For these:

- `addScriptIndicator` **waits for API-ready** via the existing
  `_apiReadyCallbacks` (`onApiReady()` at `:1097`), then forwards. The host
  calls it from a `useEffect` that fires right after chart construction; making
  it silently resolve `''` before mount would violate invariant (1). Note this
  is API-ready, not data-loaded — `executeAsIndicator` fetches its own candles
  through the datafeed, so it does not need `onDataLoaded`.
- `removeScriptIndicator` before mount → `Promise.resolve()` (nothing to remove
  — invariant (3)).
- `onScriptIndicatorRemoved` before mount → subscribe once ready, return an
  unsubscribe that works either way (same shape as the `_pendingToolbarCalls`
  queue).
- **No provider configured** → `add` rejects with `Error('No scriptProvider configured')`;
  `remove` resolves; `onRemoved` returns a no-op unsubscribe.

`getChart()`-holders need nothing extra: the methods live on the `Superchart`
instance the host already holds (it calls `createStudy`-style methods on it
today), not on the klinecharts `Chart`.

## Multi-pane templates (`5aab82e`) — nothing changes

The per-pane registration loop, the shared `dataStore`, and the
`registeredTemplates` refresh list all move into `add` untouched. The only
delta is that `registeredTemplates` is stored on `ActiveScript.templates`
instead of being fanned into `scriptTemplateOwnerRef`. Sub-pane ids
(`chart.createIndicator({name}, false, {id: paneName})`) are unaffected:
`removeIndicator({name})` finds them by template name regardless of pane, and
klinecharts drops an empty pane when its last indicator goes.

One consequence worth stating: two scripts naming the same `plotPane("osc")`
share the `osc` pane. Removing one leaves the pane with the other's indicator —
correct, and identical to the ✕ behaviour today.

## Typing / export surface

- `types/script.ts`: add
  ```ts
  export interface ScriptIndicatorParams { code: string; language?: string; settings?: Record<string, SettingValue> }
  ```
  and use it in `SuperchartApi`. `SettingValue` is already exported from
  `index.ts:184`.
- `index.ts`: export `ScriptIndicatorParams`. `UseScriptIndicatorsReturn` stays
  internal (as `UseBackendIndicatorsReturn` effectively is — it leaks through
  `getBackendIndicators()` but that is not a precedent to extend).
- `docs/scripts.md` "Script Editor API" section → renamed "Script API", the
  three methods documented beside `openScriptEditor`; `docs/api-reference.md:158`
  gets the three signatures. Minor version bump per `docs/versioning-and-release.md`
  (additive public surface).

## Known gaps — stated, not fixed in phase 1

1. **`registerIndicator` has no inverse.** klinecharts' registry
   (`extension/indicator/index.ts:78`) is a module-level object; every run
   leaves a `SCRIPT_<id>` template (and its `dataStore` closure) in it forever.
   Ten re-runs = ten dead templates. Not visible to the user, not a correctness
   issue, ids are unique so no collision. Fix is an `unregisterIndicator` in
   `packages/coinray-chart` — out of phase-1 scope (one repo boundary more).
   Flagging so the "ten re-runs" acceptance test is read as "no duplicates on
   the chart", which is what it says.
2. **Template apply / state restore wipe script indicators without stopping
   the script.** `useChartState.ts:1878` does `chart.removeIndicator()` (clear
   all). The plots vanish, the subscription keeps ticking into a `dataStore`
   nobody reads, `activeRef` still holds the record. `remove()` afterwards is
   still correct (engine calls are no-ops, `stop()` runs). The host does not
   apply templates on the TT market chart, so phase 1 does not hit it; noted
   for phase 3 ("add to charts" persistence will).
3. **Symbol/period change does nothing to script indicators inside SC.** The
   templates stay registered, `calc` keeps reading `dataStore` by timestamp — so
   after a symbol switch the old script's values render against the new
   symbol's bars wherever timestamps coincide (they always do at the same
   resolution). This is exactly the R4 hazard, and it is the host's
   remove-and-add effect over `[runId, symbol, resolution]` that prevents it.
   Contract says the host drives this; SC does not add `onSymbolPeriodChange`.
   Recording it because if the host ever misses a dep, SC will not save it.
4. **`add`/`remove` race.** If the host calls `remove(A)` while `add` for A is
   still inside `executeAsIndicator`, `remove` sees no record and no-ops; when
   `add` then resolves, A is on the chart with a handle the host has discarded.
   The host's effect ordering (cleanup runs before the next effect, and each
   effect awaits its own `add`) does not produce this, but a fast double
   "Run on chart" could. Cheap guard, included: `add` records a pending
   `AbortController`-style flag per in-flight call; `remove` on a pending id
   marks it, and `add` on resolve immediately tears down and rejects with
   `'removed before start'`. The host already handles rejection.

## Nothing awkward in the requirements

Everything asked for maps onto code that already exists; the work is a
refactor plus three forwarders. The one place I went beyond the letter is
forwarding `settings` to `executeAsIndicator` (gap-free and one line) — say if
you would rather it stay ignored until phase 2. The removal notice fires on
API-initiated removals too (see `onRemoved`), which is broader than "user
removed" — harmless for an idempotent handler, and it keeps SC from tracking
who asked.

## Files touched (for the tasks doc, later)

- `src/lib/hooks/useScriptIndicators.ts` — new
- `src/lib/components/SuperchartComponent.tsx` — pipeline + ✕ branch out, hook in, 3 API entries, unmount effect
- `src/lib/components/Superchart.ts` — interface + 3 forwarders with ready-gating
- `src/lib/types/script.ts`, `src/lib/index.ts` — `ScriptIndicatorParams`
- `docs/scripts.md`, `docs/api-reference.md`
