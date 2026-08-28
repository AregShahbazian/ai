# `@coinray/strategy` — script language reference

> Source: `$COINRAY_REST_DIR` (branch: master)
> Git hash: `87ba31b633e951212f784285680ca8654b6d716d` (2026-08-26)
> Hashes verified current: 2026-08-28. The SDK
> (`packages/strategy_compiler/sdk/index.ts`), `ta_core` math, fixtures and
> `DEFAULT_STRATEGY` are **unchanged** since the previous check — only the
> browser host's `declare_alert` support changed.
> Do NOT explore source — use this doc instead.

What a user writes in the Scripts IDE. Single source of truth:
`packages/strategy_compiler/sdk/index.ts` (539 lines). It is **AssemblyScript**,
so `f64` / `i32` / `i64` / `bool` are real types, not TypeScript annotations.

The runtime that executes it, and the compile endpoint, are in
`COINRAY_REST_API.md`.

> **This is not Pine.** The surface is much smaller. Every "does Pine have X?"
> answer below is verified against the SDK — the absent lists are exhaustive, not
> approximate.

## The contract

```ts
export function onBar(): void
```

Module top-level code (`const x = param.int(...)`, `config.warmup(...)`) runs
once in the **start function** at instantiation. Module-level `let` persists
across bars — **this is Pine's `var`**. `onBar` runs once per confirmed close
**and** repeatedly on the forming bar.

> Calling any bar-context host function from module top level **traps
> instantiation**: `"host function called outside on_bar (e.g. from the module
> start function)"`.

## `config`

```ts
namespace config { function warmup(bars: i32): void }
```

**The only member.** It is **not a hint — it is the ring-buffer capacity.**
`src.close.at(back)` returns `na` for `back >= warmup`, and any `ta.*` with
`length > warmup` returns `na` **forever, silently**. This is the single most
common cause of "my script registers but plots nothing".

Default when undeclared: `1` in `validate_module`, the stored `warmupBars` at
runtime, `max(meta.warmupBars ?? 0, 1)` in the browser host.

**No range is enforced anywhere** — the linker signature is `u32` while the SDK
declares `i32`, so a negative argument wraps to a huge `usize`. Largest value in
any fixture: `config.warmup(500)`.

## `param` — the complete list

```ts
namespace param {
  function float(name: string, def: f64, min: f64 = NaN, max: f64 = NaN): f64
  function int(name: string, def: i32, min: i32 = i32.MIN_VALUE, max: i32 = i32.MAX_VALUE): i32
  function bool_(name: string, def: bool): bool
  function options(name: string, def: i32, labels: string[]): i32
}
```

**Four overloads, that's all.** No `param.string`, no `param.source`, no
`param.color`, no `label` / `group` / `tooltip` / `step` / `inline`. The `name`
string *is* the key and the only label.

- `bool_` carries the underscore because `bool` is a reserved AssemblyScript type.
- `options` joins labels with `"\n"` (the ABI can't pass arrays) and the script
  works in **indices**, never strings.

**Clamping** (`strategy/wasm/host.rs:426-527`): float clamps to finite min/max;
int `.clamp(min, max)`; options `.clamp(0, labels.len()-1)`. Wrong-typed values
silently fall back to the default.

Declarations are deduped by key, order preserved — **that order is the
settings-modal order**. Re-calling inside `onBar` cannot grow the schema.
`validate_params` rejects unknown keys / wrong types / out-of-range at the API
boundary.

## `src`

```ts
class Series {
  constructor(readonly id: i32)
  at(back: i32): f64        // 0 = current bar, 1 = one back (Pine style); out of range → na
  get length(): i32         // = min(barsSoFar, warmup)
}
namespace src {
  const open   = new Series(0)
  const high   = new Series(1)
  const low    = new Series(2)
  const close  = new Series(3)
  const volume = new Series(4)
}
```

**Exactly five series.** No `hl2`, `hlc3`, `ohlc4`, no time series, no
user-defined series. `volume` is base volume.

The window is **transactional**: a confirmed bar commits the push, an intra-bar
tick rolls it back — so `at(1)` is always the previous *confirmed* close without
the author writing two branches.

## `ta` — all 24 functions

```ts
class BollingerBands { constructor(readonly lower: f64, readonly middle: f64, readonly upper: f64) }
class Macd           { constructor(readonly macd: f64, readonly signal: f64, readonly histogram: f64) }

namespace ta {
  function sma(series: Series, length: i32): f64
  function ema(series: Series, length: i32): f64
  function rma(series: Series, length: i32): f64
  function wma(series: Series, length: i32): f64
  function vwma(series: Series, length: i32): f64
  function stdev(series: Series, length: i32): f64
  function rsi(series: Series, length: i32): f64
  function highest(series: Series, length: i32): f64
  function lowest(series: Series, length: i32): f64
  function change(series: Series, length: i32 = 1): f64
  function mom(series: Series, length: i32): f64
  function roc(series: Series, length: i32): f64
  function cmo(series: Series, length: i32): f64
  function cog(series: Series, length: i32): f64
  function mfi(series: Series, length: i32): f64
  function bb(series: Series, length: i32, mult: f64): BollingerBands
  function macd(series: Series, fast: i32, slow: i32, signal: i32): Macd

  // OHLC-based — no series argument
  function stochK(length: i32): f64
  function tr(): f64
  function atr(length: i32): f64
  function cci(length: i32): f64
  function wpr(length: i32): f64
}
```

**Do NOT assume these exist — they don't:** `crossover`, `crossunder`, `cross`,
`sum`, `cum`, `valuewhen`, `barssince`, `pivothigh`, `pivotlow`, `supertrend`,
`adx`, `dmi`, `obv`, `sar`, `linreg`, `correlation`, `percentrank`, `variance`,
`hma`, `swma`, `alma`, `kc`, `dev`, `median`, `mode`, stoch `%D`,
`rising`/`falling`, `barstate.*`.

Crossovers are hand-written with module-level state. A full zigzag pivot engine
lives in userland at `packages/strategy_compiler/fixtures/zigzag.ts` (291 lines)
— **that is the intended pattern for anything missing.**

### Semantics worth pinning

Math is in `packages/ta_core/src/lib.rs`; all return `NaN` (= `na`) during warmup.

- `stdev` is **population** (÷n).
- `ema` seeds on `mean(v[0..length])`, `α = 2/(length+1)`; `rma` seeds the same,
  `α = 1/length`.
- `wma` weights oldest 1 … newest `length`.
- `vwma` is `na` when `Σvol == 0`.
- `rsi` needs `length+1` bars; returns `100.0` when average loss is 0.
- `change` / `mom` are **exact aliases**. `roc` is `na` when the prior value is `0.0`.
- `cmo`, `mfi` need `length+1` bars; `mfi` uses the raw series × volume
  (**not** hlc3), matching Pine.
- `cog` is `na` when the windowed sum is 0.
- `macd` requires `fast < slow` and `len >= slow + signal`.
- `stochK` returns **`50.0`** when high == low.
- `cci` returns **`0.0`** when meanDev == 0.
- `wpr` returns **`−50.0`** when hh == ll.
- `bb.which > 2` **traps**.

`ta_core` is dependency-free and compiles both native and to wasm32
(`packages/ta_wasm`), so browser preview and server alerts compute identical
values — pinned by `packages/ta_wasm/tests/parity.rs`.

## `plot` / `plotPane`

```ts
function plot(name: string, value: f64): void
function plotPane(name: string, value: f64, pane: string): void
```

**The entire plotting surface — no options at all.** No `color`, `linewidth`,
`style`, `title`, `overlay`, `display`. Both return `void`, so there is **no plot
handle and no `fill()` between plots**. Styling is entirely the chart client's
job (`buildMetadata` assigns palette colours by plot index).

`na` is a **gap, not an error** — the SDK early-returns on `isNaN(value)` and the
host drops it again. Each call still charges the event budget, including
NaN-dropped ones.

Plot names double as the screener/alert scalar bag (`name -> f64`).

## `draw` — primitives

```ts
enum Shape  { Circle = 0, Square = 1, Triangle = 2, ArrowUp = 3, ArrowDown = 4, Cross = 5 }
enum Stroke { Solid = 0, Dashed = 1, Dotted = 2 }
function rgba(r: i32, g: i32, b: i32, a: i32 = 255): i32   // packs 0xRRGGBBAA

namespace draw {
  function marker(time: i64, price: f64, shape: Shape, color: i32, sizePx: f64 = NaN, id: string = ""): void
  function line(t1: i64, p1: f64, t2: i64, p2: f64, color: i32, width: i32 = 1, style: Stroke = Stroke.Solid, id: string = ""): void
  function box(t1: i64, p1: f64, t2: i64, p2: f64, fill: i32, border: i32 = 0, borderWidth: i32 = 0, id: string = ""): void
  function label(time: i64, price: f64, text: string, color: i32, bg: i32 = 0, hasBg: bool = false, id: string = ""): void
  function remove(id: string): void
}
```

**Four primitives + remove.** No `hline`, `fill`, `trendline`, `circle`,
`polyline`, `table`, `plotshape` / `plotchar` / `bgcolor` — even though the Rust
`ChartPrimitive` enum has richer variants; those are native-Rust-only.

- **`id` decides stateful vs stateless.** Non-empty → `primitiveUpsert`
  (re-emitting the same id moves/updates it); empty (the default) → a one-shot
  `primitive`, append-only. **Always pass an id** — anonymous primitives are keyed
  by event-stream index and survive a history recompute only because strategies
  are deterministic.
- `na` price anchor draws nothing.
- `sizePx = NaN` means "client default" (5 px), **not** a skip.
- Times are **unix seconds** — pair with `barTime()`.
- `borderWidth = 0` = borderless; `hasBg = false` = no label background.
- Bad `shape` / `style` integers **trap**.
- **Pane targeting is not in the ABI** — the wasm `pane` field is always `null`.
  The fixtures use an id-prefix convention (`"osc::" + id`) interpreted by the
  chart bridge; nothing enforces it.

## `strategy` — orders

```ts
enum Side { Long = 0, Short = 1 }

namespace strategy {
  function long(groupId: string, qtyPctEquity: f64 = 100, tp: f64 = NaN, sl: f64 = NaN): void
  function short(groupId: string, qtyPctEquity: f64 = 100, tp: f64 = NaN, sl: f64 = NaN): void
  function order(groupId: string, side: Side): Order
  function close(groupId: string): void
  function closeAll(): void
}

class Order {
  marketEntry(weight: f64 = 1.0): Order
  limitEntry(price: f64, weight: f64 = 1.0): Order
  stopLimitEntry(stop: f64, limit: f64, weight: f64 = 1.0): Order
  takeProfit(price: f64, weight: f64 = 1.0): Order
  stopLoss(price: f64): Order
  qtyFixed(value: f64): Order
  qtyPercentEquity(value: f64): Order
  qtyRiskBased(riskPct: f64): Order
  cancelOnTpBeforeFill(value: bool = true): Order
  submit(): void
}
```

**No `strategy.entry` / `exit` / `cancel` / `position_size` / `opentrades` /
`equity`.** There is **no way to read position state from a script** — orders are
fire-and-forget events; the backtester owns the ledger.

### What `strategy.*` actually does

**No live trading, ever.** Per `packages/coinray_script/docs/strategy-engine.md:28`:
*"scripts emit events; consumers (backtester / scanner) decide what to do with
them."* Nothing routes an order event to an exchange.

The one Altrady signal-bot integration (`src/alerts/altrady.rs`) is fed by
**alert message text** containing JSON `{direction, entry, stop, target, ltf,
shift_time}` — an author who wants a bot to trade writes that into `alert(...)`,
**not** `strategy.*`.

### SDK call → host import → event

| SDK call | host import | event |
|---|---|---|
| `strategy.long` / `short` | `order_submit_simple` | `orderGroupSubmit` with one `market` entry |
| `Order.submit()` | `order_submit_json` | `orderGroupSubmit`, parsed + validated |
| `strategy.close(id)` | `order_close` | `orderGroupClose` |
| `strategy.closeAll()` | `order_close_all` | `orderGroupCloseAll` |
| `alert(...)` | `emit_alert` | `alert` |
| `plot` / `plotPane` | `plot` / `plot_pane` | `plotValue` |
| `draw.*` **with** id | `plot_marker/_line/_box/_label` | `primitiveUpsert` |
| `draw.*` **without** id | same | `primitive` |
| `draw.remove(id)` | `primitive_delete` | `primitiveDelete` |
| `log.*` | `log` | **nothing** (server) / `{kind:'log'}` (browser) |

`orderGroupIncrease` / `orderGroupReduce` / `column` / `snapshot` /
`publishSetup` / `deleteSetup` exist in the Rust `Event` enum but have **no wasm
ABI binding** — native strategies only.

Wire JSON (`strategy/event.rs`, `#[serde(tag="kind", rename_all="camelCase")]`,
`time` = unix seconds):

```jsonc
{"kind":"orderGroupSubmit","groupId":"stobb_long","time":1700000000,"direction":"long",
 "entries":[{"kind":"market","weight":1.0},
            {"kind":"limit","price":99.0,"weight":0.5},
            {"kind":"stopLimit","stop":101.0,"limit":101.5,"weight":0.5}],
 "takeProfits":[{"price":102.0,"weight":0.5}],
 "stopLoss":97.0,
 "qty":{"kind":"percentEquity","value":100.0},   // omitted when None (Rust) / null (browser)
 "cancelOnTpBeforeFill":true}                     // omitted when false (Rust) / false (browser)
```

**Order validation is strict:** every price and qty must be finite or the
instance **traps** — unlike a `plot` gap, a NaN here would drive a real trade off
garbage. `qtyRiskBased` **requires** a `stopLoss` or the submission is rejected.

Resolution rules (`strategy/backtest/mod.rs`): events from bar N apply at bar
**N+1's open** (Pine `process_orders_on_close = false`); an intrabar TP+SL race
resolves **pessimistically — SL wins**, with no flag to change it. Defaults:
`initial_capital 1_000_000`, `commission_pct 0.0`, `pyramiding 1`,
`default_qty PercentEquity(100)`, `max_leverage 10.0`.

## Lifecycle, alerts, logging

```ts
function na(value: f64): bool        // value != value
function isNewBar(): bool
function barIndex(): i64
function barTime(): i64              // unix SECONDS

function declareAlert(name: string): void
function alert(name: string, message: string = ""): void

namespace log {
  function debug(message: string): void   // level 0
  function info(message: string): void    // 1
  function warn(message: string): void    // 2
  function error(message: string): void   // 3
}
```

- **`na(x)` is `x != x`. There is no `nz()`**, no `na` constant — write `NaN`.
  No `fixnan`, no `ifelse`.
- **Gate all persistent-state mutation and all alerts on `isNewBar()`** — the
  single most important idiom, because `onBar` re-runs on every intra-bar tick.
- `declareAlert` makes a name discoverable to subscribers; `alert()` fires
  regardless, but undeclared names don't appear in the picker. Server-side the
  names come back as `alerts` on the compile response (collected after the
  100-bar validation replay). **`declareAlert` works in the browser host only
  from `@coinrayio/superchart-script` 0.1.8** (`4e4a5175`, 2026-08-26); on 0.1.7
  and below any script that calls it dies at instantiation with
  `LinkError: … "env" "declare_alert"`, taking its plots with it. Client-side
  the names land on `StrategyHost.declaredAlerts` — `compileStrategy` drops the
  server's `alerts` field. See `COINRAY_REST_API.md` → `StrategyHost`.
- `log.*` goes to the IDE console only, never to the chart or alerts, and is
  **not** charged against the event budget.

**Nothing else is exported.** Absent: `timeframe`, `syminfo`, `ticker`,
`bar_index` as a variable, `time()` / `timestamp()` / `dayofweek`,
`request.security` (**no multi-timeframe**), `color.*` constants (use `rgba`),
`math.*` (use AssemblyScript `Math.*`), `str.*` (use `.toString()` / `+`),
`array` / `matrix` / `map` types, tables, `input.*`, `indicator()` /
`strategy()` declarations, `barstate.*`, `strategy.risk.*`, `alertcondition`.

## Sandbox — what a script cannot do

### Compile-time (`packages/strategy_compiler/compile.js:96-119`)

Rejected before asc even runs:

1. Source > **256 KB** per file.
2. **Any import that is not `@coinray/strategy` or a registered relative
   sibling.** No npm packages, no node builtins, no `assembly/*`.
3. **Any occurrence of `@external`** — the crucial one: it stops a script binding
   the raw `env.*` ABI directly and bypassing the SDK's NaN guards.

The compiler runs on a virtual filesystem (`readFile` serves a `Map`,
`listFiles` returns `[]`) — **no filesystem, no network**.

### Module load (`strategy/wasm/mod.rs:255-286`)

Every import must be in module `env`; must export func `on_bar` and memory
`memory`. **No WASI is linked at all** — *"disk and network are unreachable by
construction."*

### Runtime (`WasmLimits::default`, `strategy/wasm/mod.rs:54-66`)

```rust
fuel_per_bar:        50_000_000,
max_memory_bytes:    16 * 1024 * 1024,
max_events_per_bar:  64,
max_string_len:      4096,
wall_clock_per_bar:  Duration::from_secs(10),   // epoch ticks of 250ms → deadline 40
max_order_json:      16_384,
```

Violations: `"exceeded CPU budget (fuel)"`, `"exceeded time budget"`,
`"out-of-bounds memory access"`,
`"event budget exceeded (64 events per bar)"`,
`"guest string of N bytes exceeds the 4096-byte limit"`.

Determinism guards: `cranelift_nan_canonicalization(true)`, `wasm_backtrace` +
`generate_address_map` for trap source mapping.

**A trap kills the instance permanently** — `failure: Option<String>` makes every
subsequent `on_bar` a no-op. Traps map back to `strategy.ts:line:col` via the
line table.

**Browser differences:** the event budget (64), string cap (4096) and order-JSON
cap (16384) are replicated as logical checks; **fuel/epoch metering is absent**,
as is any memory limiter. An infinite loop client-side is stopped only by
terminating the Web Worker.

## `DEFAULT_STRATEGY` — the canonical starter

From `packages/superchart-script/src/language.ts:172-201`. Exported as
`DEFAULT_STRATEGY` from both the package root and `/engine`. The fullest small
example of the API.

```ts
import { src, ta, plot, plotPane, param, config, strategy, na, isNewBar } from "@coinray/strategy"

// How many historical bars to warm up before the first valid signal.
config.warmup(50)

const length = param.int("length", 20, 1, 200)
const mult = param.float("mult", 2.0, 0.1, 5.0)
const rsiLength = param.int("rsiLength", 14, 1, 100)
const oversold = param.float("oversold", 30, 1, 99)

export function onBar(): void {
  // Bollinger Bands on the price pane.
  const bb = ta.bb(src.close, length, mult)
  plot("basis", bb.middle)
  plot("upper", bb.upper)
  plot("lower", bb.lower)

  // RSI on a separate pane.
  const rsi = ta.rsi(src.close, rsiLength)
  plotPane("rsi", rsi, "rsi")

  // Long when RSI is oversold and price closes below the lower band.
  // Risk off the band width: SL 25% of width below entry, TP 50% above (1:2).
  const price = src.close.at(0)
  const width = bb.upper - bb.lower
  if (isNewBar() && !na(width) && !na(rsi) && rsi < oversold && price < bb.lower) {
    strategy.long("bb_long", 100, price + width * 0.5, price - width * 0.25)
  }
}
```

## Other fixtures worth reading

All in `packages/strategy_compiler/fixtures/`:

| File | Lines | Shows |
|---|---|---|
| `stobb.ts` | 68 | The golden-parity fixture, asserted event-identical to the native Rust `StobbStrategy`. Module-level `let` as Pine `var`, a hand-rolled 3-slot shift register, hand-written crossovers. |
| `indicators.ts` | 45 | Exercises every indicator. |
| `draw_orders.ts` | 21 | The canonical drawing + multi-leg order snippet. |
| `divergence_screener.ts` + `zigzag.ts` | 161 + 291 | The only **multi-module** example. `param.options` dropdowns, `config.warmup(500)`, keyed upserts with `draw.remove` cleanup. |
| `trap.ts` | 11 | Source-map trap attribution. |
