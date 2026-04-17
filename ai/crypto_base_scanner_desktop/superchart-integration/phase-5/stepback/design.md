# Phase 5: Replay Step Back — Design

PRD: `prd.md` (id `sc-replay-stepback`)

---

## Architecture overview

Three layers, matching the existing replay stack:

```
 replay-controls.js (Button)          replay-hotkeys.js (shift+left)
            │                                     │
            └─────────── ReplayController ────────┘
                               │
                               ├── ReplayTradingController.resetTo(time)   (default)
                               ├── SmartReplayController.resetTo(time)     (smart)
                               └── engine.setCurrentTime(time)             (unified seek)
```

Everything below `ReplayController` already exists and is already tested by
`handleBackToStartClick`. This subtask only adds a new entry point (`goBackTo`,
`handleStepBack`, `canStepBack`), a button, and a hotkey.

---

## Split engine-call paths

Two public entry points, one shared helper:

| Method | Used by | Engine call | Loading flicker? |
|-|-|-|-|
| `handleStepBack()` | button, hotkey `shift+left` | `engine.stepBack()` — atomic, removes one candle | No |
| `goBackTo(time)` | future context-menu "Jump back to here" (multi-candle) | `engine.setCurrentTime(time)` — rebuilds buffer | Yes (brief) |

Both delegate to `_revertAndSeek(time, engineMove)` which owns the trade revert,
the `_stepInFlight` guard, and the catch-all error handling. `handleStepBack` passes
`() => engine.stepBack()`; `goBackTo` passes `() => engine.setCurrentTime(time)`.

**Why split.** `engine.stepBack()` is atomic and doesn't cycle through
`loading → ready`, so the chart never flickers. `setCurrentTime(time)` is required
for arbitrary seeks but rebuilds the buffer and always triggers a loading round-trip.
The Superchart storybook `Replay.stories.tsx` (`handleStepBack = () =>
controllerRef.current?.stepBack()`) is proof that `stepBack()` works as a production
engine API — it's not a storybook-only affordance.

```js
handleStepBack = async () => {
  if (!this.canStepBack) return
  const currentTime = this._replayEngine.getReplayCurrentTime()
  const ms = resolutionToMs(this._getCurrentResolution())
  if (!ms) return
  await this._revertAndSeek(currentTime - ms, () => this._replayEngine.stepBack())
}

goBackTo = async (time) => {
  if (!this._replayEngine || !this.replayMode) return
  if (this.isLoading || this.isFinished || this.isViewMode) return
  if (!Number.isFinite(time) || time >= this.time) return
  if (time < this.startTime) {
    toast.warn(i18n.t(I18N.cantGoBackEarlierThanStart))
    return
  }
  await this._revertAndSeek(time, () => this._replayEngine.setCurrentTime(time))
}

_revertAndSeek = async (time, engineMove) => {
  if (this._stepInFlight) return
  this._stepInFlight = true
  try {
    if (this.replayMode === REPLAY_MODE.SMART) {
      const err = await this.smart.resetTo(time)  // returns error / throws on backend failure
      if (err) { toast.warn(err, {autoClose: 10000}); return }
    } else {
      this.trading.resetTo(time)
    }
    await engineMove()
  } catch (e) {
    console.warn("[replay] step back failed", e)
    toast.warn(i18n.t(I18N.stepBackFailed))
  } finally {
    this._stepInFlight = false
  }
}
```

### Ordering rationale

Trade revert **before** engine move — matches TV's `handleGoBackInTime` flow. If
`smart.resetTo` rejects (backend error / partial split), the engine never moves, so
the chart stays consistent with the un-reverted backend state.

### `smart.resetTo` contract change

Original `smart.resetTo` wrapped the backend PUT in an internal try/catch and
silently toasted on failure — which would let `_revertAndSeek` proceed to move the
engine after a failed backend revert. Contract tightened: the internal catch is
removed so backend errors propagate up. `_revertAndSeek`'s outer catch handles the
toast. Only caller at the time of the change was the new `_revertAndSeek`, so the
contract change is safe.

### `_stepInFlight` re-entrancy guard

Purpose: when the user holds `shift+left`, the OS fires key-repeat events many times
per second. `goBackTo` is async — without a guard, repeats stack up and can:
- Interleave engine seeks with mid-flight backend PUTs
- Cause `smart.resetTo` validation to run against stale `currentTime`
- Corrupt the Redux trades array on the default path

With `_stepInFlight`:
- First repeat enters, flips the flag, runs through revert + seek, clears the flag.
- Repeats that arrive while the flag is true are dropped (silent early return).
- Next repeat after completion enters normally.

This is equivalent to "drop extra clicks" — simpler than a queue and avoids unbounded
backlog if the backend is slow. Matches the held-hotkey behavior the PRD requires:
continuous playback at the rate the sub-controllers can keep up with, blocked by
whatever is slowest (backend PUT in smart mode, local sync in default mode).

**Why not rely on `isLoading`?** `isLoading` is driven by engine status events which
lag behind synchronous JS execution. Two rapid repeats can both observe `isLoading =
false`, call `setCurrentTime`, and race inside the engine. A controller-owned
in-flight flag avoids the round-trip through Redux.

**Why not a promise chain?** A chain would queue every repeat, potentially building
a 100-item backlog on a slow backend. Drop-on-busy is what the user asked for
("continuous playback, blocking until processing is done") — repeats land at the
rate the work completes, not at the OS key-repeat rate.

---

## `ReplayController.handleStepBack()`

Thin wrapper — one-candle target math, then delegate.

```js
handleStepBack = async () => {
  if (!this.canStepBack) return
  const currentTime = this._replayEngine.getReplayCurrentTime()
  const resolutionMs = resolutionToMs(this._getCurrentResolution())
  if (!resolutionMs) return
  await this.goBackTo(currentTime - resolutionMs)
}
```

---

## `ReplayController.canStepBack` getter

Drives button `disabled` and acts as a cheap pre-check in the hotkey path.

```js
get canStepBack() {
  if (!this._replayEngine || !this.replayMode) return false
  if (this.isLoading || this.isFinished || this.isViewMode) return false
  if (this._stepInFlight) return false
  const currentTime = this.time
  if (!currentTime || !this.startTime) return false
  const resolutionMs = resolutionToMs(this._getCurrentResolution())
  if (!resolutionMs) return false
  return currentTime - resolutionMs >= this.startTime
}
```

Note: `this.time` is the Redux-mirrored engine time, updated via `onReplayStep`.
Reading it from Redux (vs `engine.getReplayCurrentTime()`) makes the getter
React-reactive — the button re-renders when the time changes.

**`_stepInFlight` is NOT reactive** — bumping it on its own won't re-render the
button. The Redux `isLoading` flag (toggled via `smart.updatingPosition`) will cover
smart mode. For default mode the in-flight window is sub-millisecond (synchronous
trade revert + promise microtask for engine.setCurrentTime), so the lack of
re-render is invisible.

---

## `resolutionToMs` helper

SC resolution strings: `"60"` (1h, as minutes), `"1D"`, `"1W"`, `"1M"`, `"${n}S"`
(seconds; replay is unsupported here).

Existing `resolutionToMs` lives in `src/actions/ta-scanner.js:56` but is private to
that file and incomplete (handles only `D` and minute-numbers, not `W`/`M`/`S`).
Two options:

**A. New helper in `chart-helpers.js` next to `periodToResolution`.** Centralized,
reusable by other SC controllers. Adds `W`, `M`, `S` handling.

**B. Inline in `replay-controller.js`.** Local, keeps `chart-helpers.js` lean.

**Decision: A.** A helper in `chart-helpers.js` is only 10–15 lines and matches the
existing "chart-helpers owns conversions" pattern. Signature:

```js
// chart-helpers.js
export function resolutionToMs(resolution) {
  if (!resolution) return 0
  const str = String(resolution).toUpperCase()
  if (str.endsWith("S")) return parseInt(str, 10) * 1000                   // seconds
  if (str.endsWith("D")) return (parseInt(str, 10) || 1) * 86_400_000     // days
  if (str.endsWith("W")) return (parseInt(str, 10) || 1) * 7 * 86_400_000 // weeks
  if (str.endsWith("M")) return (parseInt(str, 10) || 1) * 30 * 86_400_000 // months (approx; OK for candle stepping)
  return parseInt(str, 10) * 60_000                                         // minutes (default)
}
```

The month approximation is fine: replay on monthly resolution is uncommon, and the
value only drives `canStepBack`'s boundary math and the step target. The engine
itself uses its own candle stream for actual candle times — we just need a value
large enough to land in the previous candle.

---

## UI — step-back button

Added in `replay-controls.js`, mirroring `stepButton`:

```js
const stepBackButton = useMemo(() => (<Button
  transparent
  icon={{icon: "arrow-left-to-line"}}
  tooltip={i18n.t("containers.trade.market.marketGrid.centerView.tradingView.replay.controls.stepBack", {
    hotkey: DEFAULT_KEYMAP.replay[HOTKEY_COMMANDS.replayStepBack],
  })}
  disabled={!canStepBack}
  onClick={() => replayController.handleStepBack()}/>), [
  canStepBack,
])
```

`canStepBack` comes from a new `useCanStepBack()` hook that reads the reactive
Redux bits (`time`, `startTime`, `isLoading`, `isFinished`, replay mode, resolution)
and mirrors the controller getter's logic, OR by selecting the controller's getter
via `useSelector` on its Redux inputs.

**Decision:** recreate the boolean inside the component using `useSelector` on
`replaySession.time`, `replaySession.startTime`, `replaySession.status`, plus the
current period, so React re-renders correctly. The controller getter remains the
source of truth for imperative callers (`handleStepBack`).

**Placement:** between `backToStartButton` and `stepButton`, so the row reads:
`[⏮ back-to-start] [◀ step-back] [▶ step-forward]`.

---

## Hotkey — `shift+left`

### Collision check

Existing hotkeys on left/right keys in `src/actions/constants/hotkeys.js`:
- `nextTab`: `ctrl+right` / `cmd+right`
- `prevTab`: `ctrl+left` / `cmd+left`
- `replayStep`: `shift+right`

No existing `shift+left` binding. Safe to claim it.

### Wiring

- Add `HOTKEY_COMMANDS.replayStepBack = "replayStepBack"`
- Default binding in the `replay` keymap: `"shift+left"`
- Add i18n label under `actions.hotkeys.replayStepBack`
- In `replay-hotkeys.js`, add `handleStepBack = util.useImmutableCallback(() =>
  replay?.handleStepBack())` and map into `comboCallbackMap`

### Held-key serialization

The hotkey callback is a plain `() => replay.handleStepBack()`. OS key-repeat
invokes it ~30×/sec. The `_stepInFlight` guard inside `goBackTo` drops overlapping
calls. No debounce/throttle in the hotkey layer.

Forward step (`handleStep`) is synchronous (`engine.step()` returns void) so held
`shift+right` naturally serializes on the JS event loop. Step-back's async nature
is why we need the explicit flag.

---

## i18n keys

New keys under `containers.trade.market.marketGrid.centerView.tradingView.replay.*`:

```yaml
controls:
  stepBack: Step Back ({{hotkey}})
cantGoBackEarlierThanStart: Can't go back earlier than the replay start time
stepBackFailed: Step back failed — try again
```

Plus `actions.hotkeys.replayStepBack: Replay step back` for the keymap label.

---

## Files touched

**New / modified controller code**
- `src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js`
  — add `_stepInFlight` field, `goBackTo`, `handleStepBack`, `canStepBack` getter.
- `src/containers/trade/trading-terminal/widgets/super-chart/chart-helpers.js`
  — add `resolutionToMs` export.

**UI**
- `src/containers/trade/trading-terminal/widgets/super-chart/replay/replay-controls.js`
  — add `stepBackButton`, compute `canStepBack` locally, render between back-to-start
  and step-forward.

**Hotkeys**
- `src/actions/constants/hotkeys.js` — add `replayStepBack` command, default binding,
  descriptions map entry.
- `src/containers/trade/trading-terminal/widgets/super-chart/replay/replay-hotkeys.js`
  — wire `handleStepBack` callback into `comboCallbackMap`.

**i18n**
- `src/locales/en/translation.yaml` — new keys listed above.

No changes to:
- `ReplayTradingController` / `SmartReplayController` — `resetTo` + `checkResetToPossible`
  already exist and cover both local and backend paths.
- SC library (`$SUPERCHART_DIR`) — `setCurrentTime` is a production API already
  used by the back-to-start flow.

---

## Open questions (flag for review)

1. **Engine call split resolved.** `handleStepBack` uses `engine.stepBack()` (no
   loading flicker). `goBackTo(time)` uses `engine.setCurrentTime(time)` (unavoidable
   flicker for arbitrary seeks, acceptable for multi-candle). Earlier assumption that
   `stepBack()` was storybook-only was wrong — confirmed via `Replay.stories.tsx`
   calling `ctrl.stepBack()` in production.
2. **Should we reuse `resolutionToMs` from `ta-scanner.js`?** It's private and
   incomplete, so we're not moving it — we're adding a new export to `chart-helpers.js`.
   If during review we want to consolidate, lift the `chart-helpers.js` version and
   delete the `ta-scanner.js` copy in a follow-up refactor.
2. **Month-resolution approximation (30 days).** Affects `canStepBack` boundary math
   only on the 1M period. Acceptable given replay is rarely used at 1M and the math
   just needs to land inside the previous candle.
3. **Drop-on-busy vs queue for held-key repeats.** Chose drop-on-busy. Review will
   validate: during smart replay with a slow backend, holding `shift+left` should NOT
   build a backlog. If users complain they want a fixed N steps per key-press, revisit.
4. **`canStepBack` reactivity across tab switches.** `ChartController` is reused
   across tabs and `_marketTabId` mutates. The component already subscribes to the
   correct tab's replay session via `MarketTabContext` → `selectReplaySession`, so
   tab switches flip the getter inputs correctly. Verify during review with test case
   §F.33.
