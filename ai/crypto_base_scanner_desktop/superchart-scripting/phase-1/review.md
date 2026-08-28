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

## Verification

`[ ]` open · `✅` verified by me · `✅ (agent-verified)` verified by a subagent.

### A. SC spine — R1-R4

1. [ ] Provider = SuperChart. Open `test`, **Run on chart** → one line ~2% above price, spanning visible history.
2. [ ] The line extends as new candles print (watch one bar close).
3. [ ] Values are the chart's own candles: scroll back, the line follows the same series (no gap, no second fetch of a different symbol).
4. [ ] Open `line-and-pane`, run → 2 lines on the price pane, RSI in its own sub-pane, distinguishable colours.
5. [ ] Run `sma` on SC and on TV, same symbol/resolution → last plotted value matches.
6. [ ] Edit `test` (`1.01` → `1.05`), re-run → line moves; exactly one indicator, no leftover.
7. [ ] Re-run cycle ×10 with arithmetic edits → indicator count stays 1, no page reload needed.
8. [ ] Add a second `plot()` and re-run → 2 lines, still one indicator (plot-set change).
9. [ ] Move a plot into `plotPane()` and re-run → sub-pane appears; move it back → sub-pane disappears, no orphan pane.
10. [ ] Switch `test` → `probe-b` and re-run → line jumps to +2%, old line gone (name-collision case).
11. [ ] Remove the indicator from the chart → line gone, script stopped, no console errors afterwards.
12. [ ] Change resolution → either re-runs against the new series or is removed; never stale values.
13. [ ] Change `coinraySymbol` (same tab) → same rule as 12.
14. [ ] Switch TradingTab and back → no duplicate indicator, no throw.
15. [ ] Close the Scripts widget while a script is running → no leak, no throw.
16. [ ] Switch trading layout / unmount the chart → clean, no error in console.

### B. TV regression — R5 (hard gate)

Provider = TradingView. One run per script, first-run **and** one re-run.

17. [ ] Row 1 — `test`, `sma`
18. [ ] Row 2 — `line-and-pane`
19. [ ] Row 3 — `param` (dialog shows int/float/bool_)
20. [ ] Row 4 — `draw.line`
21. [ ] Row 5 — `draw.marker`
22. [ ] Row 6 — `draw.box`
23. [ ] Row 7 — `draw.label`
24. [ ] Row 8 — `draw.remove`
25. [ ] Row 9 — `log` → Console panel, 4 levels
26. [ ] Row 10 — `declareAlert` instantiates (no `LinkError`)
27. [ ] Row 11 — `strategy.orders` plots + the "TradingView cannot render" warning
28. [ ] Row 12 — backtest `strategy.orders` → report, equity curve, trade arrows
29. [ ] Row 13 — `multi-module`; edit `helper` only, re-run → recompiles
30. [ ] Row 14 — save a version, open an older one → entry **and** helper restored
31. [ ] Row 15 — "Add to charts" `sma` → appears on a chart with no IDE widgets

### C. Coexistence and seam — R6, R7

32. [ ] Toggle provider SC → TV → SC without reload; run a script after each toggle, both work.
33. [ ] Charts page (`#/charts`) as well as Trading Terminal, on both providers.
34. [ ] `grep -rn "chartProvider\|superchart" src/containers/scripts/` → no provider branching in the IDE.
35. [ ] The bridge is its own module; `scripts-context.js` line count did not grow materially.
36. [ ] SC's own Script / `f(x)` button and editor are untouched and unused by this path.

### D. Known-absent (phase 1 non-requirements)

Confirm these fail *cleanly* on SC — no crash, no half-rendered indicator:

37. [ ] `draw.line` on SC → plots render (if any), primitives absent, no throw.
38. [ ] `param` on SC → defaults used, no settings dialog, no throw.
39. [ ] `log` on SC → Console panel silent, no throw.
40. [ ] `multi-module` on SC → whatever the compile path does, it does not crash the chart.
41. [ ] `strategy.orders` on SC → plots render, orders silently dropped.
