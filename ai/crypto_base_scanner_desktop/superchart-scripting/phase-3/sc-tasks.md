# Phase 3 — SuperChart-side tasks [sc-script-trimmings]

Implements [sc-design.md](sc-design.md). Repo: `$SUPERCHART_DIR`, branch
`feat/superchart-scripting` (on top of `5986d63`). WIP commits per fix, never
amend, never push; squash to one `[sc-script-trimmings]` commit at phase end.
No builds — `dist-enterprise` rebuilds are Areg's. R1 needs no SC change.

Confirmed for the host: unknown names in `disabledFeatures` are inert at
runtime (the resolved set is only ever read by declared `useFeature` calls),
so cbsd's `disabledFeatures: ["script_button"]` line can land before the flag
exists without throwing.

## T1 — R3: `script_button` feature flag

- `features/types.ts`: `'script_button'` in the `FeatureFlag` union.
- `features/defaults.ts`: `script_button: true` (toolbars/chrome group).
- `widget/top-bar/index.tsx`: gate `showScript` on
  `useFeature('script_button') && onScriptClick != null`.
- `docs/features.md`: one row (button-only scope: pipeline and
  `openScriptEditor()` unaffected).

**Verify:** default-on → button unchanged for existing consumers;
`disabledFeatures: ['script_button']` with a scriptProvider set → no button,
`openScriptEditor()` still works; runtime `setFeatureEnabled` toggles it live.

## T2 — R4: widen the ephemeral chokepoint to `BACKEND_`

- `hooks/useChartState.ts`:
  - `isEphemeralIndicatorName(name)` = `SCRIPT_` or `BACKEND_` prefix;
    `isScriptIndicatorName` stays for script-specific callers.
  - `dropScriptIndicators` → `dropEphemeralIndicators` at the mutation
    chokepoint (both the immediate path and the debounced-merge call site).
  - `modifyIndicator`'s early-return widens to the new predicate
    (`overrideIndicator` still applies the visual change).
  - `restoreChartState` + `applyChartTemplate` indicator loops skip both
    prefixes silently.
  - Document the invariant at both template mint sites
    (`useBackendIndicators`, `useScriptIndicators`): runtime templates are
    `SCRIPT_*`/`BACKEND_*`, and the chokepoint depends on it.

**Verify:** eye-toggle and settings Apply on a `BACKEND_` indicator no longer
add entries to saved state; a pre-polluted state self-cleans on next save;
restore of a polluted state emits no klinecharts warning; engine indicators
(incl. default VOL backfill) persist exactly as before; backend visibility
toggle still works visually.

## T3 — Wrap-up

- `tsc --noEmit` (both configs) + vitest extension suite + eslint on touched
  files; no build.
- Append "As landed" with deltas; report to coordinator incl. what's needed
  to see it in the running app (dist-enterprise rebuild by Areg — src-only
  changes, no engine/submodule delta).

## As landed


T1+T2 landed 2026-09-01 as WIP commit (src-only, no submodule delta).
Deltas from design: none functional; additionally updated the storybook
FeatureFlags story's category map (Record<FeatureFlag,string> typecheck) and
caught a second skip site — applyChartTemplate's stateCache rebuild filter.
Verified: tsc clean both configs, vitest 36/36, eslint no new errors.
To see it live: one Areg-run dist-enterprise rebuild (pnpm build); no
coinray-chart rebuild needed.
