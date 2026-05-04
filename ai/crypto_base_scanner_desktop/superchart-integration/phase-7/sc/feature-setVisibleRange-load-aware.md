# SC feature request — `setVisibleRange` should be load-aware

> **Status: PARTIALLY shipped — needs follow-up fix for consecutive
> `setPeriod`+`setSymbol` race.**
>
> **What's done:**
> - SC commit `851d1cb` added the queue/drain mechanism in coinray-chart's
>   `Chart.ts:1119-1176`: queues on `isInitLoadInFlight()`, drains via
>   `onInitLoadComplete` after the post-load `setOffsetRightDistance`.
> - Altrady's `chart-controller.js` dropped `_pendingVR`, `_onBarsLoaded`,
>   and the `setOnBarsLoaded` registration; `setVisibleRange` is a thin
>   pass-through to `superchart.setVisibleRange`.
>
> **What's broken (see `## Follow-up: superseded getBars race` below):**
> Calling `setPeriod(newP); setSymbol(newS)` synchronously creates TWO
> in-flight `getBars(init)` Promises. `_processDataUnsubscribe` doesn't
> abort the first one. Whichever resolves first fires
> `onInitLoadComplete`, drains `_pendingVisibleRange`, nulls it. The
> second resolves later, fires `onInitLoadComplete` again, but the queue
> is empty — VR never re-applied. Chart settles at live tail.
>
> Affects: any consumer doing `setPeriod`+`setSymbol`+`setVisibleRange`
> within the same task. Quiz tab-switch between questions with different
> market AND resolution is the failing case in Altrady.

## Problem

Setting a programmatic visible range immediately after `setSymbol`/`setPeriod`
(or before the first `getBars(init)` completes on mount) does not survive the
in-flight init-load. Two distinct failure modes:

1. **Initial mount.** `new Superchart({symbol, period, ...})` triggers the
   first `getBars(type='init')` asynchronously. A consumer that calls
   `chart.setVisibleRange({from, to})` immediately after construction hits
   the `dataList.length === 0` early-return at `Chart.ts:1108` and the call
   is silently dropped.

2. **Post-`setSymbol` / `setPeriod` race.** Per `Store.ts`:
   - `setSymbol` and `setPeriod` both call `resetData` → `_processDataLoad('init')` (`Store.ts:520`, `:542`, `:938-943`).
   - `_processDataLoad` keeps the existing `_dataList` until the async `getBars` callback fires, then atomically swaps via `_clearData(); _dataList = data` (`Store.ts:665-668`).
   - The `init` branch then calls `setOffsetRightDistance(_offsetRightDistance)` (`Store.ts:671`), which **resets the scroll offset** to its stored value.

   A `setVisibleRange({from, to})` call made between the `setSymbol` and the
   init-callback runs against the still-visible OLD buffer (passes the
   `dataList.length === 0` check). When the new data arrives moments later,
   the scroll-offset reset overrides whatever scroll position
   `setVisibleRange` produced — VR snaps to live tail.

   This makes "switch to a new symbol/period AND focus on a historical
   range" effectively unreachable from outside SC. The Altrady quiz/training
   flow needs exactly this on every question transition.

## Driving use cases

- **Quiz edit-mode question switch.** Two questions can have different
  symbols, resolutions, or both. On tab click we push the new
  symbol/period and the question's saved historical date range. We need
  the date range to land on the new buffer, not get clobbered.
- **Initial mount with a historical view.** Quiz edit-mode loads a chart
  pre-focused on the question's date range — no live tail flash before
  scrolling back.
- **TT "go to date" / search-by-time.** Same need from the TT side once
  the feature lands. Currently TT only does barSpace+`scrollToRealTime`
  restore, which doesn't require this — but adding any "show me the chart
  at unix timestamp X" feature to TT will hit the same race.

## Why current workarounds are insufficient

- **Defer `setVisibleRange` until `setOnBarsLoaded`.** Works for a single
  init-load. But if the consumer calls `setPeriod(newP)` then
  `setSymbol(newS)` synchronously, only the second call's `getBars`
  callback fires (the first is unsubscribed via `_processDataUnsubscribe`,
  `Store.ts:938-943`). The single callback fires "after the last
  superseding load" — usable, but each consumer has to track this.
- **Boolean "loading" flag in app code.** What we ship today (see
  `chart-controller.js`'s `_loading` flag and `_pendingVR` queue): every
  consumer routes `setSymbol`/`setPeriod` through a wrapper that flips the
  flag, and `setVisibleRange` queues until the next `_onBarsLoaded`. Works
  but pushes SC-internal lifecycle knowledge out to every consumer (TT,
  Quiz, grid-bot, customer-service, future ones).
- **Listen to `onVisibleRangeChange` and re-apply.** Risks an infinite
  loop and doesn't help with "set VR for the first time on init mount".

## Proposed interface

Make SC's existing `setVisibleRange({from, to})` load-aware. The call
already returns `Promise<void>` after the recent
`feature-setVisibleRange-fetch.md` change. Extend the contract:

> If an init-type load is currently in flight, `setVisibleRange` defers
> application until that load has settled (the `getBars(init)` callback has
> fired, dataList has been swapped, and the post-load
> `setOffsetRightDistance` has run). Application happens AFTER the offset
> reset, so the consumer's range survives. The Promise resolves after the
> deferred application completes.

Specifically:

1. **Empty-buffer case.** Replace the `Chart.ts:1108`
   `dataList.length === 0` early-return with a deferred-apply path that
   queues the call and resolves it from the next successful init-load.

2. **In-flight init-load case.** Track when `_processDataLoad('init')` is
   active; queue any incoming `setVisibleRange` while the flag is set, and
   apply on completion (after the existing `setOffsetRightDistance(_offsetRightDistance)`
   call at `Store.ts:671`).

3. **Multiple synchronous `setSymbol`/`setPeriod` + `setVisibleRange`
   calls.** Latest VR wins; previous deferred VR's promise resolves
   cleanly without applying (see Q1 below).

The empty-buffer and in-flight cases are effectively the same state from
the consumer's perspective: "the chart isn't ready to honor a from/to
range yet." A single internal `_pendingVisibleRange` field plus a drain
hook in the init-load completion path covers both.

## Implementation clarifications

**Q1. Superseded promise resolution.** Resolve cleanly (no rejection).
Matches Promise cancellation conventions, matches the in-app workaround's
existing behavior (`_pendingVR?.resolve?.()` before replacing), and avoids
spurious error logs in consumers that use `.catch(console.error)`. A
consumer that needs to distinguish "applied" vs "superseded" can compare
its requested range against the chart's actual VR after the promise
resolves.

**Q2. Scope of "load in flight."** Init-only. `Store.ts:671`'s
`setOffsetRightDistance` reset only fires for `type === 'init'`; backward
and forward loads append data without clobbering scroll, so deferral
should gate on init-type specifically, not on a generic loading flag.

**Q3. Re-entry vs. direct apply on drain.** Full re-entry — when the init
callback fires, drain by calling the same `setVisibleRange(range)` path
(not the lower-level `_applyVisibleRange`). The queued range may fall
outside the new buffer's first bar, in which case it should compose with
the earlier `feature-setVisibleRange-fetch.md` work and trigger a
`loadRangeBackward` backfill.

**Q4. Dispose during pending.** Reject with a clear error
(`SetVisibleRangeAbortError` or similar). Avoids hanging promises and
gives consumers using `.catch` a signal that the chart was destroyed.

## Acceptance criteria

- `chart.setVisibleRange({from, to})` immediately after
  `new Superchart({...})` survives the initial `getBars(init)`.
- `chart.setVisibleRange({from, to})` immediately after `setSymbol(newS)`
  survives the init-load and the post-load offset reset.
- `chart.setVisibleRange({from, to})` immediately after
  `setPeriod(newP); setSymbol(newS)` (synchronous) lands on the post-symbol
  buffer with the consumer's range, not at live tail.
- The returned Promise resolves only after the range has actually been
  applied. A superseded VR resolves cleanly without applying. A VR queued
  when `chart.destroy()` runs rejects with an abort error.
- Calls made when no init-load is in flight keep the existing behavior:
  apply immediately, fetch missing history if needed (per
  `feature-setVisibleRange-fetch.md`), resolve when done.

## Out of scope

- Persisting visible range across app reloads (consumer concern, not SC).
- "Restore zoom level + snap to live" (TT's `barSpace` +
  `scrollToRealTime` semantic) — different mechanism, stays in app.
- Fetching missing history outside the loaded buffer — covered by the
  earlier `feature-setVisibleRange-fetch.md`.

## Altrady-side impact when this lands

- `chart-controller.js` drops:
  - `_pendingVR` field
  - `_onBarsLoaded` method
  - `_dataLoader.setOnBarsLoaded(this._onBarsLoaded)` registration in the constructor
  - the queue/drain branch in `setVisibleRange` — the wrapper itself can
    likely be deleted entirely if consumers call `sc.setVisibleRange`
    directly.
- `MarketTabSyncController.pendingVRRestore` and friends do NOT go away —
  TT's "remember zoom" is a `setBarSpace` + `scrollToRealTime` operation,
  not a `setVisibleRange` call. Different SC functions, different fix.
- `QuestionSyncController` is unaffected — VR-after-symbol-change for
  Quiz becomes possible by simply calling `sc.setVisibleRange(question.VR)`
  after the existing `sc.setSymbol`/`sc.setPeriod` calls. No queue,
  no extra fields, no extra hooks needed.
- Other consumers (grid-bot, customer-service, future) call
  `sc.setVisibleRange` directly and trust the contract.

## Follow-up: superseded `getBars` race

The queue/drain shipped in `851d1cb` works correctly when there is exactly
ONE init-type `getBars` in flight. It breaks when there are two.

### Trace (Store.ts file:line refs)

1. `setPeriod(newP)` → `Store.setPeriod` (`:542`) → `resetData` (`:938`) →
   `_processDataLoad('init')` (`:880`):
   - `_loading = true`, `_initLoadInFlight = true`
   - `void this._dataLoader.getBars(...)` — async **getBars₁** in flight
2. `setSymbol(newS)` (synchronously after) → `Store.setSymbol` (`:520`) →
   `resetData`:
   - `_processDataUnsubscribe()` (`:945-952`) — only calls
     `dataLoader.unsubscribeBar`. Does **not** abort getBars₁.
   - `_loading = false`
   - `_processDataLoad('init')` again — sets `_loading = true`,
     `_initLoadInFlight = true`, fires async **getBars₂** in flight
3. `setVisibleRange(range)` → checks `isInitLoadInFlight()` → `true` →
   queued in `_pendingVisibleRange`. ✓
4. **getBars₁ returns first** → `_addData(data, 'init', ...)` (`:665-681`)
   unconditionally:
   - `_clearData(); _dataList = data` — DATA FROM THE WRONG (period-only)
     LOAD swapped in
   - `setOffsetRightDistance(_offsetRightDistance)`
   - `_initLoadInFlight = false`
   - fires `onInitLoadComplete` → `_drainPendingVisibleRange` →
     `_pendingVisibleRange = null`, applies range against the wrong
     buffer, resolves the consumer's Promise
5. **getBars₂ returns later** → `_addData('init')` again:
   - swaps in correct symbol's data
   - `setOffsetRightDistance(_offsetRightDistance)` — resets scroll
   - fires `onInitLoadComplete` → drain runs but queue is null → no-op
6. Final state: chart shows correct symbol's data at live tail. The
   range applied in step 4 was overwritten by step 5's offset reset.

### Why Altrady can't work around this

- `setPeriod` and `setSymbol` are synchronous. No Promise to await.
- No SC API exists to update period state without triggering a load
  (so we can't "set period silently then setSymbol once").
- No SC API exists to combine symbol+period into a single init load.
- The race is in SC's internal getBars cancellation. Listening on the
  Altrady side for the second `onInitLoadComplete` would re-introduce
  exactly the `pending*` machinery this feature aimed to delete, and
  would still need a way to know "is another init load coming?"

### Proposed SC fix

Add a generation/token to `_processDataLoad`. Each call increments a
`_initLoadGeneration` counter and captures the current value. The
`getBars` callback checks: if its captured generation `!==` the current
generation, it's superseded — skip `_addData`, skip `_initLoadInFlight =
false`, skip `onInitLoadComplete`. Only the most recent init load's
callback fires the completion event and drains the queue.

This keeps the public `setVisibleRange` contract intact and only changes
the internal behavior of cancelled-but-still-in-flight `getBars`
callbacks.

### Acceptance criteria for the follow-up

Given:
```js
sc.setPeriod(newPeriod)
sc.setSymbol(newSymbol)
await sc.setVisibleRange(range)
```

- The Promise resolves only after `getBars` for `newSymbol`+`newPeriod`
  has completed and the range has been applied.
- The chart's final scroll position reflects `range`, not live tail.
- The superseded `getBars` callback (from the period-only load) does NOT
  fire `onInitLoadComplete` and does NOT swap data into `_dataList`.
