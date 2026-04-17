# Feature: Replay Session Restore

## Problem

When a consumer app remounts the chart (e.g., switching between mobile and desktop
layouts), the Superchart instance is destroyed and recreated. The replay session is
lost — the engine's internal state (buffer, drawn history, start time, current position)
is gone.

The consumer can persist session metadata externally (startTime, currentTime, endTime,
trades). On remount, it needs to restore the session to the exact position the user
was at.

Currently, the only way is `setCurrentTime(currentTime)`, but this sets
`_replayStartTime = currentTime` — the engine thinks the session starts at the
restored position, not at the original start. This breaks:

- **Step back** — won't go before `currentTime` (boundary partial uses `_replayStartTime`)
- **"Back to start"** — the consumer knows the real start, but the engine doesn't
- **Timeline markers** — consumer shows the real start, but engine's internal start
  differs

## Proposed API

```ts
restoreSession(startTime: number, currentTime: number, endTime?: number): Promise<void>
```

### Behavior

Same as `setCurrentTime(currentTime, endTime)` except:

- `_replayStartTime = startTime` (not `currentTime`)
- `_currentTimeLimit = currentTime`
- History loaded up to `currentTime`
- Buffer built from `currentTime` to `endTime`
- Boundary partial constructed at `currentTime` if mid-candle
- Step back boundary uses `startTime` (can step back to original start)
- Status transitions: `idle → loading → ready`

### Edge cases

- `startTime > currentTime` — invalid, reject or swap
- `currentTime > endTime` — invalid, reject
- `startTime` before first available candle — same handling as `setCurrentTime`
  (emit `no_data_at_time` error)
- Called while already in replay — same as `setCurrentTime` (increment generation,
  supersede previous session)
- `endTime` omitted — default to `Date.now()`, same as `setCurrentTime`

### Interface addition

Add to `ReplayEngine` interface in `types.ts`:

```ts
restoreSession: (startTime: number, currentTime: number, endTime?: number) => Promise<void>
```

### Implementation notes

Most of the logic already exists in `setCurrentTime`. The difference is just which
value gets assigned to `_replayStartTime`. Could be implemented as:

```ts
async restoreSession(startTime: number, currentTime: number, endTime?: number): Promise<void> {
  await this.setCurrentTime(currentTime, endTime)
  this._replayStartTime = startTime
}
```

Or by adding an internal parameter to `setCurrentTime`:

```ts
async setCurrentTime(timestamp, endTime?, options?: { replayStartTime?: number }): Promise<void> {
  // ... existing logic ...
  this._replayStartTime = options?.replayStartTime ?? timestamp
}
```

The second approach avoids the race where `_replayStartTime` is briefly wrong between
`setCurrentTime` resolving and the override.

### Consumer usage

```ts
// On remount, consumer reads persisted session:
const session = getPersistedSession() // { startTime, time, endTime, trades }

if (session) {
  await sc.replay.restoreSession(session.startTime, session.time, session.endTime)
  // Engine is in replay at the restored position
  // Step back works down to original startTime
  // Consumer re-renders trades from its own persistence
}
```

### Storybook testing

Add a "Restore" button to the Replay story that:
1. Saves current session state (startTime, currentTime, endTime)
2. Calls `setCurrentTime(null)` to exit
3. Calls `restoreSession(savedStart, savedCurrent, savedEnd)`
4. Verifies: chart shows same position, step back works to original start
