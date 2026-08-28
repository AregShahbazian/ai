# coinray_rest Reference — scripting stack

> Source: `$COINRAY_REST_DIR` (branch: master)
> Git hash: `87ba31b633e951212f784285680ca8654b6d716d` (2026-08-26)
> Hashes verified current: 2026-08-28.
> Do NOT explore source — use this doc instead.

Scope: the parts of the coinray_rest monorepo the desktop app consumes — the
`@coinrayio/superchart-script` npm package, and the strategy compile endpoint.
The scripting *language* has its own doc: `COINRAY_SCRIPT_LANGUAGE.md`.

## Repo map (scripting-relevant packages only)

| Path | What |
|---|---|
| `packages/superchart-script/` | The npm package the app installs. TS/React. |
| `packages/strategy_compiler/` | Node service: AssemblyScript → wasm. Also holds the SDK (`sdk/index.ts`) and fixtures. |
| `packages/coinray_script/` | Rust: the HTTP handlers, the wasm host, validation, backtest. |
| `packages/ta_core/` | Rust: the indicator math, dependency-free. |
| `packages/ta_wasm/` | `ta_core` compiled to wasm32 — the `ta_wasm.wasm` the browser loads. |

---

# A. `@coinrayio/superchart-script`

`packages/superchart-script/`, **v0.1.8**, ESM-first, published to GitHub
Packages (`npm.pkg.github.com`, restricted). Install needs a `read:packages`
token on `coinrayio` in `~/.npmrc`.

> **Master == published 0.1.8** at this HEAD — `4e4a5175` (2026-08-26) both
> implemented `declare_alert` in the browser host and bumped the version, and
> nothing has touched the package since. 0.1.8 is on the registry (the app's
> `yarn.lock` resolves it).
>
> **Publishing is manual.** `.github/workflows/publish-superchart-script.yml`
> was reduced to `workflow_dispatch:` on 2026-08-26 (`87ba31b6`); the
> `push: tags: superchart-script-v*` trigger is gone. It can't work as written
> because the package declares
> `"@coinrayio/superchart": "link:../../../Superchart/dist-enterprise"`, a path
> that doesn't exist on a runner, so `tsc --emitDeclarationOnly` fails with
> `TS2307: Cannot find module '@coinrayio/superchart'`. **No `superchart-script-v*`
> tag has ever published successfully** — 0.1.7 and 0.1.8 were both published by
> hand:
> ```
> cd packages/superchart-script && pnpm run build && npm publish   # needs write:packages
> ```

## Entry points — exactly three

```jsonc
"exports": {
  ".":        { "import": "./dist/index.js",  "require": "./dist/index.cjs" },
  "./engine": { "import": "./dist/engine.js", "require": "./dist/engine.cjs" },
  "./styles": "./dist/superchart-script.css"
}
```

`@coinrayio/superchart` is a **devDependency only**, externalised at build
(`vite.config.ts:23`) — the Superchart dependency is **type-only and
build-erased**. React `>=18` is a peer. CodeMirror is bundled.

## Root export surface (`.`) — exhaustive

```ts
export { WasmScriptProvider }              from './WasmScriptProvider'
export type { WasmScriptProviderOptions }  from './WasmScriptProvider'
export type { CompileResult, CompileArgs } from './compileClient'
export type { Candle, StrategyMeta, StrategyInput } from './engine/types'
export { COINRAY_STRATEGY_LANGUAGE, DEFAULT_STRATEGY } from './language'
export { ScriptEditor } from './editor/ScriptEditor'
export { CodeEditor }   from './editor/CodeEditor'
export type { CodeEditorProps, EditorDiagnostic } from './editor/CodeEditor'
export { createLanguageExtension } from './editor/languageAdapter'
```

> **`subscriptionAdapter` and `candleSource` are NOT exported.** `buildMetadata`,
> `eventsToPoints`, `reducePrimitives`, `periodToResolution`, `barToCandle`,
> `resolveSymbol`, `loadHistory`, `subscribeLive` are internal modules of
> `WasmScriptProvider` — no root export, no subpath. `compileStrategy` (the
> function) is exported only from `./engine`; the root exports only its types.
> Their signatures are documented below because a port that can't use
> `WasmScriptProvider` has to reimplement them.

## `./engine` subpath — chart-agnostic, zero Superchart dependency

```ts
export { StrategyHost } from './strategyHost'
export { TaEngine, SERIES } from './taEngine'
export type { Candle, StrategyInput, StrategyMeta, PlotValueEvent, AlertEvent,
  HostColor, HostPrimitive, PrimitiveEvent, PrimitiveUpsertEvent,
  PrimitiveDeleteEvent, OtherEvent, HostEvent, AdvanceResult } from './types'
export { compileStrategy } from '../compileClient'
export type { CompileArgs, CompileResult } from '../compileClient'
export { DEFAULT_STRATEGY } from '../language'
```

**This is what the app uses today** (TV adapter + `actions/coinray-strategy.js`).
`LogEvent` is in the `HostEvent` union but is not exported by name.

## Engine types (`src/engine/types.ts`)

```ts
/** One OHLCV bar as the engine consumes it. `time` is UNIX SECONDS. */
interface Candle { time: number; open: number; high: number; low: number; close: number; volume?: number }

interface StrategyInput {
  key: string
  type: 'float' | 'int' | 'bool' | 'options'   // ⚠ the WIRE field is `kind` — read `input.kind ?? input.type`
  default: number | boolean
  min?: number; max?: number
  options?: string[]                            // labels when kind === 'options'
}
interface StrategyMeta { inputs?: StrategyInput[]; warmupBars?: number }

interface PlotValueEvent { kind: 'plotValue'; name: string; time: number; value: number; pane: string | null }
interface AlertEvent     { kind: 'alert'; name: string; message: string; time: number }
interface LogEvent       { kind: 'log'; level: number; message: string; time: number }  // 0 debug 1 info 2 warn 3 error

/** r,g,b 0–255; t = alpha 0–255 (from the rgba(...) ABI). */
interface HostColor { r: number; g: number; b: number; t: number }

type HostPrimitive =
  | { kind: 'marker'; time: number; price: number; shape: string; color: HostColor; sizePx: number | null }
  | { kind: 'line';   p1: [number, number]; p2: [number, number]; color: HostColor; width: number; style: string }
  | { kind: 'box';    p1: [number, number]; p2: [number, number]; fill: HostColor; border: HostColor; borderWidth: number }
  | { kind: 'label';  time: number; price: number; text: string; color: HostColor; bgcolor: HostColor | null }

interface PrimitiveEvent       { kind: 'primitive'; primitive: HostPrimitive; pane: string | null }
interface PrimitiveUpsertEvent { kind: 'primitiveUpsert'; id: string; primitive: HostPrimitive; pane: string | null }
interface PrimitiveDeleteEvent { kind: 'primitiveDelete'; id: string }

/** Catch-all for the engine's remaining event kinds (orders, etc.). */
interface OtherEvent { kind: string; [k: string]: unknown }

type HostEvent = PlotValueEvent | AlertEvent | LogEvent
               | PrimitiveEvent | PrimitiveUpsertEvent | PrimitiveDeleteEvent | OtherEvent

interface AdvanceResult { events: HostEvent[]; cap: number; failure: string | null }
```

Marker shapes: `circle|square|triangle|arrowUp|arrowDown|cross`.
Line styles: `solid|dashed|dotted`.

Order events arrive as `OtherEvent`:

```ts
{ kind: 'orderGroupSubmit', groupId: string, time: number, direction: 'long' | 'short',
  entries: Array<{kind:'market', weight:number}
                | {kind:'limit', price:number, weight:number}
                | {kind:'stopLimit', stop:number, limit:number, weight:number}>,
  takeProfits: Array<{price:number, weight:number}>,
  stopLoss: number | null,
  qty: {kind:'fixed'|'percentEquity'|'riskBased', ...} | null,
  cancelOnTpBeforeFill: boolean }
{ kind: 'orderGroupClose', groupId: string, time: number }
{ kind: 'orderGroupCloseAll', time: number }
```

## `StrategyHost` (`src/engine/strategyHost.ts`)

A hand-written **JS reimplementation of the Rust wasm host's `env.*` ABI**, so a
compiled strategy runs client-side and emits the same event stream the server
WebSocket delivers.

```ts
class StrategyHost {
  ta: TaEngine
  schema: any[]                    // = meta.inputs
  warmup: number                   // max(meta.warmupBars ?? 0, 1); OVERWRITTEN by the guest's declare_warmup
  cap: number                      // === warmup; the OhlcvWindow capacity
  params: Record<string, number | boolean>
  limits: { maxEvents: 64; maxStr: 4096; maxOrderJson: 16384 }
  guest: WebAssembly.Instance | null
  candles: { open, high, low, close, volume, time: Float64Array, n: number } | null
  t: number                        // current bar index, -1 initially
  isNewBar: boolean
  failure: string | null
  declaredAlerts: string[]         // names from declare_alert, deduped, declaration order
  confirmedEvents: HostEvent[]
  confirmedThrough: number         // highest bar driven as confirmed, -1 initially

  constructor(taEngine: TaEngine, meta: StrategyMeta = {})
  setParams(p: Record<string, number | boolean>): void
  load(guestBytes: BufferSource): Promise<this>       // async
  loadModule(guestModule: WebAssembly.Module): this   // sync — for hosts that can't await (the TV study)
  setCandles(candles: Candle[]): void
  runAll(): HostEvent[]
  advance(candles: Candle[], confirmedCount: number): AdvanceResult
}
```

**Warmup is authoritative after `load()`.** `meta.warmupBars` seeds
`warmup`/`cap`, but the guest's start section calls `env.declare_warmup(bars)`
during load and overwrites both. `cap` is a ring-buffer capacity, not a hint:
`series_get(id, back)` returns `NaN` for `back >= min(t+1, cap)`, and every
`ta_*` computes over the trailing `cap` bars — **not** the full prefix. This is
the mechanism behind the "warmup must be ≥ your longest lookback" gotcha.

**`advance(candles, confirmedCount)`:**
1. If `failure` is set, returns immediately (permanent halt).
2. `setCandles(candles)`.
3. Drives bars `confirmedThrough+1 … confirmedCount-1` once each with
   `isNewBar = true`, appending to `confirmedEvents`.
4. Re-drives the remaining (forming) bars with `isNewBar = false` into a fresh
   array each call.
5. Returns `confirmedEvents.concat(forming)`.

The guest instance persists across calls, so module-level state carries forward.
**Indexing is absolute** — you cannot trim the candle array without corrupting
`confirmedThrough`. To extend history *backwards* you must build a fresh host
and recompute.

**Implemented `env` imports:**

| group | imports |
|---|---|
| bar/series | `is_new_bar`, `bar_index`, `bar_time`, `series_len`, `series_get` |
| TA | `ta_sma ta_stdev ta_ema ta_rma ta_wma ta_rsi ta_highest ta_lowest ta_change ta_mom ta_roc ta_cmo ta_cog ta_vwma ta_mfi ta_bb ta_macd ta_tr ta_atr ta_cci ta_wpr ta_stoch_k` |
| params | `param_decl_f64/_i64/_bool/_options`, `declare_warmup`, `param_f64`, `param_bool` |
| events | `declare_alert`, `emit_alert`, `log`, `plot`, `plot_pane` |
| orders | `order_submit_simple`, `order_submit_json`, `order_close`, `order_close_all` |
| primitives | `plot_marker`, `plot_line`, `plot_box`, `plot_label`, `primitive_delete` |

> **✅ `env.declare_alert` is implemented since 0.1.8** (`4e4a5175`, 2026-08-26).
> Before that it was missing, and any script calling `declareAlert(...)` compiled
> fine server-side but died in the browser with
> `LinkError: Import #6 "env" "declare_alert": function import requires a callable`
> — plots included. **If you are pinned below 0.1.8, that LinkError is still the
> symptom** and the workaround is `declare_alert: () => {}`.
>
> How it works: `declare_alert(ptr, len)` runs in the guest's **start section**,
> before `this.guest` is assigned, so the memory export is unreachable at call
> time (same reason `param_decl_*` ignore their ptr/len). The host stashes
> `[ptr, len]` in `_pendingAlerts` and resolves the strings in
> `_flushDeclaredAlerts()`, called at the end of both `load()` and
> `loadModule()`. Once `guest` is live, `declare_alert` reads immediately.
> `_recordAlert()` dedupes and preserves declaration order; an unreadable name
> is skipped rather than fatal. Both loaders reset `declaredAlerts` /
> `_pendingAlerts` first, so reloading a host is clean.
>
> **Declaring emits no event and charges no budget** — it only populates
> `host.declaredAlerts`. `alert()` fires with or without a declaration.

Parity rules mirrored from the native host: NaN is `na` (`plot(NaN)` dropped,
NaN-anchored primitives dropped, NaN order legs omitted); events use camelCase.
Event budget (64/bar) and string cap (4096) are replicated as logical checks;
**fuel/epoch metering is intentionally absent** — a runaway guest is bounded only
by running the host in a Web Worker the caller can terminate
(`src/engine/worker.ts`).

Divergence from server: `log` emits a `{kind:'log'}` event in the browser and is
**not** charged against the event budget; server-side it routes to `tracing` and
emits no event.

## `TaEngine` + `SERIES` (`src/engine/taEngine.ts`)

```ts
const SERIES = { open: 0, high: 1, low: 2, close: 3, volume: 4 }

class TaEngine {
  static fromBytes(bytes: BufferSource): Promise<TaEngine>
  static fromModule(module: WebAssembly.Module): TaEngine   // sync variant
  constructor(instance: WebAssembly.Instance)
  get buffer(): ArrayBuffer
  setHistory(h: {open, high, low, close, volume: Float64Array}): void
  free(): void
  value(spec: IndicatorSpec, t: number, cap: number): number
}

interface IndicatorSpec {
  fn: string; id?: number; length?: number
  mult?: number; which?: number                  // bb
  fast?: number; slow?: number; signal?: number  // macd
}
```

Wraps `ta_wasm`. Throws if `memory` / `ta_alloc` / `ta_ema` exports are missing.
`setHistory` allocates five resident `Float64Array` columns inside wasm linear
memory (all five allocated *before* writing, since `ta_alloc` may grow memory and
detach views). `value(spec, t, cap)` computes over the trailing window
`[t+1-min(t+1,cap), t]` by pointer arithmetic — no per-call copy — returning
`NaN` during warmup or out of range. `fn` ∈ `sma stdev ema rma wma rsi highest
lowest change mom roc cmo cog vwma mfi bb macd tr atr cci wpr stochK`.

## `compileClient` (`src/compileClient.ts`)

```ts
interface CompileArgs {
  endpoint: string
  source: string
  modules?: Record<string, string>   // bare module name → source, for `import … from "./zigzag"`
  headers?: Record<string, string>
  fetchImpl?: typeof fetch
}
interface CompileResult {
  success: boolean
  wasm?: Uint8Array      // iff success
  meta?: StrategyMeta    // { inputs, warmupBars }
  errors?: string[]      // iff !success
}
function compileStrategy(args: CompileArgs): Promise<CompileResult>
```

POSTs `{source, modules?}` as JSON plus `args.headers` (**no `name`** — the
server defaults it to `"strategy"`). Reads
`{wasmBase64?, lineTable?, inputs?, warmupBars?, errors?}` — **`alerts` and
`contentHash` from the server response are dropped on the floor**, and
`CompileResult` has no field for them. To get declared alert names client-side,
either POST the compile endpoint yourself and read `alerts`, or read
`host.declaredAlerts` after `StrategyHost.load()`.

Failure when `!resp.ok || errors?.length || !wasmBase64`. Base64 decoded via
`atob`, falling back to `Buffer`. Network throw → `{success:false, errors:['compile request failed: …']}`;
non-JSON → `['compiler returned non-JSON (status N)']`.

## `WasmScriptProvider`

> ⛔ **Cannot be used against Superchart `main`.** See the BLOCKER box in
> `SUPERCHART_API.md` → "ScriptProvider". It is built against the unmerged
> branch `feat/wasm-script-provider-example`.

```ts
interface WasmScriptProviderOptions {
  datafeed: Datafeed                      // MUST be the same instance passed to createDataLoader
  compileEndpoint: string
  compileHeaders?: Record<string, string>
  taWasmUrl?: string                      // override the bundled asset URL
  taWasmBytes?: ArrayBuffer | Uint8Array  // inject bytes; highest priority
  historyBars?: number                    // default 500
  fetchImpl?: typeof fetch                // COMPILE request only
}

class WasmScriptProvider implements ScriptProvider {
  readonly language: ScriptLanguageDefinition   // = COINRAY_STRATEGY_LANGUAGE
  readonly defaultScript: string                // = DEFAULT_STRATEGY
  readonly EditorComponent = ScriptEditor
  constructor(opts: WasmScriptProviderOptions)
  compile(code: string, _language: string): Promise<ScriptCompileResult>
  executeAsIndicator(params: ScriptExecuteParams): Promise<IndicatorSubscription>
  loadHistoryBefore(beforeMs: number): Promise<void>   // wire to DataLoader.setOnBarsLoaded
  stop(scriptId: string): Promise<void>
  dispose(): void
}
```

- Compiled artifacts memoised in `Map<sourceCode, {wasm, meta}>` — identical
  source never re-hits the network.
- `compile()` maps each error string to
  `{line: i+1, column: 1, message, severity: 'error'}` — **positions are
  fabricated**, not parsed from the `in strategy.ts:L:C` suffix. Parse that
  suffix yourself for real inline diagnostics.
- `executeAsIndicator` → `TaEngine.fromBytes` → `resolveSymbol` →
  `periodToResolution` → `loadHistory(countBack = historyBars ?? 500)` → fresh
  `StrategyHost` → `advance(candles, candles.length)` → `buildMetadata` /
  `eventsToPoints` / `reducePrimitives` → `subscribeLive`. Script id is
  `SCRIPT_${n}`.
- Subscription handlers (`onData`, `onHistory`, `onTick`, `onPrimitives`,
  `onError`) **replay buffered batches** on registration, so late attachment
  loses nothing.
- Settings normalised: only `number`/`boolean` pass; numeric strings coerced;
  everything else dropped.
- `loadHistoryBefore(beforeMs)` pages older bars from the *current earliest*
  (not from `beforeMs`) so pages connect with no gap, guarded at 50 iterations,
  then does **one** full recompute and emits via `onHistory` + `onPrimitives`.

## Internal helpers (not exported — reimplement if needed)

```ts
// src/candleSource.ts
function periodToResolution(period: Period): string
// second→`${span}S`, minute→`${span}`, hour→`${span*60}`,
// day→span===1?'1D':`${span}D`, week→'1W'/`${span}W`, month→'1M'/`${span}M`, year→`${span*12}M`
function barToCandle(bar: Bar): Candle        // ms → unix seconds, volume ?? 0
function resolveSymbol(datafeed: Datafeed, ticker: string): Promise<LibrarySymbolInfo>
interface HistoryRequest { symbol: LibrarySymbolInfo; resolution: string; countBack: number; to?: number }
function loadHistory(datafeed: Datafeed, req: HistoryRequest): Promise<Candle[]>
function subscribeLive(datafeed, symbol, resolution, onCandle: (c: Candle) => void): () => void

// src/subscriptionAdapter.ts
function buildMetadata(scriptId: string, events: HostEvent[], precision: number): IndicatorMetadata
function eventsToPoints(events: HostEvent[]): IndicatorDataPoint[]
function reducePrimitives(events: HostEvent[]): PrimitiveSnapshot
```

- `loadHistory` calls `getBars(symbol, resolution, {from: 0, to, countBack, firstDataRequest: req.to === undefined}, …)`.
  `subscribeLive` uses uid `scw_${ticker}_${resolution}_${n}`.
- `buildMetadata`: one `PlotLine` per distinct plot name, `style:'line'`,
  `lineWidth:1`, colours cycling
  `['#2962FF','#FF6D00','#2E7D32','#AB47BC','#00897B','#C62828']`,
  `pane: ev.pane ?? 'candle_pane'`; `paneId` is `'candle_pane'` if any plot
  targets the main pane, else `${scriptId}_pane`.
- `eventsToPoints`: groups `plotValue` by timestamp, **seconds → milliseconds**,
  ignores everything else, sorted ascending.
- `reducePrimitives`: keyed upserts overwrite by `id`; anonymous primitives keyed
  `anon_${indexInEventStream}`; deletes remove by id. Times → ms, colours →
  `rgba(r,g,b,t/255)` at 3dp. **Anonymous keys are stable across a recompute only
  because strategies are deterministic** (no clock, no RNG) — always give
  primitives an explicit id when drawing.

## Editor surface

**`CodeEditor`** — headless CodeMirror, no chrome. **This is what the Altrady IDE
uses** (`src/containers/scripts/panels/script-editor-panel.js`).

```ts
interface EditorDiagnostic {
  line: number            // 1-based, matches `strategy.ts:line:col`
  column: number          // 1-based
  endLine?: number
  endColumn?: number      // omitted → marker spans column..end-of-line
  message: string
  severity?: 'error' | 'warning' | 'info'
}
interface CodeEditorProps {
  language?: ScriptLanguageDefinition
  editorExtensions?: unknown[]   // when set, `language` is ignored
  value?: string                 // changing it RESETS the document
  readOnly?: boolean
  theme?: 'light' | 'dark'
  fontSize?: number
  lineNumbers?: boolean          // default true
  lineWrapping?: boolean         // default false
  highlightActiveLine?: boolean  // default true
  autocomplete?: boolean         // default true
  diagnostics?: EditorDiagnostic[]
  onChange?: (code: string) => void
  className?: string
  style?: CSSProperties
  debug?: boolean
}
```

**`ScriptEditor`** — the full modal editor (toolbar, script menu, help, profiler,
anchored/floating). Props are `ScriptEditorComponentProps` from
`@coinrayio/superchart` (type-only). Shortcuts: `Ctrl/Cmd+S` → `onSave(code, name)`,
`Ctrl/Cmd+Enter` → `onAddToChart(code)`, `Esc` → `onClose()`. Requires
`import '@coinrayio/superchart-script/styles'`. **Altrady does not use this** —
the IDE is Altrady's own.

**`createLanguageExtension`**

```ts
interface LanguageExtensionOptions { autocomplete?: boolean }   // default true
function createLanguageExtension(
  def: ScriptLanguageDefinition,
  theme: 'light' | 'dark' = 'dark',
  options: LanguageExtensionOptions = {},
): Extension[]
```
Returns `[LanguageSupport(StreamLanguage), autocompletion?, hoverTooltips, scriptLinter, syntaxHighlighting]`.

**`COINRAY_STRATEGY_LANGUAGE`** = `{name:'coinray', extension:'.ts', keywords[22],
typeKeywords[20], builtinVariables[15], builtinFunctions[~50],
types{Order, BollingerBands, Macd, Series}, comments{line:'//', blockStart:'/*',
blockEnd:'*/'}, operators[…], stringDelimiters:['"',"'",'`']}`. The `types` map
powers `.`-triggered member completion and is **not** part of the published
Superchart interface.

## ta_wasm bundling

`scripts/copy-ta-wasm.mjs` runs as `prebuild`, copying a prebuilt artifact into
`src/engine/assets/ta_wasm.wasm` from
`packages/coinray_script/public/dashboard/ta_wasm.wasm` or
`packages/coinray_script/frontend/public/ta_wasm.wasm` (the one that exists on
master, 49,579 bytes). Fails loudly with
`Build it first: (cd packages/ta_wasm && ./build.sh)`. The destination is
gitignored.

`WasmScriptProvider.ts:24` does `import taWasmUrl from './engine/assets/ta_wasm.wasm?url'`,
with `assetsInclude: ['**/*.wasm']` and `worker: {format: 'es'}` in the Vite
config. The URL is fetched once into a module-level `Promise<ArrayBuffer>` shared
across provider instances.

> **⚠ `?url` is a Vite-ism.** Under webpack (which is what Altrady uses) that
> import will not resolve — pass `taWasmBytes` or `taWasmUrl` explicitly.

## Tests worth reading

`tests/strategyHost.test.ts` is the most instructive: it pins the TV-style
per-bar drive (`host.advance(acc, acc.length)`, then tail-scan backwards for
`plotValue`s at the current bar time), proves `advance()` streaming equals
`runAll()`, and asserts **cross-language parity** — the same candles produce
event-for-event identical output to the native Rust host. It also demonstrates
that the guest's `declare_warmup(20)` overrides `meta.warmupBars: 1`.

`tests/declareAlert.test.ts` (added 0.1.8) pins the `declare_alert` contract:
present in the import table, stashed-then-resolved across the start section,
deduped in declaration order, read immediately once `guest` is live, and never
fatal on an unreadable name.

`tests/wasmScriptProvider.test.ts` shows a mock `Datafeed` + injected
`taWasmBytes` + a `fetchImpl` stubbing only the compile POST, and asserts
`loadHistoryBefore` pages contiguously (zero 60 s gaps) and that primitive
snapshots are idempotent across recompute.

---

# B. The compile endpoint

## Topology

| Layer | Entry | Role |
|---|---|---|
| **ta-proxy** (public) | `main/src/main.rs:145` → `coinray_script::start_proxy` | Auth, rate limit, routes by `?exchange=`. **This is what the app hits.** |
| **scanner backend** | `main/src/main.rs:136` → `start_service` | Owns the handler. No auth of its own — network-isolated. |
| **strategy-compiler** (Node) | `packages/strategy_compiler/server.js` | AssemblyScript → wasm, at `STRATEGY_COMPILER_URL` (default `http://127.0.0.1:9090`) |

The proxy forwards the raw body + query string and **only** `Content-Type`
(`proxy/handlers.rs:775-780`).

## Route

```
POST /api/v1/ta/strategy/user/compile?exchange=<EXCHANGE_CODE>
```

Proxy `proxy/mod.rs:138` inside `web::scope("/api/v1/ta")` at `:117`; backend
`#[post("/strategy/user/compile")]` at `web/user_strategies.rs:172`.

**`?exchange=` is mandatory** (the proxy uses it to pick a backend pod) even
though the handler ignores it — compilation is exchange-agnostic. Values are
codes like `BINA`, `BIFU`, `OKEX`. CORS is `Cors::permissive()` on both layers.

## Auth (proxy only, `proxy/handlers.rs:710-740`)

**Coinray JWT** — token read in priority order:
1. `Authorization: Bearer <token>` (scheme must literally be `Bearer`)
2. `cr-access-token: <token>` (raw, no scheme)
3. `?access_token=<token>`

HS256 over `COINRAY_SECRET` → `JWT_SECRET` → a built-in default; `kid` header and
`sub` claim required; `exp`/`nbf` enforced. Mint one at
`GET /api/v1/auth/coinray-token` → `{token, websocketEndpoint, expiresIn}`.

**Or** a dashboard session cookie `ta_session` (HMAC-SHA256, 24 h, HttpOnly,
SameSite=Lax) from `POST /api/v1/auth/login {password}`. **If
`DASHBOARD_PASSWORD` is unset, auth is disabled entirely.**

> **Identity caveat:** `CoinrayAuth::authenticate()` hardcodes
> `DBUser {id: 1, account_id: 1}` — only `subject` carries real identity.
> `/compile` needs no identity (stateless), but for the stateful siblings
> `user_id` is **client-supplied and trusted**. The per-user JWT +
> `X-Coinray-User-Id` scheme in
> `docs/superpowers/specs/2026-06-14-user-strategy-auth-design.md` is
> "Approved, pending implementation" — **not in the code at this HEAD**.

## Request

`web/user_strategies.rs:77-89` — no `rename_all`, no `deny_unknown_fields`
(extra fields silently ignored):

```json
{
  "source": "import { param, plot } from \"@coinray/strategy\"\nexport function onBar(): void { }",
  "name": "My Strategy",
  "modules": { "zigzag": "export function zigzag(): void { }" }
}
```

- `source` — **required**, must export `onBar(): void`.
- `name` — optional, default `"strategy"`. Diagnostics label only, never persisted.
- `modules` — optional, default `{}`. Key is the bare module name; both
  `./zigzag` and `../lib/zigzag.ts` resolve to key `"zigzag"`.

## Success (200)

```json
{
  "contentHash": "9f2c…64 lowercase hex",
  "wasmBase64": "AGFzbQEAAAA…",
  "warmupBars": 75,
  "alerts": ["oversold", "overbought"],
  "inputs": [
    { "key": "length", "kind": "int",     "default": 14,    "min": -2147483648, "max": 2147483647 },
    { "key": "mult",   "kind": "float",   "default": 2.0,   "min": 0.1,  "max": 10.0 },
    { "key": "useEma", "kind": "bool",    "default": false, "min": null, "max": null },
    { "key": "maType", "kind": "options", "default": 0,     "min": null, "max": null,
      "options": ["SMA", "EMA", "WMA"] }
  ]
}
```

- **`wasmBase64`** — standard base64 **with `=` padding, not URL-safe**.
- **`contentHash`** — `hex(sha256(wasmBytes))`, over the **wasm**, not the
  source. A good artifact-dedup key.
- **`warmupBars`** — the module's `config.warmup(n)`, falling back to `1`.
- **`alerts`** — names from `declareAlert`, collected after a 100-bar replay so
  in-`onBar` declarations are included. `[]` if none.
- **`inputs`** — in declaration order. Keys are literally
  `key`/`kind`/`default`/`min`/`max`/`options`. `min`/`max` appear as explicit
  `null` for bool/options; for `float` they're `null` unless finite; for `int`
  they're always numeric (defaults `i32::MIN`/`i32::MAX`). Only `options` is
  omitted when absent.

**Not returned:** `lineTable` / source map (the compiler emits it and `/deploy`
stores it, but `/compile` drops it), `strategyId`, `version`. **`/compile` stores
nothing.**

## Errors — two structurally different bodies, both can be 422

**(A) Compile diagnostics — 422 `{"errors": [...]}`**, passed through verbatim:

```json
{ "errors": [
  "ERROR TS2304: Cannot find name 'undefinedFn'. in strategy.ts:1:33",
  "ERROR TS2322: Type 'i32' is not assignable to type 'f64'. in zigzag.ts:12:7"
] }
```

Flat strings, **no structured diagnostic object**. Format
`ERROR TS<code>: <message> in <file>:<line>:<col>`, **1-based**. Virtual file
names: `strategy.ts` (the entry `source`), `<moduleName>.ts`, `sdk.ts`,
`entry.ts`. The ` in file:line:col` suffix is absent when asc reported no range.
Warnings are dropped — only `ERROR` entries return.

Reference parser (`coinray_script/frontend/src/tabs/StrategyEditor.jsx:91-102`):
```js
const match = str.match(/\s+in\s+strategy\.ts:(\d+):(\d+)\s*$/)
```

Non-asc entries appear in the same array (no `TS<code>`, no location):
`source exceeds the 256 KB limit`, `import "X" is not allowed — …`,
`import "./x" does not resolve to a known module — …`,
`@external bindings are not allowed — …` (helper-module errors suffixed
` (in module "zigzag")`), `compilation failed: …`,
`compilation exceeded the 10s time limit`, `compiler crashed: …`,
`compiler produced no result`.

**(B) Everything else — `{"error": {"code": "-1", "message": "..."}}`**
(`common/src/errors.rs:150-194`):

| Situation | Status | `message` |
|---|---|---|
| Host wasm validation failed (bad ABI, trap in the 100-bar replay) | **422** | `Invalid params: strategy failed validation: …` |
| Compiler unreachable / non-2xx-non-422 | 500 | `strategy compiler unreachable: …` |
| Undecodable base64 from compiler | 500 | `compiler returned undecodable wasm: …` |
| Bad/missing auth | **403** (not 401 — `errors.rs:180` maps AuthenticationError to FORBIDDEN) | `Authentication failed code: 401, message: Invalid token` |
| Missing `?exchange=` | 422 | `Invalid params: Missing exchange parameter` |
| Unknown exchange | 422 | `Invalid params: Unknown exchange 'XXXX'` |
| Rate limited | **429** | `Rate limited` |
| Backend pod unreachable | 500 | `Backend unavailable: …` |

**Client branching rule:** `body.errors` (array) → the user's code is wrong, show
inline. `body.error.message` starting `Invalid params: strategy failed validation:`
→ it compiled but the module is unsafe/broken. 403 → auth. 429 → rate limit.
5xx → infra.

Validation messages worth surfacing: ``import `X.Y` is outside the strategy ABI —
only `env.*` host functions are available``, ``module must export an `on_bar`
function``, ``module must export its linear `memory` ``,
`strategy trapped during validation replay at bar <i>: <trap>`.

## Related endpoints

All under `/api/v1/ta`, same auth, all need `?exchange=`.

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/strategy/user/compile` | `{source, name?, modules?}` | `{contentHash, inputs, alerts, warmupBars, wasmBase64}` |
| GET | `/strategy/user?exchange=&user_id=` | query (snake_case) | `UserStrategyVersion[]` — latest version of each owned strategy |
| GET | `/strategy/user/published?exchange=` | query | `UserStrategyVersion[]` — discovery list incl. `alertNames` + `inputs` |
| GET | `/strategy/user/{strategy_id}/wasm?exchange=` | — | **`Content-Type: application/wasm`, raw bytes** (not base64) |
| PUT | `/strategy/user/{strategy_id}/status` | `{user_id, status:"active"\|"disabled"}` | 204 / 404 |
| PUT | `/strategy/user/{strategy_id}/publish` | `{user_id, published: bool}` | 204 / 404, owner-only |
| POST | `/strategy/user/{strategy_id}/deploy` | `{user_id, name, source, modules?, symbol, resolution, params?}` | `Deployment` / 422 `{errors[]}` / 403 |
| GET | `/strategy/user/deployments?exchange=&user_id=` | query | `Deployment[]` |
| PUT | `/strategy/user/deployment/{id}/status` | `{user_id, status:"active"\|"paused"\|"disabled"}` | 204 / 404 |
| DELETE | `/strategy/user/deployment/{id}` | `{user_id}` — **DELETE with a JSON body** | 204 / 404 |
| POST | `/strategy/backtest` | camelCase `{strategyId?\|wasm?, sourceMap?, warmupBars?, params, symbol, resolution, from, to, config}` — `wasm` is base64, pass `wasmBase64` straight through; **`from`/`to` are `DateTime<Utc>` → RFC-3339** (`2026-08-01T00:00:00Z`) | `BacktestResult` |
| POST | `/strategy/backtest/multi` | same but `symbols: []`, compiles once, fans out 8-wide | per-symbol summaries |
| GET | `/strategies` | — | `{strategies: [...]}` built-in registry |
| GET | `/candles` | — | `[{time,open,high,low,close,volume}]`, `time` = unix **seconds** |

`UserStrategyVersion` is **camelCase** (`db/user_strategy.rs:43-66`):
`{strategyId, version, userId, name, source, contentHash, inputs, warmupBars,
sourceMap?, status, published, alertNames, createdAt}`.
`Deployment` is **snake_case** (`db/user_strategy_deployment.rs:44-58`):
`{id, user_id, strategy_id, symbol, resolution, params_json, status,
consecutive_traps, last_error, last_bar_time, created_at, updated_at}` — `id` is
an **i64**, not a UUID. Deployments auto-flip to `error` after
`STRATEGY_TRAP_DISABLE_THRESHOLD` (default 5) consecutive traps; strikes reset
only on explicit re-deploy.

**Backtest request shape** (`web/ta/mod.rs:~690-720`, `#[serde(rename_all = "camelCase")]`):
exactly one of `strategyId` / `wasm` (both or neither → 422
`Invalid params: provide exactly one of \`strategyId\` or \`wasm\`, not both` /
`… one of \`strategyId\` or \`wasm\` is required`). `warmupBars` only applies to
inline `wasm`, default **50** (`INLINE_WARMUP_FALLBACK`). `config` is
`{initialCapital, commissionPct, pyramiding, defaultQty, maxLeverage?}` —
`maxLeverage` defaults to `10.0`; the rest are **required**.

> 🚨 **A malformed `from`/`to` (or any bad JSON body) returns 500, not 422/400.**
> `web.rs:234` wires `JsonConfig::default().error_handler(|err, _| CoinrayError::from(anyhow!(err)))`;
> the anyhow downcast fails, so it becomes `CoinrayError::UnexpectedError` →
> **500** `{"error":{"code":"-1","message":"Json deserialize error: …"}}`.
> Same for `QueryConfig` and `PathConfig`. **This applies to every JSON-body
> endpoint in the service, not just backtest** — so a 500 here is often a client
> serialization bug, not infra. Send RFC-3339 (`toISOString()`), not epoch
> seconds or `YYYY-MM-DD`.

> ⚠ There is an unrelated legacy `POST /api/v1/ta/compile` (`web/ta/mod.rs:578`)
> returning `{"metadata":{}}` — **not** the strategy compiler, and not proxied.

## Limits, timeouts, caching

**Sizes:** proxy body **256 KiB** (413 over); backend `web::Json` 2 MiB; compiler
HTTP body 1 MiB; **per-file source 256 KiB**, checked for `source` *and each*
`modules` entry.

**Timeouts:** backend→compiler 30 s; proxy→backend 30 s; compiler wall-clock
**10 s** per compile (child SIGKILLed); host validation replay 100 bars, each
`on_bar` bounded by 50 M fuel + 10 s epoch.

**Rate limiting:** only when `RATE_LIMIT_RPS > 0` (default 100). Redis
`CL.THROTTLE`, key `ta:rate:{user_id}` or `ta:rate:session`. Since `DBUser.id` is
hardcoded to 1, **all JWT users share one bucket `ta:rate:1`**. Redis errors fail
open.

**Concurrency:** at most `MAX_CONCURRENT_COMPILES` (default **2**) child
processes; further requests queue in-process, unbounded. One replica
cluster-wide. Everything is synchronous — **no job queue, no polling**.

**Caching: none server-side.** Every request re-runs asc; no source-hash
memoisation on the HTTP path; no `Cache-Control`. **Client-side caching is the
intended mechanism** — mirror `WasmScriptProvider`'s `Map<source, {wasm, meta}>`
(which is what `src/actions/coinray-strategy.js` already does), or key on
`contentHash`.

## How compilation works server-side

**Not rustc, not wasm-pack, not Docker-per-compile.** It is **AssemblyScript
`asc` 0.28.19 running fully in-memory inside a Node 24 process**
(`packages/strategy_compiler/compile.js`):

1. **Static validation** — size, import allowlist, no `@external` (fails fast, 422).
2. **Virtual project assembly** — an in-memory `Map`: `entry.ts` (a fixed shim
   `import { onBar } from "./strategy"; export function on_bar(): void { onBar(); }`,
   so a user module cannot control its export surface), `strategy.ts` (user
   source with `"@coinray/strategy"` rewritten to `"./sdk"`), `sdk.ts` (the
   pinned SDK), plus `<name>.ts` per extra module.
3. **`asc.main`** with `["entry.ts","--outFile","out.wasm","-O2","--sourceMap","--use","abort="]`
   and a fully virtual `readFile`/`writeFile`/`listFiles`. **No filesystem, no
   network.** `abort=` turns AS `abort` into a bare `unreachable` trap so no
   `env.abort` import is needed.
4. **Source map → line table** — base64-VLQ mappings decoded into sorted
   `[wasmByteOffset, sourceIndex, line, col]` rows (1-based) so traps map back to
   `strategy.ts:line:col`.
5. Each compile runs in a **fresh one-shot child process** (`runner.js`, JSON
   over stdin/stdout), SIGKILLed on timeout.

Then in Rust, `validate_module` (`strategy/wasm/mod.rs:191-238`): ABI
import/export check → instantiate with `{}` — **the start function runs, which is
what produces `inputs` and `warmupBars`; the schema is a side effect of running
the module, not a static parse** → 100-bar synthetic smoke replay on a sine-wave
`BINA_USDT_BTC` R60 series with every 10th bar as an intra-bar tick → collect
`alerts` → `contentHash`.

---

# Gotchas for the desktop app

1. **`declare_alert` needs superchart-script ≥ 0.1.8.** Below that a script
   calling `declareAlert()` fails to instantiate client-side with a `LinkError`;
   shim it (`declare_alert: () => {}`) or upgrade. On 0.1.8+ read the names from
   `host.declaredAlerts` — `compileStrategy`/`CompileResult` throw the server's
   `alerts` array away.
2. **`subscriptionAdapter` / `candleSource` are not exported** — internals.
   Reimplement, or file an upstream export request.
3. **`StrategyInput.type` doesn't exist on the wire** — read `kind`, fall back
   to `type`.
4. **Two different 422 body shapes** — branch on `body.errors` (array) vs
   `body.error` (object).
5. **Auth failures return 403, not 401.**
6. **`?exchange=` is mandatory** even though compile ignores it.
7. **`/compile` stores nothing** — no `strategyId`/`version` in the response.
8. **Casing is inconsistent across the family**: compile request flat/snake,
   compile response camelCase, `UserStrategyVersion` camelCase, `Deployment`
   snake_case, mutation request bodies snake_case.
9. `DELETE /strategy/user/deployment/{id}` requires a **JSON body** — some HTTP
   clients drop DELETE bodies.
10. `user_id` is entirely client-asserted; **no** server-side binding to the
    token subject at this HEAD.
11. **No server-side compile cache** — cache client-side by source or `contentHash`.
12. **`?url` wasm import needs Vite** — pass `taWasmBytes`/`taWasmUrl` under webpack.
13. `min`/`max` arrive as explicit `null` (not omitted) for bool/options inputs;
    `int` always carries `±i32` bounds.
14. Browser `log` events exist; server `log` emits nothing.
15. **superchart-script publishing is manual** — the tag-triggered workflow is
    disabled (`workflow_dispatch` only) because the `link:` devDep on
    `@coinrayio/superchart` breaks CI. Bumping the version in `package.json` does
    not publish anything.
16. **Malformed JSON bodies → 500, not 4xx** (see the backtest note). Dates must
    be RFC-3339.
