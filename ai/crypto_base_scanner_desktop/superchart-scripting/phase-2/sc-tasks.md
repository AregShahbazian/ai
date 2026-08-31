# Phase 2 — SuperChart-side tasks [sc-script-parity]

Implements [sc-design.md](sc-design.md). Repo: `$SUPERCHART_DIR`, branch
`feat/superchart-scripting` (on top of `2250192`). One commit per phase, only
when Areg says; stage freely. No builds — `dist-enterprise` rebuilds are
Areg's, requested once via the coordinator. Verification lives in
[review.md](review.md) items 1–22.

Ordering is load-bearing: T1 unblocks coinray_rest (2b/3/5 typecheck against
SC's `.d.ts`); T2–T4 have no cross-repo dependency; T5 renders nothing real
until coinray_rest 2a populates `metadata.settings`.

## T1 — Contract types (FIRST; two repos block on it)

- `types/indicator.ts`: `ScriptLogEntry` (4 levels, ms bar time), `IndicatorSubscription.onLog?`, `ScriptExecuteParams.modules?`.
- `types/script.ts`: `ScriptProvider.updateSettings?(scriptId, settings)`; `compile()` gains optional trailing `modules?`; `ScriptDiagnostic.file?`.
- `components/Superchart.ts`: `updateScriptIndicator(scriptId, settings): Promise<void>` on `SuperchartApi` + class forwarder (ready-gated like `removeScriptIndicator`). cbsd needs this member in the `.d.ts`, so T1 ships it backed by a minimal hook `update` covering design steps 1+2 (no-op unknown id; `provider.updateSettings` path); the re-execute fallback arrives in T5, until then that path rejects with a documented temporary error.
- `index.ts`: export `ScriptLogEntry` (others ride existing exports).
- Docs: `docs/scripts.md` + `docs/api-reference.md` for the new members.
- **On completion: ping the coinray_rest session directly + tell the coordinator (single rebuild ask).**

**Verify:** `tsc --noEmit` clean; new members visible in the type surface; grep docs signatures match code.

## T2 — R1 tier (a): groupId + batched reconcile + rAF

- `extension/reconcilePrimitives.ts`: stamp `groupId: 'script:'+scriptId` (new param); collect creates into one `chart.createOverlay(array)`; full-replace fast path (changed > ½ tracked → `removeOverlay({groupId})` + recreate all); export `isScriptOverlay(o)`; debug instrumentation (path chosen, changed count, ms) via a passed logger.
- `hooks/useScriptIndicators.ts`: `onPrimitives` handler stores latest snapshot on the record, schedules one rAF per script (handle on the record); `remove()` cancels rAF and tears down via single `removeOverlay({groupId})`; unmount cleanup cancels all rAFs.
- Update `reconcilePrimitives.test.ts` for groupId/batching/fast path.

**Verify:** tests pass; review items 6–13 runnable; instrumented numbers logged under `store.debug`.

## T3 — R1 leaks

- `widget/object-tree/index.tsx`: filter `isScriptOverlay` out of sections.
- `widget/top-bar/export.ts` `buildDrawingsJson`: same filter.

**Verify:** review items 14–15; persistence (16) already holds via `save:false` — spot-check only.

## T4 — R1 tier (b): engine scoping (charting-ui domain)

- `packages/coinray-chart/src/Store.ts`: `getOverlaysByFilter` uses the pane map directly when filter has `paneId` (and short-circuits per-pane when matching `groupId`); `_sortOverlays(paneId)` sorts only the touched pane.
- No API change; lib code must not depend on (b) for correctness.

**Verify:** engine unit behaviour unchanged (existing tests if any); reconcile timings improve vs T2-only numbers.

## T5 — R2 settings

- `hooks/useScriptIndicators.ts`: `ActiveScript` gains `providerId/code/language/settings/metadata`; keyed by stable `hostId`; `getActiveByTemplateName`; `update` completes with the fallback re-execute (shared execute-and-render routine, same record, same hostId, no removal notice, in-flight guard applies).
- `components/SuperchartComponent.tsx`: `backendActiveForSettings` script fallback; `onSettingsApply` routes to `scripts.update`.
- `widget/indicator-setting-modal/DsIndicatorSettingModal.tsx`: Apply never touches `calcParams` when defs drive the form or `paramSlots` is empty.
- Docs for `updateScriptIndicator` behaviour (stable id, fallback semantics).

**Verify:** review items 17–22 runnable once coinray_rest 2a lands; the calcParams guard checkable now with a def-less script (item 21: persisted state, not screen).

## T6 — Wrap-up

- Append "As landed" (deltas from design) to this file; report instrumented perf numbers vs 8025/663 ms baseline for review item 13.
- `tsc --noEmit` + eslint on touched files (no `pnpm build`).

## As landed (2026-08-31, uncommitted on feat/superchart-scripting @ 9196960)

All of T1–T5 implemented; T4 additionally gained a bulk-removal branch in
`Store.removeOverlay` (multi-match → per-pane one-pass in-place compaction,
O(n·m) → O(n) per pane) found during review of the group-teardown path.

Deltas from sc-design.md, all small:
- Reconcile API is array-only `createOverlay(payloads[])` (no single-payload
  overload) — every call site batches anyway.
- `scriptActiveForSettings` gates on the `SCRIPT_` prefix alone (mutually
  exclusive with `BACKEND_`).
- `update()`'s fallback re-execute propagates an `executeAsIndicator`
  rejection to the caller (matches `add()`); only `stop()` is log-and-continue.
- Unmount rAF cancellation rides `remove()` per script rather than a separate
  loop.
- The primitives `groupId` is `script:<hostId>` — stable across the
  re-execute fallback, so batched teardown and the leak predicate never see
  the providerId churn.

Verification run: tsc --noEmit clean; vitest extension suite 20/20 (12 in
reconcilePrimitives.test.ts incl. batching/fast-path/groupId/debugLog cases);
eslint — no new errors (16 pre-existing no-explicit-any in the moved script
pipeline). No build, no browser QA — review items 1–22 need the Areg-run
dist-enterprise rebuild first; item 13's numbers come from the instrumented
reconcile (path, changed/new/stale counts, elapsed ms behind store.debug).
