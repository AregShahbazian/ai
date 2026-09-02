# Phase-2 code review — coinray_rest [sc-script-parity]

Scope: commits `8ab06cdf` (phase 2) + `155723a3` (0.1.9 bump) on `master`,
i.e. everything phase 2 changed in `packages/superchart-script` plus the
`strategy_compiler/sdk` na-forwarding line. Reviewed 2026-09-01 by the
coinray_rest session, per Areg's rules: fix only obvious issues; theoretical
concerns written down, not coded around.

**Outcome: no code changes.** Eleven findings, all documented-and-left — none
met the "obviously an issue that obviously needs fixing" bar. Nothing here
needs a 0.1.10; the only pending activation is the ta-v2 redeploy (finding 10).

The two bug classes phase-2 testing found (unbounded spread into a
fixed-arity mechanism; silent-nothing) were re-audited across the whole
package, not just the diff:
- **Spread audit**: the four remaining `push(...x)` sites are editor
  extension arrays (`CodeEditor.tsx:290,294`, `ScriptEditor.tsx:216,224`) —
  bounded, single-digit lengths. `[...map.values()]`-style array-literal
  spreads iterate and don't hit the argument limit. No further instances of
  the `forwardLogs` class.
- **Silent-nothing audit**: compile failures throw or surface diagnostics;
  corrupt wasm and non-JSON compiler responses produce visible errors;
  `ScriptEditor` has NO sibling of the CodeEditor lint-wipe bug (it renders
  diagnostics in its own footer list from React state,
  `ScriptEditor.tsx:37,342` — never via `setDiagnostics`). The one remaining
  silent-nothing is finding 10 (deploy-gated, known).

## Findings (all left, with reasons)

1. **Snapshot signature framing is ambiguous for crafted primitive ids** —
   `subscriptionAdapter.ts` `reducePrimitives`, `sig.push(key, …)` +
   `sig.join(' ')`. Keys are user-supplied free text pushed raw; a key
   embedding a space plus JSON-shaped text could in principle make two
   different mutation sequences serialize identically, wrongly skipping an
   emit. Natural ids (spaces included) cannot collide in practice because the
   JSON tokens always start `{"kind"` — only a deliberately crafted id could,
   and the blast radius is the author's own chart. Left per the
   no-far-fetched-fixes rule; the 1-line hardening (JSON-encode the key
   token) is noted for the next time this function is touched.

2. **History-window slack (×1.2 + 10) assumes near-continuous markets** —
   `candleSource.ts` `loadHistory`. A from/to-honoring datafeed for a market
   with big gaps (tradfi weekends need ~×1.4) would return fewer bars than
   `countBack`, shorting the warmup lead-in and slightly degrading the
   earliest visible values. All current consumers are crypto (24/7), where
   ×1.2 is ample. Left; revisit if a non-crypto datafeed ever fronts this
   provider.

3. **`buffers.tick` / `data` / `history` are unbounded pre-handler** —
   `WasmScriptProvider.ts:202-225`. Only `logs` got a ring (500), because
   `onLog` may legitimately never be registered (IDE closed). The chart
   always registers `onData`/`onTick`/`onHistory` immediately on subscribe,
   so these buffers hold at most the initial batch for one microtask. Left:
   bounding them guards a consumer that doesn't exist.

4. **Compile failures are never cached** — `ensureCompiled` only caches
   successes, so retrying broken code re-POSTs each time. Deliberate: a
   failure may be transient (network, compiler restart), and compiles are
   user-triggered and rare. Left.

5. **Compile cache is FIFO, not LRU** — a cache hit doesn't refresh recency,
   so 9+ files edited round-robin would thrash the cap-8 cache. Real usage is
   one entry (entry+helpers fingerprint). Left.

6. **`reducePrimitives` walks the full cumulative event stream every tick**
   — the snapshot-skip suppresses the *emit*, not the *reduce*, so a
   long-session chatty script pays O(total events) per tick in the reducer.
   Known and accepted in the phase-2 design (pairs with SC's rAF coalescing);
   the fix (incremental reduction) is real work, not a review fix. Left.

7. **`parseCompileError`'s WARNING branch is currently unreachable** — the
   backend filters diagnostics to `kind === "ERROR"` before responding
   (`strategy_compiler/compile.js`), so no warning string ever arrives.
   Two-line future-proofing for when the backend forwards warnings; kept.

8. **na plots now consume the per-bar event budget** — the SDK forwarding
   na calls (`strategy_compiler/sdk/index.ts` `plot`/`plotPane`) means both
   hosts `charge_event` for them, where the old guest-side guard meant no
   call at all. This exactly matches the native host's existing accounting
   (it always charged before the NaN drop), so cross-host behavior is
   consistent; only a script issuing 65+ plot calls per bar (pathological)
   would newly trip the budget. Behavior change stated for the record.

9. **Debug probes shipped in CodeEditor** — `data-ce-id` stamping and the
   `applyDiagnostics` sync/raf logging, all gated behind the `debug` prop.
   Kept deliberately: they were decisive twice during phase-2 triage and are
   inert without `debug`.

10. **ta-v2 compiler redeploy still pending → the SDK layer has never run in
    the app.** Scripts compiled by the deployed compiler keep the guest-side
    na guard, so `StrategyHost.plotNames` sees only finite plot calls and the
    undeclared-warmup silent-nothing (`buildMetadata` fix, phase 2) remains
    reproducible in Altrady until the redeploy
    (`strategy_compiler/build.sh` + `k8s.yml`, Areg/Benoist's step). Old-SDK
    scripts are otherwise unaffected by the plotNames change (declared set ==
    events-derived set).

    **Confirmed still pending 2026-09-02** with the `plot("nanline", NaN)`
    discriminator — no legend entry, so the guard is still in the deployed SDK.
    The standing test and the full symptom write-up are in `plan.md`.

    **Correction:** this does *not* also close matrix row 3. `param.options`
    compiles on the deployed host today; the red marker in the editor comes from
    a stale function table in `@coinrayio/superchart-script` 0.1.9
    (`dist/index-D_B5lGRn.js:581-583` lists `param.float`/`int`/`bool_` and
    stops), which is a client-side linter with no bearing on the deployment.

11. **Metadata is fixed at subscribe** — `updateSettings` re-runs the script
    but does not rebuild `IndicatorMetadata` (plots/settings defs), matching
    the SC contract shape. A script whose *plot set* depends on an input
    value would show stale figures after a settings change; no known script
    does this (plot sets are static). Left; would need an SC contract
    addition (metadata update event) to fix properly, not a package-side
    patch.

## What this review did NOT re-verify

Live-app behavior (Areg's 53-item review pass covers it) and the Rust crates
(phase 2 touched only the SDK line in `strategy_compiler`; the native host
was read for parity checks, not modified).
