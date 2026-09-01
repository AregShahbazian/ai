---
repo: crypto_base_scanner_desktop
phases: [sc-script-parity, sc-script-trimmings]
---

# Code review — phases 2 and 3 (cbsd)

Read of the code as it stands after `f6d99e239` / `dc4a13cbc` (phase 2) and
`93e644217` (phase 3). Both phases shipped without a code review; phase 1's
review is the model.

Ground rule applied throughout, per Areg: **fix only what is obviously a defect
and obviously needs fixing.** Anything theoretical is written down here and the
code is left alone.

## Fixed

### 1. Two overlapping syncs could add the same chart script twice
`super-chart/scripts/sc-chart-scripts-renderer.js`

`sync()` awaits `loadChartScripts()` — a network fetch — **before** it records
anything in `added`. Two syncs overlapping therefore both compute the same
`missing` list and both add it:

- toggle a second script while the first toggle's `getScript` is still on the
  wire, or
- toggle anything while the initial load is still fetching.

The second `added.set(externalId, scriptId)` overwrites the first, so one of the
two indicators is orphaned: nothing holds its id, the toggle-off path cannot
remove it, and it survives until the chart is torn down.

Fixed with an `inFlight` set that reserves the ids before the await, plus a
staleness check after each add — the list can legitimately have moved on while a
script was in flight (toggled off again, or it became the preview), and such a
script is now removed rather than recorded.

### 2. `useBacktestTrades` repeated the stale-clear bug from `useScriptRun`
`scripts/chart-bridge/use-backtest-trades.js`

Teardown read `clearRef.current`, which is rewritten on every render, so it ran
against whatever the provider looked like at teardown rather than the one the
handles came from. This is the identical shape as the phase-3 bug that orphaned
a script indicator on every market-tab switch (fixed in `daadf2101`): mid-switch
the chart resolves through context and is briefly undefined, and the optional
chain inside a provider's `clear` swallows the call in silence.

Less damaging here than in `useScriptRun`, because `draw()` clears the group
before drawing and so self-heals on the next run — but a backtest cleared during
a switch would leave its markers on the chart until then. Fixed the same way:
the `clear` is bound when the handles are stored.

Worth stating plainly: I wrote the sibling hook *after* diagnosing that exact bug
and still copied its shape. The lesson from both previous reviews — **lifetime is
this codebase's recurring defect class** — applies to the fix as much as to the
original.

## Found, deliberately not fixed

### 3. An add-to-charts script's `log.*` output is attributed to the preview run
`super-chart/scripts/sc-script-provider.js`, `sc-script-renderer.js`

`createScriptProvider` attaches `onLog` to **every** subscription
`executeAsIndicator` returns, and there is a single `logHandler` closure. The
handler is installed by the preview renderer and stamps entries with the preview
run's id. Since phase 3, chart-enabled scripts run through the same provider —
so a script with `log.*` calls that the user added to their charts will print
into the Scripts IDE console as though the previewed script had produced it.

Real, and reachable by a user who adds a logging script to their charts. Not
fixed because **the fix is not obvious**: the provider has no way to correlate an
`executeAsIndicator` call with the host-side add that caused it, so telling
"preview" from "chart script" needs either a new contract member or a
subscription-tagging scheme — a design decision, not a repair. Left for phase 4
or a follow-up, with the mechanism recorded here so it needn't be re-derived.

### 4. `closedOrdersShow` is persisted, so a reload mid-backtest hides real trades
`scripts/chart-bridge/use-backtest-trades.js`

Hiding the user's real trades dispatches `editChartSettings`, which persists. If
the app reloads while a backtest's trades are shown, the restore never runs and
the user's real trades stay hidden until they turn them back on. It bit me twice
during phase-3 testing.

Not fixed: the behaviour is inherited verbatim from the TradingView
implementation this hook was extracted from, so changing it changes TV too —
which the phase-3 R5 gate forbids — and the right fix (a non-persisted
suppression flag rather than writing the user's setting) is a design change, not
an obvious repair.

## Checked and found sound

- **The seam.** No `chartProvider` test anywhere in the scripting path; no chart
  code imports the Scripts IDE; the two providers' modules sit at mirrored paths
  and each does only mechanism. The `loadChartScripts` extraction leaves exactly
  one copy of the fetch-and-rebuild-modules logic.
- **`removeAll` in the renderer's cleanup** closes over the `chartController`
  the adds were made against — the effect is keyed on it — so it does not have
  finding 2's problem.
- **`syncRef.current?.(...)` in the preview effect** short-circuits the whole
  chain when the ref is null, `.catch` included; it does not throw on mount
  before the owning effect has run.
- **Bridge publish gating.** `publishLogs` / `publishFailure` both drop anything
  whose `runId` is not current, and the callbacks are identity-stable so the IDE
  registers once rather than once per run.
- **`loadChartScripts` error handling.** One script failing to resolve logs and
  skips rather than taking the others down; helpers come from
  `version.resolvedDependencies`, never the `script.modules` field the API does
  not return.
