---
id: sc-chart-ctx-menu-options
---

# Chart Background Context Menu — Altrady Entries (Phase 4a-1 follow-up)

Port every Altrady-specific entry that the old TradingView (TV) integration added to
the TT main chart's right-click context menu over to the new SuperChart context-menu
shell that landed in `[sc-chart-ctx-menu]`.

This PRD is the successor to `[sc-chart-ctx-menu]`. The shell already renders an
empty `ContextMenuPopup` on right-click of the empty chart background — this PRD
fills that popup with the full set of Altrady actions that TV users had.

## Scope

### In scope

- The **Trading Terminal main chart** (desktop right-click on empty chart background).
- Every Altrady custom entry that the TV integration injected via
  `widget.onContextMenu(...)` in the TT main chart — Alerts, Trading (buy/sell order
  at price, break-even start/end), and Replay (start, jump back, play/pause, speed
  up, slow down, stop).
- Reuse of existing i18n keys under
  `containers.trade.market.marketGrid.centerView.tradingViewjs.*`.
- Resolution of the follow-up blockers tracked by `[sc-chart-ctx-menu]`:
  - Replay "Start replay here" (phase-5/deferred.md, phase-5/replay/prd.md,
    phase-5/dialogs/prd.md).
  - Step-back "Jump back to here" (phase-5/stepback/prd.md + tasks.md).
- An extension point so the **grid-bot backtest chart** can keep injecting its two
  domain-specific entries ("Set Backtest Start", "Set Backtest End"), which TV
  delivered through the hook's external `onContextMenu` callback.

### Out of scope

- Grid-bot backtest entries themselves — this PRD only provides the extension
  point. Porting those two entries is tracked separately and stays on the grid-bot
  backtest owner's plate.
- The TV `objectTree` entry. It piggy-backed on a TV-specific "leading-dash
  opens built-in panel" convention that SC does not have, and there is no SC
  equivalent to the Objects Tree panel. Drop it.
- The dead `createNewRecurringAlert` i18n key that existed in the YAML but was
  never referenced in TV JS. Do not port and do not revive.
- Overlay right-click menu — already handled by `[sc-overlay-ctx-menu]`.
- Mobile long-press — desktop right-click only (same constraint as the shell PRD).
- Quiz/Tutorial entries (`setSolutionStart` / `setSolutionEnd`). They belong to
  the tutorials subsystem and are tracked by its own work. Not ported here.
- Any new hotkey for opening the menu.

## TV reference

The TV implementation lived entirely in one hook:

`release-5.2.x : src/containers/trade/trading-terminal/widgets/center-view/tradingview/context/use-on-context-menu.js`

Wired via `tvWidget.onContextMenu(...)` in
`.../context/use-trading-view.js` (inside `onChartReady`). The hook returned an
array of `{position: "top", text, click}` descriptors per right-click with
`(time, price)` at the click point. Items that should not appear were filtered
out; separators used `{text: "-"}`.

i18n source for labels: `src/locales/en/translation.yaml` lines ~2062–2078.

## Menu entries

Top-to-bottom order below is the order TV users saw and must be preserved so
muscle memory carries over. Entries absent in a given UI state must be removed
from the array — not shown as disabled. Separators do **not** auto-collapse —
TV always rendered the fixed separator before the Replay group and the fixed
separator after it, even if neighboring groups were empty, and this port does
the same.

### State exposed to the entries

Each entry is a function of the right-click point and the current Redux / chart
state. Three values must be captured at the click point and held on the
chart-context-menu state for the lifetime of the popup:

- `time` — unix seconds at the click position. Derived from SC's
  `PriceTimeResult.point.time`.
- `price` — quote-currency price at the click position. Derived from SC's
  `PriceTimeResult.point.price`. Passed through as-is.
- `timezone` — the chart's current timezone string (e.g. `"Etc/UTC"`). Derived
  from SC's timezone API. If the chart is set to `"exchange"` it is normalized
  to `"UTC"` — same TV convention.

From these, the port computes `offsetTime`:

```
offset     = moment.tz.zone(timezone).utcOffset(time * 1000)   // minutes
offsetTime = time + offset * 60                                 // unix seconds
```

`offsetTime` is timezone-adjusted unix **seconds**. Which of `time`, `offsetTime`
or `offsetTime * 1000` an entry passes to its handler depends on the entry — see
each entry below. (TV was mixed: break-even handlers take seconds; replay
handlers take milliseconds; the external extension-point callback receives the
raw `time` in seconds without the offset.)

Values must be captured **at right-click time** — entries must read from the
stored snapshot, not recompute from the cursor when clicked.

### Group A — Alerts

1. **`createNewAlert`** → "Create New Alert"
   - **Visible when:** `showAlertOptions` = not `gridBotChart`, not
     `isDefaultReplayMode`, not `backtestFinished`, not `inQuizzes`, not
     `showQuizControls`. (Note: gated only on `!gridBotChart`, not `mainChart`
     — alerts show on any non-grid-bot chart.)
   - **Action:** dispatch `createAlert(coinraySymbol, {price})` — awaited inside
     the gated callback.
   - **Gating:** `conditionalCallback` with `{features: {feature: "trading"}}`
     only. No `device` gate, no `widgets` gate.
   - **User-action label** (passed as the `callbackDescription` arg to
     `conditionalCallback`): `actions.preview.userActions.createAlerts`.

### Group B — Trading

2. **`createBuyOrder`** → "Create Buy Order"
   - **Visible when:** `showTradingOptions` = `mainChart`, not
     `isDefaultReplayMode`, not `backtestFinished`, not `inQuizzes`, not
     `showQuizControls`.
   - **Action:** dispatch `startOrder({orderSide: BUY, price: new BigNumber(price)})`
     synchronously, then call `document.getElementById("trade-form-buy-quote")?.focus()`
     on the next event-loop tick (TV used `_.defer`, i.e. `setTimeout(fn, 0)` —
     the port must match so the focus lands after the trade form has rendered
     from the dispatch).
   - **Gating:** `conditionalCallback` with
     `{features: {feature: "trading"}, device: {mustBeActive: !replayMode && !exchangeApiKey?.paperTrading}, widgets: {widget: "Trade"}}`.
     Note `mustBeActive` is computed per-right-click: the device gate is
     effectively off when the session is in replay or the active api-key is
     paper-trading.
   - **User-action label:** `actions.preview.userActions.createOrders`.

3. **`createSellOrder`** → "Create Sell Order"
   - Same visibility and gating as entry 2.
   - **Action:** dispatch `startOrder({orderSide: SELL, price: new BigNumber(price)})`,
     then defer-focus `#trade-form-sell-base`.
   - **User-action label:** `actions.preview.userActions.createOrders`.

4. **Separator** (`{text: "-"}`). Shown when `showTradingOptions` is true — i.e.
   gated by the same flag as entries 2/3/5/6, not independently collapsible.

5. **`setBreakevenStart`** → "Set break even start"
   - **Visible when:** `showTradingOptions` (same as entries 2/3).
   - **Action:** dispatch `setPositionStartTime(offsetTime)` — `offsetTime` in
     **seconds**, not milliseconds.
   - **Gating:** `conditionalCallback` with `{features: {feature: "trading"}}`.
   - **User-action label:** `actions.preview.userActions.userBreakEven`.

6. **`setBreakevenEnd`** → "Set break even end"
   - **Visible when:** `showTradingOptions` (same as entries 2/3).
   - **Action:** dispatch `setPositionEndTime(offsetTime)` — seconds.
   - **Gating:** `conditionalCallback` with `{features: {feature: "trading"}}`.
   - **User-action label:** `actions.preview.userActions.userBreakEven`.

### Separator

7. **Separator** (`{text: "-"}`) — **unconditional**, always present in the
   array regardless of surrounding groups. Matches TV behavior. The port does
   not attempt to suppress adjacent or leading separators.

### Group C — Replay

Predicate base: `showReplayControls` = not `gridBotChart` and (no active
question controller OR the question is in `new`/`edit` mode). Note this is
independent of `showQuizControls` / `inQuizzes` — the replay controls remain
available during quiz editing. All derived replay-entry predicates below build
on top of `showReplayControls`.

`replayMode` here means the TV controller's `replayMode` getter — truthy when
any replay session (default OR smart) is active. `isDefaultReplayMode` (used by
Alerts/Trading hiding above) is truthy ONLY for the default mode — in a smart
replay / backtest session Trading and Alerts remain visible.

8. **`startReplay`** → "Start replay from here"
   - **Visible when:** `showReplayControls`.
   - **Action:** start a replay session at `offsetTime * 1000` (milliseconds)
     using the same flow as the pick-on-chart replay-start flow — that is,
     feature-gated with `conditionalCallback({features: {feature: "trading"},
     widgets: inTrade ? {widget: "CenterView"} : undefined})`, then stop any
     existing session (with the loss-of-trades confirm modal if applicable),
     then run the mode-dialog → `startReplay(time)` flow that
     `handleSelectReplayStartTimeClick` currently uses after a click lands.
   - **Design note:** The new SC `ReplayController` does not yet expose a
     public method equivalent to TV's `handleSelectReplayStartTime(time)` —
     only `handleSelectReplayStartTimeClick(isMobile)` (which starts an
     interaction to pick a time) and the private `_handleFirstReplay(time)`
     (which does not apply the feature/widget gate or the loss-of-trades
     confirm). The design doc adds a new public entry point on `ReplayController`
     that mirrors TV's `handleSelectReplayStartTime` — context menu and any
     future direct-time callers route through it.
   - This entry **replaces** the "Start replay here" follow-up called out in
     the shell PRD, `phase-5/deferred.md`, `phase-5/dialogs/prd.md`, and
     `phase-5/replay/prd.md`.

9. **`goBackInTime`** → "Jump back to here"
   - **Visible when:** `showGoBackInTime` = `showReplayControls && replayMode
     && !replayIsLoading && !backtestIsFinished`.
   - **Action:** `replayController.handleGoBackInTime(offsetTime * 1000,
     {keepSession: true})`. Must guard against `time === current`,
     `time > current`, and `time < startTime` with the same toast warnings TV
     showed ("Can't jump to the future", "Can't go back earlier than
     start-time") — keys to be added if they do not already exist in the
     replay namespace. With `keepSession: true` the replay trading state is
     rewound via `resetTo(time)` rather than the session being torn down.
   - **Design note:** The SC `ReplayController` does not yet implement
     `handleGoBackInTime`. The design doc adds it — based on TV's body, the
     underlying `resetTo(time)` + `setStartTime(startTime, {jumpTime: time,
     keepSession: true})` primitives must exist or be added in the same PR.
     This PRD resolves the deferred "Jump back to here" entry point in
     `phase-5/stepback/prd.md` and `phase-5/stepback/tasks.md`.

10. **`play`** / **`pause`** → "Play" / "Pause" (label is dynamic)
    - **Visible when:** `showPlayPauseReplay` = `showReplayControls &&
      replayMode && !replayIsLoading`.
    - **Label:** when `replayIsPlaying` the label is the `pause` key;
      otherwise the `play` key. TV used
      `containers.trade.market.marketGrid.centerView.tradingViewjs.play` /
      `.pause` — reuse those so the label matches TV exactly.
    - **Action:** `replayController.handlePlayPause()`.

11. **`speedUpReplay`** → "Speed up replay"
    - **Visible when:** `showReplayControls && replayMode && !replayIsLoading
      && replay.intervalMs > ReplayController.minIntervalMs`.
    - **Action:**
      ```
      const faster = Math.max(0, INTERVAL_OPTIONS.indexOf(replay.intervalMs) - 1)
      await replayController.setIntervalMs(INTERVAL_OPTIONS[faster])
      ```
      Uses the same `INTERVAL_OPTIONS` table the replay-controls UI uses.
      When `intervalMs` is not a member of the table (`indexOf` → `-1`), the
      port must clamp to the fastest option (index 0) — TV's expression did
      this by accident via `Math.max(0, -2)`; the SC port must preserve that
      clamp explicitly, not rely on the accident.

12. **`slowDownReplay`** → "Slow down replay"
    - **Visible when:** `showReplayControls && replayMode && !replayIsLoading
      && replay.intervalMs < ReplayController.maxIntervalMs`.
    - **Action:**
      ```
      const slower = Math.min(INTERVAL_OPTIONS.length - 1, INTERVAL_OPTIONS.indexOf(replay.intervalMs) + 1)
      await replayController.setIntervalMs(INTERVAL_OPTIONS[slower])
      ```
      Same `indexOf(-1)` clamp requirement — when the current interval is
      unknown, clamp to the slowest option.

13. **`stopReplay`** → "Stop replay"
    - **Visible when:** `showStopReplay` = `showReplayControls && replayMode
      && !replayIsLoading && !replayIsPlaying`. TV only offered Stop while
      paused — preserve this.
    - **Action:** `replayController.handleStop()` — which shows the
      loss-of-trades confirmation modal when `willLoseDataIfStopped` is true.

### Dropped

14. **`objectTree`** (TV entry 18) — not ported. See Out of scope.

### Terminal separator (dropped)

TV ended the array with a trailing `{text: "-", position: "top"}` separator
immediately before the `objectTree` entry. Since `objectTree` is dropped, that
terminal separator is dropped too — there is nothing after it to separate from
TV's native menu entries (SC has none to append).

## Extension point for external entries

TV's hook accepted an `onContextMenu({time, timezone, price})` callback whose
return array was prepended to the built-in entries via `contextMenu.concat(...)`.
The grid-bot backtest chart used this to add "Set Backtest Start" / "Set
Backtest End", both of which computed from the **raw `time` in seconds** (not
`offsetTime`) because the backtest range is set from candle time directly.

The SC port must provide an equivalent extension mechanism so domain-specific
charts can inject their own top-of-menu entries without forking the controller.
The mechanism must:

- Deliver the `{time, timezone, price}` snapshot captured at right-click time.
  `time` is **raw unix seconds**, not `offsetTime` — the backtest chart's two
  entries depend on this.
- Prepend returned entries above the built-in Altrady entries.
- Apply the same filter-out semantics (a falsy entry is dropped).
- Be registerable/unregisterable per chart controller instance so the main chart
  and the grid-bot backtest chart do not interfere.

Porting the two backtest entries themselves is **not** part of this PRD — only
the extension point is. The backtest owner must introduce i18n keys for "Set
Backtest Start" / "Set Backtest End" before porting; TV had them as raw strings.

## Visibility predicate requirements

The TV hook concentrated every show/hide flag at the top of the function and
reused them across entries. The SC port must do the same — a single source of
truth per predicate — so the entries cannot drift from each other. The
predicates are (names are requirements, not prescribed identifiers):

- `isMainChart` / `isGridBotChart`
- `inReplayMode` (default replay is active)
- `isBacktestFinished`
- `inQuizzes` / `showQuizControls` (quiz/tutorial predicates stay wired so the
  main chart correctly hides Trading/Alerts entries when a tutorial is
  overlaid — even though quiz-only entries are not ported)
- `tradingFeatureAllowed`, `deviceActive`, `isPaperTrading`
- `tradeWidgetOpen`
- `replaySessionActive`, `replayIsLoading`, `replayIsPlaying`,
  `replayIntervalAtMin`, `replayIntervalAtMax`

The set of entries that ends up in the menu for a given state must match what
the TV hook would have produced for the same state. Where TV computed the flag
from a specific selector, the SC port should use the same selector so the
behavior is bit-for-bit equivalent.

## Context-menu state shape

The shell PRD ([sc-chart-ctx-menu]) stored only `{x, y}` on the controller's
chart-context-menu state. This PRD extends the shape to:

```
{ x, y, time, price, timezone }
```

Where:
- `x`, `y` — page coordinates for popup positioning (already in the shell).
- `time` — unix seconds from `PriceTimeResult.point.time`.
- `price` — quote-currency price from `PriceTimeResult.point.price`.
- `timezone` — chart timezone offset in minutes, captured at right-click time so
  `offsetTime` computation is stable for the lifetime of the popup.

The existing page-coord bridge in `ContextMenuController._onChartRightSelect`
keeps its `TODO` pointing at the SC-library task; this PRD does not touch it.

## Action gating and dispatch pattern

Every entry that dispatches through a feature / widget / device gate must use
the same dispatch path the header buttons and hotkeys use today. Do not
re-implement the gate inline. The TV hook wrapped trading/alert entries in
`conditionalCallback(..., {features: {feature: "trading"}, widgets: {widget:
"CenterView"}})`; the SC port must either reuse `conditionalCallback` directly
or route through an existing method that already applies the same gating (e.g.
`replayController.handleRandomReplayStartTime` already shows the pattern in the
new codebase).

Replay entries 8–13 must route through `ReplayController` methods, not through
ad-hoc Redux dispatches, so the controller remains the single source of truth
for replay lifecycle state.

## i18n

Reuse existing keys from
`containers.trade.market.marketGrid.centerView.tradingViewjs.*`:

- `createNewAlert`
- `createBuyOrder`
- `createSellOrder`
- `setBreakevenStart`
- `setBreakevenEnd`
- `startReplay`
- `goBackInTime`
- `play`
- `pause`
- `speedUpReplay`
- `slowDownReplay`
- `stopReplay`

Do **not** introduce new keys for entries that already have one. Delete
`createNewRecurringAlert` from the YAML, since no code path references it and
TV never wired it up.

User-action labels for `conditionalCallback` calls:
- `actions.preview.userActions.createAlerts` (Create Alert)
- `actions.preview.userActions.createOrders` (Create Buy/Sell Order)
- `actions.preview.userActions.userBreakEven` (Set break-even start/end)
- `actions.preview.userActions.setReplay` (Start replay from here — reuses
  the TV key already used by `handleRandomReplayStartTime` in the new codebase)

## Dismissal, cleanup, lifecycle

Unchanged from `[sc-chart-ctx-menu]`. In particular:

- Clicking an entry closes the popup before dispatching the action. Any action
  that opens another popup/modal (e.g. `startOrder`, `editAlert`,
  `_handleFirstReplay` with mode dialog) must not race with the context-menu
  popup — the context menu closes first, its dispose path runs, then the entry
  handler fires.
- Chart unmount, symbol change, resolution change — all close the popup (shell
  already handles this via the symbol-change cleanup hook pattern).
- Escape, outside click, scroll — handled by `ContextMenuPopup` today.

## Unblocks / references to update

This PRD supersedes the "deferred until chart context menu lands" bullets in:

- `ai/superchart-integration/phase-5/deferred.md` — remove the "Start replay
  here" deferred bullet; note `[sc-chart-ctx-menu-options]` resolved it.
- `ai/superchart-integration/phase-5/replay/prd.md` — update the out-of-scope
  line that currently reads "Chart context menu 'Start replay here'".
- `ai/superchart-integration/phase-5/dialogs/prd.md` — flip the "Deferred — no
  chart context menu yet" row to done, linked to this PRD.
- `ai/superchart-integration/phase-5/stepback/prd.md` — remove the non-
  requirement "No 'jump to here' chart context-menu entry" and replace with
  "Delivered in `[sc-chart-ctx-menu-options]`".
- `ai/superchart-integration/phase-5/stepback/tasks.md` — mark the deferred
  "Context-menu 'Jump back to here' entry point" task resolved in this PRD.

All four doc updates are part of this PRD's implementation, not a separate
chore.

## Non-requirements

- No changes to the shell (`[sc-chart-ctx-menu]`) architecture — same
  `ContextMenuController`, same `ChartContextMenu` component. This PRD only
  extends the state shape and fills in the popup body.
- No new popup component, no custom styling, no new icons. Entries render as
  plain `PopupItem`s (text only, matching how TV displayed them).
- No reordering or renaming of existing `common.*` keys.
- No changes to `ReplayController`'s existing handler method signatures, aside
  from whatever the stepback work requires for "Jump back to here" — that
  work is owned by `phase-5/stepback`, not this PRD.
- No keyboard shortcut for any of the entries. Right-click only.
- No hover-preview of the price/time the entry will act on (TV had none either).
- No grid-bot backtest chart support beyond the extension point.
- No tutorial/quiz entries.
