# Phase 1 — SuperChart-side tasks [sc-script-spine]

Implements [sc-design.md](sc-design.md). Repo: `$SUPERCHART_DIR`, branch as
Areg decides (work left uncommitted on the current branch until then). No
build runs unless Areg asks; verification is by reading + `tsc` only if asked.

## T1 — `ScriptIndicatorParams` type + export

- `src/lib/types/script.ts`: add `ScriptIndicatorParams { code; language?; settings? }`
  next to `ScriptExecuteParams`.
- `src/lib/index.ts`: export it from the script-types block.

**Verify:** type is importable from `src/lib`; `SettingValue` still exported.

## T2 — `useScriptIndicators` hook (new)

`src/lib/hooks/useScriptIndicators.ts`, shape per design:
`add / remove / ownerOf / onRemoved / disposeAll`, `activeRef: Map<scriptId, ActiveScript>`,
in-flight guard for the add/remove race, `settings` forwarded to
`executeAsIndicator`. Body of `add` is the current `onAddToChart` moved
verbatim (figures, hline/fill/shape/gapConnect, draw callback, main +
`_<pane>` templates, data handlers, `reconcilePrimitives`), minus the editor
close and try/catch.

**Verify:** diff of the moved block against `SuperchartComponent.tsx@d5298aa:1226–1872`
shows only the listed deltas (return id, throw, `settings`, record bookkeeping).

## T3 — Wire the hook into `SuperchartComponent`

- Delete `scriptOverlaysRef` / `scriptTemplateOwnerRef`.
- `'close'` handler `SCRIPT_` branch → `ownerOf` + `remove`.
- `<ScriptEditor onAddToChart>` → `await scripts.add({ code })` then close editor.
- Unmount effect → `scripts.disposeAll()`.
- API object: `addScriptIndicator`, `removeScriptIndicator`, `onScriptIndicatorRemoved`.

**Verify:** no remaining reference to the deleted refs; editor path and API
path call the same `add`; `reconcilePrimitives` import is gone from the component.

## T4 — `Superchart.ts` interface + forwarders

- `SuperchartApi`: three methods beside `openScriptEditor`.
- Class: `addScriptIndicator` waits for API-ready (`onApiReady`) then forwards;
  `removeScriptIndicator` resolves before mount; `onScriptIndicatorRemoved`
  subscribes once ready and returns a working unsubscribe either way.

**Verify:** calling all three on a not-yet-mounted instance neither throws nor
leaks a listener after unsubscribe.

## T5 — Docs

- `docs/scripts.md`: "Script Editor API" → "Script API", document the three methods.
- `docs/api-reference.md`: add the three signatures beside `openScriptEditor`.

**Verify:** signatures in docs match `Superchart.ts` exactly.

## Verification checklist (for the coordinator's review.md)

- [ ] Editor "Add to chart" still renders the same plots/panes/primitives as at `d5298aa` (examples/client).
- [ ] `chart.addScriptIndicator({code})` on a mounted chart resolves a string id and renders identically to the editor path.
- [ ] `plotPane` script → `SCRIPT_<id>` + `SCRIPT_<id>_<pane>`; `removeScriptIndicator(id)` removes both and the empty pane.
- [ ] Legend ✕ on either pane removes both, drops primitives, calls `provider.stop(id)`, fires `onScriptIndicatorRemoved(id)`.
- [ ] `removeScriptIndicator('nope')` and a second call with a real id both resolve without throwing.
- [ ] `addScriptIndicator` before mount waits and then runs; after `dispose()` it rejects.
- [ ] No `scriptProvider` configured → `add` rejects, `remove` resolves, `on…` returns no-op unsubscribe.
- [ ] Fast double add of the same code → one indicator on the chart; earlier promise rejects `'removed before start'` only if `remove` was called for it.
- [ ] Unmount (`dispose()`) with a running script → `provider.stop` called, no console error.
- [ ] `pnpm lint` / `tsc` clean (only if Areg asks for a build check).

## As landed (2026-08-28, uncommitted on `main` @ d5298aa)

Signatures exactly as in sc-design.md. Deltas from the design, all small:

- `remove` on an id whose `add` is still executing records a cancellation;
  when that `add` resolves it calls `provider.stop`, skips rendering and
  rejects `'removed before start'`. Unknown ids also land in that set — it is
  consulted once and is otherwise inert.
- `onPrimitives` handler early-returns if the script is no longer active, so a
  late snapshot cannot resurrect overlays after teardown.
- `addScriptIndicator` before mount queues on `onApiReady`; after `dispose()`
  it rejects `'Superchart disposed'`.
- Unmount teardown lives inside the hook (`useEffect` cleanup → `disposeAll`),
  not in the component.
- The moved block carries its 21 pre-existing ESLint errors / 4 warnings
  (`no-explicit-any`, `prefer-const`) — identical count at `d5298aa`; left
  untouched to keep the move verbatim.

Verification run: `tsc --noEmit` clean. No build, no browser QA yet.
