# Scripting — learning tour (guide)

**Goal:** understand what scripting is, how it works, and where it lives, before
porting it to SuperChart. The port itself is planned in [plan.md](plan.md);
running observations live in [notes.md](notes.md).

**Branch context:** this tour ran on the TradingView implementation.
`feature/coinray-script` is a 5.4 clone and does NOT contain the
superchart-integration changes.

**Status:** Part 1 complete (all 15 capability-matrix rows). Parts 3 and 3b
remain — Areg is reading the code himself and will ask when he wants them.

## Interaction format

- Stepped tour, one step at a time; Areg says **"next step"** to advance.
- Each step is mostly a **<20-word explanation** of what something is / how it
  works, plus **file/repo references** (`path:line`).
- **Example scripts:** each functionality is demonstrated with the simplest
  bare script that exercises it, followed through the code to the result
  (drawing, submitting, creating, …).
- Logs are the exception, not the rule: at 1–2 well-chosen points per
  implementation area, suggest a `/log-guide` and run it (stepped, <30-word
  pointers, Areg reloads the web app and checks the console).
- Claude never runs/builds the app; the dev webserver is already running.

## Tour outline

**Agreed order (Areg, 2026-08-18):** Part 1 (functionalities) → Part 3
(implementation) → Part 3b (coinray_rest guide) → Part 3c (the 2 issues).
Part 4 (SC implementation) became the scope survey in [plan.md](plan.md).
Parts 2, 5 and 6 were dropped: 2 and 5 because MCP is a remote control while
scripting is a compute pipeline — no useful overlap; 6 because the scope survey
superseded it.

### 1. Functionalities of scripts
What a script can do, shown with bare example scripts:
- draw on chart (lines, shapes, indicators?)
- CRUD other data — orders, alerts, …?
- **backtesting** — what it does, how a run is driven, what it produces
- limitations (sandboxing, what it explicitly cannot do)

**Method:** exhaustive. Every script capability is exercised through "Run on
chart", and for each one we also test **the effect of a re-run** — does the
second run replace the first, or leave residue? Re-runs are the known weak
spot (see the `loadOnChart` compile-cache bug), so every capability gets both
a first-run and a re-run verdict.

Starter/probe scripts live code-side in
`src/containers/scripts/scripts-context.js` — `STARTER_SCRIPT` (SMA) and
`TEST_SCRIPT` (2%-offset probe, no lookback), toggled via `ACTIVE_STARTER`.

#### Capability test matrix

| # | Capability | First run | Re-run effect | Notes |
|---|---|---|---|---|
| 1 | `plot` — line on price pane | ✅ works | ✅ fixed | 2%-offset probe + SMA both drawn |
| 2 | `plotPane` — sub-pane | ✅ works | ✅ fixed | |
| 3 | `param.*` inputs in study dialog | ✅ | ✅ fixed | int/float/bool_ and `options` all compile and render. The editor's red marker on `param.options` is a stale function table in the npm package's linter, not a compiler rejection (corrected 2026-09-02) |
| 4 | `draw.line` | ✅ works | ✅ | keyed `id` upserts. **A draw-only script never runs on TV** — needs >=1 `plot()`. Plot-count change isn't in `structureKey`, so it needed a manual `reloadTradingView()` |
| 5 | `draw.marker` | ✅ works | ✅ | Arrow up/down per bar, id-keyed per `barTime()`. **Script *name* isn't in `structureKey` either** — switching scripts with identical inputs+warmup didn't re-register; needed a manual reload |
| 6 | `draw.box` | ✅ works | ✅ | Rolling 20-bar range box, one id → slides. Colour edits propagate (verified yellow/red). `rgba()`'s 4th arg is **alpha** — `rgba(0,0,0,0)` is invisible, not black. Auto-reloaded because warmup differed |
| 7 | `draw.label` | ✅ works | ✅ | Bollinger bands with keyed labels pinned to the last bar on each band. Both `hasBg` modes render |
| 8 | `draw.remove` | ✅ works | ✅ | Trailing 10-marker window, older ids deleted. **Bug: `Shape.Circle`/`Shape.Square` throw `Wrong points count for circle. Required 2`** — TV's circle is a 2-point shape, the bridge creates it single-point. **Shape fidelity is lossy**: `square`→circle, `triangle`→arrow_up, and `cross` renders as a flag |
| 9 | `log.*` → Console panel | ✅ works | ✅ | 4 levels (debug 0 / info 1 / warn 2 / error 3). Ring buffer caps at `LOG_CAP = 500`, oldest evicted. Gate on `isNewBar()` or every intra-bar tick logs |
| 10 | `alert` / `declareAlert` | ✅ works | ✅ | `alert()` runs (silent client-side sink; only meaningful server-side). `declareAlert()` **was** fatal — `LinkError: Import #6 "env" "declare_alert"` → `registered 0 indicator(s)`. **Issue #2 FIXED and shipped** in `@coinrayio/superchart-script@0.1.8` |
| 11 | `strategy.long/short/close` | ✅ works | ✅ | MA-crossover script: both APIs (`strategy.long` one-liner + chained `Order` builder with split entries), hand-rolled crossover via module-level state. Plots render; orders dropped with one warning: *"submits strategy orders, which TradingView cannot render — run it in Superchart to see them."* **By design, not a defect** — a capability gap. Orders become visible via the backtester (row 12) or SC after the port |
| 12 | Backtest run + trade markers | ✅ works | ✅ | Report + equity curve in the panel, trade arrows on the chart. 48 trades / 176 orders / 4516 events / 2220 equity points, full `stats` block; `exitReason: stopLoss` proves the bracket resolves. **API note:** `from`/`to` must be RFC 3339 strings — unix ints get a **500** (not a 422) with `Json deserialize error … expected an RFC 3339 formatted date` in the body. `runBacktest` also auto-adds the script to the chart if nothing is previewed |
| 13 | Multi-module (sibling imports) | ✅ works | ✅ | `strategy` + `helper`, imported as `./helper`; exported functions *and* an exported `const` both cross. Files are virtual — an in-memory `Map` at compile, `resolvedDependencies` when saved. **Helper-only edits do invalidate the compile cache** (verified: entry untouched, `WIDE 1.5→6.0`, re-run recompiled and re-inited) — the case the old `if (!wasm)` check would have silently stalled |
| 14 | Save / versions / load | ✅ works | ✅ | Every Save appends an immutable version; `open()` rehydrates entry + helpers. **Two bugs found and fixed**: `openVersion()` restored only the entry (helpers dropped → `Cannot find module './helper'`), and the version menu's checkmark never left the head version. Both from `openVersion` being written independently of `open`; now share `hydrateFiles()`, plus an explicit `openedVersion` |
| 15 | "Add to charts" (non-preview path) | ✅ works | ✅ | Per-device id list (`scripts.chartEnabled`, localStorage — does not follow the account). Script appears on every chart with no IDE widgets and no "Run on chart". **Two bugs found and fixed**: the toggle only took effect after a widget rebuild (`onChartScriptsChanged` had no subscribers — dead code); and helpers were dropped because it read `script.modules`, which the API never returns (they are `version.resolvedDependencies`) |

Legend: ✅ works · ❌ broken · ⚠ partial · ⏳ not tested.

**Open question carried forward:** does a re-run clear the previous run's
`draw.*` shapes? The reconciler does a real diff (`custom-indicators.js:39-45`)
and the owner pushes even an empty list, so keyed shapes should be removed —
but anonymous ones are keyed positionally and a suspected `StrategyHost.
loadModule()` residue path leaves `confirmedEvents` unreset. Settle at rows 4–8.

**Re-run bugs found and fixed while testing rows 1–3** (branch merged into
`feature/superchart-scripting`):
- `loadOnChart`/`runBacktest` never recompiled after an edit — every re-run
  re-pushed the first compile. Fixed by fingerprinting the compiled sources.
- Switching scripts then re-running crashed `ScriptPreviewBridge`
  (`activeChart()` on a removed widget). Fixed by clearing `previewStudies`
  before the reload.
- `structureKey` read `i.type` on inputs carrying `kind`, so every entry
  serialised `name:undefined`. Fixed.
- Dev affordance added: `window.DEBUG.scripts` exposes the whole live context.

### 3. Implementation (the code tour)
- **Which code is where, and in which repo**: `crypto_base_scanner_desktop`
  (IDE + actions + TV adapter) vs `@coinrayio/superchart-script`
  (= `packages/superchart-script` in coinray_rest) vs the coinray_rest Rust
  crates vs coinrayjs.
- **How the code is structured across the four layers**: logic / UI / wasm /
  backend — and which layer each file belongs to.
- Where the modules link up (editor → compile → execute → TV chart
  primitives / API calls).
- 1–2 suggested log-guides max, e.g. "script edited & submitted → drawn on TV
  chart". `[coinray-strategy]` logs come from the TV adapter
  `…/tradingview/controllers/ci/coinray-strategy.js`.

### 3b. Minor guide — the coinray_rest repo itself
Areg only learned of this repo via scripting, but it long predates it. Short
orientation, not a deep dive:
- What coinray_rest *is* and what it serves beyond scripting.
- Its monorepo shape: Rust crates vs Node packages vs the npm package we install.
- Which parts scripting touches (`superchart-script`, `strategy_compiler`,
  `coinray_script`, `ta_core`, `ta_wasm`) and which are unrelated.
- Where the compile endpoint lives and how a request travels through it.
- Reference: `~/ai/crypto_base_scanner_desktop/deps/COINRAY_REST_API.md`.

### 3c. The two open issues — do they *need* fixing?
Decide per issue, separately for TV and for SC:
1. ~~**Unmerged SC branch**~~ — **RESOLVED 2026-08-26**: re-ported onto a fresh
   branch off SC `main` and merged (`d5298aa`) — primitives + editor slot,
   `plotPane` sub-pane routing as a separate revertable commit. `17154ee`
   (the circular devDep) was dropped. Original description below.
   `@coinrayio/superchart-script@0.1.7`'s
   `WasmScriptProvider` was built against `origin/feat/wasm-script-provider-example`,
   never merged into SC `main`; `main` has no `PrimitiveSnapshot` and no
   rendering path for `draw.*` primitives. Blocks SC only, and only once the
   port starts.
2. ~~**Missing `env.declare_alert`**~~ — **RESOLVED 2026-08-26**: implemented in
   the browser `StrategyHost` (the name is stashed during the wasm start section
   and flushed at the end of `load()`/`loadModule()`), published as
   `@coinrayio/superchart-script@0.1.8`, which this branch pins. Original
   description below. The SDK gained `declareAlert()`
   (`4d5ea2d4`) after the browser `StrategyHost` was last touched (`975b1598`).
   A script using it compiles server-side but fails to instantiate client-side
   with `LinkError`. **Affects TV today**, not just SC.
   **CONFIRMED live 2026-08-18** (matrix row 10): exact message
   `LinkError: WebAssembly.Instance(): Import #6 "env" "declare_alert":
   function import requires a callable`, followed by
   `registered 0 strategy indicator(s)` — the whole script dies, plots included.
   Fix belongs in `@coinrayio/superchart-script`'s `StrategyHost`; needs a
   package release from coinray_rest.

## Tour tracker

`[ ]` not started · `[~]` in progress · `[x]` done.

- [x] 1. Functionalities (incl. backtesting) — ALL 15 rows done; both blockers resolved
- [ ] 3. Implementation — code locations, repos, layers
- [ ] 3b. coinray_rest minor guide
- [x] 3c. The two open issues — BOTH RESOLVED upstream (`d5298aa`, 0.1.8)
- [x] 4. Port scope — moved to [plan.md](plan.md)

## Prep (Claude, at tour start)

1. Read `~/ai/crypto_base_scanner_desktop/deps/` docs first (hard rule) —
   `COINRAYJS_API.md`, `SUPERCHART_API.md`, `SUPERCHART_USAGE.md`; use
   `sc-source-explorer` for any cross-repo source digging.
2. Locate the script feature's entry points in this repo (editor UI, actions,
   execution) and any bundled example scripts.

## Deliverables

- The tour itself (chat, stepped).
- Notes worth keeping get distilled into this folder afterwards (e.g.
  `functionalities.md`, `tv-implementation.md`) — only on request.
