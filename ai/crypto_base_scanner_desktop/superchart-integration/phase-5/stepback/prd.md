---
id: sc-replay-stepback
---

# Phase 5: Replay Step Back

Add a one-candle step-back button to the SC replay controls panel for both default
replay and smart (backtest) replay. Step-back rewinds the chart by one candle and
reverts any trading state that was created during the removed candle.

This ports the TV "Jump back to here" logic down to a single-candle step, exposed as
a button + hotkey. A generic `goBackTo(time)` method underlies the button so the
multi-candle entry point (chart context menu → "Jump back to here") can reuse the
same flow without duplication. That entry point is delivered in
`[sc-chart-ctx-menu-options]`.

---

## Scope

### In scope

- Step-back button in the replay controls panel (mirrors the existing Step forward button)
- Hotkey binding for step back
- Generic `goBackTo(time)` method on `ReplayController` that both the button and future
  multi-candle entry points will share
- Trade reverts during step back:
  - Default replay: local trade filter + position recalculation
  - Smart replay: backend coordination (uses existing `PUT /backtests/{id}/reset`)
- Validation rules (session start boundary, loading, finished, view-mode, smart
  position-split check)
- Button disabled state driven by controller getter

### Out of scope

- Multi-candle "Jump back to here" chart context menu entry — delivered in
  `[sc-chart-ctx-menu-options]`, which wires the entry straight to `goBackTo(time)`
  without requiring changes to this PRD.
- Forward step-back stack / undo history — step-back is destructive, matching
  `handleBackToStartClick` semantics.
- New backend endpoints — smart revert already uses `PUT /backtests/{id}/reset`.
- Changes to sub-controller `resetTo` methods — already shipped and working.

---

## Requirements

### 1. Generic `goBackTo(time)` Method

A new method on `ReplayController` that moves the replay session backward to an
arbitrary timestamp. Used by the step-back button and by any future multi-candle
entry point (context menu).

**Flow:**
1. Validation gates (see §4). Abort on failure.
2. Trade revert — runs **before** the engine seek so a failing revert leaves the
   chart state untouched.
   - Default replay: `trading.resetTo(time)` (synchronous, local)
   - Smart replay: `smart.checkResetToPossible(time)` → on error, toast and abort.
     Otherwise `await smart.resetTo(time)` which does the backend PUT. On backend
     error, abort.
3. Seek engine: `await engine.setCurrentTime(time)`.

**Signature:** `async goBackTo(time)` — `time` is an absolute timestamp in
milliseconds.

### 2. Step-Back Handler

`handleStepBack()` computes the single-candle target and delegates to `goBackTo`.

**Behaviour:**
- Read the current replay time from the engine (`engine.getReplayCurrentTime()`).
- Compute the target as `currentTime − resolutionMs`, where `resolutionMs` comes from
  the current chart resolution.
- Call `goBackTo(target)`.

### 3. `canStepBack` Getter

A computed getter on `ReplayController` drives the button's enabled/disabled state.
Returns `true` only when **all** of the following hold:

- An engine is attached
- A session is active (replay mode is set)
- `!isLoading`
- `!isFinished`
- `!isViewMode`
- `currentTime − resolutionMs ≥ startTime` (at least one candle of headroom above
  the session start)

### 4. Validation Rules (inside `goBackTo`)

| Check | Outcome |
|-|-|
| No engine, or no active session | silent no-op |
| `isLoading` / `isFinished` / `isViewMode` | silent no-op |
| `time >= currentTime` | silent no-op (can't step forward / same) |
| `time < startTime` | toast `"Can't go back earlier than start-time"` |
| Smart: `checkResetToPossible(time)` returns error | toast the returned error (10s `autoClose`), abort |
| Smart: backend `_resetBacktest` rejects | toast the backend error, abort |

Silent no-ops exist because `canStepBack` will typically already prevent the button
click; the controller still guards defensively in case the guard is called from the
hotkey or a future entry point.

### 5. UI — Step Back Button

Added to `replay-controls.js` next to the existing forward Step button.

- Icon: `arrow-left-to-line` (mirror of the Step forward button's `arrow-right-to-line`)
- Tooltip: i18n key describing "Step back one candle" + the hotkey chord
- `disabled` prop bound to `!canStepBack`
- `onClick` calls `replayController.handleStepBack()`
- Placement: immediately before the existing Step forward button in the controls row,
  so the pair reads `[⏮ back-to-start] [◀ step-back] [▶ step-forward] …`

### 6. Hotkey

- New command `HOTKEY_COMMANDS.replayStepBack` in `src/actions/constants/hotkeys.js`
- Default binding: `shift+left` (mirror of `shift+right` for forward step)
- Wire in `replay-hotkeys.js` to call `handleStepBack`
- Respects the same enabled/disabled logic as the button — if `canStepBack` is false
  the hotkey is a no-op

### 7. Mode Coverage

**Default replay:**
- Trades placed after the target time are filtered out by `trading.resetTo(time)`
- Position is recalculated from remaining trades via `Position.positionFromTrades()`
  (already wired in `ReplayTradingController`)
- Engine seeks to the target; chart shows the earlier state
- No backend interaction

**Smart replay:**
- `checkResetToPossible(time)` guards against position splits (open time before target
  with exit orders after target — the existing smart controller already implements
  this check)
- `smart.resetTo(time)` performs the existing backend `PUT /backtests/{id}/reset`
  with `{resetTo: time/1000, resolution}`; server returns the updated backtest with
  positions/trades/orders/alerts removed after the target
- Local `triggeredAlerts` are filtered client-side as part of `smart.resetTo` (already
  wired)
- Engine seeks to the target only after backend confirms success

### 8. i18n

New translation keys under
`containers.trade.market.marketGrid.centerView.tradingView.replay.*`:

- `cantGoBackEarlierThanStart` — toast when target precedes session start
- `stepBack.tooltip` — button tooltip text
- Any other user-facing strings introduced by this PRD

Reuse existing keys where available (forward Step tooltip pattern, existing smart
revert error messages from the smart PRD).

---

## Non-Requirements

- No changes to `ReplayTradingController.resetTo` or `SmartReplayController.resetTo` —
  both exist and are already used by session-restart flows.
- No changes to `checkResetToPossible` — the smart-side validation already exists.
- No changes to the SC library. `sc.replay.setCurrentTime(time)` is already used by
  `handleBackToStartClick` for in-session seeking, so no new engine API is needed.
- No "jump to here" chart context-menu entry in this PRD. It is delivered in
  `[sc-chart-ctx-menu-options]`, which wires a `PopupItem` in
  `chart-context-menu.js` directly to the `goBackTo(time)` method this PRD added.
- No forward-stack / undo history for step-back.
- No progress indicator beyond the existing `isLoading` gating during the engine seek.
