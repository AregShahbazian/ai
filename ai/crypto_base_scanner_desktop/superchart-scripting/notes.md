# Scripting tour — notes

Working knowledge of the Coinray scripting feature, gathered by driving the real
app (Playwright, TradingView provider) on `feature/superchart-scripting`.
Companion to `plan.md`, whose capability matrix records what was exercised and
what broke — all 15 rows are now green. Last verified 2026-08-26. Paths are relative to the repo root; the live worktree is
`~/git/worktrees/crypto_base_scanner_desktop-superchart-scripting`.

## Branch topology

- `release-5.4.x` — prod. `feature/superchart-integration` (SC coexists with TV)
  and `feature/coinray-script` (Benoist's scripting, TV-only) both branch off it.
- `feature/superchart-scripting` = superchart-integration + coinray-script,
  merged. Lives only in the worktree above. **This is where the SC port happens.**
- `feature/superchart-integration` is its parent: 5.4 updates and the DS work
  (`feature/superchart-integration-ds-update`, pending SC's design-system and
  feat/drawing-label-and-drag-fixes branches) arrive through it, then get merged
  down into `feature/superchart-scripting`.
- No SC-side scripting code exists **in this app** yet — `super-chart/` has zero
  strategy references. But SC itself is no longer a blank slate: as of 2026-08-26
  SC `main` (`d5298aa`) carries script primitives, the provider-supplied editor
  slot, and `plotPane` sub-pane routing. See "Upstream state" below.

## Where the code lives

**IDE (Altrady's own, chart-agnostic)** — `src/containers/scripts/`
- `panels/script-editor-panel.js` — editor + toolbar. Imports only `CodeEditor`
  and `COINRAY_STRATEGY_LANGUAGE` from `@coinrayio/superchart-script`; the IDE
  itself is Altrady's. The 4 widgets are `script-editor-panel`,
  `script-list-panel`, `console-panel`, `backtest-panel` (+ `backtest-report`,
  `backtest-saved`).
- `scripts-context.js` — all IDE state. `STARTER_SCRIPT` (the empty default),
  `compile()`, `save()`, `loadOnChart()` (= "Run on chart" → compile + push
  preview), `toggleOnChart()` (= "Add to charts", persisted per-device),
  `parseDiagnostic()`, log ring buffer.

**Compile + CRUD** — `src/actions/`
- `coinray-strategy.js` — POSTs source to
  `ta-v2…/api/v1/ta/strategy/user/compile`, returns `{wasm, meta{inputs,
  warmupBars}}`. Stateless, memoised by source+modules. Uses the package's
  `compileStrategy()`.
- `coinray-scripts.js` (CRUD + versions), `coinray-script-backtest.js`,
  `coinray-chart-scripts.js` (per-device "on charts" id list).

**TV adapter (the part that must be re-written for SC)** —
`src/containers/trade/trading-terminal/widgets/center-view/tradingview/`
- `controllers/ci/coinray-strategy.js` — the whole bridge.
  `buildCoinrayStrategyIndicators()` compiles ta + guest WASM, `discover()` runs
  the strategy over synthetic candles to learn plot names/panes, `buildIndicator()`
  emits **one TV study per pane group**, `init()` instantiates
  `TaEngine`/`StrategyHost`, `main()` runs one bar and returns the plot row.
- `controllers/ci/coinray-strategy-drawings.js` — `draw.*` primitives → TV shapes.
- `controllers/ci.js:2710+` — registration; `controllers/setup.js:119` wires it as
  TV's `custom_indicators_getter`.
- `context/use-trading-view.js:315-372` — composes two providers: scripts added to
  charts, plus a caller-supplied preview provider. Also the debug sample fallback.
- `tradingview.js:93-105` — the IDE's preview provider (`getLiveWasm`, `onLog`).
- `script-preview-bridge.js` — auto-adds the registered studies, hot-swaps on a
  value edit, reloads the widget on a structural change.

**The package** — `@coinrayio/superchart-script` (= `packages/superchart-script`
in the coinray_rest monorepo). Two subpaths: the editor (`CodeEditor`, language)
and `/engine` (`StrategyHost`, `TaEngine`, `compileStrategy`, `DEFAULT_STRATEGY`).
Chart-agnostic — shared by TV and SC.

## Script API (verified against the package's completion metadata)

- `config.warmup(n)` — bars of history before the first output.
- `param.int(key, default, min, max)` / `param.float(...)` — become TV study
  inputs, editable in the study settings dialog.
- `src.close` etc.; `ta.sma|ema|rma|wma|vwma|rsi|stdev|highest|lowest|change|mom|
  roc|cmo|cog|mfi|atr|cci|tr` → `f64`, `ta.bb` → `BollingerBands`,
  `ta.macd` → `Macd`. Signature is `(series, length[, extra])`.
- `plot(name, value)` — price pane. `plotPane(name, value, paneName)` — sub-pane.
- `strategy.long(...)` / order submission — **TV cannot render these**; they're
  dropped with a one-time console warning. Orders are a SuperChart-only capability
  and a main reason for the port.
- `onBar()` runs once per candle; `isNewBar()`, `na()` available.

## Gotchas (all reproduced)

**`config.warmup(n)` must be ≥ your longest lookback.** Otherwise the study
registers, appears in the legend, and plots `null` on every bar — no error
anywhere. Verified on identical fresh loads: `sma(20)`+warmup 50 works;
`sma(100)`+warmup 50 → all null; `sma(100)`+warmup 200 works. Engine-side, so it
should carry over to SC.

**~~"Run on chart" is reliable only on a freshly loaded page.~~ FIXED 2026-08-26.**
The real cause was not the hot-swap path: `loadOnChart` only compiled when
`compiledWasm` was null, and editing never cleared it — so every re-run re-pushed
the *first* compile's bytes and meta. Identical bytes → identical `structureKey`
→ no reload, and the hot-swap's `cur !== this._loadedWasm` check was false too,
so nothing at all happened. `runBacktest` had the same bug. Now fingerprinted on
`compileCacheKey(source, modules)`; helper-only edits invalidate it too.

**Registration only reaches TV at widget creation** via `custom_indicators_getter`.
A structural change needs the chart reload that `script-preview-bridge.js:37`
triggers; without it TV keeps a stale definition. `structureKey` covers inputs +
warmup only — **not the plot set and not the script name**, so adding a plot, or
switching to a different script with the same inputs and warmup, still leaves a
stale registration. Same root cause made "Add to charts" appear to do nothing
until a widget rebuild (fixed: `onChartScriptsChanged` now has a subscriber).

**A `draw.*`-only script never runs on TV.** With no `plot()` call the study has
no plot series and TV never instantiates it — no error anywhere. Add one plot.

**A plot can hide under an existing indicator.** `sma(20)` lands exactly on the
Bollinger basis (BB middle *is* SMA 20). Check the legend value before concluding
a script is dead.

**The empty default script draws nothing** — bare `onBar()`, no `plot()` calls.
Correct, not a bug.

**`rgba()`'s 4th argument is alpha**, not a colour channel: `rgba(0,0,0,0)` is
fully transparent, which reads as "my colour edit did nothing".

**`Shape.Circle` / `Shape.Square` are broken on TV** — they map to TV's `circle`,
a 2-point shape, but the bridge creates it single-point: `Error: Wrong points
count for circle. Required 2`, once per marker. Shape fidelity is lossy in
general: `square`→circle, `triangle`→arrow_up, and `cross` renders as a flag.

**Always pass an `id` to `draw.*`.** Keyed primitives upsert; anonymous ones are
keyed by position in the event stream, so they are torn down and recreated
whenever the stream shifts — visible flicker on the forming bar.

## Debugging

- `[coinray-strategy] registered N strategy indicator(s)` — `controllers/ci.js:2716`,
  once per chart load. N counts pane groups, not scripts.
- `[coinray-strategy] init "<name>" ok {plots, warmup, params}` — study
  instantiated. **Absent = the study never ran**; the strongest failure signal.
- `[coinray-strategy] "<name>" bar {bars, plotEvents, values}` — per-bar run.
- These logs are Benoist's, shipped in `coinray-strategy.js`.
- `window.DEBUG.scripts` — the whole live Scripts context (`mine`, `selected`,
  `files`, `preview`, `compiledMeta`, `logs`, `chartScriptIds`, plus callables
  `open(script)`, `compile()`, `loadOnChart()`, `runBacktest({symbol, resolution,
  from, to, params, config})`). Added 2026-08-26; re-assigned on every render.
  `runBacktest` wants `from`/`to` as **RFC 3339 strings** — unix ints come back
  as a 500, not a 422.
- `chart.exportData()` in the console gives one column per plot; `null` there
  proves the plot, not the rendering, is at fault.
- `localStorage.coinrayStrategies = "true"` + reload loads three built-in samples
  (Default Strategy, Drawing Test, Smart Money) — only when no script is added to
  charts (`use-trading-view.js:340-359`). Good known-good reference; turn it off after.
- `DEFAULT_STRATEGY` from `@coinrayio/superchart-script/engine` is a Bollinger +
  RSI + long-entry demo — the fullest small example of the API.

## Working test script (verified on TV)

Two EMAs on the price pane + an RSI sub-pane; registers as two studies
(`Untitled script`, `Untitled script (rsi)`).

```ts
import { src, ta, plot, plotPane, param, config } from "@coinray/strategy"

config.warmup(250)

const fast = param.int("fast", 20, 1, 200)
const slow = param.int("slow", 100, 1, 200)

export function onBar(): void {
  plot("fast", ta.ema(src.close, fast))
  plot("slow", ta.ema(src.close, slow))
  plotPane("rsi", ta.rsi(src.close, 14), "rsi")
}
```

Last-bar values when verified: fast `64157.18`, slow `63660.67`, RSI `57.58`.

## Upstream state (2026-08-26)

Both blockers that stood in front of the port are gone.

- **SC `main` = `d5298aa`.** The old `feat/wasm-script-provider-example` branch
  was not merged (203+ commits of divergence, and it predated the design-system
  migration); it was **re-ported** onto a fresh branch off `main` as three
  commits: script primitives + editor slot, removal of SC's built-in script
  editor, and `plotPane` sub-pane routing (separate so it stays revertable).
  `main`'s `dist-enterprise` now exports `PrimitiveSnapshot`, `ScriptPrimitive`,
  `PrimitivePoint`, `MarkerShape`, `ScriptEditorComponentProps`, `onPrimitives?`
  and `EditorComponent`.
- **`@coinrayio/superchart-script@0.1.8`** is published, adding `env.declare_alert`
  to the browser `StrategyHost`. Before it, any script calling `declareAlert()`
  compiled server-side then died client-side with a `LinkError` — plots included.
  Note its publish CI is disabled: the package's SC devDep is a `link:` to a
  local `dist-enterprise`, which no runner can resolve, so releases are manual
  (`pnpm run build && npm publish`, needs a `write:packages` PAT).

## Open / unverified

- The 5.4 → superchart-integration merge dropped a
  `flexLayout.global.tabSetTabStripHeight = FLEX_LAYOUT_TAB_STRIP_HEIGHT` line
  (`trading-layouts-controller.js`, `correctLayoutOnce`) because the SC branch no
  longer exports that constant. Test old saved custom layouts for wrong tab-strip
  heights; if SC needs the patch, it needs its own constant.
- **`param.options` is rejected by the deployed compiler.** It exists in
  coinray_rest master (`sdk/index.ts:283`, added `975b1598`) but the deployed
  `strategy_compiler` predates it: `Could not find function or function reference
  'param.options'`. Needs a redeploy, not a code change.
- SC's new primitive rendering has **not been seen in a browser** — it is
  unit-tested (14/14) and typechecks, but nothing in this app feeds it yet.
- How orders should map onto SC is still open. SC renders plots and primitives;
  orders are not a chart concept there either, so the port must choose between
  `executeAsBot`/`BotSignal` and drawing entry/TP/SL as primitives itself.
- Three SC host-side gaps confirmed from source: no way to suppress SC's `fx`
  button (shown iff `scriptProvider` is set), nothing on `main` reads
  `scriptProvider.language`, and `useChartState` is not exported so hosts cannot
  read/write chart preferences.
