---
id: sc-script-parity
repo: crypto_base_scanner_desktop
---

# Phase 2 tasks — parity (cbsd) [sc-script-parity]

From [design.md](design.md). SC's tasks are in [sc-tasks.md](sc-tasks.md),
`superchart-script`'s in [rest-tasks.md](rest-tasks.md), each owned by that
repo's session.

cbsd's share is wiring. Parts A and D have **no cross-repo dependency** and land
first; parts B and C need SC's contract types in a rebuilt `dist-enterprise`.

## Part A — the neutral channels (no dependency)

- [x] A1. `chart-bridge/context.js`: add `registerConsumer({onLogs, onFailure})`
      returning an unsubscribe, plus `publishLogs(runId, entries)` and
      `publishFailure(runId, error)`. Both publishes drop anything whose
      `runId` is not the current run — a late line from a previous run must not
      appear under the current one.
- [x] A2. `scripts-context.js`: register the consumer (`onLogs` → the existing
      `appendLog`, `onFailure` → new `runError` state). Depend on
      `chartBridge?.registerConsumer`, not on the bridge value — the latter
      changes every run and would re-register each time.
- [x] A3. `runError` clears where diagnostics clear: a new run, a compile, a
      file edit, opening another script.
- [x] A4. `console-panel.js`: render `runError` beside the compile diagnostics,
      styled as an error. This is the half that makes A1's failure channel
      worth having — no channel without a consumer (phase-1 lesson).
- [x] A5. `use-script-run.js`: on a failed apply, publish the failure as well as
      logging it. Hold `publishFailure` in a ref like `apply`/`clear`, so the
      spread dep array can't go stale.
- [x] A6. `tradingview.js`: TV publishes to the sink instead of calling
      `useScripts().appendLog` directly. Drops the IDE import from the TV
      widget. Behaviour-preserving — the entries are already in the target
      shape.

## Part B — modules on the SC path (needs SC)

- [x] B1. `sc-script-renderer.js`: pass `run.modules` on the add; delete the
      comment explaining why they were dropped.
- [ ] B2. Verify a helper script that compiles green in the IDE now also runs on
      SC (review item 29), and that a helper-only edit re-runs (item 30).

## Part C — logs on the SC path (needs SC + `superchart-script`)

- [x] C1. `sc-script-provider.js`: intercept the subscription returned by
      `executeAsIndicator` and attach `onLog`. cbsd owns the `ScriptProvider`
      object it hands SC, so this needs no SC consumer — which is why SC's
      design deliberately has none.
- [x] C2. Map SC's entry shape (string level, ms) to the console's
      (`{level: 0-3, message, time}` in seconds) in the SC module. The neutral
      channel carries cbsd's existing shape; no new shape is invented.
- [x] C3. `sc-script-renderer.js`: install the handler for the current run and
      clear it on teardown, so a log can never outlive the run that produced it.

## Part D — diagnostics (no dependency)

- [x] D1. `parseDiagnostic`: keep the file from the compiler's
      `" in <file>:L:C"` suffix instead of discarding it with `.+?`.
- [x] D2. `script-editor-panel.js`: place inline markers on the file they belong
      to, rather than only ever on the entry (`activeFile === 0`).

## Status (2026-08-31)

All of A, C, D and B1 are implemented; ESLint clean on every touched file.

- **Verified live** (Playwright, dev server): the failure channel (a rejected run
  now shows in the Console panel), `parseDiagnostic`'s file field, and TV's logs
  arriving through the bridge with all four levels — A6 changes the TV path, so
  that one is an R6 gate item.
- **Written but not yet exercisable:** B1 and C1-C3 need SC's contract types in a
  rebuilt `dist-enterprise`. Both are written against the landed signatures
  (`ScriptExecuteParams.modules`, `IndicatorSubscription.onLog`) and degrade to
  no-ops on the current bundle, exactly as phase 1's `onScriptIndicatorRemoved`
  guard did.
- **Blocked elsewhere:** D2's inline markers land on the wrong file because
  `CodeEditor` ignores the diagnostics it is mounted with. cbsd's routing is
  correct and verified; the fix belongs in `superchart-script` and is with that
  session.

## Verification

Run [review.md](review.md). cbsd owns items 23-28 (logs, jointly with the
emitter), 29-35 (modules and diagnostics), 36-39 (seam) and the phase-1 spine
re-run in item 49. Items 1-22 depend on the other two repos.

Playwright against the live dev server, as in phase 1 — console globals
(`window.DEBUG.scripts`, `window.chartController`), screenshots read visually.
