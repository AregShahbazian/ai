# SC feature request — `chart.resetView()` for "back to defaults"

## Problem

A common UX hotkey on charting apps (e.g. TradingView's `alt+R`) restores
the chart to its "freshly mounted" state: latest candle anchored at the
right edge with the default zoom (bar-space) and the default right-side
offset. SC currently exposes the primitives needed (`scrollToRealTime`,
`setBarSpace`, `setOffsetRightDistance`) but not the **defaults
themselves**, and recombining them correctly requires the consumer to
know SC-internal initial values it doesn't have access to.

Specifically:

- **`scrollToRealTime()` only resets scroll, not zoom.** If the user has
  zoomed in/out via wheel/pinch, calling `scrollToRealTime()` lands on
  the latest candle but keeps their current bar-space — not "as if the
  chart just loaded."
- **No public way to read the initial bar-space.** SC chooses a default
  on construction (driven by container width / period / built-in
  heuristics). Consumers can call `getBarSpace()` once on `onReady` and
  cache it, but that pushes SC-internal state out into every consumer.
- **No public way to read the initial offset-right.** Same issue —
  consumers can't recover SC's "freshly mounted" right padding.
- **Replay mode complicates "latest candle".** In a replay session, the
  conceptual "real time" is the latest *drawn* candle, not the live
  market tail. Consumers shouldn't have to branch on replay state to
  pick the right anchor.

## Driving use cases

- **Altrady alt+R hotkey**, mounted on every SC consumer (Trading
  Terminal main chart, /charts grid items, customer-service chart,
  grid-bot chart). Live mode: reset to latest candle + default zoom.
  Replay mode (DEFAULT and SMART): reset to latest drawn candle +
  default zoom. The hotkey should not need to introspect replay state.
- **Quiz alt+R is out of scope for this request** — quiz uses an
  app-specific focus (a question's `solutionStart` / `solutionEnd`
  timestamps with padding) and routes through SC's existing
  `setVisibleRange({from, to})`. Only the "no app-shaped focus, just go
  home" case needs this new method.

## Why current workarounds are insufficient

- **Capture initial bar-space + offset-right on `onReady`, store in app
  state.** Works, but every SC consumer pays the same bookkeeping cost,
  and it locks in the very-first-frame value (which may be off if
  `onReady` fires before SC has finalized layout, e.g. before a
  ResizeObserver callback). Pushing SC-internal lifecycle knowledge to
  the app side mirrors the problem `feature-setVisibleRange-load-aware`
  solved for visible range.
- **Combine `scrollToRealTime()` + a hardcoded bar-space constant.**
  Brittle — a future SC release that changes the default zoom would
  silently break every consumer.
- **Branch on replay state in the app.** Replay's "real time" semantic
  is SC-owned (the engine knows whether `scrollToRealTime` should mean
  live tail or replay-drawn tail). Forcing the app to rebuild that
  decision tree duplicates SC logic.

## Proposed interface

A single new method on the chart instance:

```ts
chart.resetView(): void
```

Semantics:

> Restore the chart to its "freshly mounted" view: scroll the latest bar
> (live tail outside replay, latest drawn bar inside replay) to the right
> edge, restore the default bar-space and default right-offset distance,
> and re-render. No options.

Equivalent to the user's first frame after `new Superchart({...})`
without any subsequent zoom/scroll/setVisibleRange interaction.

## Implementation clarifications

**Q1. What "default bar-space" means.** Whatever SC computes when
constructing a chart for the same `{period, container}` it has now —
i.e. whatever value `getBarSpace()` would return on a fresh mount with
identical inputs. Recompute, don't cache, so resize-time changes are
respected.

**Q2. What "default offset-right" means.** SC's built-in default — the
value that would be applied if the consumer never called
`setOffsetRightDistance`. Same rule as Q1.

**Q3. Replay-mode tail.** "Real time" = latest bar in `_dataList`. In a
replay session, `_dataList` is the buffer up to the replay's current
time, so its last element is the latest drawn bar. No replay-specific
branch needed in the implementation — `scrollToRealTime` semantics over
`_dataList`'s last element already give the right answer.

**Q4. During an init-load.** If `_initLoadInFlight === true`, defer
`resetView` until the load completes (same drain-on-completion pattern
as the load-aware `setVisibleRange`). The promise / sync-vs-async story
can mirror whatever `setVisibleRange` does — currently `void`, fine for
this method too if the existing call is sync.

**Q5. Does this replace `scrollToRealTime` etc.?** No. The primitives
remain for consumers that want partial behavior (scroll only, zoom only).
`resetView` is the convenience method that combines them with internal
defaults.

## Acceptance criteria

- `chart.resetView()` after the user has zoomed in/out and scrolled
  away returns the chart to the same view a freshly-mounted chart
  would show given the same `{symbol, period, container size}`.
- In a replay session, `chart.resetView()` anchors the right edge on
  the latest drawn candle (replay buffer's tail), not on live market
  tail.
- `chart.resetView()` after `setVisibleRange({from, to})` snaps back to
  the default tail-anchored view (defaults restored, not the
  user-supplied range).
- `chart.resetView()` called during an in-flight init-load defers
  until the load settles, then applies (no early-return / silent drop).
- Calling `chart.resetView()` repeatedly is idempotent (after the
  first call, subsequent calls produce no visible change).

## Out of scope

- App-specific focus on a historical from/to range — covered by the
  existing `setVisibleRange` API (and its load-aware behavior shipped in
  `feature-setVisibleRange-load-aware.md`).
- Persisting / restoring user-adjusted zoom across reloads — consumer
  concern.
- Custom keybinding registration — every consumer wires its own
  hotkey; SC only provides the imperative method.

## Altrady-side impact when this lands

- Single `useChartResetHotkey({enabled})` hook in Altrady binds `alt+R`
  to `chartController._superchart.resetView()` for live + replay modes.
- No `_initialBarSpace` capture, no replay-state branching on the
  Altrady side.
- Quiz modes continue to route their app-specific focus through
  `setVisibleRange({from, to})` — orthogonal to this feature.
