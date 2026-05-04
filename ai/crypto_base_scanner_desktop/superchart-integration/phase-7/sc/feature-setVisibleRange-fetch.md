# Feature Request — `setVisibleRange` should fetch missing history

**Audience:** SC library maintainers (Basty)
**Source phase:** Altrady Phase 7 (Quiz / training port)
**Priority:** Blocker for quiz edit-mode in Phase 7; enables future "go-to-date" navigation across Altrady.

---

## Problem

`superchart.setVisibleRange({from, to})` is documented as
*"scroll/zoom to show {from, to} (unix seconds)"*, but the current implementation
operates only on the **already-loaded in-memory bar buffer**:

- It calls `binarySearchNearest` over `chart.getDataList()` to find indices for
  `from` / `to`.
- If `from` is older than the first loaded bar, it silently clamps to the
  earliest loaded bar.
- It does **not** invoke `dataLoader` / datafeed `getBars` for the missing range.

Net effect for Altrady: when a caller asks the chart to focus on a historical
window that is outside the buffer (e.g. June 2025 while the chart was just
constructed at wall-clock now), the call is effectively a no-op and the user
keeps seeing the present.

The contract documented in `SUPERCHART_API.md` is correct; the implementation
under-delivers.

---

## Driving use cases (Altrady)

### 1. Quiz edit-mode — open at the question's historical timeframe

When a user opens `/quizzes/edit/<quiz>/question/<id>`, we set the chart's
symbol/period to the question's market and want it scrolled/zoomed to the
question's `[solutionStart - margin, solutionEnd + margin]` window — a
historical window that is typically months old.

The chart must remain a **live** chart (live WebSocket subscription active —
no replay session). We need: "scroll the live chart to a historical bar,
fetching backwards if needed."

### 2. Quiz new-question creation — pattern hunting on a live chart

When the editor creates a new question, the user needs to scroll back
through historical candles, looking for a suitable price pattern, **while
the latest candle keeps updating live**. Same primitive: jump/scroll the
live chart to a historical bar with on-demand backloading.

### 3. Future Altrady "go to date" UX

Generic navigation feature that has been requested in Trading Terminal for
some time. Same primitive.

---

## Why existing tools don't fit

| Approach | Why it's wrong |
|---|---|
| **Replay engine `setCurrentTime(target)`** | Couples backloading (good) with freezing live ticks (bad). The editor wants live ticks active while inspecting a historical window. Misusing replay would force a session, hide the live tail, and require a teardown step to return to live. |
| **Caller invokes `dataLoader.getRange(from, to)` manually before `setVisibleRange`** | Pushes a low-level concern into every consumer. Each consumer has to (a) detect that the range is outside the buffer, (b) call `getRange`, (c) wait for it to land, (d) then call `setVisibleRange`. This is exactly what `setVisibleRange` should already do. |
| **Datafeed redirection** (set a flag on the datafeed so the next `firstDataRequest` returns bars centered on the target time) | Bleeds quiz state into the generic datafeed layer; brittle around `setSymbol`/`setPeriod` reset semantics; hostile to the new-question flow where the user navigates repeatedly. |

The right fix is in the chart, not in 3 layers of caller-side hackery.

---

## TV parity

TradingView's `chart.setVisibleRange({from, to})` triggers `getBars`
backloading via the datafeed contract. The Altrady TV-era quiz worked at all
because TV would call `getBars` repeatedly with arbitrary `from`/`to` ranges
as the user navigated — that's why our TV `DataProvider.getBars` had to
honour a `maxCandleTime` filter for arbitrary historical ranges.

SC inherits the same TV-compatible datafeed shape (we use the same `getBars`
signature) but `setVisibleRange` does not exercise it for backloading.
Closing this gap brings SC to parity with TV's documented behavior — not a
new feature, just honouring the contract the datafeed already supports.

---

## Proposed interface

Two options. We prefer (A); (B) is the safe fallback if existing callers
depend on the no-op-on-miss behavior.

### Option A — Make `setVisibleRange` honour its contract (preferred)

Same public signature. New behaviour:

```ts
setVisibleRange(range: VisibleTimeRange): void
//   Scroll/zoom the chart to show {from, to} (unix seconds).
//   If `from` is older than the earliest loaded bar, the chart fetches the
//   missing range via the dataLoader (datafeed `getBars`) and applies the
//   scroll/zoom once data lands. Live subscription is unaffected.
```

Behavioural notes:
- If the request is fully within the loaded buffer → behaves exactly as today.
- If the request requires backloading → emits a single `getBars` call (or a
  bounded sequence, if SC's loader paginates) covering at minimum the gap
  between `from` and the current first bar; applies `setVisibleRange` once
  bars are appended.
- Live tail is untouched; no replay session is created.
- No-op (with a debug-level warning, not an error) if the datafeed returns
  `noData: true` for the requested range.

This matches TV's behaviour and keeps Altrady's call sites simple:

```js
chartController.setVisibleRange({from, to})  // Just works. No await, no buffer check, no datafeed flag.
```

If callers want to know when the navigation completes (e.g. to draw an
overlay anchored to a bar that may not yet be loaded), expose a sibling
`setVisibleRangeAsync(range): Promise<void>` resolving when bars are in and
the scroll has been applied. Optional — not required for our current uses.

### Option B — Add a sibling API (non-breaking)

Keep `setVisibleRange` as a scroll-only primitive; add an explicit
fetching variant:

```ts
setVisibleRange(range: VisibleTimeRange): void          // unchanged: in-buffer only
navigateToRange(range: VisibleTimeRange): Promise<void> // fetches missing bars, then scrolls/zooms
```

Or, equivalently, a flag on the existing API:

```ts
setVisibleRange(range: VisibleTimeRange, opts?: { fetch?: boolean }): void
// opts.fetch === true → backload first if needed.
```

Both shapes are acceptable. The Promise-returning variant is slightly more
useful for callers that want to chain overlay draws onto the bars-loaded
event; the flag variant is more compact.

---

## Acceptance criteria

1. Calling `setVisibleRange({from, to})` on a freshly mounted chart, with
   `from` several months in the past, results in a `getBars` call to the
   datafeed covering the gap, then a scroll/zoom that visibly centers the
   chart on `[from, to]`.
2. The live subscription remains active throughout — the latest bar
   continues updating from `subscribeBars` callbacks.
3. Calls fully inside the loaded buffer remain synchronous and do **not**
   emit extra `getBars` calls (no regression on the hot path).
4. If the datafeed responds `noData: true` for the requested range, the
   chart does not enter a broken state — it stays where it was, and a
   debug log explains why.
5. Subsequent `setVisibleRange` calls to overlapping or already-loaded
   ranges reuse the buffer (no redundant fetches).

---

## Out of scope

- Smooth animation / interpolation between current view and target range.
- Predictive prefetch of adjacent windows.
- Behaviour during an active replay session (replay's own `setCurrentTime`
  remains the right tool there).

---

## Altrady-side impact (FYI)

Phase 7's quiz edit-mode is currently shipping with a no-op
`setVisibleRange` and a 500 ms retry. Once this lands on SC, Altrady's
`DrawController.setVisibleRange` collapses to a one-liner pass-through,
the retry goes away, and the new-question pattern-hunting flow becomes
implementable without any of the workarounds enumerated above.
