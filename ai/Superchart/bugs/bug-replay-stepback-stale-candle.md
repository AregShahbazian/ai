# Bug: Replay `stepBack()` emits stale candle from live-data tail

## Symptoms

In a replay session that was started mid-history via
`engine.setCurrentTime(time)` (i.e. random-bar / pick-on-chart entry, not a
zero-time replay), pressing **Step Back** once after pausing produces a
visual artifact: the chart renders a single "weird" candle far past the
replay cursor, near the right edge of the chart. Pressing **Step Forward**
once after that fixes the artifact (the engine emits the correct next candle
and the chart re-renders cleanly). Stepping back again immediately
re-introduces the same artifact.

The artifact does **not** appear in:
- A replay session played from the very start of available data (no
  `setCurrentTime` mid-history call).
- Smart-replay sessions (Altrady-side: smart sessions rebuild trading info
  from a backend response after every step back, which masks any chart-side
  artifact — but the underlying engine bug still happens).

## Reproduction

1. In Altrady's Trading Terminal (or any SC consumer), open a market and
   start a default replay session via "Random Bar" (chooses a candle-aligned
   start time mid-history; ends up calling `engine.setCurrentTime(T)`).
2. Wait for replay to be `ready`.
3. Click **Play**, let the replay run forward for a few seconds, then click
   **Pause**.
4. Click **Step Back** once.
5. Observe the chart: a "weird" candle appears at the right edge, well past
   where the replay cursor actually is. Subscribers to `onReplayStep` also
   receive a payload with garbage time/price values (see logs below).
6. Click **Step Forward** once. The artifact is gone.
7. Click **Step Back** again. The same artifact reappears with **identical**
   candle values.

## Evidence — `onReplayStep` payloads

Logged via the consumer's wrapper around `engine.onReplayStep` (the consumer
just dumps `{direction, candle.time, candle.open, candle.close,
engine.getReplayCurrentTime(), engine.getReplayBufferLength()}`):

### Forward play (correct)

Each step advances `currentTime` by exactly 3,600,000 ms (1h) on a 1h chart.
Candle prices are 2022 BTC values (~$36k–$38k):

```
onReplayStep direction=forward currentTime=1643360400000 open=36658.46 close=36486.09 bufferLength=36914
onReplayStep direction=forward currentTime=1643364000000 open=36486.10 close=36615.35 bufferLength=...
onReplayStep direction=forward currentTime=1643367600000 open=36615.35 close=36448.28 bufferLength=...
... (40 more forward steps, all consistent)
onReplayStep direction=forward currentTime=1643511600000 open=37931.75 close=37951.80 bufferLength=36872
```

State at pause: `currentTime=1643511600000` (2022-01-30T01:00:00 UTC),
`bufferLength=36872`.

### First step back (BUG)

Consumer computes `targetTime = currentTime − resolutionMs`:

```
_stepBackOnce BEFORE: currentTime=1643511600000 targetTime=1643508000000 ms=3600000 bufferLength=36872
```

Then `engine.stepBack()` is called. The engine fires:

```
onReplayStep direction='back'
  candleOpen:  42283.58
  candleClose: 71172.62
  currentTime: 1776042000000     ← engine.getReplayCurrentTime() reports this
  bufferLength: 36873
```

`bufferLength` correctly increments from 36872 → 36873 (one candle pulled
out of the "drawn" stack and back into the buffer).

But the candle and the reported `currentTime` are **wrong**:
- Expected: `currentTime` should be `1643508000000` (2022-01-30T00:00:00 UTC,
  the previous candle in the replay buffer, with 2022 BTC prices).
- Actual: `currentTime = 1776042000000` (2026-04-13T01:00:00 UTC). That is
  ~2 days before the consumer's wall clock (`new Date() ≈ 2026-04-15`).
- The OHLC values (`42283.58 → 71172.62`) match real BTC prices for
  ~2026-04-13, not for 2022.

### Step forward after the bad step back (recovery)

```
handleStep ENTER currentTime=1776042000000   ← consumer's Redux is now polluted with the bogus time
onReplayStep direction='forward'
  candleOpen:  37931.75                       ← back to 2022 prices
  candleClose: 37951.80
  currentTime: 1643511600000                  ← back to the paused timestamp
```

The engine has the correct next candle in its buffer — only the `stepBack`
emit was bad.

### Subsequent step backs are byte-identical

Forward to a different cursor (`1643536800000`), then Step Back again:

```
_stepBackOnce BEFORE: currentTime=1643536800000 targetTime=1643533200000 bufferLength=36865
onReplayStep direction='back'
  candleOpen:  42283.58            ← identical to the first bad emit
  candleClose: 71172.62            ← identical
  currentTime: 1776042000000       ← identical
```

Same phantom candle, every time. **Not random memory corruption** — it's a
fixed reference somewhere in the engine.

## Hypothesis

The candle that `engine.stepBack()` emits via `onReplayStep` looks like the
**latest candle from the chart's live-data array** (or whatever array holds
the data that was loaded into the chart before replay started). Random-start
replay calls `engine.setCurrentTime(T)` to park the cursor mid-history; this
seems to leave the live tail loaded somewhere in addition to the replay
buffer. When `stepBack()` constructs the `onReplayStep` payload, it appears
to be reading the candle from the wrong source:

- Buffer accounting (`getReplayBufferLength`) is updated correctly.
- But the candle reference handed to the callback (and the value
  `getReplayCurrentTime` returns afterward) comes from a stale "tail of
  loaded data" pointer rather than from the candle that was actually pulled
  out of the replay-drawn stack.

The strong indicators for "stale tail-of-loaded-data" specifically:

1. The phantom timestamp (`1776042000000`) is ~2 days before the consumer's
   wall clock — exactly where the chart's most-recent live candle would sit
   if the chart was loaded with normal historical data before replay
   started.
2. The OHLC values match real-world BTC prices for that timestamp, so it's
   genuine candle data, not uninitialized memory.
3. The phantom is **identical** across every `stepBack` call regardless of
   the actual replay cursor position — it's a fixed pointer, not a function
   of the cursor.
4. The bug only manifests when replay was entered via
   `setCurrentTime(midHistoryTime)`. A theoretical zero-history replay
   wouldn't have a "live tail" to confuse with.

`engine.step()` (forward) is unaffected because forward stepping reads from
the replay buffer's head, which is correctly populated.

## Where to look in the engine

Likely in `ReplayEngine.stepBack()` (or whatever method `engine.stepBack`
maps to) — specifically, the line(s) that:

1. Pop a candle from the "drawn" stack
2. Push it back into the buffer
3. Determine which candle to emit via `onReplayStep` and what `currentTime`
   to set

The buffer push (#2) is working — `getReplayBufferLength` increments
correctly. The emit (#3) appears to read from the wrong list.

Also worth checking: how `setCurrentTime(midHistoryTime)` interacts with the
chart's pre-existing data list. If `setCurrentTime` doesn't fully clear /
rebind the chart's source data when entering replay mid-history, the engine
might be holding two parallel lists and `stepBack`'s emit logic is reading
from the wrong one.

## Root Cause (localized)

A second pass through the SC source pinpointed the exact bug. The
hypothesis above ("stepBack reads from a stale tail-of-loaded-data
pointer") is correct, and the contamination of that tail comes from a
**too-narrow replay guard** in `Store._addData`.

### The bad code path

1. Consumer calls `engine.setCurrentTime(midHistoryTime)` to start replay
   at a 2022 timestamp.
2. `_waitForInit` → `_processDataLoad('init')` loads 2022 history into
   `_dataList`. ✓
3. **Inside `_addData(data, 'init')` at `Store.ts:718-719`**,
   `_adjustVisibleRange()` is called. The visible range hits the right
   edge (`to === totalBarCount`) and `_dataLoadMore.backward` is `true`
   from the datafeed, so it fires another `_processDataLoad('backward')`.
4. **`Store.ts:867-869`** — `_processDataLoad('backward')` builds
   `params.timestamp = _dataList.last.timestamp` (a 2022 candle) and asks
   the datafeed for newer candles. The datafeed obliges and returns every
   candle from 2022 to the present (~2026).
5. **`Store.ts:675-676`** — `_addData(data, 'backward')` runs
   `this._dataList = this._dataList.concat(data)`, appending all 2026
   candles to `_dataList` **with no replay-mode check**.
6. **`Store.ts:696-697`** — the replay guard that exists is one branch
   too narrow:

   ```ts
   if (this._replayEngine.isInReplay() && type === 'update') {
     return
   }
   ```

   It blocks `type === 'update'` (single live-candle pushes) but not
   `type === 'backward'` (bulk-load appends), so step 5 is unguarded.
7. From this point on, `_dataList` is permanently contaminated for the
   rest of the replay session. Forward `step()` reads from
   `this._replayBuffer.shift()` (a separate list), so forward stepping
   looks fine and emits real 2022 candles.
8. **`ReplayEngine.ts:519-522`** — `stepBack()` does:

   ```ts
   const updatedDataList = this._s._dataList
   if (updatedDataList.length > 0 && period !== null) {
     const last = updatedDataList[updatedDataList.length - 1]
     this._replayCurrentTime = last.timestamp + this._getPeriodDurationMs(period)
   ```

   `updatedDataList.last` is the 2026 candle from step 5. Hence
   `_replayCurrentTime` is set to a 2026 timestamp, the chart re-renders
   with that bogus position, and the consumer sees the phantom candle on
   the right edge.
9. The phantom is **identical** across every `stepBack` call because
   `_dataList`'s tail never changes during the session — `_drawCandle`'s
   `_addData('update')` calls during forward play silently no-op when
   the step candle's timestamp (2022) is less than `_dataList.last`'s
   timestamp (2026), so the contamination is permanent.

### Why forward `step()` is unaffected

`step()` reads from `this._replayBuffer.shift()` (`ReplayEngine.ts:442`),
which is populated by `_fetchReplayBuffer` directly from the datafeed
with explicit time bounds. The replay buffer is completely independent
of `_dataList`. Only `stepBack()` consults `_dataList.last`, and only
for the `_replayCurrentTime` assignment.

## Expected Fix

**Minimal, one-line:** `Store.ts:696-697` — extend the replay guard to
also block `'backward'`:

```ts
// Before:
if (this._replayEngine.isInReplay() && type === 'update') {
  return
}

// After:
if (this._replayEngine.isInReplay() && (type === 'update' || type === 'backward')) {
  return
}
```

This prevents background backward loads from contaminating `_dataList`
once replay starts. `stepBack()`'s `_dataList.last` then refers to the
correct 2022 boundary again and `_replayCurrentTime` gets a sane value.

**Cleaner alternative (recommended):** gate the network call in
`_processDataLoad`'s backward branch instead of discarding the response
after the fact:

```ts
case 'backward': {
  if (this._replayEngine.isInReplay()) {
    // Replay manages its own buffer; don't fetch live history.
    this._loading = false
    return
  }
  params.timestamp = this._dataList[this._dataList.length - 1]?.timestamp ?? null
  break
}
```

This avoids the wasted fetch entirely and makes the intent obvious.

**Defensive secondary fix:** in `ReplayEngine.stepBack()` at
`ReplayEngine.ts:519-522`, sanity-check the `_dataList.last` timestamp
against `_replayBuffer`'s known time range before assigning
`_replayCurrentTime`. If they're inconsistent, that's a clear internal-
state bug and an assertion would catch it. This wouldn't fix the root
cause but would make any future regression scream loudly instead of
silently emitting a phantom candle.

## Notes for the Altrady consumer (after SC fix lands)

- Altrady's `_setSession({time, price})` writes the engine-reported values
  straight into Redux on every `onReplayStep`. After the fix, this should
  reflect the correct cursor automatically — no consumer-side change needed.
- Altrady has **no workaround** for this bug. Disabling step-back during
  play does not help — the bug also reproduces from a paused state because
  the contamination of `_dataList` happens at session init, not at any
  later transition.
- A defensive consumer-side workaround would be to compare the engine's
  `currentTime` against the locally-computed `targetTime` in the stepBack
  callback and ignore the emit if they diverge by more than one resolution
  unit. We are *not* applying this workaround in Altrady because it would
  hide the real fix and only patches Redux, not the chart's own visual
  rendering of the phantom.

## Notes for the Altrady consumer (after SC fix lands)

- Altrady's `_setSession({time, price})` writes the engine-reported values
  straight into Redux on every `onReplayStep`. After the fix, this should
  reflect the correct cursor automatically — no consumer-side change needed.
- A defensive consumer-side workaround would be to compare the engine's
  `currentTime` against the locally-computed `targetTime` in the stepBack
  callback and ignore the emit if they diverge by more than one resolution
  unit. We are *not* applying this workaround in Altrady because it would
  hide the real fix and only patches Redux, not the chart's own visual
  rendering of the phantom.
