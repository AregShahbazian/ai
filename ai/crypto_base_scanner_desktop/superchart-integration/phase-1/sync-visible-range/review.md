# Review: Sync Visible Range for SuperChart

## Round 1: Double restore on mount (2026-03-18)

### Bug 1: `restoreVisibleRange` called twice on initial mount

**Root cause:** Two independent code paths both trigger restore on mount:

1. The `[readyToDraw]` effect fires when `readyToDraw` becomes true and calls
   `restoreVisibleRange()`.
2. The `[coinraySymbol]` effect fires on mount with the initial symbol. It calls
   `setSymbol()` (redundant — chart was already constructed with this symbol) and sets
   `pendingVRRestore.current = true`. When the chart finishes loading data and fires
   `onVisibleRangeChange`, the callback sees the flag and calls
   `restoreVisibleRangeRef.current()`.

Both paths run during the initial mount sequence.

**Attempted fix (reverted):** Skip `[coinraySymbol]` effect on mount with
`initialMountRef`. This removed the working restore path (path 2). The `[readyToDraw]`
effect (path 1) fires before data has loaded — `readyToDraw` only means the klinecharts
instance exists, not that candles are loaded. The datafeed delivers candles after and
resets the viewport, overwriting the restore.

**Attempted fix 2 (reverted):** Set `pendingVRRestore` in init `useEffect` instead.
The `onVisibleRangeChange` from the initial data load fires at a different timing than
from a `setSymbol()` reload — the initial load's event fires before the chart has fully
settled, so `setVisibleRange()` gets overwritten.

**Final fix:** Remove the `[readyToDraw]` restore effect (the too-early, ineffective
call). Let `[coinraySymbol]` fire on mount — the redundant `setSymbol()` triggers a data
reload whose `onVisibleRangeChange` fires at the right timing for restore. Single
effective restore call via `pendingVRRestore` for both mount and tab switch.

The redundant `setSymbol()` on mount is harmless and creates the correct timing for
restore. Both mount and tab switch now use the same path: `[coinraySymbol]` effect →
`setSymbol()` → data loads → `onVisibleRangeChange` → `pendingVRRestore` → restore.

### Verification

- [x] On mount with stored VR: restore fires once (via pendingVRRestore), zoom level
  is correctly applied
- [x] Tab switch between tabs with different stored VRs: each tab restores its own
  zoom level independently
- [x] Without stored VR: no restore attempted, chart shows default zoom

## Round 2: VR shrinks on every restore (2026-03-19)

### Bug 2: Gradual zoom-in on each `restoreVisibleRange` call

**Symptom:** With `miscRememberVisibleRange` enabled, each restore cycle shrinks the
visible range by ~10%. Calling `restoreVisibleRange()` repeatedly shows the left edge
moving forward while the right edge stays at `now`:

```
visibleRange: 17-03-26 04:00:00 → 19-03-26 13:00:00 (2.4days)
visibleRange: 17-03-26 10:00:00 → 19-03-26 13:00:00 (2.1days)  // after restore
visibleRange: 17-03-26 15:00:00 → 19-03-26 13:00:00 (1.9days)  // after restore
visibleRange: 17-03-26 19:00:00 → 19-03-26 13:00:00 (1.8days)  // after restore
```

This happens on every app reload or tab switch with a stored VR.

**Root cause:** The design copied TV's restore formula (`duration * 0.9`) but missed
that TV's `chart.setVisibleRange(range, {percentRightMargin})` handles the right margin
*internally*. Here's the difference:

- **TV**: `setVisibleRange({from: now-D*0.9, to: now}, {percentRightMargin: 10})`
  - TV widget positions the data range in 90% of the viewport, adds 10% empty space
    on the right
  - The viewport width in time = `D*0.9 / 0.9 = D`
  - `onVisibleRangeChanged` reports `to - from ≈ D` (matches stored duration)
  - Persist stores `D` → next restore reads `D` → no drift

- **SC**: `setVisibleRange({from: now-D*0.9, to: now})` (no `percentRightMargin` option)
  - SC sets the range directly — viewport shows exactly `D*0.9`
  - `onVisibleRangeChange` reports `to - from = D*0.9`
  - Persist stores `D*0.9` → next restore applies 0.9 again → `D*0.81` → drift

Each cycle: `D → D*0.9 → D*0.81 → D*0.729 → ...`

**Fix:** Remove the `* 0.9` correction from `restoreVisibleRange()`. SC's
`setVisibleRange` doesn't support `percentRightMargin`, so the correction just causes
drift. Restore with the full duration: `{from: now - duration, to: now}`. The latest
candle sits at the right edge (no empty margin), but the zoom level is stable.

**Files:** `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`
(`restoreVisibleRange` method — remove `percentRightMargin` and `correctedDuration`
logic, use `duration` directly)

**Design notes:** The design's restore formula (`now - duration*0.9`, described as
"TV-style") is incorrect for SC. TV's formula works because `setVisibleRange` accepts
`{percentRightMargin}` which widens the viewport, so the reported duration matches the
stored one. SC's `setVisibleRange` has no such option. The restore formula should be
`now - duration` (no correction). The "same formula as TV" framing doesn't apply — the
APIs differ.

### Verification

- [ ] Enable "Remember visible range", zoom to a range, note the duration
- [ ] Call `chartController.restoreVisibleRange()` multiple times — duration stays stable
- [ ] Switch tabs back and forth — zoom level preserved without drift
- [ ] After restore, manually scroll/zoom — new range persists normally
