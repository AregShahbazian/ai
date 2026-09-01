---
id: sc-script-trimmings
repo: Superchart
---

# Phase 3 — SuperChart-side design [sc-script-trimmings]

Implements SC's share of [prd.md](prd.md): R3 (`script_button` flag), R4 (the
`BACKEND_` persistence leak), and the R1 confirmation that `createTradeLine`
needs no SC change. Verified against `feat/superchart-scripting` @ `5986d63`.
SC's share is deliberately small; this doc keeps it that way.

## R3 — `script_button` feature flag

Mechanism, per the established feature-flag pattern (the same one gating
`settings_button`, `indicator_picker`, `screenshot_button` …):

- `features/types.ts`: add `'script_button'` to the `FeatureFlag` union.
- `features/defaults.ts`: default `true` — existing consumers see no change.
- `widget/top-bar/index.tsx`: `const scriptFeature = useFeature('script_button')`,
  and line ~401 becomes `showScript={scriptFeature && onScriptClick != null}`.
- `docs/features.md`: one row.

Contract exposed to the host: `disabledFeatures: ['script_button']` in
`SuperchartOptions` hides the button while `scriptProvider` stays set; the
runtime `setFeatureEnabled('script_button', …)` toggle works like every other
flag. Invariants: the flag affects **only** the button — `openScriptEditor()`,
`addScriptIndicator` and the whole script pipeline are untouched by it (a host
hiding the button but calling `openScriptEditor()` still gets the editor; that
is the flag doing exactly one job, same as `indicator_picker` not disabling
`removeIndicator`). ~8 lines + docs, as costed in scoping.

Rejected: a `SuperchartOptions` boolean (`showScriptButton`) — that is the
legacy `showVolume` shape, not the current pattern; and auto-hiding when the
provider has no `EditorComponent` — too clever, breaks hosts that supply an
editor but want the button gone (exactly Altrady's case).

## R4 — the `BACKEND_` half of the persistence leak

### The routes, named (verified @ 5986d63)

`modifyIndicator` (`useChartState.ts`) gates its `enqueueMutation` on
`!isScriptIndicatorName(name)` — the phase-2 fix — so a `BACKEND_<id>` name
still reaches the backfill branch: no saved entry matches, the live indicator
is snapshotted via `indicatorToSaved` and **appended to saved chart state**.
Two call sites feed it raw backend names:

1. the pane-legend eye toggle (`SuperchartComponent.tsx:639/643`,
   `{visible}`), and
2. `DsIndicatorSettingModal`'s apply (`:119/125`) — the phase-2 guard stopped
   the `calcParams` write, but the defs path still writes
   `{settings, visible}` through `modifyIndicator`.

On the next app load the restore loop `createIndicator`s the saved
`BACKEND_<id>` entry; backend templates are registered per subscription, so
klinecharts warns "indicator not supported" — the same symptom the `SCRIPT_`
half produced.

### The fix — same chokepoint, widened predicate

`BACKEND_` and `SCRIPT_` templates are both minted inside SC itself
(`useBackendIndicators`: `BACKEND_${indicatorId}`; `useScriptIndicators`:
`SCRIPT_${indicatorId}`) and both have their own persistence story (backend:
`syncToStorage` keyed by the stable definition name; scripts: the host's
enabled list — R2). Neither belongs in saved chart state. So:

- `isScriptIndicatorName` generalises to `isEphemeralIndicatorName(name)` =
  `SCRIPT_` **or** `BACKEND_` prefix, one exported predicate beside the
  existing one (which stays, delegating, for its script-specific callers).
- `dropScriptIndicators` at the mutation chokepoint becomes
  `dropEphemeralIndicators` — every mutation result is filtered, so Areg's
  already-polluted state self-cleans on the next save, exactly as the
  `SCRIPT_` entries did in phase 2. No migration.
- `modifyIndicator`'s early-return widens to the new predicate. The visual
  effect still applies via `overrideIndicator`.
- `restoreChartState` and `applyChartTemplate`'s indicator loops skip both
  prefixes silently — kills the startup warning immediately, before the
  self-clean lands.

**One behavioural consequence, stated rather than hidden:** after this, a
backend indicator's eye-toggle and settings Apply no longer persist `visible`
into chart state (they persisted only by accident of the leak — and were
restored into a warning, not into a working indicator, so nothing user-visible
worked anyway). If backend visibility persistence is ever wanted for real, it
belongs in the backend path's own storage (`ActiveIndicator` +
`syncToStorage`), not in chart state; noted as a backlog line, not built —
that would be a dead path today.

### The coordinator's question: can the chokepoint be closed by construction?

Honest answer: **within SC, the prefix pair is already closed by
construction** — the only two modules that mint runtime klinecharts templates
are `useBackendIndicators` and `useScriptIndicators`, and each stamps its
prefix unconditionally. There is no third minter, and a grep-able invariant
("runtime templates are `SCRIPT_*` or `BACKEND_*`") documented at both mint
sites plus on the predicate keeps it that way. What prefix enumeration does
*not* cover is a **consumer** who registers a template via the public
`registerIndicator` and places it outside SC's toggle paths — but that is
persistable *on purpose* (a consumer's custom indicator should survive
reload), so excluding it would be wrong, not safe.

True by-construction — ownership metadata instead of name parsing — means the
engine registry learns an `ephemeral` marker: `registerIndicator(tpl,
{ephemeral: true})` (or a field on the template), a registry query, and the
chokepoint asking the registry instead of the name. Cost: S–M, engine +
both hooks + chokepoint, plus a submodule release step. It buys robustness
against a hypothetical third SC-internal minter forgetting its prefix. Not
worth it while the minter count is two and the phase is "deliberately small";
recorded here so the option isn't lost. Recommendation: predicate now,
registry marker only if a third runtime minter ever appears.

## R1 — confirmation: `createTradeLine` needs no SC change

Confirmed as stable public surface: `createTradeLine(chart, options)` is
re-exported from the package root (`src/lib/index.ts:37`) and is one of the
documented factory functions in the repo's re-export policy (CLAUDE.md "DO
re-export"), implemented in `tradeLineApi.ts:83`. For phase-3 scale (a few
hundred markers; the reference run is 48 trades):

- **Creation**: one imperative call per marker; each returns a fluent handle.
  Fine at this scale — the phase-2 store scoping (id fast path, per-pane
  sort) also lowered the constant here, though this path was never the
  bottleneck.
- **Teardown**: `handle.remove()` per marker. The host keeps the handles for
  the active backtest result and removes them on clear/unmount — the same
  lifetime discipline as `useScriptIndicators`' records: handles die with the
  result that created them.
- **Lifetime guarantees SC promises**: trade lines are never persisted
  (`docs/storage.md:213`), never appear in saved chart state, and are pinned
  `lock: true` on the candle pane. They are invisible to the object tree
  concern only if the host wants them user-visible — they are *not* filtered
  like script primitives (they carry no `script:` groupId), which is correct:
  backtest trades are host-owned output, and the host may legitimately want
  them listed. If Areg wants them excluded from the object tree/export too,
  that is a one-line extension of the phase-2 predicate's call sites — say so
  before implementation, default is not filtered.
- **No batch API, and none added**: at ≤ a few hundred markers a batch route
  is a dead path. The PRD already carries the escape hatch (raise, don't
  absorb, if a run reaches thousands).

No SC code for R1.

## Established patterns followed

- `script_button` → the feature-flag system (`useFeature`, `enabledFeatures`/
  `disabledFeatures`), not an options boolean.
- R4 → the phase-2 chokepoint fix, widened: same predicate shape, same
  self-cleaning property, same silent-skip on restore.
- R1 → the existing public factory + fluent-handle pattern (`createTradeLine`
  like `createOrderLine`/`createPriceLine`), host-owned lifetime.

## Phase-1/2 lessons applied

- **Lifetime**: R4 is exactly a state-outliving-its-owner bug — a runtime
  template name snapshotted into durable state. The fix removes the write
  path rather than cleaning up after it, and the chokepoint filter makes the
  stale entries die with the next save rather than surviving indefinitely.
  Trade-line handles (R1, host-side) are documented to die with the backtest
  result that created them, including unmount.
- **Dead paths**: no batch trade API, no backend-visibility persistence, no
  registry `ephemeral` marker, no gear-hiding — each named and deliberately
  not built. Everything designed here has a caller in the PRD's review items.
- **Silent nothing**: restore's skip of ephemeral entries is silent by design
  (it is correct behaviour, not a failure), but the chokepoint keeps the
  phase-2 debug observability untouched.

## Files touched (forecast for sc-tasks.md)

- `src/lib/features/types.ts`, `src/lib/features/defaults.ts`,
  `src/lib/widget/top-bar/index.tsx` — R3
- `src/lib/hooks/useChartState.ts` — R4 (predicate, chokepoint, restore +
  template-apply skips)
- `docs/features.md` — R3 row; `docs/storage.md` — one sentence on ephemeral
  indicator names if useful
- No engine/submodule changes; no contract-type changes; nothing for R1
