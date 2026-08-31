---
id: sc-script-parity
repo: crypto_base_scanner_desktop
---

# Phase 2 design — parity (cbsd) [sc-script-parity]

Host design for [prd.md](prd.md), plus the **cross-repo contract** the other two
repos build against. SC's internals are in
[sc-design.md](sc-design.md); `superchart-script`'s in
[rest-design.md](rest-design.md) — each written by that repo's own session, as
`~/ai/workflow.md` -> "Multi-repo work" requires.

## Shape of the solution

Phase 1 built the seam; phase 2 mostly fills it in from the other end. Almost
all the new capability is implemented in `superchart-script` (emit) and SC
(render, settings, batching). **cbsd's share is wiring and one new neutral
channel** — nothing here is a new mechanism, and the module layout does not
change.

Concretely, four small deltas:

| Requirement | cbsd's part |
|---|---|
| R1 primitives | **Nothing.** Already works end to end; scale is SC's. |
| R2 params | **Nothing.** Inputs are edited in the chart's own dialog on both providers — that is the design, not a shortcut. The IDE gains no parameter UI. |
| R3 logs | Route a running script's log output into the existing Console panel. Needs one new neutral channel (below). |
| R4 modules | Stop dropping `run.modules` on the SC path. |
| R5 diagnostics | Make a run failure visible in the IDE instead of `console.error`, and keep the *file* a diagnostic belongs to. |

## R3 — logs: one new neutral channel

The problem is access, not translation. On TV the shim is ours, so the renderer
passes `onLog: appendLog` straight into it (`tradingview.js:110`). On SC the
subscription belongs to SuperChart; the host never sees it. So SC has to hand
log entries out, and the SC renderer forwards them.

This is the first thing in the scripting path that flows **chart → IDE** rather
than IDE → chart, so it needs a channel the bridge does not have yet.

- The bridge gains a neutral sink alongside `run(payload)`: the IDE registers
  a consumer, a renderer publishes to it. The renderer never imports the IDE
  context; the IDE never learns which provider produced a line. Same
  discipline as `currentRun` in the other direction.
- The neutral entry keeps **cbsd's existing console shape**
  (`{level: 0|1|2|3, message, time /* seconds */}`) — that shape is already
  what `appendLog` and `LEVEL_STYLE` speak, and TV already produces it. The SC
  renderer maps SC's contract shape (string level, ms) into it, because
  translation belongs on the provider side of the seam. **No new shape is
  invented for the neutral channel.**
- The TV path moves onto the same sink rather than keeping its direct
  `onLog: appendLog` wire. Otherwise the same idea exists twice — the exact
  duplication principle 1 forbids. It is a pure re-route: the entries are
  already in the target shape, so R6 exposure is minimal.
- Ownership follows `useScriptRun`: a sink registration is torn down with the
  run that owns it. A log arriving after teardown is dropped, not appended.

## R4 — modules on the SC path

`sc-script-renderer.js` currently drops `run.modules` with a comment saying why.
The drop site becomes a pass-through once SC accepts modules on the add. No
other cbsd change: the multi-file editor, `buildModules`, `compileCacheKey` and
`resolvedDependencies` all already exist and already feed the TV path.

Note what this removes: cbsd's own `compileForDiagnostics` already passes
`modules`, so today a helper script compiles *green in the IDE* and then fails
inside SC. Fixing the pass-through removes that contradiction, which is half of
review item 32.

## R5 — diagnostics: visibility, and which file

Two distinct gaps, only one of which is about line numbers.

1. **A failed run is console-only.** `useScriptRun`'s catch logs
   `[scripts] failed to run on chart` and stops. From the UI the indicator
   simply never appears (phase-1 review item 40). The bridge gets a failure
   channel — the same neutral sink idea as logs, one severity higher — so the
   IDE can show it where a compile error already shows. Provider-agnostic:
   TV's failures should surface the same way, and today they don't either.
2. **`parseDiagnostic` drops the file.** It already extracts real `line:col`
   from the compiler's `" in <file>:L:C"` suffix — so the "everything at line
   i+1" problem the PRD describes is `superchart-script`'s internal compile
   path, not the IDE's. What the IDE does lose is *which file*: the regex
   matches `.+?` and discards it, so a helper's error is rendered against the
   entry file's line numbers. That is review item 34, and it is a two-line fix
   in `parseDiagnostic` plus the marker-placement code choosing a file.

## The contract — what the host needs from the other repos

Capability requirements and invariants only. Interface shape is each repo's own
call (phase-1 lesson: I over-specified SC's signatures and had to withdraw
them).

### From SuperChart

1. **Accept helper modules with a script add.** A script whose entry imports
   `./helper` must compile and run. cbsd holds the modules and will pass them
   in whatever shape SC's add takes.
2. **Hand a running script's log output to the host.** SC owns the
   subscription; the host has no other access. Entries must identify the script
   they came from, so a late line from a previous run cannot be appended under
   the current one — the same discipline `onScriptIndicatorRemoved` already
   uses, and the reason phase 1 guards it by handle.
3. **A failed add rejects with the compiler's message intact.** Already true;
   recorded so it stays true — the IDE will render that message to the user
   rather than a generic failure.
   Structured diagnostics on a rejection were offered during design and
   **declined**: cbsd compiles through `compileForDiagnostics` before it ever
   calls the add, so compile errors are already caught and rendered with
   accurate line/col, and once R4 lands the class of failure that reaches SC's
   add is nearly empty. A run-time rejection also has no reliable file to
   anchor to in a multi-file script. The message string is sufficient for R5.

### Invariants

- **A settings change must not silently change the script's identity.** The
  host holds the id returned by the add as its only handle: `useScriptRun`
  clears by that id on unmount, and the removal notice is matched against it.
  If a settings update falls back to stop + re-execute and the id changes,
  the host's handle is stale — teardown becomes a no-op and the new indicator
  leaks. Either the id survives a settings update, or the host is told the new
  one. **Do not leave this to the fallback path's discretion.**

  *Resolved 2026-08-31.* Note the host is **not** the caller: settings are
  edited in SC's own modal, so SC performs the update internally and cbsd never
  sees a return value. Returning the new id therefore does not discharge this
  invariant. SC keeps its host-facing id stable and lets the underlying
  subscription id churn beneath it (`ActiveScript` is already keyed by
  scriptId, so the remap is internal bookkeeping); if that indirection proves
  expensive, the agreed fallback is an explicit id-change notification the host
  subscribes to, consumed in the same renderer guard that already handles
  removal notices. Silent churn is not an option.
- **Log delivery is tied to a live script.** Nothing may be delivered for a
  script the host has already removed.
- **No new host-visible behaviour on the TV side.** R6 is a hard gate;
  `superchart-script` is on both paths, so anything changed there must be
  neutral to TV.

### From `superchart-script`

Nothing addressed to cbsd directly — its output reaches us through SC. The one
thing cbsd depends on is that log gating happens **at the emitter**: an ungated
per-tick stream would flush a 500-line ring buffer before the user reads it, and
no amount of host-side filtering recovers what was dropped.

## Conformance to the architecture principle

Audited against plan.md -> "Architecture principle".

| # | Principle | Verdict |
|---|---|---|
| 1 | One flow, not two | **Holds, and improves.** Logs get one neutral sink used by both renderers instead of TV's private wire. |
| 2 | Minimum duplicated code | Holds. The only per-provider code added is the SC shape → console shape mapping, which is genuinely provider-specific. |
| 3 | Provider code in provider modules | Holds. Mapping lives in `super-chart/scripts/`; nothing provider-shaped enters the bridge or the IDE. |
| 4 | No branching outside those modules | Holds. No `chartProvider` test is added; selection stays structural. |
| 5 | Symmetry | Holds. Both renderers register a sink through the same hook-owned lifetime. |
| 6 | Third provider is additive | Holds. A third provider implements `apply`/`clear` and publishes to the same sink. |

**Deliberately not done — converging TV fully onto `useScriptRun`.** Phase 1's
design recorded this as "a phase-2 cleanup". It is not being done in phase 2,
and the reason is R6: TV's state machine carries reload guards the neutral hook
does not model, and phase 2 already changes shared code (`superchart-script`,
the log route) that the R6 gate has to cover. Bundling a TV state-machine
rewrite into the same gate makes a regression impossible to attribute. The
condition for doing it is phase 3, alongside the `structureKey` bug class it is
really about. Recorded again so it does not quietly become permanent.

## Phase-1 lessons applied

From the phase-1 code review (`../phase-1/review.md` -> "Round 1"), whose
findings clustered into three shapes:

- **Lifetime.** Every phase-1 bug but one was a value that outlived its
  validity: an endpoint captured at chart construction, an `earliest` remembered
  across a symbol change, a dep array missing a value that resolves
  asynchronously. Phase 2's new state is a log sink registration — so it is
  owned by the run, torn down with it, and late entries are dropped rather than
  appended. It is not module-level state, and not a ref that outlives the
  effect that made it.
- **Dep arrays.** `useScriptRun` spreads its deps, which opts the effect out of
  `exhaustive-deps` — that is how the `chartController` bug got in. Anything
  the SC renderer's new code reads goes in `deps` explicitly, and the reason is
  stated at the call site.
- **No dead paths.** Phase 1 shipped a `clear()` that was written, memoized,
  documented and never called. Every channel added here has both ends
  implemented in the same phase: the failure sink is only worth adding because
  the Console panel renders it.

## Accepted gaps

- **Pane-routed primitives** stay unrouted on SC (PRD non-requirement). Review
  item 50 asserts the fallback is silent, not broken.
- **Marker shape fidelity on TV** is not fixed; SC will simply be better here.
  Worth a line in the eventual user-facing docs, not a code change.
- **`superchart-script`'s internal diagnostics** improve for SC's own editor,
  which Altrady does not mount. cbsd benefits only through the run-failure
  message.

## Decisions taken during design

- **The neutral log entry keeps cbsd's existing console shape**, and the SC
  renderer maps into it — rather than adopting SC's contract shape neutrally
  and remapping in the panel. Reason: the panel, `LEVEL_STYLE` and the TV path
  already speak it, so the alternative changes three call sites to change zero
  behaviour.
- **TV moves onto the shared log sink in this phase**, despite R6, because
  leaving it on its private wire creates exactly the duplication principle 1
  exists to prevent, and the re-route is behaviour-preserving by construction.
- **Run failures get their own channel rather than being pushed as
  `level: 3` log lines.** A failure is not script output — it has no bar time,
  and it must be visible whether or not the script ever ran.
- **No parameter UI in the IDE.** Inputs belong to the indicator, and the
  indicator lives on the chart. This also keeps R7 clean: a parameter UI in the
  IDE would need to know which provider's settings it is editing.
