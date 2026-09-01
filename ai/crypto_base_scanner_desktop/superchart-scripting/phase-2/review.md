# Phase 2 review — parity [sc-script-parity]

Verification for [prd.md](prd.md). Same emphasis as phase 1: **breadth**, one
pass per capability, enough to prove parity holds and nothing regressed. Deeper
poking happens manually on top of this.

Phase 1's review is the baseline — anything it verified must still be true, so
section F is a re-run rather than a fresh proof.

**Round 1 (2026-08-31)** — run against SC's rebuilt `dist-enterprise` plus a
local link of `coinray_rest/packages/superchart-script`, driven with Playwright
against the dev server, the same way phase 1 was.

Legend: `⬜` open · `✅` verified by me · `✅ (Areg)` verified manually ·
`❌` failed · `⚠` partial.

## Test scripts

The saved scripts (account `areg`, Scripts IDE → Open) already cover every row
this phase touches; the TV suite needs no new material.

| Matrix row | Saved script | Used for |
|---|---|---|
| 3 `param.*` | `param` (int/float/bool_) | SC + TV |
| 4 `draw.line` | `draw.line` | SC + TV |
| 5 `draw.marker` | `draw.marker` | SC + TV |
| 6 `draw.box` | `draw.box` | SC + TV |
| 7 `draw.label` | `draw.label` | SC + TV |
| 8 `draw.remove` | `draw.remove` | SC + TV |
| 9 `log.*` | `log` | SC + TV |
| 13 multi-module | `multi-module` (+ `./helper`) | SC + TV |
| 1, 2 (regression only) | `test`, `probe-b`, `sma`, `line-and-pane` | SC + TV |

### To add

**`draw-all`** — the four primitive kinds plus a `plot()` in one script (the
`DRAWING_TEST_STRATEGY` source in `sample-strategies.js`). Two jobs: it is the
one script that exercises all four overlay templates in a single run, and
keyed-per-bar markers make it the scale case — it produced **8025 primitives**
over ~8000 bars in the 2026-08-31 probe. Save it so the scale numbers are
reproducible rather than typed into the console each time.

**`options-param`** — a script declaring an `options` input. Matrix row 3 is
only *partial* on TV (`options` was rejected by the deployed compiler), so
without this the enum case goes untested on both providers.

No other new script needed. Missing-module and bad-syntax cases are made by
editing `multi-module` / `test` in the editor without saving.

---

## A. Primitives on SC — R1

Provider = SuperChart. Run each, then re-run after an edit.

1. ✅ **`draw.line`** — the line renders, in the right place, and follows its anchor bars.
    Verified 2026-08-31 via `draw-all`: `scriptLine` on the chart, anchored correctly.
2. ✅ **`draw.marker`** — markers on the right bars; `circle`, `square`, `triangle`, `cross` all render as themselves (TV collapses these — SC should not).
    *How:* edit `draw.marker`'s script so successive markers use `Shape.Circle`,
    `Shape.Square`, `Shape.Triangle` and `Shape.Cross` (e.g. pick by
    `barIndex() % 4`), run, and look at four consecutive markers. Each must be
    its own shape — on TV `square` becomes a circle, `triangle` an arrow and
    `cross` a flag, and SC is expected to do better, not the same.
    Passed 2026-08-31 (Areg), after two SC fixes. All six shapes drawn from one
    script (`barIndex() % 6`, 102 of each) render distinctly, with colour and
    size honoured.
    Two bugs closed here. Markers rendered blue regardless of colour — the
    figure-`styles` thunk (round 1). And `arrowUp`/`arrowDown` drew
    **triangles** rather than TV's trade-arrow glyph, collapsing them with
    `Shape.Triangle`; SC now shares `tradeLine`'s arrow geometry
    (`wideArrowGeometry`, tip anchored at the price, body extending away), so
    arrows match TV and `triangle` stays a triangle.
    Process note: I first marked this passed off a screenshot while the app was
    still running a `dist-enterprise` that predated the fix. Verify a glyph
    change against the built bundle, not the pixels.
3. ✅ **`draw.box`** — box spans the right range; fill and border colours match, alpha respected.
    `scriptBox` renders with fill and border; alpha respected. Confirmed by Areg 2026-08-31 after the styling fix.
4. ✅ **`draw.label`** — text renders at the right point, both `hasBg` modes.
    `scriptLabel` renders at its anchor point. Confirmed by Areg 2026-08-31 after the styling fix.
5. ✅ **`draw.remove`** — removed ids disappear; a trailing-window script leaves exactly the window.
    *How:* run the saved `draw.remove` script (trailing 10-marker window).
    Count the markers on screen — exactly the window, no older ones left
    behind. No need to wait for a live bar: every run replays history, so the
    pruning has already happened by the time the chart draws.
    Passed 2026-08-31 (Areg): exactly 10 ✕ markers, on the latest 10 candles.
    So removal really deletes rather than overdrawing. `Shape.Cross` also
    renders as an ✕ here, where TV drew it as a flag — and `Shape.Circle` /
    `Shape.Square` threw outright on TV (`Wrong points count for circle`),
    which SC does not.
6. ✅ **Re-run replaces** — an edit-and-re-run swaps the whole primitive set, no ghosts from the previous run.
    Re-ran `draw-all` at 8025 primitives: counts identical afterwards (8022/1/1/1), not doubled.
7. ✅ **Symbol and resolution change** — primitives re-anchor to the new series, none stale.
    *How:* with `draw-all` running, switch BTC → ETH in the same tab, then 1h →
    4h. After each, the box/line/label must sit on the new series' bars, and no
    marker may remain at a price or time from the old one.
    Passed 2026-08-31 (Areg): BTC → ETH and 1h → 4h both re-anchor, nothing stale.
8. ✅ **Removal is complete** — removing the indicator removes every primitive it drew, and nothing else.
    8042 overlays → 17 (the host's own) after `removeScriptIndicator`.

### Scale — the new work

With `draw-all` on a chart scrolled back to several thousand bars.

9. ✅ **Pan and zoom** stay smooth — no visible stutter.
    Measured over 12 programmatic scrolls at 8025 primitives: p90 frame 24 ms, worst 172 ms. Usable, not silky. No baseline captured without the script, so this needs a human eye and a comparison run before it counts as passed.
    *How:* run `draw-all`, scroll back a few thousand bars, then drag-pan and
    wheel-zoom for ten seconds or so. Compare against the same gestures with the
    script removed — the question is whether it feels *different*, not whether
    it is perfect. If it drags, say so and it goes back to SC as tier (c).
    Passed 2026-08-31 (Areg) by eye, with `draw-all` running. My instrumented numbers before SC's batching and the history fix: p90 frame 24 ms, worst 172 ms; the history fix alone took a 5m run from 280k bars to ~600.
10. ✅ **Crosshair** movement stays responsive (hit-testing walks overlays today).
    *How:* with `draw-all` running, sweep the mouse across the chart. The
    crosshair and the OHLC readout must track the pointer without lag — every
    overlay is hit-tested on mousemove today, so this is where 8k bites first.
    Passed 2026-08-31 (Areg): crosshair tracks the pointer with `draw-all` on the chart.
11. ✅ **Full re-run** replacing the whole set does not stall the chart.
    Replace at 8k did not stall the chart; the swap completes with no duplicate overlays.
12. ✅ **Teardown** is not perceptible. Baseline to beat: **663 ms** for 8025 overlays, 2026-08-31.
    **663 ms → 6 ms** for 8025 overlays — same chart, same script, before and after SC's batching.
13. ✅ **Numbers recorded** for one run — primitive count, re-run time, teardown time — read off SC's instrumented reconcile path, not inferred.
    8025 primitives (8022 markers + box + line + label); teardown 6 ms (was 663 ms); re-run replaces with no duplication; pan p90 24 ms / worst 172 ms.

### Leaks

14. ✅ **Object tree** — script primitives do not appear in it.
    SC filters via an `isScriptOverlay` predicate and unit-tests it; not yet confirmed in the UI. Persistence is clean — see 16.
    *How:* open the chart's object/drawing list from the toolbar with `draw-all`
    running. It must show only your own drawings — none of the 8000-odd script
    markers, and no `scriptBox`/`scriptLine`/`scriptLabel` entries.
    Passed 2026-08-31 (Areg): script primitives absent from the object tree. SC filters them with an `isScriptOverlay` predicate.
15. ✅ **Drawings export** — contains none of them.
    Same as 14 — filtered and unit-tested in SC, UI check outstanding.
    *How:* export drawings (toolbar → export/share drawings) with `draw-all`
    running and inspect the output. Script primitives must not be in it.
    Passed 2026-08-31 (Areg): script primitives absent from a drawings export.
16. ✅ **Not persisted** — reload the page and they are gone with the script.
    No key in persisted state matches `script(Marker|Box|Line|Label)` after a run with 8025 primitives.

---

## B. Params on SC — R2

17. ✅ **`param` on SC** — the settings dialog lists int/float/bool_ inputs with their names, defaults and min/max.
    `metadata.settings` arrives as `[{id:"len", type:"number", defaultValue:20, min:2, max:200, step:1}, {id:"mult", type:"number", min:0.1, max:5}, {id:"on", type:"boolean", defaultValue:true}]`, and the script renders.
18. ✅ **`options-param`** — the enum renders as a picker with the declared options.
    Passed 2026-09-01 (Areg + me). `metadata.settings` carries
    `{id: "source", type: "select", defaultValue: "0", options: [{value: "0", label: "close"}, … "open", "high", "low"]}` —
    labels intact, index-valued as the language defines.
    **Matrix row 3 is no longer partial:** `param.options` now *compiles*. The
    deployed ta-v2 rejected it in phase 1, which is why row 3 has carried a ⚠
    since; it does not any more. New saved script `options-param`.
19. ✅ **A change re-runs** — editing a value re-runs the script and the plot/primitives change accordingly.
    `updateScriptIndicator("SCRIPT_15", {len: 100})` → plotted value moved 78333.96 (SMA20) → 78628.18 (SMA100).
    Re-verified numerically 2026-09-01: switching `source` close → high moved
    the plot to **78853.259**, against an SMA20 of the chart's own highs of
    **78853.259**; then `len` 20 → 50 gave **78458.1752** against a computed
    SMA50 of closes of **78458.1752**. Exact both times, so the script really
    re-executes on a settings change rather than relabelling.
20. ✅ **In place** — the change needs no remove-and-add; the indicator keeps its id, its place and its pane.
    Same indicator id before and after, one indicator, 42 ms. The stable-hostId design holds, so the host's handle stays valid.
    Re-confirmed across two consecutive updates 2026-09-01: same id
    (`SCRIPT_SCRIPT_3`) throughout, one indicator, `calcParams` still `[]`.
21. ✅ **Regression: no empty dialog** — it never opens empty, and applying it never writes `calcParams: []` into autosave. Check the persisted chart state, not just the screen.
    `calcParams` stays `[]` on the indicator, and nothing reaches persisted state.
22. ✅ **No-input scripts** — defaults still apply; opening the dialog does nothing harmful.
    Passed 2026-09-01. A script with no inputs reports `settings: []`, plots
    correctly (78646.1395 against an independently computed SMA20 of
    78646.1395), opening its settings dialog throws nothing, and afterwards the
    persisted chart state contains no `SCRIPT_` entry at all.

---

## C. Logs on SC — R3

**All six confirmed by Areg, 2026-09-01**, on top of my instrumented pass.

23. ✅ **`log` on SC** — lines appear in the Console panel, all four levels, styled as on TV.
    All four levels reach the Console panel.
24. ✅ **Level mapping** — `log.debug` shows as DEBUG, not INFO.
    `log.debug` → 0, info → 1, warn → 2, error → 3.
25. ✅ **Timestamps** show the bar time, not wall-clock arrival.
    Bar time in seconds, ascending with the series.
26. ✅ **No tick flood** — one confirmed bar produces one set of lines, not one per tick.
    25 s of live ticks on one forming bar: `logsForwarded` unchanged at 1736 while `snapshotsSkipped` rose 16 → 40. Gating and snapshot-skip both doing real work.
27. ✅ **Ring buffer** still caps (`LOG_CAP = 500`), oldest evicted, IDE stays responsive.
    Capped at 500 with 173228 lines forwarded; the IDE stayed responsive.
28. ✅ **IDE closed** — a script running on SC with the Scripts widget closed accumulates nothing unbounded.
    The emitter's pre-handler ring is capped at 500 — nothing unbounded.

---

## D. Modules and diagnostics on SC — R4, R5

29. ✅ **`multi-module` on SC** — compiles and runs; the helper's exported function *and* exported const both cross.
    Helper compiles and runs on SC; plotted value = close × the helper's factor.
30. ✅ **Helper-only edit** — re-run recompiles and the result changes (the cache-invalidation case).
    Edited only the helper, 1.01 → 1.20: the re-run recompiled, the ratio moved to 1.2000, one indicator (SCRIPT_1 → SCRIPT_2).
31. ⛔ **Linked module** (not a local helper) resolves on SC. — **BLOCKED, backend.**
    A module is a separate script saved with `scriptType: "module"` and imported
    by ref (`@username/name`) through the 🔗 button, rather than added as a local
    file. It cannot be created at all right now:

        POST /api/v3/coinray_scripts → 422
        {"error": ["A username is required to publish a module"]}

    Reproduced 2026-09-01 with `visibility: private` and `public` +
    `openSource: true`, while Settings → Profile shows the username `areg`
    saved. So the scripts service checks a different record from the one the
    profile UI writes, or the value never propagates to it. Nothing in the three
    phase-2 repos touches that endpoint — it belongs to `crypto_base_scanner`.
    It also means *nobody* can publish a module at present, which is worth
    raising independently of this phase.

    **Not held against phase 2.** The module mechanism is proven by item 29: a
    local helper compiles, runs on SC and re-runs on a helper-only edit
    (verified numerically, 1.01 → 1.20). What 31 would add is only that a module
    resolved *by ref* reaches the same compile path — a namespace concern, not a
    scripting one. Re-test when the backend accepts module creation.
32. ✅ **Broken import is visible in the IDE** — delete the helper's import target; the failure surfaces in the UI, not console-only (phase-1 item 40's wart).
    Verified 2026-08-31: the Console panel shows `✗ compile failed: import "./helper" does not resolve to a known module — provide it as an extra module` in red. Re-check once modules land, when it should succeed instead.
33. ✅ **Real line and column** — a syntax error reports the actual position, not `line 1, col 1`, and points at the right file in a multi-file script.
    Verified 2026-08-31: an error in the helper parses to `{file: "helper", line: 2, column: 10}`.
34. ✅ **Right file** — an error in a helper points at the helper, not the entry.
    Passed 2026-08-31 after the `CodeEditor` fix: the marker appears on the
    helper and **persists** (checked at +3.5 s and +6.5 s), and the entry shows
    none. Previously the external diagnostics were wiped ~750 ms later by the
    language extension's own lint source, which owns the same field — and the
    marker that did appear on the entry was that checker's false positive on
    functions imported from a helper module. Both fixed in `superchart-script`.
35. ✅ **Cleared on fix** — fixing the error and re-running clears the diagnostics.
    Fixed the helper and recompiled: `diagnostics` empty, no markers on either file.

---

## E. Seam — R7

36. ✅ **No provider branching** — no `chartProvider` test anywhere in the scripting path (grep, both directions).
    Verified 2026-09-01. `chartProvider` appears nowhere in
    `scripts/`, `super-chart/scripts/` or `tradingview/scripts/`. No provider
    name (`superchart`, `tradingview`, `klinecharts`, `tvWidget`) appears
    anywhere in `chart-bridge/`. In the IDE the only matches are four comments
    saying "TradingView-style" about visual styling, and the `CodeEditor` import
    from the `superchart-script` package — the editor component, not the chart.
37. ✅ **Module placement** — new SC code in `super-chart/scripts/`, new TV code in `tradingview/scripts/`; the bridge carries neither provider's vocabulary.
    Verified 2026-09-01. `chart-bridge/` holds `context.js`,
    `use-script-run.js`, `index.js` and imports nothing but React and itself.
    TV's state and renderer live in `tradingview/scripts/`, SC's provider and
    renderer in `super-chart/scripts/`. Of the eight files this phase touched,
    the only one outside those areas is `tradingview.js`, which mounts TV's
    renderer and wires its log sink — TV's own widget.
38. ✅ **No parameter UI in the IDE** — inputs are edited in the chart's own dialog on both providers.
    Verified 2026-09-01: no parameter UI was added. The only inputs in the IDE
    panels are the script search box, the script-name field, and the *editor*
    settings (font size, line numbers, wrapping) — none of them script inputs.
    Script parameters are edited in the chart's own dialog on both providers.
39. ✅ **Neutral channels** — log delivery and module passing go through the bridge in a shape neither provider's vocabulary leaks into. The TV widget no longer imports the Scripts IDE at all.

---

## F. TV regression — R6 (hard gate)

**All ten passed, verified by Areg 2026-09-01.** The hard gate is met: the
log re-route through the bridge and `superchart-script`'s changes — both of
which sit on the TradingView path too — cost TradingView nothing.

Provider = TradingView. One run per script, first-run and one re-run. All 15
matrix rows, as in phase 1 — this phase changes shared code
(`superchart-script`, the log route), so the gate is re-run in full, not sampled.

*How:* switch the chart provider to TradingView (chart settings modal, or
`toggleChart("tradingview")` in the console), then open each saved script in
turn, **Run on chart**, edit one number and run again. What matters is that
nothing behaves differently from phase 1 — the log route changed underneath
row 9, and `superchart-script` sits on both paths.

40. ✅ **Rows 1-2** — `test`, `sma`, `probe-b`, `line-and-pane`
41. ✅ **Row 3** — `param` (and `options-param`, if the compiler now accepts it)
42. ✅ **Rows 4-8** — `draw.line`, `draw.marker`, `draw.box`, `draw.label`, `draw.remove`
43. ✅ **Row 9** — `log` → Console panel, 4 levels. Verified 2026-08-31 **after** the re-route through the bridge: all four levels arrive with correct numeric levels and bar times, ring buffer caps at 500.
44. ✅ **Row 10** — `declareAlert` instantiates
45. ✅ **Rows 11-12** — `strategy.orders` plots + warning; backtest report, equity curve, trade arrows
46. ✅ **Row 13** — `multi-module`, including a helper-only edit
47. ✅ **Row 14** — save a version, open an older one → entry and helper both restored
48. ✅ **Row 15** — "Add to charts" → appears on a chart with no IDE widgets
49. ✅ **Phase-1 SC spine still holds** — plots, panes, re-run replaces, symbol/resolution change, legend ✕, ten re-runs (phase-1 review section A).

---

## G. Known-absent (phase 2 non-requirements)

Confirm these fail *cleanly* — no crash, no half-rendered indicator.

50. ✅ **Pane-routed primitive** — a `pane::`-prefixed id on SC lands on the candle pane rather than a sub-pane, and nothing throws.
    Verified 2026-09-01 with a script that both plots into a sub-pane and draws
    a line keyed `"osc::mid"`. The sub-pane is created for the plot
    (`SCRIPT_2_osc` on pane `osc`), and the primitive lands on `candle_pane`
    with its colour intact — no throw, nothing on the console. So panes work;
    only *primitive* pane-routing is absent, which is the documented
    non-requirement.
51. ✅ **`strategy.*` on SC** — plots and primitives render, orders silently dropped.
    Passed 2026-09-01 (Areg).
52. ✅ **Backtest on SC** — the report still works; chart trade markers absent (phase 3).
    Passed 2026-09-01 (Areg).
53. ✅ **"Add to charts" on SC** — still the phase-3 gap, no error.
    Passed 2026-09-01 (Areg).

---

## Bugs found in round 1 (2026-08-31)

Three, all found by driving the real app rather than by reading code.
**All three are fixed; none needs a decision.** One is fixed but cannot reach
the browser yet — see 2.

1. **`forwardLogs` blew the stack on any chatty script.** `buffers.logs.push(...logs)`
   spread the entire initial confirmed batch as call arguments; a script logging
   four lines per bar over ~500 bars threw `RangeError: Maximum call stack size
   exceeded` and the whole add failed. Fixed in `superchart-script` (copies the
   newest 500 in a loop; the same shape was de-spread in three `StrategyHost`
   sites). **Fixed and re-verified** in the browser: 173228 lines forwarded, no
   throw, indicator renders.

2. **`buildMetadata` returns `plots: []` when the probed run yields only NaN.**
   `plot("ma", ta.sma(src.close, 20))` **without** `config.warmup` adds
   successfully — an id is returned, no error — and renders nothing;
   `paneId` also degrades to `SCRIPT_N_pane`. Adding `config.warmup(30)` fixes
   it. A parity break: the same script works on TradingView, whose metainfo
   comes from declared plots rather than observed values.

   **Fixed in coinray_rest, but not yet reachable here.** The fix has three
   layers; the third is in the `@coinray/strategy` SDK that the *compiler*
   bundles, and Altrady dev compiles against the deployed `ta-v2` host, which is
   behind (it still rejects `param.options` — that is the same staleness that
   has kept matrix row 3 at ⚠ since phase 1). Until that host is updated, or dev
   is pointed at a locally-run `strategy_compiler`, undeclared-warmup scripts
   keep failing silently in this app.

   No decision needed, and **nothing in this checklist depends on it** — it is
   not one of the 53 items. Deferred as a known gap.

   Also decided during the hunt: **do not give scripts a default warmup.** It
   would make values appear without `config.warmup`, at the cost of diverging
   browser execution from the native engine — an invisible inconsistency traded
   for a visible, explainable one. The fix's scope is killing the
   silent-nothing, so the legend, pane and settings appear and the line is
   simply empty, which is what TV does.

   Worth recording: this cost a wrong diagnosis. Both failing scripts happened
   to use `ta.sma` without warmup, so it was first reported to the SC session as
   a `param` bug. SC is adding a `console.warn` when a script registers zero
   templates — the silent-nothing failure mode is what made it expensive, and a
   host cannot detect it (the add resolves normally).

3. **`CodeEditor` never applies the diagnostics it is mounted with.** Markers
   appear only on a prop change under a living editor, and the applied set is
   the previous one. Invisible until diagnostics became per-file, because
   switching files remounts the editor. One fix attempt landed
   (value-reset path) and did not help; the real cause was found on the third
   pass: `createLanguageExtension` installs its own static-check lint source,
   and a CodeMirror lint source **replaces the whole diagnostics field** on its
   own ~750 ms schedule, wiping externally-applied entries. Every harness
   asserted inside that window, which is why source, dist, jsdom and real Chrome
   all passed while a +3 s probe caught it.

   A second bug fell out of the same hunt: the marker that did appear on the
   entry was that checker's **false positive** on functions imported from a
   helper module — unreachable while scripts were single-file.

   **Both fixed** (external diagnostics moved to their own state field, the
   static source returns the union) and **verified in the browser**: the
   helper's marker persists at +3.5 s and +6.5 s, the entry shows none. Item 34
   passes.
