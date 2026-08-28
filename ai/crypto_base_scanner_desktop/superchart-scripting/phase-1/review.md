# Phase 1 review — spine [sc-script-spine]

Verification for [prd.md](prd.md). Emphasis is **breadth**: one pass per
capability, enough to prove nothing regressed and the SC spine holds. Deeper
poking happens manually on top of this.

## Test scripts

Saved scripts (account `areg`, Scripts IDE → Open) already cover the 15-row
matrix one-for-one — the TV regression suite needs no new material.

| Matrix row | Saved script | Used for |
|---|---|---|
| 1 `plot` | `test` (1% probe, `warmup(1)`), `sma`, `probe-b` | SC + TV |
| 2 `plotPane` | `line-and-pane` (ema fast/slow + rsi sub-pane) | SC + TV |
| 3 `param.*` | `param` (int/float/bool_) | TV only (phase 2 on SC) |
| 4-8 `draw.*` | `draw.line`, `draw.marker`, `draw.box`, `draw.label`, `draw.remove` | TV only |
| 9 `log.*` | `log` | TV only |
| 10 alerts | `declareAlert` | TV only |
| 11-12 orders + backtest | `strategy.orders` | TV only |
| 13 multi-module | `multi-module` (+ `./helper`) | TV only |
| 14 save/versions | `multi-module` (v2), `test` (v4) | TV only |
| 15 "Add to charts" | `sma` | TV only |

### Added

**`probe-b`** (`a9145545-6015-4877-ae4d-b1ecb6e3b160`, v1, saved 2026-08-28) —
a copy of `test` with offset `1.02` and a different script name. Same inputs,
same `warmup(1)`, same plot count, so the two are indistinguishable to
`structureKey`. Exists purely to catch that collision class (matrix row 5):
switching `test` → `probe-b` and re-running must swap the line on **both**
providers.

No other new script needed. Plot-set and pane-layout changes are tested by
editing `test` in the editor without saving (add a second `plot()`, then wrap
one in `plotPane()`).

## Implementation status (2026-08-28)

- **cbsd Part A — done.** Neutral `chart-bridge` (`context.js`, `use-script-run.js`);
  TV run-state moved to `…/tradingview/scripts/`; `scripts-context.js` no longer
  holds `preview` / `previewStudies` / `registeredPreviewKey` / `pushPreview`;
  bridge mounted in `trading-terminal.js`. ESLint clean.
- **cbsd Part B — done and running.** Provider construction, renderer and
  `ChartController` pass-throughs are in; verified live after Areg rebuilt SC's
  `dist-enterprise` bundle.
- **Bug found and fixed during the first SC run.** `sc-script-provider` built
  the compile URL from `altradyConfig.apiEndpoint`; the compiler lives behind
  `coinrayConfig.apiEndpoint`. The app host answered `200 text/html`, surfacing
  as `compile failed: compiler returned non-JSON (status 200)`. Fixed by
  extracting one shared `strategyCompileEndpoint(state)` in
  `actions/coinray-strategy.js` — both paths now resolve the same URL, so this
  cannot drift again.
- **Incidental find.** `runBacktest`'s dep array referenced `pushPreview` ~55
  lines before its `const` — a temporal-dead-zone access that only stayed
  harmless because Babel downlevels `const` to `var`. Gone with the refactor.

## Verification

Section A items 1-13 were run twice: once by Areg manually, once by Claude via
Playwright against the live dev server. Scripts exercised in phase 1: `test`,
`probe-b`, `line-and-pane`, `sma`.

**Re-run 2026-08-28 against SuperChart `2250192`** (its post-review amend, which
changed removal-notice timing, added the disposed rejection, made unknown-id
removal a pure no-op, and reordered dispose). Every section A item still passes,
console clean throughout: items 1, 4, 6, 10 (plots, panes, edit-and-re-run,
script switch); 7 (ten re-runs, count 1 every time); 8 and 9 (plot-set and
pane-layout changes, no orphan pane); 11 (legend ✕, and a fresh run works
after); 11b plus the race guard (`removed before start`, running indicator
untouched); 12 and 13 (resolution and symbol); 3 and 5 (scroll-back 501 → 1202
with the SMA still matching an independent calculation exactly); 2 (bar close).

`[ ]` open · `✅` verified by me · `✅ (agent-verified)` verified by a subagent.

### A. SC spine — R1-R4

1. ✅ Provider = SuperChart. Open `test`, **Run on chart** → one line above price, spanning visible history. (`SCRIPT_1` on `candle_pane`, single `probe` figure; screenshot confirmed.)
2. ✅ On 1m: one bar close → bars +1 and last timestamp advanced exactly 60 000 ms, with the new bar carrying a plotted value. (The just-closed bar's value does shift between snapshots — it was the forming bar, still taking ticks — which is correct, not drift.)
3. ✅ `setVisibleRange` back 200 bars → dataList 501 → 1202, first bar moved back ~29 days, `loadHistoryBefore` recomputed across the whole extended series (values present from index 0), and the last bar's value was byte-identical before and after — same series, no gap, no re-fetch of anything else.
4. ✅ Open `line-and-pane`, run → `SCRIPT_2` on `candle_pane` + `SCRIPT_2_rsi` on its own `rsi` pane.
5. ✅ `sma` (length 20) on SC: plotted `79756.8575`; SMA computed independently from the chart's own `getDataList()` closes: `79756.8575`. Exact match. (Checked against the chart's candles rather than TV — TV's charting library exposes no public API to read a study's plotted values, so this is the stronger available check.)
6. ✅ Edited `test` (`1.01` → `1.05`), re-run → line moved (`78854.75` → `82030.20`, both = 1.0x x close); `SCRIPT_1` replaced by `SCRIPT_2`, exactly one indicator. Also verified earlier on `line-and-pane` (rsi 14 → 7).
7. ✅ Ten arithmetic re-runs (`1.01` … `1.10`): indicator count was 1 after every single one, ending at `SCRIPT_12`. No reload. (Dead klinecharts templates accumulate invisibly — known, out of scope; this checks the *chart*, not the registry.)
8. ✅ Second `plot()` added → one indicator (`SCRIPT_13`) with two figures `probe`, `probe2`; both lines visible in the screenshot.
9. ✅ Moved `probe2` to `plotPane(..., "extra")` → `SCRIPT_14` on `candle_pane` + `SCRIPT_14_extra` on pane `extra`. Moved back → single `SCRIPT_15` with both figures; screenshot shows the price pane at full height, no orphan pane.
10. ✅ Switched `test` → `probe-b` (identical inputs, warmup and plot count — the TV `structureKey` collision case) and re-ran → `SCRIPT_15` gone, `SCRIPT_16` in its place, plotted `79851.72` = 1.02 x close. The collision class cannot occur on SC: there is no `structureKey`, every run is a full remove-and-add. Still to be run on **TV**, where it can.
11. ✅ Clicked the ✕ in the pane legend (canvas hit area at the indicator row) → `SCRIPT_16` removed, indicator list empty, no errors. The next run worked normally, so the host dropped its handle.
11b. ✅ Two `loadOnChart()` calls back to back, un-awaited → both settled fulfilled, exactly one indicator (`SCRIPT_2`), zero `console.error` calls. The `'removed before start'` path needed React taken out of the loop to reach: calling `addScriptIndicator()` and then `removeScriptIndicator()` on its id synchronously from the console rejected the add with exactly `removed before start`, left the in-flight script off the chart, and did not disturb the indicator already running. SC's race guard verified.
12. ✅ Resolution 1h → 4h → re-ran as `SCRIPT_4*`, two templates, nothing stale. Re-confirmed 1h → 1m → 1h during item 2.
13. ✅ BTC → ETH (same tab) → re-ran as `SCRIPT_5*`, two templates.
14. ✅ Switch TradingTab and back → no duplicate indicator, no throw. (Areg)
15. ✅ Close the Scripts widget while a script is running → no leak, no throw. (Areg)
16. ✅ Switch trading layout / unmount the chart → clean, no error in console. (Areg)

### B. TV regression — R5 (hard gate)

Provider = TradingView. One run per script, first-run **and** one re-run.

**Verified by Areg, 2026-08-28: every saved script works on TV, no regression.**
R5's hard gate is met — the chart-bridge refactor moved TV's run state out of
`scripts-context.js` without changing its behaviour.

17. ✅ Row 1 — `test`, `sma` (also checked post-refactor via Playwright: `loadOnChart()` → runId 1 → study "test" on the chart, clean console)
18. ✅ Row 2 — `line-and-pane`
19. ✅ Row 3 — `param` (dialog shows int/float/bool_)
20. ✅ Row 4 — `draw.line`
21. ✅ Row 5 — `draw.marker`
22. ✅ Row 6 — `draw.box`
23. ✅ Row 7 — `draw.label`
24. ✅ Row 8 — `draw.remove`
25. ✅ Row 9 — `log` → Console panel, 4 levels
26. ✅ Row 10 — `declareAlert` instantiates (no `LinkError`)
27. ✅ Row 11 — `strategy.orders` plots + the "TradingView cannot render" warning
28. ✅ Row 12 — backtest `strategy.orders` → report, equity curve, trade arrows
29. ✅ Row 13 — `multi-module`; edit `helper` only, re-run → recompiles
30. ✅ Row 14 — save a version, open an older one → entry **and** helper restored
31. ✅ Row 15 — "Add to charts" `sma` → appears on a chart with no IDE widgets

### C. Coexistence and seam — R6, R7

32. ✅ SC → TV → SC with no reload, running the script after each toggle: SC indicator, TV study `test`, SC indicator again. Zero `console.error` calls across all three.
33. ✅ `/charts` on SC: four charts mount, **none** carries a `scriptProvider` and none shows a Script button — matching the phase-1 decision that only the TT main chart runs scripts. `/charts` on TV: four widgets, clean console. TT on both providers covered by item 32.
34. ✅ `grep -rn "chartProvider|superchart|tradingview" src/containers/scripts/` → one hit, and it is the editor package import (`CodeEditor`, `COINRAY_STRATEGY_LANGUAGE` from `@coinrayio/superchart-script`), used regardless of provider. No chart-provider branching in the IDE.
35. ✅ `scripts-context.js` **shrank** 520 → 506 lines; the bridge is 91 lines in its own folder.
36. ✅ The provider handed to SC exposes `language`, `defaultScript`, `compile`, `executeAsIndicator`, `loadHistoryBefore`, `stop`, `dispose` — and no `EditorComponent`. Clicking SC's Script button changes nothing: page text identical before and after, no editor mounted (the two CodeMirror nodes present are Altrady's own IDE). Button renders but is inert, as designed; removing it is phase 3.

### Known issue — SC toolbar overflows (not ours to fix)

At the terminal's chart-widget width the SC toolbar's content is ~495px inside a
331px box, so it spills over the neighbouring controls and Playwright cannot
click the Script button (a gear icon intercepts the pointer). Measured by
removing the Script button from the DOM: content drops to ~423px — still wider
than the box. **So the overflow predates this work; the Script button adds ~72px
to it.**

**Decision (Areg, 2026-08-28): known issue, not fixed here.** Another developer
owns it; we work around it. Recorded so a future reader doesn't mistake it for
scripting fallout — and it still strengthens the phase-3 case for suppressing
the Script button, which would give back ~72px for free.

### Post-amend check — SC's `'Superchart disposed'` rejection (2026-08-28)

SC amended its commit (`2750afa` → `2250192`) so `addScriptIndicator` rejects
with `'Superchart disposed'` when the chart is torn down before or during
execution. Concern was that this would surface as console noise from
`use-script-run.js`'s catch on every teardown.

Verified against the rebuilt bundle, with the compile cache warmed so the add
actually reached SC before the teardown: disposing the chart mid-flight (by
switching provider) rejected the raw promise with exactly `Superchart disposed`,
and the host logged **nothing**. React's effect cleanup runs before the chart
disposes, so `cancelled` is already true and the catch is skipped. No change
needed.

### D. Known-absent (phase 1 non-requirements)

Confirm these fail *cleanly* on SC — no crash, no half-rendered indicator.
**All five verified by Areg, 2026-08-28.**

37. ✅ `draw.line` on SC → plots render, primitives absent, no throw. (Areg)
38. ✅ `param` on SC → defaults used, no settings dialog, no throw. (Areg)
39. ✅ `log` on SC → Console panel silent, no throw. (Areg)
40. ✅ `multi-module` on SC → the compile is rejected and nothing renders; the chart is unaffected. Exact message:

    [scripts] failed to run on chart Error: compile failed:
    import "./helper" does not resolve to a known module — provide it as an extra module

    This is the documented `run.modules` drop (design.md; code-review round 1):
    SC compiles from source and its provider takes no modules parameter, so
    helper imports are phase-2 work. It fails cleanly and the message is
    accurate — which is what this item asks for. The wart is that it is
    **console-only**: from the UI the indicator simply never appears. Surfacing
    it to the user belongs with the phase-2 modules work.
41. ✅ `strategy.orders` on SC → plots render, orders silently dropped. (Areg)

## Round 1: code review of the cbsd commit (2026-08-28)

Reviewed `b56acc3ea`. Seven findings; five fixed, two documented. Amended into
the same commit per the one-commit-per-phase rule.

### Bug 1: a remounted chart silently loses the running script
**Root cause:** `sc-script-renderer` passed only `[coinraySymbol, resolution]` to
`useScriptRun`. `chartController` resolves through `ChartRegistry` and is
`undefined` on the first render of a chart whose lifecycle effect hasn't run
yet, so `apply` returned `null` and nothing ever retried — the later
`readyToDraw` re-render doesn't change any dep.
**Trigger:** a script running while the chart widget remounts — provider switch,
FlexLayout tab or layout change.
**Fix:** `chartController` added to the deps. Verified: with a run active,
SC → TV → SC now re-applies the indicator (it was empty before the fix).
**Files:** `…/super-chart/scripts/sc-script-renderer.js`

### Bug 2: scroll-back stops working after switching to a younger market
**Root cause:** the `earliest` guard lives in an effect keyed only on
`[chartController]`, but the controller survives symbol and resolution changes
(TT mutates the tab in place). An `earliest` remembered from a long-history
market makes every later `first >= earliest` check short-circuit.
**Fix:** effect keyed on `[chartController, coinraySymbol, resolution]`.
**Files:** `…/super-chart/scripts/sc-script-renderer.js`

### Bug 3: compile endpoint captured at chart construction
**Root cause:** auth was resolved per request precisely because a chart outlives
its token — but the endpoint had the same lifetime problem and was captured
once. `coinrayConfig.apiEndpoint` changes on config update and logout reset.
**Fix:** `fetchImpl` now resolves the endpoint per request too. It is only ever
called for the compile request, so overriding the URL is safe.
**Files:** `…/super-chart/scripts/sc-script-provider.js`

### Bug 4: backtest auto-add no longer cleared the console
**Root cause:** the removed `pushPreview` called `clearLogs()` on every push.
`loadOnChart` kept it; `runBacktest`'s auto-add path lost it, so the previous
run's output accumulated under the new one. A regression I introduced.
**Fix:** `clearLogs()` restored on that path.
**Files:** `src/containers/scripts/scripts-context.js`

### Bug 5: dead `clear()` on the bridge
**Root cause:** written, memoized and documented, never called.
**Fix:** removed, along with a stale comment on `loadOnChart`'s return value.
**Files:** `src/containers/scripts/chart-bridge/context.js`

### Documented, not fixed
- **`run.modules` is dropped on the SC path.** SC compiles from source and its
  provider takes no modules parameter, so a script with helper imports runs on
  TV but fails here. Already a phase-1 non-requirement (helper modules are
  phase 2); now carries a comment at the drop site. The failure is quiet — it
  surfaces only as a `console.error` — which phase 2 should improve.
- **`useScriptRun` spreads its deps array.** That opts the effect out of
  `react-hooks/exhaustive-deps`, which is how bug 1 slipped through. The rule
  isn't configured in this repo, so a disable comment would itself error; the
  contract is documented in the hook's header instead.

### Verification
1. ✅ ESLint clean on every touched file.
2. ✅ Bug 1 fix verified live (remount re-applies the script).
3. [ ] Bugs 2-5 not separately exercised — reasoned fixes, no live repro.
