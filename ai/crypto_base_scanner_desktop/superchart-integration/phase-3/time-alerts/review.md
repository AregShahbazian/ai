# Review: Time Alerts — SuperChart Integration

## Round 1: Post-implementation fixes (2026-03-25)

### Bug 1: `_b.call is not a function` on line move
**Root cause:** Callbacks passed as `{params: {}, callback: fn}` wrappers (the `createOrderLine` convention), but `chart.createOverlay()` used by `verticalStraightLine` expects raw functions `(event) => ...`.
**Fix:** Changed `onClick` in `time-alerts.js` and `onPressedMoveEnd` in `edit-time-alert.js` to plain functions.
**Files:** `overlays/time-alerts.js`, `overlays/edit-time-alert.js`
**Design notes:** SC overlay callbacks are raw functions, unlike `createOrderLine` which wraps them in `{params, callback}`. This distinction matters for any future overlay that uses `chart.createOverlay()` directly.

### Bug 2: Moving a submitted time alert doesn't enter edit mode
**Root cause:** Only `onClick` was registered on pending alerts. `onClick` doesn't fire on drag — `onPressedMoveEnd` does.
**Fix:** Replaced `onClick` with `onPressedMoveEnd` on pending alerts. SC fires `onPressedMoveEnd` on both click (zero-distance drag) and actual drag, so a single callback handles both cases.
**Files:** `overlays/time-alerts.js`

### Bug 3: Colors decided in component instead of controller
**Root cause:** Components were passing `color: chartColors.alert` / `chartColors.closedAlert` to controller methods. Price alerts pattern has the controller read `this.colors.alert` / `this.colors.closedAlert` internally.
**Fix:** Removed `color` param from all three components. Controller methods now read `this.colors.alert` (pending/editing) and `this.colors.closedAlert` (triggered) internally. Components keep `chartColors` as effect dependency to trigger redraws on theme change.
**Files:** `chart-controller.js`, `overlays/time-alerts.js`, `overlays/edit-time-alert.js`, `overlays/triggered-time-alerts.js`

### Bug 4: `styles.line.*` not applied by SuperChart
**Root cause:** SC's `verticalStraightLine` does not properly handle `styles.line.color`, `styles.line.size`, or `styles.line.style` passed via `chart.createOverlay()`. The overlay renders with default styling instead.
**Fix:** None — this is an SC bug. Removed `styles` from `createTimeAlert` and `createTriggeredTimeAlert` since they have no effect. Color variables are still read and ready to be applied once SC fixes `verticalStraightLine` style support.
**SC task:** Fix `verticalStraightLine` to respect `styles.line.*` properties.

### Verification
- [x] Click a pending time alert line → enters edit mode
- [x] Drag a pending time alert line → enters edit mode with new time
- [x] Drag editing time alert line → form time updates (no submit)
- [x] Triggered time alerts show with darker blue, not draggable (color blocked by Bug 4)
- [x] Toggle alertsShowClosed → triggered lines appear/disappear
- [x] Switch symbols → all lines clear and redraw

**Blocked:** Line color styling (Bug 4) — all lines render with SC default color instead of `chartColors.alert`/`chartColors.closedAlert`. Requires SC fix for `styles.line.*` on `verticalStraightLine`.
