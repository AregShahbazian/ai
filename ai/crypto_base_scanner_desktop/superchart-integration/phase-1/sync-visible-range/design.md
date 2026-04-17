# Design: Sync Visible Range for SuperChart

## Architecture

### VR state lives in `SuperChartContextProvider`

Add `visibleRange` (`{from, to}` in unix seconds) as React state in
`SuperChartContextProvider`. Expose it via the existing `useSuperChart()` hook — no
separate context needed.

SC overlays already call `useSuperChart()` — they just read `visibleRange` from the
same object instead of importing TV's `VisibleRangeContext`.

### No shared hook with TV

TV's `useVisibleRange` hook is tightly coupled to TV (it computes duration, calls
`handleTVVisibleRangeChanged`). SC's needs are simpler (store `{from, to}` directly),
so we add VR handling inline in the context provider rather than creating a parallel hook.

### Persist format: `{from, to}` (stores richer data for future use)

SC stores `visibleRangeFromTo: {from, to}` on the market tab. TV continues using
`visibleRange` (duration). Both gated by `miscRememberVisibleRange`.

### Restore uses duration derived from `{from, to}` (TV-style)

On restore, compute `duration = to - from` from the stored range, then restore as
`{from: now - duration*0.9, to: now}` — same formula as TV. This keeps the latest
candles in view and only preserves the zoom level. The absolute `{from, to}` is stored
for future use (e.g., exact position restore) but not used for restore yet.

SuperChart exposes `setVisibleRange({from, to})` (unix seconds) for the actual call.

## Data Flow

```
onVisibleRangeChange({from, to})    ← SuperChart fires (unix seconds)
    │
    ├─► setVisibleRange({from, to}) ← React state in context provider
    │       │
    │       └─► overlays re-render, filter by {from, to}
    │
    └─► if miscRememberVisibleRange:
            debounce 500ms
            MarketTab.setVisibleRangeFromTo({from, to})
            └─► Redux + persist

[tab switch / symbol ready]
    │
    └─► if miscRememberVisibleRange && visibleRangeFromTo:
            duration = to - from
            newTo = now, newFrom = now - duration * 0.9
            chart.setVisibleRange({from: newFrom, to: newTo})
```

## Key Decisions

### SC trade filter units

The current SC trades overlay compares `time * 1000` against `from`/`to`. This is wrong
— both `time` and SC's `{from, to}` are in unix seconds. The `* 1000` is a latent bug
(never executes because `from`/`to` are always undefined today). Fix: remove `* 1000`
to match TV's pattern (`time >= from && time < to`).

### When to subscribe

Subscribe to `onVisibleRangeChange` once, unconditionally (not gated by
`miscRememberVisibleRange`). The setting only gates persistence — local state always
updates so overlay filtering works regardless.

### When to restore

Restore on chart ready (after `_notifyReady()`) and on tab switch (when `marketTabId`
changes and the chart already exists). Same timing as TV's `updateVisibleRange()` which
runs on `onReady` and `activeChanged`.

### Cleanup

The `onVisibleRangeChange` method returns an unsubscribe function. Call it in the init
`useEffect` cleanup. Also clear the debounce timeout on unmount.
