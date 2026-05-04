# Bug — zoom drifts to unrelated time periods after `setVisibleRange` jump

**Status:** Open
**Audience:** SC library maintainers
**Reporter:** Areg (Altrady)
**Date observed:** 2026-05-04
**SC branch / commit:** `async-setVisibleRange` @ `c8f7e92f` (submodule), root @ uncommitted continuation of `5b32838`

---

## Symptom

After jumping to a historical window via `superchart.setVisibleRange(...)`, the
**zoom gesture** (touchpad two-finger vertical scroll → `mouseWheelVertEvent`
→ `Store.zoom`) causes the visible range to drift to **unrelated time
periods**, rather than expanding/contracting around the cursor as expected.

Reproduced in `.storybook/api-stories/Sync.stories.tsx`:

| Step | Action                                  | Visible range                                |
|------|-----------------------------------------|----------------------------------------------|
| 0    | jump to Jan 26 2026 (5-day window)      | `2026-01-26 21:00 — 2026-01-31 10:00`        |
| 1    | zoom out (two-finger scroll, touchpad)  | `2025-10-03 15:00 — 2025-10-14 01:00` ⚠️     |
| 2    | zoom in                                 | `2026-01-03 14:00 — 2026-01-09 13:00` ⚠️     |
| 3    | zoom in fully                           | `2026-04-15 19:00 — 2026-04-16 19:00` ⚠️     |

Each zoom step shifts the **center** of the visible range by weeks/months, and
the direction of the shift is inconsistent between zoom-in and zoom-out steps.
Magnitude scales with how far back from the latest live candle the user is
viewing.

## What works (does not exhibit the bug)

- Zooming when the **latest live candle is visible** (i.e., chart is at
  `_lastBarRightSideDiffBarCount ≥ 0`). The cursor anchor behaves correctly.
- Zooming during an **active replay session**, regardless of how far back in
  time the cursor is. Replay clamps `_dataList` to the cursor (see
  `ReplayEngine` calling `_dataList.pop()` etc.), so
  `_lastBarRightSideDiffBarCount` remains close to zero.

The common thread: the bug only manifests when `_dataList` extends far past
the rightmost rendered bar — i.e., when `_lastBarRightSideDiffBarCount` is
strongly negative. After `setVisibleRange(historical)`, this counter is set
to roughly `-(dataList.length - 1 - toIndex)`; for a Jan 26 window with
~3 months of buffer to "now", that is in the range −2000 to −3000.

## Reproduction

1. `cd /home/areg/git/altrady/Superchart && pnpm storybook` (port 6007).
2. Open `API › Sync`.
3. In the floating panel, set "jump to" to a date several months in the past
   and "window" to 1D or 1W. Click "jump".
4. Two-finger scroll vertically on the touchpad over the chart canvas.
5. Observe the `range:` line in the panel — it jumps to unrelated dates.

The bug requires the **`async-setVisibleRange` branch** (the `setVisibleRange`
fetch behavior in `packages/coinray-chart/src/Chart.ts:1108`). Without that
branch, `setVisibleRange` to a historical window is a no-op (clamps to first
loaded bar), so the buggy state cannot be entered.

## Affected code paths

### Where `_lastBarRightSideDiffBarCount` ends up strongly negative

`packages/coinray-chart/src/Chart.ts:1132` — `_applyVisibleRange`:

```ts
private _applyVisibleRange (range: { from: number; to: number }): void {
  const dataList = this.getDataList()
  if (dataList.length === 0) return
  const fromIndex = binarySearchNearest(dataList, 'timestamp', range.from)
  const toIndex = binarySearchNearest(dataList, 'timestamp', range.to)
  const barCount = Math.max(toIndex - fromIndex + 1, 1)
  const totalBarSpace = this._chartStore.getTotalBarSpace()
  const newBarSpace = totalBarSpace / barCount
  this._chartStore.setBarSpace(newBarSpace)
  this.scrollToDataIndex(toIndex)            // ← drives LBSDBC = -(length-1-toIndex)
}
```

After the jump, the chart is showing indices `[~from, toIndex]` while the
buffer extends all the way to `dataList[length-1]` (the live candle). This
is the "zoom-fragile" state.

### The zoom math

`packages/coinray-chart/src/Store.ts:1364` — `Store.zoom`:

```ts
const x = zoomCoordinate.x!
const floatIndex = this.coordinateToFloatIndex(x)
const prevBarSpace = this._barSpace
const barSpace = this._barSpace + scale * (this._barSpace / SCALE_MULTIPLIER)
this.setBarSpace(barSpace, () => {
  this._lastBarRightSideDiffBarCount += (floatIndex - this.coordinateToFloatIndex(x))
})
```

Cursor anchor: take `floatIndex` at `x`, change `_barSpace`, then nudge
`_lastBarRightSideDiffBarCount` so the same `x` resolves to the same
`floatIndex` again. Math is symmetric — purely analytical, this should
keep the cursor pinned regardless of how negative `LBSDBC` is.

### Where the visible range can shift on prepend

`packages/coinray-chart/src/Store.ts:682` — `_addData('forward')`:

```ts
case 'forward': {
  this._dataList = data.concat(this._dataList)
  this._dataLoadMore.forward = realMore.forward
  adjustFlag = dataLengthChange > 0
  break
}
```

Note: forward-prepend does **not** adjust `_lastBarRightSideDiffBarCount`
(unlike the `'backward'` case at `:675` which does
`this._lastBarRightSideDiffBarCount -= dataLengthChange`). This is correct
on its face — `LBSDBC` is measured from the *rightmost* bar, which doesn't
change when we prepend at the left — but combined with auto-load triggered
from `_adjustVisibleRange`, it produces a chain of state mutations that are
plausibly miscompounding. See "Investigation paths" below.

### Auto-load on left-edge

`packages/coinray-chart/src/Store.ts:868` — at the end of `_adjustVisibleRange`:

```ts
if (from === 0) {
  if (this._dataLoadMore.forward) {
    this._processDataLoad('forward')
  }
}
```

After `setVisibleRange(historical)`, `from === 0` is true (the visible range
hits the left edge of the buffer), so any zoom-out that re-runs
`_adjustVisibleRange` will spawn a `getBars(type='forward')` to fetch ~500
older bars. The async callback goes through `_addData('forward')`, which
re-runs `_adjustVisibleRange`, which can re-trigger another forward load if
the new visible range still touches index 0. With the touchpad firing many
wheel events in quick succession, this can chain.

## Investigation paths / hypotheses

**Note:** static analysis traces I ran with realistic numbers (totalBarSpace
1200, period 1H, range Jan 26–31 with `_dataList` of ~2400 bars) did *not*
reproduce a multi-month drift in any single zoom step. The cursor-anchor
math and the `_addData('forward')` / `_adjustVisibleRange` interaction both
appear correct in isolation. The empirical drift is much larger than the
analytical model predicts, so something is happening I haven't pinpointed.

Likely culprits, ranked:

1. **Cascading auto-load + cursor re-anchor over many wheel events.**
   Touchpad scrolls fire many small wheel events. Each one runs zoom →
   `_adjustVisibleRange` → potentially `_processDataLoad('forward')`. A
   load completion mid-gesture flips `_loading` back to false, allowing the
   next wheel event to spawn another load. If any one of these intermediate
   `_adjustVisibleRange` runs computes `floatIndex` against a transient
   state, the cursor anchor could drift cumulatively. **Worth instrumenting
   `coordinateToFloatIndex(x)` returns and `LBSDBC` deltas across a single
   touchpad gesture.**

2. **Duplicate bars from `_processDataLoad('forward')`.**
   `_processDataLoad('forward')` in `Store.ts:917` passes
   `params.timestamp = this._dataList[0]?.timestamp`. The createDataLoader
   adapter (in `src/lib/datafeed/index.ts:213`) translates this into a
   `getBars` call with `to = floor(timestamp/1000)`. If the datafeed
   includes the bar at `to` (boundary inclusive) in its response, that bar
   is a duplicate of the existing `_dataList[0]`. The `'forward'` branch
   of `_addData` at `Store.ts:682` does `data.concat(this._dataList)` with
   **no de-duplication**. Multiple forward loads → accumulating duplicates →
   `binarySearchNearest` and `dataIndexToTimestamp` produce shifted values.
   `loadRangeBackward` (which we added in `Store.ts:754`) does dedup via
   `data.filter(d => d.timestamp < firstTimestamp)`; the regular
   `_addData('forward')` path does not. **Worth verifying with a
   `console.assert` that `_dataList` timestamps are strictly increasing
   after each `_addData('forward')`.**

3. **Bar-space limit early-return swallowing the cursor adjustment.**
   `setBarSpace` in `Store.ts:975` early-returns *before* invoking
   `adjustBeforeFunc` if the requested `barSpace` is outside `[1, 50]` or
   equals the current value. In the zoom path, the closure that adjusts
   `_lastBarRightSideDiffBarCount` is `adjustBeforeFunc`. So a sequence
   where the bar-space delta is small enough to round to no change, or
   where we hit the `min`/`max` clamp, leaves `LBSDBC` un-adjusted while
   `_barSpace` may have already been touched by surrounding logic. Less
   likely as a primary cause but worth ruling out.

4. **`scrollToDataIndex` inside `_applyVisibleRange` racing the
   auto-load.** `_applyVisibleRange` calls `setBarSpace(newBarSpace)`
   first, which fires `_adjustVisibleRange`. At that point we're using the
   *old* `LBSDBC` with the *new* `_barSpace`, so the visible range is
   wrong; if `from === 0` evaluates true here, an auto-load fires. Then
   `scrollToDataIndex(toIndex)` runs and snaps `LBSDBC` to the right
   value. If the in-flight forward-load returns *between* those two steps
   (extremely tight window, but possible if the loader resolves
   synchronously, e.g. a memoized cache hit), the `_dataList` has shifted
   indices when `scrollToDataIndex` does its math.

## What replay does differently

`ReplayEngine` mutates `_dataList` directly (`_dataList.pop()` /
`_dataList[length-1] = partial` in `replay/ReplayEngine.ts`), so
`_dataList[length-1]` is always at or near the replay cursor. That keeps
`_lastBarRightSideDiffBarCount` close to 0 even when "the last drawn candle"
is months in the past from wall-clock now. The forward-load-on-left-edge
path is also short-circuited because the engine sets `isInReplay() = true`
and several store methods check that flag.

`setVisibleRange` does not have this kind of buffer trimming. It loads
*more* data into `_dataList` rather than narrowing it, so `_dataList[0]` is
the historical jump target while `_dataList[length-1]` is still the live
candle.

## Suggested next steps for whoever fixes this

1. Add `console.log` in `Store.zoom` printing `floatIndex`, `x`,
   `_dataList.length`, `_lastBarRightSideDiffBarCount` before/after the
   `setBarSpace` callback, and replay the user's gesture in the storybook
   to see which value diverges.
2. Add an assertion in `_addData('forward')` that timestamps remain
   strictly increasing — if it fires, hypothesis (2) is confirmed and the
   fix is dedup at the seam (or a better `to` boundary in the loader
   adapter).
3. Consider: should auto-load-on-left-edge be **disabled** while a
   `setVisibleRange` is in flight or has just resolved? The user's request
   was explicit ("show me this window"); auto-fetching past it on the
   first wheel event may be undesirable. (This is a UX call separate from
   the drift bug, but they interact.)
4. As a defensive belt-and-braces fix: in the zoom callback, verify the
   resulting `_lastBarRightSideDiffBarCount` does not move the cursor's
   floatIndex by more than some epsilon — if it does, fall back to the
   pre-zoom `LBSDBC`.

## Files referenced

- `packages/coinray-chart/src/Chart.ts:1108` — `setVisibleRange`
- `packages/coinray-chart/src/Chart.ts:1132` — `_applyVisibleRange`
- `packages/coinray-chart/src/Store.ts:647` — `_addData`
- `packages/coinray-chart/src/Store.ts:754` — `loadRangeBackward` (added in this branch)
- `packages/coinray-chart/src/Store.ts:880` — `_processDataLoad`
- `packages/coinray-chart/src/Store.ts:975` — `setBarSpace`
- `packages/coinray-chart/src/Store.ts:1364` — `Store.zoom`
- `packages/coinray-chart/src/Store.ts:1091` — `coordinateToFloatIndex`
- `src/lib/datafeed/index.ts:180` — `createDataLoader.getBars`
- `.storybook/api-stories/Sync.stories.tsx` — repro story
