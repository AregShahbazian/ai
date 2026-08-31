# Phase 2 — SuperChart-side design [sc-script-parity]

Implements SC's share of [prd.md](prd.md): R1 (primitive scale + leaks), R2
(settings), R3 (`onLog` type), R4/R5 (contract fields only). Verified against
SC `feat/superchart-scripting` @ `2250192`.

**Perf baseline being designed against:** 8025 primitives from one `draw-all`
run over ~8000 bars; full teardown **663 ms**; measured 2026-08-31 in Altrady
dev (SC 2250192 + superchart-script 0.1.8).

## Contract additions (types SC owns)

All in `src/lib/types/` and re-exported from `src/lib/index.ts`:

```ts
// types/indicator.ts — IndicatorSubscription gains (emit side: superchart-script)
onLog?(handler: (entry: ScriptLogEntry) => void): void

export interface ScriptLogEntry {
  level: 'debug' | 'info' | 'warn' | 'error'   // wasm LogEvent 0–3, 1:1
  message: string
  timestamp: number                             // bar time, ms epoch
}

// types/script.ts — ScriptProvider gains
/** Re-run the script with new settings, keeping the same scriptId. Data
 *  re-flows through the existing onData/onPrimitives handlers. */
updateSettings?(scriptId: string, settings: Record<string, SettingValue>): Promise<void>

// types/indicator.ts — ScriptExecuteParams gains (R4; provider consumes)
/** Additional module sources keyed by import path (e.g. "./helper"). */
modules?: Record<string, string>

// types/script.ts — ScriptProvider.compile gains the same (R4/R5):
compile(code: string, language: string, modules?: Record<string, string>): Promise<ScriptCompileResult>
// (optional trailing param — existing implementations stay conformant)

// types/script.ts — ScriptDiagnostic gains (optional polish, not contract):
file?: string   // which module the diagnostic points at, for multi-file scripts
```

`ScriptIndicatorParams` picks up `modules?` for free once it derives from
`ScriptExecuteParams` (it already does, via `Omit`). `modules` goes on **both**
entry points (settled with cbsd + rest, 2026-08-31): the validation path must
see the same module set as the execute path, or a broken helper import yields a
diagnostic about a file the compiler was never given. `ScriptDiagnostic.file?`
is for SC's own editor only — Altrady parses its own diagnostics and never
consumes it; it rides along because it is one optional field, and is dropped
without argument if it causes any friction. Confirmed-bar gating and log
dedupe are emit-side per the settled contract; SC only defines the shape.

**Sequencing / rebuild sync point.** coinray_rest items 2b/3/5 typecheck
against SC's `.d.ts` via the `link:` dependency, and cbsd consumes the same
built bundle — so the contract types land first in the SC implementation
order, and their arrival in `dist-enterprise` is one Areg-run rebuild covering
both consumers (coordinator asks once). SC pings the rest session directly
when the types are committed.

**Deliberately no SC consumer for `onLog` in phase 2.** SC has no console
surface and Altrady's IDE is the consumer; building an SC-side log panel now
would be exactly the "path nothing takes" phase-1 review flagged. The hook does
not even register the handler — a host that wants logs gets the subscription's
events via its own provider wrapper. Documented as such in `docs/scripts.md`.

**R5 needs no SC code.** Compile/execute failures already reject out of
`addScriptIndicator` (phase 1 made `add` throw), and the rejection's message
survives intact — that is all R5 needs from SC (decided with cbsd 2026-08-31:
cbsd compiles through its own diagnostics path before calling add, so
structured diagnostics on the add rejection would be a path nothing takes).
`ScriptExecutionError` is dropped; revisit only if a real case shows up.

## R2 — settings

### Existing patterns followed

The whole feature is the `BACKEND_` settings path with `SCRIPT_` substituted:

| Piece | Pattern copied |
|---|---|
| Setting defs | `IndicatorMetadata.settings: IndicatorSettingDef[]` (types/indicator.ts:468) — already the modal's native vocabulary; coinray_rest starts populating it |
| Modal wiring | `backendActiveForSettings` → `settingDefs`/`settingValues`/`onSettingsApply` props on `DsIndicatorSettingModal` (SuperchartComponent.tsx:1665–1678) — the modal needs **zero changes** to render script inputs |
| Update call | `useBackendIndicators.updateBackendSettings` (:436–448): `provider.updateSettings(id, settings)` → mutate record → done; data re-flows through the existing `onData` handler |
| Reverse lookup | `getActiveIndicatorByKlinechartsName` — the hook gains the script twin |

### Bookkeeping

`ActiveScript` (useScriptIndicators.ts) gains what an update needs to exist:

```ts
interface ActiveScript {
  providerId: string                    // see "stable scriptId" under update
  templates: string[]
  primitives: Map<string, TrackedOverlay>
  // R2 additions — captured at add() time, updated on updateSettings:
  code: string
  language: string
  settings?: Record<string, SettingValue>
  metadata: IndicatorMetadata           // carries .settings defs for the modal
}
```

New hook member `getActiveByTemplateName(name)` → `{scriptId, settings,
metadata} | undefined` (linear scan, same as `ownerOf` — they merge into one
lookup returning the record + id).

### Modal wiring

`backendActiveForSettings` in `SuperchartComponent` grows a script fallback:
resolve `BACKEND_` via `backendApi` as today, else `SCRIPT_` via
`scripts.getActiveByTemplateName`; hand the modal
`metadata.settings`/`record.settings`, and route `onSettingsApply` to
`scripts.update(scriptId, settings)` instead of `updateBackendSettings`. Both
`SCRIPT_<id>` and `SCRIPT_<id>_<pane>` names resolve to the same record, so the
gear works on any of the script's panes.

### The `calcParams: []` autosave defect

Root cause: `DsIndicatorSettingModal`'s apply path calls
`modifyIndicator({calcParams})` even when there are no calc-param slots, and a
script template registers none — so Apply on the empty modal writes
`calcParams: []` into the autosaved template. Fix in the modal, not the caller:
**when `settingDefs` drive the form, or when `paramSlots` resolves empty, Apply
must not touch `calcParams`** — it either calls `onSettingsApply` (defs) or is
inert (nothing to edit). This also covers a script with zero declared inputs
(review item 22): the gear opens, shows the empty state the modal already has
for def-less indicators, and Apply writes nothing. No gear-hiding — one
behaviour for all indicators, no special case.

### `update` — the hook and the API

```ts
// hook
update: (scriptId, settings) => Promise<void>     // hostId stays valid throughout
// SuperchartApi + Superchart class
updateScriptIndicator: (scriptId: string, settings: Record<string, SettingValue>) => Promise<void>
```

**The host-facing scriptId is stable across updates** (decided with cbsd
2026-08-31: SC's own modal is the update caller, so a changed id would strand
the host's only handle — it would see a removal notice for an id it holds and
a live indicator nobody owns). The id the host receives from
`addScriptIndicator` is the record's key for the record's whole life; the
provider-side subscription id may churn beneath it:

```ts
interface ActiveScript {           // keyed in activeRef by hostId (stable)
  providerId: string               // current subscription id — stop/updateSettings target
  …
}
```

`add()` mints `hostId = providerId` of the first subscription. Behaviour of
`update(hostId, settings)`:

1. Unknown/removed id → resolves unchanged, a no-op — same invariant family as
   `removeScriptIndicator`. (Racing the user's ✕ must not throw out of the
   settings modal.)
2. Provider has `updateSettings` → `await provider.updateSettings(record.providerId,
   settings)`, mutate `record.settings`. Rendering updates arrive through the
   already-registered handlers — no re-registration, no template churn.
3. Fallback (no `updateSettings`) → internal re-execute: tear down the chart
   side (templates, primitives, rAF) and `stop(record.providerId)`, run the
   shared execute-and-render routine with the stored `{code, language,
   settings, modules}`, then write the new `providerId` and `templates` into
   the **same** record under the **same** hostId. No `onScriptIndicatorRemoved`
   fires — the script was never removed from the host's point of view. The
   phase-1 in-flight guard applies to the re-execute leg unchanged.

Consequence: teardown, `ownerOf`, and the removal notice all speak hostId only;
`stop()` is the one call that uses `providerId`. `update` returns
`Promise<void>` — with a stable id there is nothing to re-read. The rejected
alternatives (returning a new id; an id-change event; hard-requiring
`provider.updateSettings`) are in the decision log below.

Class forwarder follows `removeScriptIndicator`'s ready-gating: before mount
nothing exists → resolve unchanged.

## R1 — primitive scale

### Tier (a) — SC lib, reconcile batching + rAF coalescing

Current cost is not the reconcile loop (O(n)) but 2n individual engine calls
against O(n)-per-call store bookkeeping. Changes, all in
`reconcilePrimitives.ts` + the hook's `onPrimitives` wiring:

1. **`groupId` on every primitive overlay**: `primitiveToOverlay` stamps
   `groupId: 'script:' + scriptId` (field exists, types/overlay.ts:201). This
   is the load-bearing change — it buys batch removal *and* the R1 leak fixes.
2. **Batched creates**: reconcile collects `OverlayCreate[]` and issues **one**
   `chart.createOverlay(array)` — the engine funnels an array into a single
   `addOverlays` → one sort, one invalidation (Chart.ts:898–930), verified in
   the scaling probe.
3. **Full-replace fast path**: when the changed-key count exceeds half the
   tracked set, skip per-key diffing: `removeOverlay({groupId})` (one filtered
   pass) + recreate everything in one array call. The moving-keys-every-bar
   script drops from O(n²) to one scan + one sorted insert. Threshold ½ is a
   heuristic, not a contract; recorded in code as such.
   Which path ran, the changed-key count, and the elapsed time are logged
   behind the existing `store.debug` flag — review item 13 reads its
   before/after numbers off an instrumented run (asked for by cbsd; phase-1
   review was slowed by not seeing which path code took).
4. **rAF coalescing, latest-wins**: the `onPrimitives` handler stores the
   snapshot on the record and schedules one rAF per script; the rAF reconciles
   the *latest* snapshot. Teardown (`remove`) becomes
   `cancelAnimationFrame` + `removeOverlay({groupId})` — the 663 ms loop is
   gone entirely.

Teardown in `remove()` switches from per-overlay `removeOverlay({id})` to the
single `removeOverlay({groupId})` call. The per-overlay tracked map stays (it
is the diffing state), but is no longer walked for teardown.

### Tier (b) — engine fork (`packages/coinray-chart`)

Two scoped fixes, no API change: `getOverlaysByFilter` uses the pane map
directly when the filter carries a `paneId`/`groupId` instead of concatenating
every pane's array (Store.ts:1854–1880), and `_sortOverlays(paneId)` sorts only
the touched pane (Store.ts:1949). Both are the "S-sized engine win worth taking
regardless" from the scaling verdict. Work lands via the charting-ui agent's
domain; SC lib code does not depend on (b) for correctness, only speed —
(a) alone must already pass review items 9–13.

### Tier (c) — deferred

One-overlay-per-script drawing from `extendData` is **not designed here**, per
the PRD non-requirement. If a real script exhausts (a)+(b), that design starts
from the existing `drawCallback` shape in the hook.

### R1 leaks — object tree, export, persistence

One predicate, used everywhere: `isScriptOverlay(o) =
o.groupId?.startsWith('script:')`, exported from `reconcilePrimitives.ts`.

- **Object tree** (`widget/object-tree/index.tsx`): filter script overlays out
  of `chart.getOverlays()` before building sections — they are script output,
  not user objects.
- **Drawings export** (`widget/top-bar/export.ts` `buildDrawingsJson`): same
  filter. (It already serialises `groupId`, so today they'd leak with their
  group visible — confirmed unfiltered.)
- **Persistence**: already correct — primitives are created `save: false` and
  never reach the StorageAdapter; review item 16 verifies, no change.

Filtering by `groupId` prefix rather than by the four template names means a
fifth primitive kind never reopens the leak.

## Established patterns — summary (coordinator ask #1)

- `updateScriptIndicator` ≡ `updateBackendSettings` + `IndicatorProvider.updateSettings`, down to the record-mutation order.
- Settings modal: the existing `settingDefs` props, added for `BACKEND_` in the DS migration — zero modal-rendering changes.
- `getActiveByTemplateName` ≡ `getActiveIndicatorByKlinechartsName`.
- `onLog`/`ScriptLogEntry` join `onData`/`onTick`/`onPrimitives` as optional emit-only members of `IndicatorSubscription` — same optional-chained non-registration when absent.
- `groupId` batch removal uses the engine's existing filtered `removeOverlay`; no new engine API.
- API additions sit on `SuperchartApi` beside the phase-1 trio, same ready-gating idioms.
- The only new file-level artifact is the `isScriptOverlay` predicate; everything else extends phase-1 files.

## Phase-1 lessons applied (coordinator ask #2)

Lifetime — every new resource is owned by the `ActiveScript` record and dies
in `remove()`:

- The **rAF handle** lives on the record; `remove()` and the unmount cleanup
  cancel it before touching the chart. An rAF that fires after teardown hits
  the existing `activeRef.has()` guard as a second fence.
- The **pending snapshot** is stored on the record, so a snapshot arriving
  during teardown is dropped with the record — no closure captures it.
- **Settings writes** go through the record: `update` re-reads
  `activeRef.current.get(id)` *after* every `await` (provider update, or
  remove+add), so an update racing a ✕ finds the record gone and no-ops
  instead of writing to a dead indicator — the "settings write that outlives
  its indicator" case named by the coordinator.
- **`code`/`language` captured at add** are immutable inputs, not live state —
  storing them for the fallback is capture-by-value of something that cannot
  drift (unlike phase-1's compile-endpoint example).
- **No dead paths**: no SC log consumer, no tier-(c) scaffolding, no
  gear-hiding flag, `ScriptExecutionError` dropped unless the emit side
  commits to it. Everything designed here has a caller in this phase's review
  checklist.
- The phase-1 race guard (`pendingRef`/`cancelledRef`) extends to `update`'s
  fallback path unchanged — the fallback's `add` is an ordinary add.

## Decision log (settled with cbsd, 2026-08-31)

1. **Stable host-facing scriptId across updates** — internal providerId remap,
   as designed above. Rejected: returning a possibly-new id (strands the
   host's handle silently); an id-change event (workable but pushes
   bookkeeping onto every host); hard-requiring `provider.updateSettings`
   (a capability gap would present as a broken settings dialog, and doesn't
   bind anyway).
2. **`ScriptExecutionError.diagnostics` dropped** — cbsd's own compile path
   already produces IDE diagnostics before add is called; the rejection
   message surviving intact is all R5 needs from SC.
3. **Full-replace threshold stays a tunable heuristic**, with the chosen path
   and timings observable behind the debug flag.

## Files touched (forecast for sc-tasks.md)

- `types/indicator.ts` (`onLog`, `ScriptLogEntry`, `modules?`), `types/script.ts` (`updateSettings?`), `index.ts` exports
- `hooks/useScriptIndicators.ts` — record fields, `update`, `getActiveByTemplateName`, rAF reconcile wiring, groupId teardown
- `extension/reconcilePrimitives.ts` — groupId stamp, batched creates, full-replace path, `isScriptOverlay`
- `components/SuperchartComponent.tsx` — settings-modal fallback wiring, API entry
- `components/Superchart.ts` — `updateScriptIndicator` interface + forwarder
- `widget/indicator-setting-modal/DsIndicatorSettingModal.tsx` — the calcParams guard
- `widget/object-tree/index.tsx`, `widget/top-bar/export.ts` — the filter
- `packages/coinray-chart/src/Store.ts` — tier (b) scoping
- `docs/scripts.md`, `docs/api-reference.md`
