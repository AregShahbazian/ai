# Phase 2 tasks — coinray_rest [sc-script-parity]

Implements [rest-design.md](rest-design.md). Repo: `~/git/altrady/coinray_rest`,
`packages/superchart-script`, branch `master` (work left uncommitted until Areg
asks). No publish — 0.1.9 is Areg's manual step at phase end; cbsd links the
local build. Verification map: [review.md](review.md) items 17–22 (params),
23–28 (logs), 29–35 (modules + diagnostics).

Split into **Part A** (no cross-repo dependency — runs now; A1 is SC's critical
path, their settings modal is blocked on it) and **Part B** (starts only after
the SC session pings that the contract types — `updateSettings?`, `modules?` on
`ScriptExecuteParams` + `compile()`, `onLog?` — are committed to
`dist-enterprise`; not against a guessed `.d.ts`).

`[ ]` open · `[x]` done.

## Part A — now

### A1 — 2a: `meta.inputs` → `IndicatorSettingDef` (SC's critical path)

- [x] `subscriptionAdapter.ts`: `inputsToSettingDefs(inputs)` per the design's
  kind table (`type ?? kind` fallback; int gets `step: 1`; options →
  `select` with `{value: String(i), label}`, `defaultValue: String(default)`).
- [x] `buildMetadata` gains an `inputs` parameter, returns
  `settings: inputsToSettingDefs(inputs)`; `executeAsIndicator` passes
  `running.meta.inputs`.
- [x] Tests (`subscriptionAdapter.test.ts`): each kind maps; min/max pass
  through; empty/absent inputs → `[]`; options round-trip
  def → `"2"` → `normalizeSettings` → host index `2`.

### A2 — 4: real compiler diagnostics

- [x] `WasmScriptProvider.ts`: `parseCompileError(raw)` (exported) — trailing
  `` in <path>:<line>:<col>`` regex → `line`/`column` (+ file kept inside
  `message`, which stays the full string); `WARNING ` prefix →
  `severity: 'warning'`; no suffix → `{line: 1, column: 1}` fallback.
- [x] `compile()` maps errors through it instead of `{line: i+1, column: 1}`.
- [x] Tests: entry-file error, helper-file error, warning severity,
  suffix-less fallback (limit error / crash string / unresolved-import).

### A3 — housekeeping in the same files

- [x] `_declParam` clamps numeric values to `schema[k].min/max` (parity with
  the native host; protects the persisted-settings path, review item 21).
  Test in `strategyHost.test.ts`.
- [x] Full suite green: `pnpm vitest run` in `packages/superchart-script`.

## Part B — after the SC contract ping

### B1 — 5: `onLog` (engine + provider)

- [x] `types.ts`: `AdvanceResult.confirmedPrefix: number`;
  `strategyHost.ts`: set it to `this.confirmedEvents.length` in both `advance`
  return paths. Test: correctness across confirm/forming mixes.
- [x] `subscriptionAdapter.ts`: `eventsToLogs(events)` — levels 0–3 →
  `'debug'|'info'|'warn'|'error'`, seconds → ms. Test beside `eventsToPoints`.
- [x] Provider: `logsScanned` mark on `RunningScript`, written where the design
  says (in/next to `runFresh`, never a distant caller): initial run and
  `updateSettings` forward from 0; `loadHistoryBefore` sets
  `logsScanned = confirmedPrefix` forwarding nothing; live tick forwards
  `slice(logsScanned, confirmedPrefix)` only (no forming-bar logs — review 26).
- [x] `onLog` on the returned subscription, register-then-drain like
  `onPrimitives`; pre-handler buffer is a 500-entry ring, newest kept
  (review 28). Tests: gating table from the design + ring cap.

### B2 — 3: modules plumbing

- [x] `ensureCompiled(code, modules?)` → `compileStrategy({modules})`; cache
  key = canonical entry+modules fingerprint
  (`JSON.stringify([code, ...sorted entries])`) — must agree with cbsd's
  `compileCacheKey(source, modules)` invariant; `compiled` map capped
  (evict oldest > 8).
- [x] `compile(code, language, modules?)` + `executeAsIndicator` forward
  `params.modules`. Signatures exactly per SC's committed `.d.ts`.
- [x] Tests: helper-only edit misses the cache (review 30); modules reach the
  POST body; eviction.

### B3 — snapshot-skip (lands with B2's plumbing)

- [x] `reducePrimitives` accumulates a signature during its existing walk and
  returns it alongside the snapshot; tick path emits only when the signature
  differs from the last **emitted** one; reference lives with handler/buffer
  plumbing and resets on `onPrimitives` (re)registration — first emit after a
  register/drain is never suppressed.
- [x] Tests: unchanged tick emits nothing; changed tick emits; re-registration
  always receives the current snapshot.

### B4 — 2b: `updateSettings`

- [x] `updateSettings(scriptId, settings)` per SC's committed signature:
  unknown id throws; `normalizeSettings` → `running.params`; `runFresh`;
  emit recomputed points via `onData` + full snapshot via `onPrimitives`
  (buffered if unregistered); logs re-forward from 0 (design reset table).
- [x] Tests: re-run changes output; tick → updateSettings → tick uses the new
  host; failure parks host + `onError`, previous drawing untouched.

### B5 — wrap

- [x] Full suite green; `pnpm build` clean (needs SC `dist-enterprise` built —
  if the build is stale/missing, stop and tell the coordinator, don't rebuild
  SC from here).
- [x] Report to coordinator: what landed, debug hooks available for their
  Playwright pass, anything contract-adjacent that came up.

## Debug hooks for the coordinator's live testing

Offered once implemented (B5 report lists the final shape): a per-subscription
counter object reachable from the provider instance — logs forwarded / logs
suppressed-as-forming / snapshots emitted / snapshots skipped — so review items
26 and 28 are checkable from Playwright without instrumenting the page.

## B6 — CodeEditor diagnostics fix (added mid-phase, coordinator 2026-08-31)

cbsd found `CodeEditor` never showing diagnostics present at mount, and ghost
markers surviving a file switch (blocks review item 34).

- [x] Root cause reproduced in jsdom (new `tests/codeEditor.diag.test.tsx`,
  jsdom added as devDep): the external `value`-reset effect replaced the doc
  WITHOUT re-deriving diagnostics. A diagnostics prop whose reference doesn't
  change alongside the value was never re-applied — its spans either
  position-mapped through the full-doc replacement (ghosts on unrelated
  content) or, when the editor mounted before the real content arrived, stayed
  clamped against the old/empty doc as invisible zero-width spans at offset 0
  ("0 markers at mount, indefinitely").
- [x] Fix: the value-reset effect calls `applyDiagnostics()` after the doc
  replacement — positions always re-derive from the current prop (via ref)
  against the current doc. Plus: a column at/past EOL now backs up one char so
  the span is never invisible.
- [x] 4 new component tests (mount, replacement-with-new-ref,
  replacement-with-stable-ref, late-arriving value) + EOL-span test.
