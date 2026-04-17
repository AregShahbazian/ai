---
id: sc-sync-vr
---

# PRD: Sync Visible Range for SuperChart

## Goal

Wire up bidirectional visible-range (VR) syncing for SuperChart so that:
1. Overlay filtering works (trades/bases only render what's on screen)
2. The user's zoom level is remembered and restored across tab switches

## Background

### How TV does it today

1. **Chart → App**: TV fires `onVisibleRangeChanged({from, to})` (unix seconds).
   `use-visible-range.js` updates local React state (`VisibleRangeContext`) immediately.
   If `miscRememberVisibleRange` is enabled, it debounces 500ms then stores the
   **duration** (`to - from`) to `marketTab.visibleRange` via
   `MarketTab.setVisibleRange(duration)`.

2. **App → Chart**: On tab switch / symbol change, `useTradingView.updateVisibleRange()`
   reads the stored duration, computes `{from, to}` as `{now - duration*0.9, now}` with
   a 10% right margin, and calls `chart.setVisibleRange({from, to})`.

3. **Overlay filtering**: TV overlays (trades, bases) read `{from, to}` from
   `VisibleRangeContext` and filter items to only draw those within the visible window.

### Current SC state

- SC has **no** VR syncing. `onVisibleRangeChange` is not wired.
- SC overlays import `VisibleRangeContext` from TV's context, but SC is rendered outside
  TV's `ChartContextProvider`. They get the **default empty context** (`{visibleRange: {}}`),
  so `from` and `to` are always undefined.
- The SC overlay filter guards (`if (from && to)`) pass through — all trades/bases are
  drawn regardless of what's visible on screen.

### SuperChart API available

The SuperChart library now provides both sides of VR syncing:

- **Read**: `onVisibleRangeChange(callback)` — fires `{from, to}` in unix seconds on
  scroll/zoom. Returns an unsubscribe function. Internally clamps `realTo` to the last
  valid data index (prevents out-of-bounds when there's empty space after the last candle).
- **Write**: `setVisibleRange({from, to})` — scrolls/zooms the chart viewport to show the
  given time range (unix seconds). Converts to milliseconds internally for klinecharts.

### What `visibleRange` is used for

| Consumer | What it does | File |
|---|---|---|
| TV trades overlay | Filters trades to `time >= from && time < to` | `tradingview/trades.js` |
| TV bases overlay | Filters bases: `formedAt < to`, respected `>= from` | `tradingview/bases.js` |
| SC trades overlay | Same filter, but currently no-ops (empty VR) | `super-chart/overlays/trades.js` |
| SC bases overlay | Same filter, but currently no-ops (empty VR) | `super-chart/overlays/bases.js` |
| `updateVisibleRange()` | Restores VR on tab switch (TV only) | `use-trading-view.js` |
| `miscRememberVisibleRange` | Gates whether VR is persisted to market tab | `use-visible-range.js`, `use-trading-view.js` |

## Requirements

### R1: Chart → App (SC fires VR change)

When the user scrolls or zooms SuperChart:

- Wire `chart.onVisibleRangeChange(callback)` — callback receives `{from, to}` (unix seconds)
- Update local React state with `{from, to}` so SC overlays can filter immediately
- If `miscRememberVisibleRange` is enabled, debounce 500ms then persist to market tab
- Store `{from, to}` to `visibleRangeFromTo` on the market tab — see R3

### R2: App → Chart (restore zoom level on tab switch)

When switching back to a tab that has a stored VR:

- If `miscRememberVisibleRange` is enabled and the market tab has a stored `visibleRangeFromTo`
- Compute duration from stored `{from, to}`: `duration = to - from`
- Restore as `{from: now - duration*0.9, to: now}` with latest candles in view (TV-style)
- Call `chart.setVisibleRange({from, to})` with the computed range
- This happens after symbol/period are loaded, same as TV

### R3: Store `visibleRangeFromTo` separately in market tab

- Add a new field `visibleRangeFromTo: {from, to}` to the market tab state
- Keep the existing `visibleRange` (duration in seconds) untouched — TV still uses it
- SC reads/writes `visibleRangeFromTo`, TV reads/writes `visibleRange`
- Both are gated by the same `miscRememberVisibleRange` setting

**Why separate?**
- TV stores duration, SC stores absolute `{from, to}` — different formats
- Storing `{from, to}` preserves richer data for future use (e.g., exact position restore)
- For now, restore uses duration derived from `{from, to}` (TV-style zoom level restore)
- Don't break TV's existing behavior

### R4: SC overlays filter by VR

SC overlays (trades, bases) must filter items based on the current visible range:

- Trades: only draw trades with `time >= from && time < to`
- Bases: only draw bases where `formedAt < to` and (if respected) `respectedAt >= from`
- This must use SC's own VR state, not TV's `VisibleRangeContext`

### R5: SC overlays get VR from SC's own context

- SC overlays currently import `VisibleRangeContext` from TV's context provider
- They must instead read VR from SC's own context (or a new SC-specific VR context)
- This decouples SC from TV's context tree entirely for VR

### R6: `miscRememberVisibleRange` behavior

- When `false` (default): VR changes are NOT persisted to market tab, but local React
  state still updates (so overlay filtering works in real-time)
- When `true`: VR changes are persisted (debounced 500ms) and restored on tab switch
- Same setting controls both TV and SC — no separate toggle

## Non-Requirements

- **No changes to TV**: TV's VR behavior must remain exactly as-is
- **No changes to SuperChart library**: All needed APIs exist (`onVisibleRangeChange`,
  `setVisibleRange`) — we only consume them
- **No changes to `miscRememberVisibleRange` UI**: Same checkbox controls both charts
- **No new UI elements**: This is purely data plumbing
- **Replay mode VR interaction**: Out of scope (Phase 5)
- **VR restore precision**: Best-effort match of the stored range

## Data Flow

```
User scrolls/zooms SC
    |
    v
chart.onVisibleRangeChange({from, to})   // unix seconds, realTo clamped
    |
    v
Update SC's local VR state (React)  ──> SC overlays re-filter trades/bases
    |
    v
If miscRememberVisibleRange:
    debounce 500ms
    |
    v
    MarketTab.setVisibleRangeFromTo({from, to})
    |
    v
    Persisted to Redux + saved

[Tab switch back to this tab]
    |
    v
If miscRememberVisibleRange && visibleRangeFromTo exists:
    |
    v
    duration = to - from
    newTo = now, newFrom = now - duration * 0.9
    chart.setVisibleRange({from: newFrom, to: newTo})   // restores zoom level
```

## Files (expected scope)

| File | Change |
|---|---|
| `src/actions/constants/market-tabs.js` | Add `visibleRangeFromTo: undefined` to default state |
| `src/models/market-tabs/market-tab.js` | Add `visibleRangeFromTo` getter + `setVisibleRangeFromTo` method |
| `src/models/market-tabs/market-tabs-selectors.js` | Add `selectMarketTabVisibleRangeFromTo` selector |
| `src/containers/trade/trading-terminal/widgets/super-chart/super-chart.js` | Wire `onVisibleRangeChange`, VR state, persist logic, restore via `setVisibleRange` |
| `src/containers/trade/trading-terminal/widgets/super-chart/context.js` | Expose VR state via SC context |
| `src/containers/trade/trading-terminal/widgets/super-chart/overlays/trades.js` | Read VR from SC context instead of TV's `VisibleRangeContext` |
| `src/containers/trade/trading-terminal/widgets/super-chart/overlays/bases.js` | Read VR from SC context instead of TV's `VisibleRangeContext` |

## Testing Steps

1. Open Trading Terminal with SuperChart visible
2. **VR filtering works**: Zoom into a narrow range on SC. Verify trades/bases outside
   the visible window are not drawn. Zoom out — more trades/bases should appear.
3. **Persist + restore**: Enable "Remember visible range" in chart settings. Zoom to a
   specific range. Switch to another tab, then switch back. Verify the zoom level is
   approximately restored.
4. **Persist disabled**: Disable "Remember visible range". Zoom/scroll. Switch tabs and
   back. Verify the chart resets to default range (not the previous zoom).
5. **TV unaffected**: Verify TV chart's VR filtering, persist, and restore all still work
   exactly as before.
6. **No echo loops**: Rapidly zoom/scroll. Verify no console errors, no infinite
   re-renders.
