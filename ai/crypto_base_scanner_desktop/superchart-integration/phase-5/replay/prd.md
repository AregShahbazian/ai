---
id: sc-replay
---

# Phase 5: SuperChart Default Replay

Integrate the SuperChart replay engine into Altrady's Trading Terminal. This PRD covers
default replay only — play forward through historical candles with simulated buy/sell trading.

## Scope

### In scope

- ScReplayController wrapping SC's `ReplayEngine` (`sc.replay`)
- ScReplayTradingController for simulated buy/sell during replay
- Replay controls panel at bottom of CenterView (reuse existing ReplayControls)
- Header "Replay" button with visual select mode + mobile random start
- Hotkey bindings (mousetrap)
- Speed control using SC engine's candles-per-second values
- Resolution change during replay (handled by SC engine)
- Redux as source of truth for replay state (no mirroring)
- Shared constants extracted from TV-specific paths
- Datafeed `getFirstCandleTime` implementation

### Out of scope (future PRDs)

- Smart replay / backtest → `smart.md`
- Step back functionality + trading reverts → `stepback.md`
- Replay overlays (timeline markers, position/PnL lines, trade markers) → `overlays.md`
- PriceTimeSelect for click-to-select start time
- Chart context menu "Start replay here" — delivered in `[sc-chart-ctx-menu-options]`
  alongside the full set of Altrady-specific context-menu entries ported from TV
- Quiz integration
- Multi-chart replay (main Trading Terminal chart only)

---

## Requirements

### 1. Replay Engine Integration

The SC library exposes a `ReplayEngine` via `sc.replay` (null before chart mounts).
The engine handles all internal replay mechanics:

- Buffer management (fetch, queue, step through candles)
- Partial candle construction (mid-period cursor)
- Playback loop (setInterval-based stepping)
- State machine: `idle → loading → ready → playing ⇄ paused → finished`
- Data isolation (blocks live candle updates during replay)
- Resolution change during replay (with auto-revert on failure)
- Generation counter for race-condition safety

Altrady does NOT reimplement any of this. The ScReplayController is a thin wrapper
that delegates to `sc.replay` and adds Altrady-specific orchestration on top.

**Playback end-of-data behaviour — pause on last candle (Altrady deviation).**
The SC engine's default behaviour during continuous playback is to keep calling
`step()` until the replay buffer is empty, at which point status auto-transitions
to `finished`. Altrady overrides this: after each forward step, if the session is
in `playing` and `engine.getReplayBufferLength() === 0`, the controller calls
`engine.pause()`. Effect:

- Continuous playback pauses on the LAST drawn candle instead of transitioning
  straight to `finished`.
- The user gets a chance to step back to review before the session ends — and
  for smart replay, before `setBacktestFinished()` is called on the backend.
- The next manual `play()` or `handleStep()` hits the empty buffer and lets the
  engine's normal `step() → finished` transition run, triggering the existing
  `onReplayStatusChange(FINISHED)` handler and the backend sync.
- Manual stepping is unchanged: `handleStep()` runs outside the `playing`
  state, so the controller's `engine.pause()` call is a no-op there and the
  existing "one extra manual step to mark finished" behaviour is preserved.
- Hook lives in `ReplayController._wireCallbacks` → `onReplayStep` handler.

**Engine re-seek rule — always pass `endTime`.** The SC engine's
`setCurrentTime(time, endTime?)` captures `endTime ?? Date.now()` into
`_replayEndTime` on every call (`ReplayEngine.ts:321`). That means any
Altrady-side re-seek that omits the second argument silently resets the
engine's end boundary to "now" — blowing past a smart session's
`backtest.replayEndAt` or drifting past a default session's frozen
`Date.now()` snapshot, while `session.endTime` in Redux keeps pointing at the
original boundary (the overlay shows the right line, the engine ignores it).

**Rule:** every internal `engine.setCurrentTime(time)` callsite that is
re-seeking *within* an active session must pass the current session's
`endTime` as the second argument:

```js
await this._replayEngine.setCurrentTime(time, this.endTime || undefined)
```

Applies to (at minimum):
- `_startSession` — creates the session's `endTime` (explicit for smart, frozen
  `Date.now()` for default) and must pass it straight through
- `handleBackToStartClick` default branch — re-seeks to startTime on restart
- `smart.exitSmartMode` — re-seeks to startTime after tearing down smart state
- `goBackTo(time)` and any future multi-candle rewind — arbitrary in-session
  seek
- `smart.loadBacktest` — resume-from-widget re-seek

Does NOT apply to `setCurrentTime(null)` (session exit — no boundary relevant).
`handleStepBack` uses `engine.stepBack()` which operates on the existing buffer
without touching `_replayEndTime`, so it is also exempt.

If you add a new re-seek callsite, grep existing occurrences of
`setCurrentTime(` in the SC controllers before writing the new line — the
pattern is consistent enough that copy-paste from an existing site is safer
than writing from scratch.

### 2. ScReplayController

Sub-controller of `ChartController`, following the existing pattern (`header`, `alerts`,
`positions`, etc.). Created in ChartController's constructor, accessible via
`chartController.replay`.

Location: `src/models/replay/sc-replay-controller.js`

Wraps `sc.replay` with Altrady-specific behavior:

**Initialization:**
- Created by ChartController, receives parent reference
- Polls for `sc.replay` availability on the Superchart instance
- Subscribes to engine events: `onReplayStatusChange`, `onReplayStep`, `onReplayError`
- Writes state to Redux via `dispatch` (Redux is source of truth)

**Handler methods** (same interface ReplayControls already calls):

| Method | Behavior |
|--------|----------|
| `handleSelectReplayStartTimeClick(isMobile)` | Mobile: `handleRandomReplayStartTime()`. Desktop: toggle `selectingStartTime` |
| `handleRandomReplayStartTime(resolution)` | Pick random time (avoid last 5%), call `sc.replay.setCurrentTime(time)` |
| `handlePlayPause()` | If playing → `sc.replay.pause()`. If ready/paused → `sc.replay.play(speed)`. If finished → restart |
| `handleStep()` | `sc.replay.step()` |
| `handleBackToStartClick()` | `sc.replay.setCurrentTime(startTime)` — restart from original start |
| `handleStop()` | Confirmation if trades exist, then `sc.replay.setCurrentTime(null)` + trading reset |
| `setSpeed(candlesPerSec)` | Store speed, call `sc.replay.play(speed)` if currently playing |

**State exposed** (matches existing ReplayContext shape for controls reuse):
- `status` — mapped from SC engine's `ReplayStatus`
- `selectingStartTime` — boolean
- `startTime` — session start timestamp
- `time` — current replay time (from `sc.replay.getReplayCurrentTime()`)
- `price` — current price (from last stepped candle's close)
- `isLoading` — derived from status
- `isPlaying` — derived from status

**Confirmation dialog:**
- Before stop, check `willLoseDataIfStopped` (trades exist)
- Show confirmation via `replaySafeCallback` pattern

**Error handling:**
- `onReplayError` receives typed errors from engine
- `resolution_change_failed` → sync period UI back to engine's actual period

### 3. ScReplayTradingController

Location: `src/models/replay/` (named `ScReplayTradingController` or similar).

Manages simulated trading during default replay. Same responsibilities as current
`ReplayTradingController`:

- `handleBuy()` / `handleSell()` — execute trade at current replay time + price
- `setAmount(amount)` — set order size, persist to settings
- `reset()` — clear all trades and position
- `resetTo(time)` — filter trades to before given time (for restart)
- `updateCurrentState()` — recalculate position from trades

**State:**
- `amount` — trade size (BigNumber)
- `trades[]` — executed trades
- `currentPosition` — open position (side, entry price, invested amount)
- `pnl` — realized quote profit, profit percentage

Trade execution must validate that replay is active and not loading/finished.
Price comes from the last stepped candle's close.

### 4. State & Access

**Redux is the source of truth.** All replay state lives in Redux, keyed by chart ID:

```
state.replay.sessions[chartId] = {
  status,              // ReplayStatus string
  startTime,           // session start timestamp
  time,                // current replay time
  price,               // current price
  speed,               // candles per second
  selectingStartTime,  // boolean
  // trading state:
  amount,              // trade size
  trades,              // executed trades[]
  currentPosition,     // open position
  pnl,                 // realized profit
}
```

The controller dispatches actions to write state. Components and thunks read via
selectors. No mirroring — Redux is the single source.

**Controller access — three paths for different consumers:**

| Consumer | Access |
|----------|--------|
| Shared UI (ReplayControls) | `useContext(ReplayContext).replayController` |
| SC-specific components | `useSuperChart().chartController.replay` |
| Thunks / external code | `ChartRegistry.get(chartId).replay` |

**ReplayContext** is a thin React context holding only the controller instance ref.
Both TV and SC provide the same `ReplayContext` — shared UI components don't know
which chart type is active. State is NOT in this context — components read it from
Redux via selectors.

**Multi-chart ready:** Each ChartController has its own `this.replay`. Each dispatches
to its own keyed slice in `state.replay.sessions`. No architectural changes needed
when multi-chart is added.

### 5. Shared Constants

Extract to a shared location (e.g. `src/models/replay/constants.js`):

- `REPLAY_STATUS` — status constants (or use SC engine's `ReplayStatus` type directly)
- `REPLAY_MODE` — `{ DEFAULT: "default", SMART: "smart" }`
- Speed display helpers

Both TV and SC controllers import from this shared file. TV's current constants become
re-exports from here. This keeps TV functional during coexistence and allows clean
removal later.

### 6. Controls Panel

**Position:** Bottom of CenterView widget, in the `SuperChartControls` area.

**Visibility:**
- Replay active → show ReplayControls, hide ActionButtons
- Replay inactive + mobile → show ActionButtons (which include PickReplayStartButton)
- Replay inactive + desktop → show nothing (current behavior)

**Reuse:** The existing `ReplayControls` component is reused. Required adaptations:
- Import constants from shared location (not TV-specific paths)
- Read from ScReplayContext (same shape as TV's ReplayContext)
- `currentMarket` available via `MarketTabContext` (already in SC widget tree)
- `replayMode` available via ScReplayContext

**Controls shown for default replay:**
- PickReplayStartButton (main button + "Random Bar" dropdown)
- Back to Start
- Play / Pause (shows restart icon when finished)
- Step forward
- Speed dropdown
- Exit Replay
- Buy / Sell buttons with order amount selector
- P&L display (when position open)

**Controls NOT shown (deferred):**
- Step Back button → `stepback.md`
- Toggle Replay Mode button → `smart.md`
- Auto-resume playback toggle → `smart.md`

### 7. Speed Options

Adopt SC engine's candles-per-second values:

```
[1, 2, 5, 10, 20, 100, 200, 400]
```

Displayed as `"Nx"` (e.g. "20x"). Controller passes speed directly to
`sc.replay.play(speed)`. No `intervalMs` conversion needed.

Replaces TV's interval-based options (`[10, 100, 333, 1000, 2000, 3000, 10000]` ms).

### 8. Header Button

The existing "Replay" button in SC's header toolbar (`header-buttons.js`).

**Click behavior:**
- Mobile (`isMobile=true`): `handleRandomReplayStartTime()` → starts replay immediately
- Desktop (`isMobile=false`): toggle `selectingStartTime` mode (visual highlight only —
  no functional time selection without PriceTimeSelect)

**Visual state:**
- `setReplayButtonHighlight(active)` called when `selectingStartTime` changes
- Exit select mode when clicking outside the chart (already implemented pattern)

**Header button enable/disable:**
- Buy/Sell/Alert header buttons disabled during replay via `setHeaderButtonsEnabled(false)`
- Re-enabled on replay exit

### 9. Hotkeys

Follow existing mousetrap pattern. Same default bindings (user-customizable via Redux):

| Command | Default Binding |
|---------|----------------|
| Play / Pause | `shift+down` |
| Step forward | `shift+right` |
| Back to Start | `shift+r` |
| Stop / Exit | `shift+q` |
| Buy | `shift+b` |
| Sell | `shift+s` |

Bindings read from `state.hotkeys` (same Redux location as TV hotkeys).

SC uses mousetrap global binding only (no chart-internal shortcut system like TV's
`tvWidget.onShortcut`). Hotkeys are active when replay is active.

### 10. Entry & Exit Flow

**Start replay (mobile):**
1. User taps PickReplayStartButton in ActionButtons or header "Replay" button
2. → `handleRandomReplayStartTime()` picks random time (avoids last 5% of data)
3. → `sc.replay.setCurrentTime(randomTime)`
4. Engine: idle → loading (fetch history + buffer) → ready
5. Controls panel appears (replaces ActionButtons)
6. User is in replay, can play/step/trade

**Start replay (desktop):**
1. User clicks header "Replay" button
2. → enters `selectingStartTime` visual mode (highlight, no function)
3. No way to actually select start time without PriceTimeSelect — dead end
4. Click outside chart exits select mode
5. **Functional desktop entry point deferred to PriceTimeSelect integration**

**During replay:**
- Play/Pause/Step controls → `sc.replay.play()` / `pause()` / `step()`
- Speed changes → `sc.replay.play(newSpeed)` if currently playing
- Buy/Sell → `scReplayTradingController.handleBuy()` / `handleSell()`
- Resolution change → SC engine handles automatically (re-fetches at new resolution,
  auto-reverts on failure)

**Back to Start / Restart:**
- `sc.replay.setCurrentTime(startTime)` — re-fetch + rebuild buffer from original start
- Trading state reset

**Exit replay:**
1. User clicks Exit / presses `shift+q`
2. If trades exist → confirmation dialog
3. `sc.replay.setCurrentTime(null)` → engine exits → status → idle
4. Chart resumes live data
5. Trading state cleared
6. Controls panel hides, ActionButtons reappear (mobile)

**Symbol change during replay:**
SC engine auto-exits replay when `setSymbol` is called. Controller should sync state
(clear trading, hide controls).

### 11. Datafeed Requirements

**`getFirstCandleTime(ticker, resolution, callback)`** — must be added to
`CoinrayDatafeed`. Required by the SC engine for validating start times (prevents
starting before any data exists).

Implementation: call `getCoinrayCache().fetchCandles()` with a minimal range or use
a dedicated API endpoint if available.

**`getBars` with `countBack: 0`** — already works. Current implementation passes
`periodParams.from` / `periodParams.to` directly to `fetchCandles`, ignoring `countBack`.
The SC engine uses `countBack: 0` for arbitrary range fetches (buffer, partial construction).

---

## Non-Requirements

- No smart replay / backtest logic (separate PRD)
- No step back (separate PRD)
- No chart overlays during replay — no timeline markers, no position lines, no trade
  markers (separate PRD)
- No PriceTimeSelect integration — start time selection via chart click deferred
- No context menu entry point
- No quiz/play mode integration
- No multi-chart replay — main Trading Terminal chart only
- No new UI components — reuse existing controls, existing header button
- No modification of SC library code — consume `sc.replay` API as-is
