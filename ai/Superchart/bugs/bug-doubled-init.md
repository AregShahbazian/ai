# Bug: Doubled _processDataLoad on init causes intermittent corrupted chart

## Symptoms

On chart load, candles appear "cut" — a range of candles is shown, then an abrupt
jump to an earlier range, then continues to current time. The same market randomly
shows correctly or corrupted across reloads (roughly 50/50).

Only observed on resolution `120` (2hr candles). Not seen on `60` (1hr). The timing
of async `getBars` responses varies by resolution, making the race more or less likely.

## Reproduction

1. Load any market on 2hr resolution
2. Reload multiple times
3. Some loads show correct chart, some show "cut-time" chart with overlapping ranges

No replay or special features needed — happens on plain chart load.

## Root Cause

The Superchart constructor calls `setSymbol`, `setPeriod`, and `setDataLoader` during
initialization. Each of these calls `resetData()`, which:

1. Resets `this._loading = false`
2. Calls `this._processDataLoad('init')`

Since `resetData` resets the `_loading` guard before each `_processDataLoad`, multiple
init calls get through. On a typical load, 3 `_processDataLoad('init')` calls fire
(one per `resetData`), resulting in 2 parallel `getBars` requests with identical params.

### The race

Two init `getBars` fire in parallel (#1 and #2). After #1 resolves:
- `_addData(data, 'init')` loads 500 candles
- Backward scroll triggers, fetching older candles (#3)
- #3 resolves, `_addData(data, 'backward')` extends to 1000+ candles

Then #2 resolves (late):
- `_addData(data, 'init')` **replaces** the data list with 500 candles (init replaces, not appends)
- The backward scroll data from #3 is lost
- A new backward scroll triggers, but now the data list has a gap

The result: overlapping or discontinuous candle ranges visible on the chart.

### Stack traces from _processDataLoad

Observed on a typical load (3 init calls from constructor):

```
#1: StoreImp.setSymbol → resetData → _processDataLoad('init')
#2: StoreImp.setPeriod → resetData → _processDataLoad('init')
#3: StoreImp.setDataLoader → resetData → _processDataLoad('init')
```

All three have `loading: false` because each `resetData` resets it.

Note: a 4th init can occur if the consumer calls `setSymbol` after construction
(e.g., to sync React state). This was fixed on the consumer side by skipping
the redundant call on mount, but the constructor's 3 calls remain.

## Expected Fix

`resetData` should cancel any in-flight init before starting a new one. Options:

1. **Generation counter for data loads** — increment on each `resetData`, check in the
   `getBars` callback. If stale, discard the result. Similar to the replay engine's
   generation counter.

2. **Single init per tick** — debounce `_processDataLoad('init')` so multiple
   synchronous `resetData` calls collapse into one init.

3. **Skip redundant resets in constructor** — `setSymbol`, `setPeriod`, `setDataLoader`
   each call `resetData` independently. The constructor could set all three first,
   then call `resetData` once.

Option 3 is the simplest and most targeted. Option 1 is the most robust (also prevents
races from `setSymbol` during replay, which causes the same doubled-init pattern).
