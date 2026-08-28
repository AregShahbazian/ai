# Phase 1 tasks — crypto_base_scanner_desktop [sc-script-spine]

Implements [design.md](design.md). SC-repo tasks are in
[sc-tasks.md](sc-tasks.md) (delegated). Verification checklist: [review.md](review.md).

Split into **Part A** (no dependency on the SC API — runs now) and **Part B**
(needs SC's three methods to exist). Part A ends with the TV regression green,
so R5 is banked before any new path lands.

---

## Part A — the neutral seam + moving TV out

### A1. `src/containers/scripts/chart-bridge/index.js` (new)

`ScriptChartBridgeProvider` + `useScriptChart()`. Provider-neutral, names no
chart library.

State: `currentRun` — `{runId, name, source, modules, wasm, meta}` — plus
`run(payload)` (bumps `runId`, returns the snapshot) and `clear()`.

**Verify:** `grep -in "tradingview\|superchart\|structureKey\|nonce" src/containers/scripts/chart-bridge/` returns nothing.

### A2. `src/containers/scripts/chart-bridge/use-script-run.js` (new)

The shared apply / re-apply / clear policy. `useScriptRun({apply, clear, deps})`
runs `apply(currentRun)` when `currentRun.runId` or any `deps` entry changes,
and `clear(handle)` on change or unmount. Handles the async race: if cleanup
runs while `apply` is still pending, the resolved handle is cleared immediately
rather than leaked.

**Verify:** unit-free — exercised by A6/B2. Read it once for the pending-apply path.

### A3. `…/center-view/tradingview/scripts/tv-script-state.js` (new)

TV-local run state, moved verbatim out of `scripts-context.js`:
`previewStudies`, `registeredPreviewKey`, and the `preview` snapshot derived
from `currentRun` (`structureKey` + `nonce`).

`structureKey` keeps today's exact formula — `{inputs: [`${key}:${kind}`], warmup}`.
It is known-incomplete (misses plot set and script name, see notes.md), and
fixing it would be a TV behaviour change, which R5 forbids. Leave it.

`nonce` is `currentRun.runId`.

**Verify:** the object handed to `strategyProvider` is field-for-field what
`pushPreview` produced.

### A4. `…/center-view/tradingview/scripts/tv-script-renderer.js` (new, replaces `script-preview-bridge.js`)

Move `script-preview-bridge.js` here unchanged except its state source: reads
`useTvScriptState()` + `useScriptChart()` instead of `useScripts()`. Reload
guard, hot-swap branch, auto-add effect and the `activeChart()` belt-and-braces
all stay exactly as they are.

**Verify:** `git diff` shows only import/hook-source changes, no logic edits.

### A5. `…/center-view/tradingview/scripts/index.js` (new)

Barrel: `TvScriptStateProvider`, `useTvScriptState`, `TvScriptRenderer`.

### A6. `src/containers/scripts/scripts-context.js` (edit)

- Delete `preview`, `previewStudies`, `registeredPreviewKey`, `pushPreview` and
  their entries in the `value` memo + deps array.
- `loadOnChart` becomes: `ensureCompiled()` → `chartBridge.run({name, source, modules, wasm, meta})`.
- `clearLogs()` moves with it — it fires on run, so it belongs at the `run` call.
- Keep `logs` / `appendLog` here: the Console panel is IDE state, not chart state.

**Verify:** `grep -n "preview\|structureKey" src/containers/scripts/scripts-context.js`
returns only `previewSymbol` / `previewResolution` (backtest + preview-chart
controls, unrelated).

### A7. `…/center-view/tradingview.js` (edit)

Split `MainChartTradingWidget` into a thin outer that mounts
`TvScriptStateProvider` and an inner holding today's body — the inner needs the
hook, so it can't also mount the provider.

`strategyProvider` / `onStrategyIndicatorsBuilt` read from `useTvScriptState()` +
`useScriptChart()`. Swap `ScriptPreviewBridge` for `TvScriptRenderer` in
`MAIN_CHART_COMPONENTS`.

**Verify:** `grep -n "useScripts" …/tradingview.js` → only `appendLog` remains.

### A8. `src/containers/trading-terminal.js` (edit)

Mount `ScriptChartBridgeProvider` immediately inside `ScriptsProvider` (line
~217) so both chart trees see the same bridge.

### A9. Delete `…/center-view/tradingview/script-preview-bridge.js`

### A10. TV regression

Run review.md **section B** (items 17-31) end to end. This is the R5 gate —
Part B does not start until it is green.

---

## Part B — the SuperChart path (blocked on SC's API)

### B1. `…/super-chart/scripts/sc-script-provider.js` (new)

Build the per-chart `ScriptProvider`. Wraps `WasmScriptProvider` in a forwarder
that omits `EditorComponent`, so SC's Script button is inert rather than opening
a second IDE.

Options: `datafeed` (the same instance `createDataLoader` got — this is why it
is per-chart, not a singleton), `compileEndpoint` + `compileHeaders` reusing
`taEndpointFrom` and the coinray-token lookup from
`src/actions/coinray-strategy.js:79-85`.

**Verify:** `window.DEBUG` — the provider instance differs per chart id.

### B2. `…/super-chart/scripts/sc-script-renderer.js` (new)

`useScriptRun({apply, clear, deps: [coinraySymbol, resolution]})`:

- `apply(run)` → `chart.<add>({code: run.source})`, returns the script id
- `clear(id)` → `chart.<remove>(id)`
- subscribe to SC's removal notice; ignore any id that is not the one held
  (the notice fires for host-initiated removals too — see design.md)
- tolerate the `'removed before start'` rejection from SC's race guard

Method names land from [sc-tasks.md](sc-tasks.md).

### B3. `…/super-chart/charts/market-tab-chart.js` (edit)

Pass `scriptProvider` in `superchartOptions` **only when `isMainChart`** — the
TT chart is the only one with a Scripts IDE (design.md → Decisions taken).
Build it in the existing `setup()` hook, which already has `superchart` and can
reach `dataLoader`.

Wire `dataLoader.setOnBarsLoaded` → `provider.loadHistoryBefore()` for
scroll-back.

**Verify:** `/charts`, preview, grid-bot and quiz charts get no `scriptProvider`
and show no Script button.

### B4. `…/super-chart/charts/trading-terminal-chart.js` (edit)

Mount `<ScScriptRenderer/>` beside `MarketTabChartOverlays`. Not inside it —
`MarketTabChartOverlays` is shared with `/charts`.

### B5. SC verification

Run review.md **sections A, C, D** (items 1-16, 32-41).

---

## Conventions

- Stage every new file at creation (`git add`), per the repo CLAUDE.md.
- No commits unless Areg asks. No builds — the dev server is running; HMR picks
  most of this up. A7's inner/outer split changes a component identity, so that
  one needs a hard reload.
