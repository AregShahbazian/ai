# Chart Background Context Menu — Altrady Entries — Review

PRD: `menu-options-prd.md` (`[sc-chart-ctx-menu-options]`)
Design: `menu-options-design.md`
Tasks: `menu-options-tasks.md`

## Round 1: Initial implementation (2026-04-15)

### Summary

Landed `[sc-chart-ctx-menu-options]`: all Altrady-specific context-menu entries
ported from the old TradingView integration into the SuperChart chart-background
context menu.

### What changed vs. the design doc

1. **`handleGoBackInTime` was not added.** The SC `ReplayController` already
   had `goBackTo(time)` (line 654) — an equivalent, already-shipped entry
   point with all the boundary guards (`!replayMode`, `isLoading`, `isFinished`,
   `isViewMode`, future-time, before-start-time). The context-menu entry wires
   straight to `goBackTo` instead of a new wrapper, so Task 5 from
   `menu-options-tasks.md` collapsed to one line in `getChartContextMenuItems`.

2. **Speed navigation uses `SC_SPEED_OPTIONS` + `setSpeed`, not `INTERVAL_OPTIONS`
   + `setIntervalMs`.** The new SC `ReplayController` is built around the
   "candles per second" multiplier (`speed`), not TV's "ms between draws"
   (`intervalMs`). The mapping:
   - TV: `replay.intervalMs > ReplayController.minIntervalMs` → Speed-up visible.
   - SC: `SC_SPEED_OPTIONS.indexOf(replay.speed) < SC_SPEED_OPTIONS.length - 1` → Speed-up visible.
   - TV "faster" = smaller `intervalMs` = lower index in `INTERVAL_OPTIONS`.
   - SC "faster" = larger `speed` multiplier = **higher** index in `SC_SPEED_OPTIONS`.
     So the SC speed-up handler does `idx + 1` where TV did `idx - 1`.
   - New static fields `minIntervalMs` / `maxIntervalMs` were **not** added —
     `SC_SPEED_OPTIONS[0]` / `[length-1]` serves the same purpose without
     introducing dead constants.

3. **No new i18n toast keys needed.** The new SC `goBackTo` already uses
   `replay.cantGoBackEarlierThanStart` for its lower-bound toast, and
   `_handleFirstReplay` already uses `replay.cantReplayFuture`. Task 8 from
   `menu-options-tasks.md` reduced to deleting the dead
   `createNewRecurringAlert` key from en / nl / es YAMLs.

4. **Grid-bot chart does not yet mount `ChartContextMenu`.** The shell PRD
   mounted the component only in `super-chart.js` (main TT chart). The
   `setChartContextMenuItemsProvider` extension point is implemented on the
   controller as planned, but until grid-bot-super-chart.js mounts
   `ChartContextMenu` the backtest chart will not open a context menu at all.
   This is **consistent with the PRD** which explicitly scopes grid-bot
   backtest chart entries as out-of-scope, but it means the extension-point
   smoke test can only be exercised on the main chart.

### Files changed

- `src/containers/trade/trading-terminal/widgets/super-chart/controllers/context-menu-controller.js`
  — imports for i18n, moment-timezone, BigNumber, lodash, selectors, replay
  constants, alerts/trading/positions actions, conditionalCallback. New
  `_chartContextMenuItemsProvider` field + `setChartContextMenuItemsProvider(fn)`
  setter. Extended `_onChartRightSelect` to capture `time`, `price`, `timezone`
  (with `exchange → UTC` normalization) onto the menu state alongside `x`/`y`.
  New `getChartContextMenuItems(menuState)` method building the full ordered
  descriptor list.

- `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`
  — constructor accepts `isMainChart` / `isGridBotChart` options (both default
  `false`) and stores them as public fields. The context-menu builder reads
  them as visibility predicates.

- `src/containers/trade/trading-terminal/widgets/super-chart/super-chart.js`
  — passes `isMainChart: true` when constructing the controller.

- `src/containers/trade/trading-terminal/widgets/super-chart/grid-bot-super-chart.js`
  — passes `isGridBotChart: true` when constructing the controller.

- `src/containers/trade/trading-terminal/widgets/super-chart/chart-context-menu.js`
  — replaced empty body with `useMemo` mapping of descriptors into
  `PopupItem`s and `PopupSeparator`s. Each item's onClick is wrapped with a
  leading `close()` so the popup dismisses before the action runs. The
  component returns `null` when the item list is empty (e.g. during right-click
  inside an overlay or before the chart is fully wired).

- `src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js`
  — new public method `handleSelectReplayStartTime(time)` that wraps
  `_handleFirstReplay(time)` in `conditionalCallback` with the same
  `features: trading` + `widgets: CenterView` (when `inTrade`) gating the
  existing `handleRandomReplayStartTime` uses.

- `src/locales/{en,nl,es}/translation.yaml` — removed the dead
  `createNewRecurringAlert` key from all three locales. No new keys added.

- `ai/superchart-integration/phase-5/deferred.md`,
  `phase-5/replay/prd.md`, `phase-5/dialogs/prd.md`, `phase-5/stepback/prd.md`,
  `phase-5/stepback/tasks.md` — flipped the "deferred until chart context
  menu lands" bullets to "delivered in `[sc-chart-ctx-menu-options]`".

### Apply steps

Nothing special — HMR should pick up the changes. No rebuild of a linked
package, no new deps.

### Verification

#### Main chart — Alerts + Trading visibility (baseline, no replay, in trade)

1. Open Trading Terminal with a standard market, no replay session, Trade
   widget visible in the layout.
2. Right-click on empty chart background.
3. Expect to see, in order:
   - Create New Alert
   - Create Buy Order
   - Create Sell Order
   - (separator)
   - Set break even start
   - Set break even end
   - (separator)
   - Start replay from here
4. Click **Create New Alert** → popup closes, alert-creation flow starts at
   the right-click price.
5. Click **Create Buy Order** → popup closes, trade form is populated with
   the clicked price, buy quote input receives focus on the next tick.
6. Click **Create Sell Order** → sell base input receives focus.
7. Click **Set break even start** → position start time is set to the
   right-click timestamp.
8. Click **Set break even end** → position end time is set.

#### Main chart — trading feature gate

9. Revoke `trading` feature (dev tools / settings). Right-click → Create Buy
   Order → expect the feature-gate denial flow (message or upgrade prompt
   via `conditionalCallback`), NOT the trade form populated.

#### Main chart — `Trade` widget missing

10. Remove the Trade widget from the current layout. Right-click → Create Buy
    Order → expect the widget-gate flow (prompt to open the Trade widget),
    NOT a silent dispatch against a missing widget.

#### Main chart — Device gate + paper trading

11. Switch to a non-active device (`mustBeActive` should kick in). Right-click
    → Create Buy Order → expect the device-active prompt.
12. Switch to a paper-trading api key. Right-click → Create Buy Order →
    expect the buy dispatch to go through without the device prompt (the
    `mustBeActive` flag evaluates to `false`).

#### Main chart — Default replay active, paused

13. Start a default (non-smart) replay session and pause it.
14. Right-click on empty chart background.
15. Expect:
    - **No** Create New Alert, Create Buy/Sell Order, Set break even
      entries (all hidden by `!isDefaultReplayMode`).
    - (separator)
    - Start replay from here
    - Jump back to here
    - Play
    - Speed up replay (unless at max speed)
    - Slow down replay (unless at min speed)
    - Stop replay
16. Click **Jump back to here** on a point before the current replay time →
    replay rewinds via `goBackTo`, trades from the rewound range are
    reverted.
17. Click **Jump back to here** on a point after the current replay time →
    no change (the `time >= this.time` guard inside `goBackTo` silently
    drops the call).
18. Click **Jump back to here** on a point before `startTime` → toast
    warning "Can't go back earlier than start-time" (existing
    `cantGoBackEarlierThanStart` key).
19. Click **Play** → replay starts playing, label flips to Pause on next
    right-click.
20. Click **Speed up replay** → speed increments one step in
    `SC_SPEED_OPTIONS`. Verify at maximum (400) the entry is hidden.
21. Click **Slow down replay** → speed decrements one step. Verify at
    minimum (1) the entry is hidden.
22. Click **Stop replay** → loss-of-trades confirm if applicable, then
    session ends.

#### Main chart — Default replay active, playing

23. Start a default replay and let it play.
24. Right-click.
25. Expect the Play entry to read **Pause**, and **no Stop replay entry**
    (TV only showed Stop while paused — preserved here).

#### Main chart — Smart replay / backtest active

26. Start a smart replay session.
27. Right-click.
28. Expect **Alerts + Trading entries to remain visible** (smart mode is not
    `isDefaultReplayMode`) alongside the replay entries. This is the
    intentional TV behavior: only *default* replay hides trading.

#### Main chart — Backtest finished

29. Let a smart backtest finish.
30. Right-click.
31. Expect Alerts, Trading, and **Jump back to here** to be hidden (all
    gated on `!backtestIsFinished`). Play/Speed-Up/Slow-Down/Stop may still
    be visible depending on status — verify against the predicate matrix
    in `getChartContextMenuItems`.

#### Grid-bot chart

32. Open a grid-bot with the SC chart. Right-click on empty chart
    background.
33. Expect **no popup** (shell not mounted on grid-bot). This is the
    current pre-existing constraint of the shell and is NOT a regression.
    Noted for a future follow-up when grid-bot backtest entries get ported.

#### Extension point smoke test (main chart, dev console)

34. In the browser console, with the TT main chart mounted, register a
    temporary provider on the active chart controller:
    ```js
    const cc = ChartRegistry.getActive()
    cc.contextMenu.setChartContextMenuItemsProvider(({time, price, timezone}) => [
      {key: "smoke", type: "item", text: `t=${time} p=${price}`, onClick: () => console.log("smoke clicked", {time, price, timezone})},
    ])
    ```
35. Right-click → the smoke entry appears at the **top** of the menu, above
    Create New Alert. Click it → console logs the captured `{time, price,
    timezone}`.
36. Clear: `cc.contextMenu.setChartContextMenuItemsProvider(null)` → next
    right-click no longer shows the smoke entry.

#### Trading Terminal context actions

Each of the following must leave the menu in a consistent state. Perform
each action while the popup is open (expect the popup to close on symbol
change / chart destroy) and between right-clicks (expect the next menu to
reflect the new state):

37. Change TradingTab (switch between open tabs).
38. Change coinraySymbol (different market within the same tab).
39. Change resolution (timeframe change within the same tab).
40. Change exchangeApiKeyId (different api-key for the same tab).

#### Regressions check

41. Overlay right-click — still opens the OverlayContextMenu, not the
    chart-background menu. Both menus share `ContextMenuPopup` so verify
    they don't collide when one closes and the other opens.
42. Right-click while the replay pick-on-chart interaction is active
    (press the "Pick replay start" header button, then right-click) —
    expect the interaction to cancel (existing behavior — gated on
    `this.c.interaction?.active` inside `_onChartRightSelect`), menu does
    NOT open.
43. Right-click → Escape → popup closes. Right-click → scroll → popup
    closes. Right-click → click outside the popup → popup closes.

### Open items for follow-up review

- Confirm that `_handleFirstReplay`'s existing `cantReplayFuture` guard is
  reached when clicking a future timestamp via "Start replay from here"
  (expected — the guard fires synchronously at the top of
  `_handleFirstReplay`, before the mode dialog).
- Mount `ChartContextMenu` on `grid-bot-super-chart.js` when porting the
  two backtest provider entries (separate PRD).
- Verify the `moment.tz.zone(timezone)` call returns a non-null zone for
  all plausible values SC's `getTimezone()` can return. The datafeed
  currently hardcodes UTC so the exercise is trivial today — but if SC is
  given an exotic timezone string at some point, `zone` could be `null`
  and the code would fall through to `offset = 0`. Acceptable fallback;
  no need to fix speculatively.
