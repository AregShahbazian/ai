# Phase 2 — coinray_rest design [sc-script-parity]

Design for the `packages/superchart-script` side of [prd.md](prd.md). Written by
the coinray_rest session against `master` `87ba31b6` (== tag
`superchart-script-v0.1.8`, the published baseline). Design only — no tasks, no
implementation.

Verification targets: [review.md](review.md) sections B (17–22), C (23–28),
D (29–35); the contract lines in the PRD's Constraints.

## Files touched

| File | Items |
|---|---|
| `src/subscriptionAdapter.ts` | 2a (settings defs), 5 (log extraction), snapshot signature |
| `src/WasmScriptProvider.ts` | 2b (updateSettings), 3 (modules), 4 (diagnostics), 5 (onLog plumbing), snapshot-skip |
| `src/compileClient.ts` | 3 (already accepts `modules` — no change), 4 (no change; parsing lives in the provider) |
| `src/engine/types.ts` | 5 (`AdvanceResult.confirmedPrefix`), 3 (`StrategyMeta` untouched) |
| `src/engine/strategyHost.ts` | 5 (one line: expose confirmed-prefix length), 2b (min/max clamp in `_declParam`) |
| `tests/subscriptionAdapter.test.ts`, `tests/wasmScriptProvider.test.ts` | all |

Nothing in the Rust crates or `strategy_compiler` changes. The backend already
returns everything these items need (`inputs`, `modules` threading, located
error strings).

## 2a — `meta.inputs` → `IndicatorSettingDef`

**Current state.** `compileStrategy` already returns
`meta.inputs: StrategyInput[]` and `WasmScriptProvider` stores it on
`RunningScript.meta`; `buildMetadata` (`subscriptionAdapter.ts:58`) hardcodes
`settings: []`. Wire shape per `WasmInputDef` (Rust,
`coinray_script/src/strategy/wasm/mod.rs:84`):
`{key, kind: 'float'|'int'|'bool'|'options', default, min?, max?, options?: string[]}`.
NB the wire field is **`kind`**; `StrategyInput` declares `type` with a
documented fall-back to `kind` (`engine/types.ts:16`) — the mapper reads
`type ?? kind`.

**Design.** New pure function in `subscriptionAdapter.ts`, alongside
`buildMetadata` and called from it (same pattern as the plots mapping —
declaration order preserved, one def per input):

```
inputsToSettingDefs(inputs: StrategyInput[]): IndicatorSettingDef[]
```

Kind mapping:

| wire kind | IndicatorSettingType | defaultValue | notes |
|---|---|---|---|
| `float` | `number` | as-is | `min`/`max` pass through; no `step` |
| `int` | `number` | as-is | `min`/`max` pass through; `step: 1` |
| `bool` | `boolean` | as-is | |
| `options` | `select` | `String(defaultIndex)` | see round-trip below |

`id = key`, `name = key` (the SDK has no display-name concept; the key is what
the script author wrote). No `group`.

**Options round-trip** (the index/string mismatch). The host resolves an
`options` input **by index**: `param_decl_options` → `_declParam` → a number
(`strategyHost.ts:184`). `SettingOption.value` is a string. Mapping:
`options[i]` → `{value: String(i), label: options[i]}`, and
`defaultValue = String(default)` (the wire default for options is the index).
The return path needs **no new code**: SC hands back
`settings[key] = "2"`, and the existing `normalizeSettings`
(`WasmScriptProvider.ts:296`) already converts finite numeric strings to
numbers, so the host receives index `2`. This is the round-trip test to write:
def → simulated modal value → `normalizeSettings` → `_declParam` returns the
right index.

**Metadata is built from `meta`, not from a run.** `buildMetadata` currently
takes `events`; settings come from `running.meta.inputs`, passed as a new
parameter. A script with no inputs yields `settings: []` — unchanged shape, and
review item 22's "dialog does nothing harmful" case stays on SC's side.

## 2b — `updateSettings` (re-run with new params)

**Contract consumed** (SC-owned, must land first):
`ScriptProvider.updateSettings?(scriptId, settings)`. If SC ships the
stop+re-execute fallback instead, nothing here changes — the fallback calls
`stop()` + `executeAsIndicator()`, both existing.

**Design.** New method on `WasmScriptProvider`:

```
async updateSettings(scriptId: string, settings: Record<string, SettingValue>): Promise<void>
```

1. `running = this.running.get(scriptId)`; unknown id → throw (SC decides
   whether to fall back to remove/re-add).
2. `running.params = normalizeSettings(settings)` — the same normalizer the
   initial path uses.
3. `await this.runFresh(running)` — the **existing** rebase path used by
   `loadHistoryBefore`: fresh `StrategyHost`, `setParams`, full re-drive of
   `running.candles`. No new execution machinery; a settings change is
   deliberately the same operation as a history rebase.
4. Emit exactly what `loadHistoryBefore` emits, plus data: the recomputed
   points via `onData` (the contract documents `onData` as "called when
   indicator is first subscribed **or settings change**"), and the full
   primitive snapshot via `onPrimitives`. Buffer both when handlers aren't
   registered, into the existing `buffers`.

**Lifetime analysis (the phase-1 lesson, applied).**
- The live-tick closure reads `running.host` **at call time**, not captured —
  `runFresh` swapping the host is already safe for ticks (this is how
  `loadHistoryBefore` works today). No change needed, but the design test is:
  tick → updateSettings → tick, asserting the second tick runs on the new host.
- The new host's `confirmedThrough`/`confirmedEvents` restart from scratch —
  the log high-water mark (item 5) **must be reset by the same code path**, so
  the reset lives inside `runFresh`, not in each caller. See item 5.
- `running.params` is read by `runFresh` every time, never captured — a later
  backfill recompute re-applies the latest settings, not the ones at subscribe
  time.
- Failure: `runFresh` on a failing script parks a failed host and calls
  `onError` (existing behaviour, `WasmScriptProvider.ts:232`). The screen keeps
  the previous run's drawing; subsequent ticks surface `onError` per tick.
  Acceptable and unchanged; noted so review item 19's failure sibling isn't a
  surprise.

**Min/max clamp (small hardening, same item).** The native Rust host clamps
out-of-range numbers; the browser `_declParam` does not
(`strategyHost.ts:107`). Clamp against `schema[k].min/max` in `_declParam` so a
hand-edited persisted value can't run the script outside its declared range —
parity with the native host, and it protects the autosave path review item 21
worries about. ~4 lines + one test in `strategyHost.test.ts`.

## 3 — `modules` through the SC compile path

**Current state.** `compileClient.compileStrategy` accepts and posts
`modules` (commit `8bcbd601`; backend threads them; the unprovided-import
diagnostic exists). `ensureCompiled` never passes them, and the SC contract
(`ScriptExecuteParams`, `ScriptProvider.compile`) has no field. cbsd's
multi-file editor already produces the `Record<name, source>` map on the TV
path — no editor work.

**Contract consumed** (SC-owned, must land first): `modules?:
Record<string, string>` on `ScriptExecuteParams` **and** on
`ScriptProvider.compile()` (diagnostics for a broken helper must flow through
the same validation entry cbsd calls — review items 32/34).

**Design.**
- `ensureCompiled(code, modules?)` passes `modules` to `compileStrategy`.
- **Cache key** — the phase-1 "stale captured value" shape, and review item
  30's exact case: the cache is keyed by entry source only
  (`WasmScriptProvider.ts:77`), so a helper-only edit would silently hit the
  stale wasm. New key: a canonical fingerprint of entry + modules —
  `JSON.stringify([code, ...Object.entries(modules ?? {}).sort()])`. Cheap,
  deterministic, no hashing dependency. A test drives: compile, edit helper
  only, compile again → second wasm differs.
- The `compiled` map also grows without bound across edits (same lifetime
  theme, minor): evict oldest beyond a small cap (e.g. 8 entries) while
  touching the code anyway.
- **Cache agreement with cbsd** (coordinator, 2026-08-31): cbsd hit the
  identical stale-helper bug in phase 1 and fixed it the same way
  (`compileCacheKey(source, modules)`). The two caches must keep agreeing on
  what invalidates a compile — a mismatch is invisible: the IDE shows a fresh
  compile while this side serves a stale wasm. Any future change to either
  key's inputs is a cross-repo change.
- `executeAsIndicator` forwards `params.modules` into `ensureCompiled`.
  `RunningScript` does **not** store modules — nothing re-compiles after
  subscribe (a re-run is a new `executeAsIndicator`), so storing them would be
  a dead path.

## 4 — Real compiler diagnostics

**Current state.** `compile()` maps each backend error string to
`{line: i+1, column: 1}` (`WasmScriptProvider.ts:123`) — the array index as a
line number. The backend already formats every locatable error as
`` `${kind} TS${code}: ${message} in ${path}:${line}:${col}` ``
(`strategy_compiler/compile.js` `locate()`), and `rewriteSdk` is an in-place
string replace, so user line numbers survive compilation. Entry compiles as
`strategy.ts`; a helper `foo` compiles as `foo.ts`.

**Design.** A small parser in `WasmScriptProvider.ts` (exported for tests):

```
parseCompileError(raw: string): ScriptDiagnostic & { file?: string }
```

- Regex the trailing ` in <path>:<line>:<col>` suffix → `line`, `column`,
  `file` (path minus `.ts`; `strategy` = the entry). Strip the suffix from
  `message`? **No** — keep the full string as `message` so nothing is lost if
  the UI ignores `file`, and set the structured fields beside it.
- Leading `WARNING ` → `severity: 'warning'`, `ERROR ` (or no prefix) →
  `'error'`.
- No suffix match (limit errors, crash messages, `import "./x" does not
  resolve…`) → `line: 1, column: 1`, full string as message — the honest
  fallback, no longer pretending array position is a line.

**`ScriptDiagnostic.file?` — resolved (coordinator, 2026-08-31):** Altrady
will **not** consume it — the Scripts IDE compiles through its own
`compileForDiagnostics` action against ta-v2 and parses the `" in <file>:L:C"`
suffix itself; the multi-file routing gap (review item 34) is a two-line fix in
cbsd's `parseDiagnostic`. So `file?` benefits only SC's own editor: propose it
to SC only if nearly free, keep the file name visible inside `message`
regardless, and it must not hold up item 4.

## 5 — `onLog`

**Contract consumed** (SC-owned, must land first):
`IndicatorSubscription.onLog?(handler: (entry: {level: 'debug'|'info'|'warn'|'error';
message: string; timestamp: number /* bar time, ms */}) => void): void`.

**Current state.** The host already emits
`LogEvent {kind:'log', level: 0–3, time /* bar seconds */}`
(`strategyHost.ts:224`), uncharged against the event budget; the adapter drops
them (`eventsToPoints` filters to `plotValue`).

**Design — extraction** (mirrors `eventsToPoints`, in `subscriptionAdapter.ts`):

```
eventsToLogs(events: HostEvent[]): LogEntry[]
```

`level` 0–3 → `'debug'|'info'|'warn'|'error'` (1:1, no folding — settled),
`time * 1000` → `timestamp`. Pure, tested beside `eventsToPoints`.

**Design — confirmed-bar gating.** The provider cannot currently tell
confirmed events from forming ones: `advance()` returns
`confirmedEvents.concat(forming)` as one array. Rather than reconstructing the
boundary from bar times, expose it: `AdvanceResult` gains
**`confirmedPrefix: number`** — the length of the confirmed prefix (=
`this.confirmedEvents.length` at return). One line in `strategyHost.ts`, one
field in `types.ts`, engine-internal, no SC contract impact.

Gating in the provider, per `RunningScript`: a high-water mark
`logsScanned: number` — how far into the confirmed prefix logs have already
been forwarded. On every advance result:
forward `eventsToLogs(events.slice(logsScanned, confirmedPrefix))`, then
`logsScanned = confirmedPrefix`. Forming-bar events (index ≥ `confirmedPrefix`)
are never scanned — intra-bar ticks emit nothing (review item 26), and a bar's
logs go out exactly once, when it confirms.

**Reset semantics — designed explicitly, not implied** (the phase-1 lifetime
lesson; `runFresh` replaces the host, so the prefix restarts from zero and a
stale mark would silently mute or duplicate logs):

| Path | Reset | Forward history logs? | Why |
|---|---|---|---|
| Initial run (`executeAsIndicator`) | `logsScanned = 0` | **yes** | Parity: TV's initial run drives all bars confirmed and the console shows them (ring caps at 500 on cbsd's side — their stated job). |
| `updateSettings` re-run | `logsScanned = 0` | **yes** | A re-run is a new run; TV re-runs re-emit. Same rule as initial. |
| `loadHistoryBefore` rebase | `logsScanned = confirmedPrefix` **after** the recompute, forwarding nothing | **no** | A scroll-back is not a re-run; re-flooding the console with already-seen lines (plus older bars' lines) on every backfill would destroy it, and there is no per-line identity to dedupe with. TV has no equivalent path. |

Mechanically: `runFresh` gains a `forwardLogs: boolean` argument (or the two
callers set `logsScanned` right after it — pick at implementation; the design
point is that the mark is written **in the same function** that invalidates it,
never left to a distant caller).

**Bounded buffering.** The existing pre-handler buffers are unbounded; for
ticks/history that is bounded by usage, but logs from an 8000-bar initial run
with no `onLog` handler registered would sit forever (R3: "IDE closed must not
accumulate anything unbounded"). The log buffer is a ring capped at **500**
(matching cbsd's `LOG_CAP` — buffering more than the console can show is dead
weight), newest kept. Same register-then-drain shape as `onPrimitives`
(`WasmScriptProvider.ts:211`).

## Ordering and dependencies

```
2a (settings defs)        — no dependency; SC's modal needs it to land FIRST
4  (diagnostics)          — no dependency (file? field optional, flagged)
5  host confirmedPrefix   — no dependency (engine-internal)
── SC contract lands: updateSettings?, modules on params+compile, onLog?, [file?]
2b (updateSettings)       — after SC type exists
3  (modules plumbing)     — after SC type exists
5  (onLog emission)       — after SC type exists
── 0.1.9 manual publish (human step, end of phase)
```

While iterating, cbsd links the local build (settled). The `link:` devDep on a
local SC build means my typecheck needs the new SC `.d.ts` before 2b/3/5
compile — the SC session pings this session when their contract types are in
`dist-enterprise` (agreed). Note: cbsd consumes SC through the same built
bundle, and rebuilding `dist-enterprise` is a step only Areg can run — a
contract-type change is a synchronisation point for all three repos and will
likely land as one batch.

## Primitive cap / dedupe emit-side — decided (coordinator, 2026-08-31)

**No cap, no extra dedupe** (agreed). Reasons:
- Dedupe already exists: `reducePrimitives` keys the snapshot, keyed upserts
  overwrite, so the snapshot is minimal (one entry per live key). There is
  nothing further to dedupe emit-side.
- A count cap would silently drop drawings and diverge from TV, which renders
  everything — a parity phase shouldn't introduce a parity gap to help
  performance. The host's per-bar `maxEvents = 64` already bounds the emit rate.
- 8k primitives is a *render* scaling problem; SC's tiers (a)/(b) are the right
  layer.

**Skip-identical-snapshot emit — IN** (decided): most live ticks change no
confirmed primitives, yet every tick emits a full snapshot and forces SC to
reconcile ~8k entries. Suppress the emit when the snapshot equals the last one
emitted — suppressing *work*, not *output*; invisible to the contract ("on
every change" — an unchanged snapshot is not a change). This pairs with SC's
rAF latest-wins coalescing: we suppress the no-op ticks, SC collapses the
bursts that remain. Two binding constraints (coordinator):

- **Never suppress the first emit** after a handler registers or a buffer
  drains — the classic "unchanged" guard sitting in front of initial state. The
  last-emitted reference therefore lives with the handler/buffer plumbing and
  resets to "nothing emitted yet" whenever a handler is (re)registered; the
  drain path in `onPrimitives(handler)` always delivers.
- **Comparison stays genuinely cheap** — no second full serialisation pass per
  tick. `reducePrimitives` already walks every event; while doing so it
  produces a per-snapshot signature (e.g. an order-sensitive string/hash of
  `key + primitive` fields accumulated during the same walk). The tick path
  compares two signatures, O(1) after the walk that happens anyway.

Test: tick with unchanged primitives emits nothing; tick that changes one
primitive emits; handler re-registration always receives the current snapshot.

## Decisions — all resolved (coordinator, 2026-08-31)

1. **`modules?` on both `ScriptExecuteParams` and `compile()` — confirmed**,
   relayed to the SC session.
2. **`ScriptDiagnostic.file?`** — SC-editor-only benefit; Altrady parses files
   from its own diagnostics path. Non-blocking, see item 4.
3. **Snapshot-unchanged emit skip — in**, with the two constraints designed
   above.
4. Nothing here needs a permission this session lacks. The 0.1.9 publish
   remains the known human step (PAT with `write:packages`).

## Test plan (all in the package's vitest suite, no browser needed)

- `subscriptionAdapter.test.ts`: kind mapping table incl. options
  index/label/round-trip; `eventsToLogs` level + ms mapping.
- `wasmScriptProvider.test.ts` (mock datafeed + tiny wasm fixtures, existing
  harness): updateSettings re-runs and re-emits onData + full snapshot; tick →
  updateSettings → tick uses the new host; helper-only edit misses the compile
  cache; diagnostics parse entry + helper + suffix-less fallback; log gating —
  initial run forwards, intra-bar tick forwards nothing, bar confirm forwards
  once, backfill forwards nothing, updateSettings re-forwards; log ring buffer
  caps at 500 pre-handler.
- `wasmScriptProvider.test.ts` (snapshot-skip): unchanged tick emits no
  snapshot; changed tick emits; handler re-registration always receives the
  current snapshot.
- `strategyHost.test.ts`: `confirmedPrefix` correctness across
  confirm/forming; `_declParam` clamps to min/max.
