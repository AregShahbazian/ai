# Phase 5: Default Replay — Review

## Round 1: Implementation fixes (2026-04-07)

### Bug 1: Missing imports after file move
**Root cause:** Three additional files importing the moved components were not updated:
`order-form.js`, `alerts-form.js`, `use-on-context-menu.js`.
**Fix:** Updated import paths to new shared `widgets/replay/` location.
**Files:** `order-form.js`, `alerts-form.js`, `use-on-context-menu.js`

### Bug 2: ESLint `REPLAY_MODE` / `REPLAY_STATUS` not defined
**Root cause:** `export { ... } from "..."` re-exports without making the names
available in local scope. `replay-controller.js` still uses them internally.
**Fix:** Changed to `import` + separate `export`.
**Files:** `replay-controller.js`

### Bug 3: TV random-bar crashes with "Unsupported resolution undefined"
**Root cause:** Shared `PickReplayStartButton` no longer passes `currentResolution`
(removed ChartContext dependency). TV's `getRandomReplayStartTime` passed `undefined`
to `util.roundTimeToCandle`.
**Fix:** Fall back to `this.resolution` when `resolution` param is undefined.
**Files:** `replay-controller.js` (TV)

### Bug 4: SC buy/sell hotkey crash — "Cannot read properties of undefined (reading 'toNumber')"
**Root cause:** `ScReplayTradingController.amount` was never initialized. The TV
version gets it from `useReplayTrading` hook which reads Redux settings. The SC
version only set it locally in the constructor without dispatching.
**Fix:** Initialize amount from `Selectors.selectReplaySettings` in constructor.
Added guards in `buy()`/`sell()` for undefined amount/price.
Dispatch initial trading state in `ScReplayController.init()` via `saveState()`.
**Files:** `sc-replay-trading-controller.js`, `sc-replay-controller.js`

### Bug 5: SC replay controls don't push chart up
**Root cause:** Chart container div had `tw="flex-1 h-full"` — `h-full` (height: 100%)
prevents flex shrink when controls panel appears below.
**Fix:** Changed to `tw="flex-1 min-h-0"` to allow the chart to shrink.
**Files:** `super-chart.js`

### Bug 6: SC amount control renders empty
**Root cause:** Same as Bug 4 — `amount` undefined in Redux session because the
trading controller's constructor sets local state but doesn't dispatch to Redux.
**Fix:** Same as Bug 4 — `init()` calls `trading.saveState()` to dispatch initial state.
**Files:** `sc-replay-controller.js`

### Bug 7: Header button started random replay on mobile
**Root cause:** SC controller's `handleSelectReplayStartTimeClick` called
`handleRandomReplayStartTime()` on mobile. TV's version doesn't — it enters
selection mode on both platforms.
**Fix:** Removed the mobile branch. Button only toggles `selectingStartTime`.
**Files:** `sc-replay-controller.js`

### Bug 8: `clearReplaySession` not imported
**Root cause:** Import was lost when the file was rewritten to extend Controller.
**Fix:** Added `clearReplaySession` to the import from `~/actions/replay`.
**Files:** `sc-replay-controller.js`

### Bug 9: Session not cleaned up on chart unmount
**Root cause:** `destroy()` didn't clear Redux state. When switching desktop↔mobile,
chart remounts but Redux still had active session → controls stayed visible.
**Fix:** `destroy()` dispatches `clearReplaySession` and `setReplayMode(undefined)`
when a session was active.
**Files:** `sc-replay-controller.js`
**Design note:** Session persistence across remount deferred to `session-persist.md`.

### Verification
1. ✅ TV: Random Bar on mobile starts replay without crash
2. ✅ TV: replay controls work (play/pause, step, speed, stop)
3. ✅ SC: chart loads without errors
4. ✅ SC: `chartController.replay._replayEngine` is non-null in console
5. ✅ SC: Random Bar dropdown starts replay on mobile
6. ✅ SC: replay controls panel appears with proper layout (chart shrinks)
7. ✅ SC: amount control shows default value between Buy/Sell
8. ✅ SC: shift+b / shift+s don't crash
9. ✅ SC: shift+right steps, shift+down play/pauses, shift+q stops
10. ✅ SC: header Replay button toggles selectingStartTime highlight
11. ✅ SC: desktop↔mobile screen switch aborts session cleanly, controls disappear
12. ✅ SC: "Replay Random" desktop test button starts session
