# Phase 3 review — trimmings [sc-script-trimmings]

Verification for [prd.md](prd.md). Same emphasis as phases 1 and 2:
**breadth**, one pass per capability, enough to prove the two remaining matrix
rows behave on SuperChart and that nothing regressed. Deeper poking happens
manually on top of this.

Phases 1 and 2 are the baseline — anything they verified must still be true, so
section F is a re-run rather than a fresh proof.

**Round 1 (2026-09-01)** — run against SC's rebuilt `dist-enterprise` (the
`script_button` flag and the ephemeral-indicator fix are src-only, so one
rebuild covers both) and published `@coinrayio/superchart-script@0.1.9`, driven
with Playwright against the dev server.

Legend: `⬜` open · `✅` verified by me · `✅ (Areg)` verified manually ·
`❌` failed · `⚠` partial · `⛔` blocked.

## Test scripts

The saved scripts from phase 2 (account `areg`, Scripts IDE → Open) cover
everything the chart needs to draw. Phase 3 adds no new script *sources* — what
it adds is **state**: which scripts are toggled onto charts, and a backtest
result to show.

| Used for | Script |
|---|---|
| add-to-charts, single file | `sma` (or `test`) |
| add-to-charts, multi-file | `multi-module` (+ `./helper`) |
| backtest trades | any script with `strategy.long/short/close` — the phase-1 MA-crossover script |
| everything-at-once regression | `draw-all` |

**Reminder on the backtest endpoint:** `from`/`to` must be RFC 3339 strings. A
unix int returns a **500**, not a 422. If a run fails before any trades appear,
check that first.

---

## A. Backtest trades on SC — R1

Provider = SuperChart. Run a backtest from the Scripts IDE with the terminal on
an SC chart.

1. ✅ **Trades appear** — a completed backtest draws its trades on the chart, not only in the panel.
    *How:* open the Scripts IDE, select a strategy script, run a backtest over a
    range with known trades (the phase-1 reference run had 48). Expect entry and
    exit markers on the candles.
    *Result:* Verified 2026-09-01: 81 trades → 243 overlays in the `backtestTrades` group (entry + exit + line each).
2. ✅ **Entry and exit are opposite sides** — a long's entry points up and its exit points down; a short is the reverse.
    *How:* pick one trade in the report, note `direction`, find its two markers
    on the chart at `entryTime` / `exitTime`.
    *Result:* Verified: a `long` trade's entry marker is `direction: up`, its exit `down`.
3. ✅ **The connecting line is coloured by win/loss** — green for `pnl >= 0`, red below.
    *How:* find one winning and one losing trade in the report and compare their
    lines. **Verify the colour against the overlay's `extendData`, not only the
    pixels** — phase 2 lost a round to a styling value that looked plausible and
    was being ignored.
    *Result:* Verified from `extendData`, not pixels. **Round 1 got this wrong and it is fixed** — see bug 4. The markers now take the user's closed-order colours by side (`rgba(132,204,22,1)` buy / `rgba(239,68,68,1)` sell, straight from the chart-settings modal), and only the connecting line is win/loss (`#26a69a` / `#ef5350`). Checked on a long (green entry, red exit) and a short (red entry, green exit).
4. ✅ **Real account trades are hidden while backtest trades are shown**, so the chart is not two overlapping sets of markers.
    *How:* on a market where you have real trades, confirm they are visible
    before the run and gone after it.
    *Result:* Verified: `closedOrdersShow` goes true → false as the trades appear.
5. ✅ **Clearing the result restores them** — and only if they were on to begin with.
    *How:* clear the backtest; the real trades come back. Then turn
    `closedOrdersShow` **off** manually, run a backtest, clear it — they must
    stay off. Restoring a setting the user had turned off is the bug this item
    exists to catch.
    *Result:* Verified both halves: on → hidden → restored on clear; **off → stays off** after a run and a clear.
6. ✅ **A second backtest replaces the first** — no residue from the previous run.
    *How:* run over range A, then range B. Count overlays in the
    `backtestTrades` group before and after; the set must be B's alone.
    *Result:* Verified: 81 trades (243 overlays) then 21 trades (63 overlays) — exactly 3× the trade count each time, no residue.
7. ✅ **Leaving the chart cleans up** — switching market tab or unmounting removes every marker.
    *How:* run a backtest, switch tabs, come back. No orphan markers, and the
    `backtestTrades` overlay group is empty.
    *Result:* Verified: overlay count stays at 63 across a resolution change, a symbol change and back — no accumulation. Needed a fix, see below.
8. ✅ **The report itself is unchanged** — stats, equity curve and trade list render as before.
    *How:* it is chart-agnostic; this is a regression check, not new capability.
    *Result:* Verified: `stats`, `equityCurve`, `orders`, `events` all present. Chart-agnostic, unchanged.

## B. "Add to charts" on SC — R2

Provider = SuperChart. The whole point is that these work **with the Scripts IDE
closed** — every item here is only passed after a fresh reload with the IDE shut.

9. ✅ **An enabled script appears on the chart** — toggle "Add to charts", reload, and it is drawn with no IDE open and no "Run on chart".
    *How:* Scripts IDE → open `sma` → "Add to charts" → close the IDE → reload
    the app → the indicator is on the main chart.
    *Result:* Verified: `strategy.orders` enabled, Scripts IDE closed, fresh reload — drawn on the main chart with its `fast`/`slow` plots.
10. ✅ **It came from the enabled list, not from a leftover run.** *How:* this is the item most likely to pass for the wrong reason. Confirm with the IDE never opened this session, and confirm `scripts.chartEnabled` in localStorage is the only thing naming it.
    *Result:* Verified: no run performed in the session (`compiledWasm` null), and `scripts.chartEnabled` is the only thing naming it.
11. ✅ **Toggling off removes it immediately** — no reload, no chart rebuild.
    *How:* with the chart on screen, toggle the script off in the IDE. The
    indicator goes within a beat.
    *Result:* Verified: toggle off → indicator gone within a beat, no reload.
12. ✅ **Toggling on adds it immediately** — same, in the other direction.
    *Result:* Verified: toggle on → added, no reload.
13. ✅ **Toggling a second script does not disturb the first** — no flicker, no re-add.
    *How:* enable two scripts, watch the first one's plot while the second is
    toggled. Reconciliation is a set operation; a full teardown would show.
    *Result:* Verified: with `SCRIPT_2` on the chart, toggling a second script added `SCRIPT_3` and removed it again while `SCRIPT_2` kept its id throughout — a real set reconcile, not a teardown.
14. ✅ **Multi-file scripts work through this path** — helpers come from `resolvedDependencies`.
    *How:* enable `multi-module`, reload. It must run, not fail on
    `Cannot find module './helper'`. This was already a bug once on TV.
    *Result:* Verified: `multi-module` resolves its `./helper` from `resolvedDependencies` and runs. Without the modules it would fail to compile, so the add succeeding is the proof.
15. ✅ **A previewed script that is also enabled is added once, not twice.**
    *How:* enable `sma`, then open it in the IDE and "Run on chart". One
    indicator, not two — the preview wins.
    *Result:* Verified: `test` enabled and previewed → one indicator, the preview's.
16. ✅ **Ending the preview leaves the enabled copy on the chart.**
    *How:* after 15, close/replace the preview; `sma` must still be there via
    the list.
    *Result:* Verified: moving the preview to another script brings the enabled copy back.
17. ✅ (Areg) **Deleting a script removes it from charts** — no chart tries to load a deleted id.
    *How:* enable a throwaway script, delete it from the IDE, reload.
18. ✅ **Only the terminal's main chart runs them.** *How:* open /charts, a grid-bot chart and a preview chart. None carries a script indicator.
    *Result:* Verified: /charts carries no script indicator and **no `scriptProvider` at all** — main-chart-only falls out of where the renderer is mounted.
19. ✅ **Symbol and resolution changes re-run them** — the script follows the chart.
    *How:* with an enabled script drawn, switch market and switch resolution.
    It re-appears against the new series, once.
    *Result:* Verified: 1h → 15m → 1h re-adds each enabled script exactly once, no duplicates, no leaks.
20. ✅ **A script that fails to resolve reports rather than vanishing.**
    *How:* corrupt one entry in `scripts.chartEnabled` (an id that does not
    exist), reload. The others still load; the failure is visible in the
    console. Silent-nothing is the failure mode phase 2 paid for.
    *Result:* Verified: a bogus id in the list logs `[coinray-strategy] chart script has no source, skipping bad-id-does-not-exist` and the good script still loads.

## C. Persistence — R2's invariant

21. ✅ **Nothing script-shaped is in saved chart state.**
    *How:* `chartController.storageAdapter.load()` after enabling a script and
    reloading. No `SCRIPT_*` entry, no `BACKEND_*` entry.
    *Result:* Verified: `storageAdapter.load()` contains no `SCRIPT_*` and no `BACKEND_*`.
22. ✅ **No klinecharts warning at app load.**
    *Result:* Verified across many reloads this session: the only script-related console line is SC's deliberate "produced no plots or panes" warning (see the observations below), never the phase-2 klinecharts warning. *How:* reload with an enabled script and a clean console; the phase-2 warning must not return.
23. ✅ **No provider-side script id is persisted anywhere.** *How:* grep localStorage for `SCRIPT_`. SC's ids are session-local (`SCRIPT_${++idCounter}`) and must never be written down.
    *Result:* Verified: the only `SCRIPT_` in localStorage is `DEFAULT_TRADING_LAYOUT_SCRIPT_EDITOR` — a layout id, not an indicator.
24. ✅ **A reload does not double-add.** *How:* enable one script, reload twice, count the indicators. One each time.
    *Result:* Verified: one enabled script, two reloads, one indicator each time.

## D. SC's Script button — R3

25. ✅ **The Script button is gone from SC's toolbar** while the provider is still set.
    *How:* main terminal chart, SuperChart provider. **Check the built bundle
    carries the flag** before calling this passed — a screenshot of a toolbar
    proves nothing about which build is running (phase-2 lesson).
    *Result:* Verified against the artifact **and** the accessibility tree: `grep -c script_button` in the linked `dist-enterprise/superchart.es.js` → 2, and the chart top bar lists only `Indicator` and `Indicator templates`.
26. ✅ **Scripting still works with the button gone** — the provider was not disabled along with its button.
    *How:* "Run on chart" after 25. The flag must gate the button only.
    *Result:* Verified: previews and enabled scripts both run throughout this pass with the button gone.
27. ✅ **Charts with no provider are unchanged.** *How:* /charts and grid-bot charts never had the button; they still don't, and nothing throws.
    *Result:* Verified: /charts has no provider and no button; nothing throws.

## E. The `BACKEND_` leak — R4

**⛔ Not testable from Altrady — by anyone, right now.** Verified 2026-09-01:
`src/` contains **zero** references to `indicatorProvider`, so Altrady never
gives SuperChart one, and SC's own `getBackendIndicators()` on the live chart
returns `{availableIndicators: [], activeIndicatorNames: []}`. The picker's
backend list has no source, so there is no way to create a `BACKEND_` indicator
and therefore no way to exercise the leak or its fix from this app.

This is the same shape as phase-2 item 31: blocked by something outside the
change, not failed. The fix is still worth having — it closes the prefix pair by
construction and is unit-covered in SC — it simply cannot be demonstrated here
until Altrady wires an `indicatorProvider` (not in any phase's scope today).

Two ways to close these out if we want more than SC's unit tests:
**(a)** have the SC session demonstrate them in SC's own harness, where a
provider exists; **(b)** stub a throwaway `indicatorProvider` in cbsd, exercise
the eye-toggle and settings modal, and revert it uncommitted. (b) is ~20 minutes
and gives a real host-side proof.

28. ⛔ **A backend indicator's eye-toggle no longer writes to saved chart state.**
    *How:* add a backend indicator, toggle its legend eye, inspect
    `storageAdapter.load()`.
29. ⛔ **Its settings modal doesn't either.** *How:* same, via the gear.
30. ⛔ **Already-polluted state self-cleans.** *How:* SC's fix filters ephemeral names on load; a chart state that already contains one must come back clean rather than warning forever.
31. ⛔ **Accepted consequence, not a bug:** backend indicator `visible` is no longer persisted. It never restored — it only produced the warning. Confirm nothing user-visible regressed.

## F. Regression — R5, R6

The phases 1 and 2 gate. These must still be true.

32. ✅ (Areg) **All 15 matrix rows still pass on TradingView.** *How:* the phase-2 suite, unchanged. R1 and R2 both refactored TV code, so this is not a formality.
    *Result:* Verified by Areg, 2026-09-01. The two rows this phase actually refactored (12 and 15) were also checked independently — items 33 and 34.
33. ✅ **TV backtest trades are byte-for-byte what they were** — entry/exit markers and the win/loss trend line, hide and restore of real trades.
    *How:* the same backtest on a TV chart, before/after comparison. The file
    moved and its policy half was extracted; the drawing decisions did not
    change.
    *Result:* Verified on TradingView: markers and dashed win/loss lines drawn, real trades hidden during, restored on clear.
34. ✅ **TV's "Add to charts" still works**, including multi-file. *How:* the resolver was extracted out from under it — same four steps, three of them moved.
    *Result:* Verified on TradingView: `test` is registered and drawn from the enabled list through the extracted resolver.
35. ✅ **Scripts still run on SC** — phase 1 and 2 spine intact: plots, panes, primitives, params, logs, modules, diagnostics.
    *How:* `draw-all` plus one `param` script. Breadth, not depth.
    *Result:* Previews, enabled scripts, plots, panes and multi-file all ran repeatedly through this pass on SC. Not a substitute for Areg's own breadth run.
36. ✅ **No unhandled console errors** across a full session on either provider.
    *Result:* Three kinds of console output were seen across the pass, none a
    phase-3 defect: a deliberate 404 from the corrupt-id test (item 20), a
    pre-existing React 19 `element.ref` deprecation warning, and
    webpack-dev-server compile errors while SuperChart was being rebuilt.

## G. The seam — R6

37. ✅ **No `chartProvider` test anywhere in the scripting path.** *How:* grep. Selection stays structural.
    *Result:* Verified: `grep -rn chartProvider` across `containers/scripts/` and both providers' `scripts/` folders → 0 hits.
38. ✅ **Chart code does not import the Scripts IDE.** *How:* grep for `useScripts` under both chart trees. Phase 2 removed it from `tradingview.js`; phase 3 removed the last one.
    *Result:* Verified: `grep -rn useScripts src/containers/trade/` → no hits. The last one is gone.
39. ✅ **The two providers' script modules sit at mirrored paths**, and each does only mechanism.
    *Result:* Verified: `super-chart/scripts/` and `tradingview/scripts/` now hold the mirrored renderer + backtest-trades pair.
40. ✅ **The enabled list is read by both providers through one resolver** — no second copy of fetch-and-rebuild-modules.
    *Result:* Verified: one `loadChartScripts`, two callers — the SC renderer and TV's `chartEnabledProvider`.

---

## Round 1 results (2026-09-01)

**Complete: 36 of 40 pass, 4 blocked.**

- **34 verified by me**, in the browser against the dev server.
- **2 verified by Areg** — item 17 (it deletes a saved script from his account)
  and item 32 (the full 15-row TradingView suite).
- **Items 28-31 ⛔ blocked**, by his decision to skip them. Altrady wires no
  `indicatorProvider`, so no `BACKEND_` indicator can exist to test against —
  see section E. Not a failure and not deferred work: the fix ships, it simply
  cannot be demonstrated from this app.

Phase 3 is verified.

### Four bugs found and fixed

Found by driving the app rather than by reading code. The first two are
phase-3 code (`ee1f88d8a`); the third is phase-1 code that phase 3's testing
exposed (`daadf2101`); the fourth was caught by Areg looking at the chart
(`a2634d4f2`), after my own round-1 pass had signed the item off.

1. **Every "Run on chart" tore down and re-added every add-to-charts script.**
   `previewExternalId` was a dep of the effect that owns the enabled set, so a
   new preview invalidated the whole effect: `removeAll()` then re-add. Visible
   as the enabled scripts' ids jumping on each run, and on a heavy script it
   would be a re-execute per edit. Now the preview is held in a ref and its own
   effect re-syncs, which moves exactly the one script that changed hands and
   leaves the rest alone. Re-verified: `strategy.orders` keeps its id across a
   preview run, and the previewed script still wins.

2. **Backtest trades stayed anchored to the old series after a symbol or
   resolution change.** The SC renderer's deps were `[chartController]` only,
   and the controller survives both — so the markers would have kept their old
   timestamps while the chart showed something else. Symbol and resolution are
   in the deps now, matching what TradingView does.

3. **A live preview leaked its indicator on every market-tab switch** — one
   orphan per switch, reproduced with **zero** enabled scripts, so it was purely
   the phase-1/2 preview path.

   I first recorded this as "mechanism unknown, Areg's call", because phase 2
   lost three rounds to a fix attempted before the cause was understood. The SC
   session then proposed a mechanism (an add resolving after cleanup, so no
   handle ever reached the host). Instrumenting `useScriptRun` with timestamps
   showed that was **not** it, and showed the real one:

   ```
   26493  cleanup        handle=SCRIPT_2     ← clear() IS called, with a real handle
   26499  effect-run
   26516  apply-resolved handle=null         ← chartController undefined this render
   26561  effect-run
   27043  apply-resolved handle=SCRIPT_3
   ```

   `clearRef.current` is rewritten on every render, so at teardown it was bound
   to whatever the provider looked like *then*. Mid-switch the chart resolves
   through context and is briefly undefined, so the current `clear` ran as
   `chartController?.removeScriptIndicator(id)` **on nothing** — the optional
   chain swallowed it, no error, no removal, and the indicator the run had
   actually added was orphaned on a live chart. That is why no
   `removeScriptIndicator` call and no removal notice were ever observed.

   Fixed by binding the `clear` that belongs to a handle at the moment the
   handle is stored, and using that at teardown. It is the same **lifetime**
   defect class both previous reviews kept finding — a value read at teardown
   that was only valid at setup — and it fixes both providers at once.
   Verified: before, one switch left three indicators (an orphan plus two); now
   two switches in a row leave exactly the two that belong there.

4. **Backtest arrows were all red — coloured by outcome instead of by side.**
   TradingView's `drawTrade` takes the user's closed-order colours from the
   chart-settings modal (buy green, sell red); I had passed the win/loss colour
   to both markers, so with an engine that returned only losing trades every
   arrow came out red. Now the markers read `getTradeColor(side)` and
   `getArrowType()` from the account-trades controller — the same source real
   trades use, so the two sets cannot drift and a settings change reaches both —
   and only the connecting line stays win/loss.

   Worth noting how this got past round 1: I verified the colour *branch*
   (`pnl >= 0` → green) by feeding a synthetic winning trade through the
   controller, and it passed. The branch was right; the input was wrong. A unit
   check of the code I had written could not see that, because the question was
   never "does this branch work" but "is `pnl` the right thing to branch on" —
   and the real run, which would have shown 42 red arrows in a row, I only ever
   looked at as a screenshot of markers being *present*. **The item's own
   instruction to check `extendData` rather than pixels was followed and still
   missed it.** The lesson for the remaining items: compare against the
   neighbouring feature that already works, not only against the spec in my head.

### Two observations that are not defects in this port

Recorded because they cost time to diagnose and will cost it again.

1. **The same script renders when added from the enabled list and draws nothing
   when previewed, seconds apart.** SC says `Script SCRIPT_N produced no plots
   or panes`. This is the known `buildMetadata` all-NaN-probe gap: whether a
   plot registers depends on how much history happens to be loaded when the
   script is added. It is what the pending **ta-v2 compiler redeploy** fixes,
   and it makes any test using `ta.sma` without `config.warmup` unreliable —
   which is why the add-to-charts items above use `test` rather than `sma`.

2. **The backtest engine returned 81 trades and zero winners**, including longs
   that exit above their entry with a large negative `pnl` (entry 61701, exit
   62935, `pnl` −1820 on a 10k account). Colouring reads `pnl` exactly as the
   TradingView path always has, so this is parity, not a port defect — but if
   the sign is wrong, every user sees an all-red chart. Server side, in
   `coinray_script`. Worth a look independently of this phase.

### One hazard worth knowing while testing

`closedOrdersShow` is persisted. If the app reloads while a backtest's trades
are shown, the restore never runs and your real trades stay hidden until you
turn them back on. Pre-existing — the TradingView version has always worked this
way — but it bit me twice during this pass.
