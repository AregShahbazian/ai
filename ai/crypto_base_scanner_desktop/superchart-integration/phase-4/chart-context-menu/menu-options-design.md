# Chart Background Context Menu — Altrady Entries — Design

PRD: `menu-options-prd.md` (`[sc-chart-ctx-menu-options]`).

This is the design for filling the empty context-menu shell from
`[sc-chart-ctx-menu]` with the full set of Altrady entries from the old TV
integration.

## Architecture

### Where menu items are built

TV built the item list inside a React hook (`useOnContextMenu`) that read
Redux state via `useSelector` and closed over `dispatch`. That put visual logic
and action dispatching in the component tree.

The SC port moves this logic **into `ContextMenuController`**, consistent with
the "controller owns all visual logic" rule already established for other SC
sub-features (overlay controllers, bases, replay). The controller exposes a
single entry point:

```js
contextMenu.getChartContextMenuItems(menuState) → Descriptor[]
```

Where `menuState` is the snapshot captured at right-click time
(`{x, y, time, price, timezone}`) and `Descriptor` is a plain object of one of
these shapes:

```js
{ key: string, type: "item", text: string, onClick: () => void }
{ key: string, type: "separator" }
```

The React component (`ChartContextMenu`) does no selector calls, no dispatches,
no visibility logic — it just maps descriptors to `PopupItem`s (and to a visual
separator element for `type: "separator"`).

Rationale: TV's hook was a source of drift because visibility predicates lived
next to UI rendering. Moving the list into the controller means any
visibility-logic regression shows up when exercising the controller, not only
when right-clicking in a running app.

### Items are computed once per right-click, not live-updated

TV rebuilt the item list on every right-click and never updated it while the
menu was open. The SC port matches this: `getChartContextMenuItems` is called
once, at React render time when `menuState` flips from `null` to a snapshot.
If the user pauses a replay session while the menu is open, the visible
"Pause" entry does not change to "Play" — this matches TV behavior. The next
right-click rebuilds the list against fresh state.

No `useEffect` / live subscription is required. The descriptors are computed
synchronously from `this.c.getState()` at the time of the call.

## Data flow

1. User right-clicks the chart background.
2. SC fires `onRightSelect(result)` — delivered to
   `ContextMenuController._onChartRightSelect`.
3. The handler currently stores only `{x, y}`. This PRD extends it to capture
   the full snapshot:
   ```js
   _onChartRightSelect = (result) => {
     if (this.c.interaction?.active) return
     const rect = this.c.getContainer()?.getBoundingClientRect()
     if (!rect) return
     const x = rect.left + result.coordinate.x
     const y = rect.top  + result.coordinate.y
     const time  = result.point?.time  ?? null   // unix seconds
     const price = result.point?.price ?? null   // quote currency
     let timezone = this.c._superchart?.getTimezone?.() || "Etc/UTC"
     if (timezone === "exchange") timezone = "UTC"
     this.openChartContextMenu({x, y, time, price, timezone})
   }
   ```
4. `ChartContextMenu` React component re-renders with `menuState` set.
5. Component calls `contextMenu.getChartContextMenuItems(menuState)` and maps
   the descriptors to popup elements.
6. On click, each descriptor's `onClick` runs. The component wraps each
   descriptor's `onClick` with a leading `close()` so the popup dismisses
   before the action dispatches (avoids modal-stacking races with actions that
   open their own dialogs, e.g. `startOrder`, `createAlert`,
   `_handleFirstReplay`'s mode dialog).

## State shape extension

```js
// context-menu-controller.js
this._chartContextMenuState = null // { x, y, time, price, timezone } or null
```

`time` is unix seconds. `price` is a plain number. `timezone` is a
moment-timezone identifier (`"Etc/UTC"`, `"America/New_York"`, etc.).
`offsetTime` is **not** stored — it is derived inside
`getChartContextMenuItems` via moment-timezone, so the closure that computes it
also owns which entries need seconds vs. milliseconds.

## `getChartContextMenuItems` implementation sketch

```js
// context-menu-controller.js
import moment from "moment-timezone"
import {BigNumber} from "bignumber.js"
import {conditionalCallback} from "~/actions/conditional-callback"
import {createAlert} from "~/actions/alerts"
import {startOrder} from "~/actions/trading"
import {OrderSide} from "~/actions/constants/trading"
import {setPositionStartTime, setPositionEndTime} from "~/actions/positions"
import {REPLAY_MODE, ReplayController} from "./replay-controller"
import {INTERVAL_OPTIONS} from "../replay/replay-controls"
import {Selectors} from "~/util/selectors"
import i18n from "~/i18n"
import _ from "lodash"

getChartContextMenuItems(menuState) {
  if (!menuState) return []
  const {time, price, timezone} = menuState
  if (time == null || price == null) return []

  const offset     = moment.tz.zone(timezone)?.utcOffset(time * 1000) ?? 0
  const offsetTime = time + offset * 60

  // Visibility predicates — single source of truth per flag, matching TV.
  const state               = this.c.getState()
  const replay              = this.c.replay                    // ReplayController instance
  const replayMode          = replay?.replayMode               // undefined | DEFAULT | SMART
  const replayIsPlaying     = !!replay?.isPlaying
  const replayIsLoading     = !!replay?.isLoading
  const replayIntervalMs    = replay?.intervalMs
  const isDefault           = replayMode && replayMode !== REPLAY_MODE.SMART
  const backtestIsFinished  = !!this.c._backtestIsFinished
  const inQuizzes           = Selectors.inQuizzes(state)
  const isMainChart         = !!this.c.isMainChart             // set in constructor
  const isGridBotChart      = !!this.c.isGridBotChart
  const showQuizControls    = false                            // not ported in this PRD
  const inTrade             = Selectors.inTrade(state)
  const exchangeApiKey      = this.c.getExchangeApiKey?.()
  const mustBeActive        = !replayMode && !exchangeApiKey?.paperTrading

  const showAlertOptions    = !isGridBotChart && !isDefault && !backtestIsFinished && !inQuizzes && !showQuizControls
  const showTradingOptions  = isMainChart      && !isDefault && !backtestIsFinished && !inQuizzes && !showQuizControls
  const showReplayControls  = !isGridBotChart  // quiz-mode carve-out not in scope
  const showPlayPauseReplay = showReplayControls && replayMode && !replayIsLoading
  const showGoBackInTime    = showPlayPauseReplay && !backtestIsFinished
  const showSpeedUp         = showReplayControls && replayMode && !replayIsLoading && replayIntervalMs > ReplayController.minIntervalMs
  const showSlowDown        = showReplayControls && replayMode && !replayIsLoading && replayIntervalMs < ReplayController.maxIntervalMs
  const showStopReplay      = showReplayControls && replayMode && !replayIsLoading && !replayIsPlaying

  // External provider — prepend domain-specific entries (e.g. grid-bot backtest).
  const external = this._chartContextMenuItemsProvider
    ? (this._chartContextMenuItemsProvider({time, timezone, price}) || [])
    : []

  const T = (key) => i18n.t(`containers.trade.market.marketGrid.centerView.tradingViewjs.${key}`)
  const dispatch = (thunk) => this.c.dispatch(thunk)

  return [
    ...external.filter(Boolean),

    showAlertOptions && {
      key: "createNewAlert",
      type: "item",
      text: T("createNewAlert"),
      onClick: () => dispatch(conditionalCallback(
        async () => { await dispatch(createAlert(this.c.coinraySymbol, {price})) },
        i18n.t("actions.preview.userActions.createAlerts"),
        {features: {feature: "trading"}},
      )),
    },

    showTradingOptions && {
      key: "createBuyOrder",
      type: "item",
      text: T("createBuyOrder"),
      onClick: () => dispatch(conditionalCallback(
        () => {
          dispatch(startOrder({orderSide: OrderSide.BUY, price: new BigNumber(price)}))
          _.defer(() => document.getElementById("trade-form-buy-quote")?.focus())
        },
        i18n.t("actions.preview.userActions.createOrders"),
        {features: {feature: "trading"}, device: {mustBeActive}, widgets: {widget: "Trade"}},
      )),
    },
    showTradingOptions && {
      key: "createSellOrder",
      type: "item",
      text: T("createSellOrder"),
      onClick: () => dispatch(conditionalCallback(
        () => {
          dispatch(startOrder({orderSide: OrderSide.SELL, price: new BigNumber(price)}))
          _.defer(() => document.getElementById("trade-form-sell-base")?.focus())
        },
        i18n.t("actions.preview.userActions.createOrders"),
        {features: {feature: "trading"}, device: {mustBeActive}, widgets: {widget: "Trade"}},
      )),
    },
    showTradingOptions && {key: "sep-trading", type: "separator"},
    showTradingOptions && {
      key: "setBreakevenStart",
      type: "item",
      text: T("setBreakevenStart"),
      onClick: () => dispatch(conditionalCallback(
        () => dispatch(setPositionStartTime(offsetTime)),
        i18n.t("actions.preview.userActions.userBreakEven"),
        {features: {feature: "trading"}},
      )),
    },
    showTradingOptions && {
      key: "setBreakevenEnd",
      type: "item",
      text: T("setBreakevenEnd"),
      onClick: () => dispatch(conditionalCallback(
        () => dispatch(setPositionEndTime(offsetTime)),
        i18n.t("actions.preview.userActions.userBreakEven"),
        {features: {feature: "trading"}},
      )),
    },

    {key: "sep-replay", type: "separator"},   // unconditional — matches TV

    showReplayControls && {
      key: "startReplay",
      type: "item",
      text: T("startReplay"),
      onClick: () => replay.handleSelectReplayStartTime(offsetTime * 1000),
    },
    showGoBackInTime && {
      key: "goBackInTime",
      type: "item",
      text: T("goBackInTime"),
      onClick: () => replay.handleGoBackInTime(offsetTime * 1000, {keepSession: true}),
    },
    showPlayPauseReplay && {
      key: "playPause",
      type: "item",
      text: T(replayIsPlaying ? "pause" : "play"),
      onClick: () => replay.handlePlayPause(),
    },
    showSpeedUp && {
      key: "speedUpReplay",
      type: "item",
      text: T("speedUpReplay"),
      onClick: async () => {
        const idx   = INTERVAL_OPTIONS.indexOf(replayIntervalMs)
        const faster = idx < 0 ? 0 : Math.max(0, idx - 1)
        await replay.setIntervalMs(INTERVAL_OPTIONS[faster])
      },
    },
    showSlowDown && {
      key: "slowDownReplay",
      type: "item",
      text: T("slowDownReplay"),
      onClick: async () => {
        const idx    = INTERVAL_OPTIONS.indexOf(replayIntervalMs)
        const slower = idx < 0 ? INTERVAL_OPTIONS.length - 1 : Math.min(INTERVAL_OPTIONS.length - 1, idx + 1)
        await replay.setIntervalMs(INTERVAL_OPTIONS[slower])
      },
    },
    showStopReplay && {
      key: "stopReplay",
      type: "item",
      text: T("stopReplay"),
      onClick: () => replay.handleStop(),
    },
  ].filter(Boolean)
}
```

Note the TV `indexOf → -1` clamp is made explicit — TV relied on the accidental
`Math.max(0, -2)` behavior. The port clamps intentionally with an `idx < 0` guard.

## Timezone sourcing

`superchart.getTimezone()` exists in the SC public API (`SUPERCHART_API.md` L84,
defaults to `"Etc/UTC"`). The controller already holds the `_superchart`
reference from `mount(superchart)`. Capture the timezone at right-click time
so that if the user changes timezone between opening the popup and clicking an
entry, the entry still acts on the snapshot that was displayed.

The SC datafeed currently hardcodes `timezone: "UTC"` on every symbol
(`coinray-datafeed.js:42`), so in practice `offset === 0` today and `offsetTime
=== time`. The bridging code is still implemented so that the menu continues
to work correctly when per-user timezone support is added later — no rework
needed at that point.

## `ReplayController` additions

Two new methods on the existing SC `ReplayController`. Both mirror the TV
controller's public API for the context menu callers.

### `handleSelectReplayStartTime(time)`

```js
handleSelectReplayStartTime = (time) => {
  const inTrade = Selectors.inTrade(this.getState())
  this.dispatch(conditionalCallback(
    () => this._handleFirstReplay(time),
    i18n.t("actions.preview.userActions.setReplay"),
    {
      features: {feature: "trading"},
      widgets: inTrade ? {widget: "CenterView"} : undefined,
    },
  ))
}
```

Distinct from the existing `handleSelectReplayStartTimeClick(isMobile)` (which
starts a click-to-pick interaction, not a direct-time call). The context menu
bypasses the pick-interaction because the time is already known.

Note on loss-of-trades confirm: TV wrapped this path in `handleStop(cb)` which
shows the confirm modal when `willLoseDataIfStopped` is true. The SC port
**intentionally does not** — `_handleFirstReplay` → `_startReplayInMode` →
`_stop({keepEngine: true})` already handles the existing-session teardown, and
the current pick-on-chart flow (`handleSelectReplayStartTimeClick`) silently
tears down without a confirm. Adding a confirm here only for the context-menu
entry would create an inconsistency with the pick-on-chart flow — so the
context-menu entry matches pick-on-chart's behavior instead of TV's. If a
confirm is desired, it is a separate cross-cutting change that applies to both
flows at once and is owned by phase-5.

### `handleGoBackInTime(time, {keepSession})`

```js
handleGoBackInTime = async (time, {autoPlay, keepSession} = {}) => {
  if (!time || this.isLoading) return
  if (keepSession) {
    if (time === this.time) return
    if (time > this.time) {
      toast.warn(i18n.t("containers.trade.market.marketGrid.centerView.tradingView.replay.cantJumpFuture"))
      return
    }
    if (time < this.startTime) {
      toast.warn(i18n.t("containers.trade.market.marketGrid.centerView.tradingView.replay.cantGoEarlierThanStart"))
      return
    }
    const resetToError = await this.resetTo(time)
    if (resetToError) {
      toast.warn(resetToError, {autoClose: 10000})
      return
    }
    await this.setStartTime(this.startTime, {jumpTime: time, keepSession})
  } else {
    const startTime = this.startTime
    await this.handleStop(async () => {
      await this._startReplay(startTime, {autoPlay, quickStart: true})
    })
  }
}
```

**Dependencies that must exist in the new `ReplayController` (or be added in
the same PR):**

- `resetTo(time)` — rewinds `replayTradingController` state to `time` and
  returns an error string on failure, `null` on success. TV had this;
  `phase-5/stepback/prd.md` line 159 confirms it exists in the new codebase.
- `setStartTime(startTime, {jumpTime, keepSession})` — re-seeds the engine at
  `startTime` using `jumpTime` as the draw position, skipping the trading-state
  reset when `keepSession: true`. The engine seek primitive
  `sc.replay.setCurrentTime(time)` (already used by `handleBackToStartClick`
  per phase-5/stepback/prd.md L163) is the underlying call.
- `toast` keys `cantJumpFuture` and `cantGoEarlierThanStart` — TV used hardcoded
  English strings ("Can't jump to the future" / "Can't go back earlier than
  start-time"). The port adds proper i18n keys under the existing
  `tradingView.replay.*` namespace.

If either primitive is missing, the design falls back to implementing
`handleGoBackInTime` on top of whatever seek primitive does exist — this is
called out in tasks as a verification step.

### `ReplayController.minIntervalMs` / `.maxIntervalMs`

TV exposed these as `static` class fields on the TV `ReplayController` (values
`10` and `10000`). Verify they exist on the SC `ReplayController` — if not, add
them as static fields matching the `INTERVAL_OPTIONS` endpoints. The context
menu reads them directly via `ReplayController.minIntervalMs`, not through an
instance method, matching TV.

## External extension point

Controller API:

```js
setChartContextMenuItemsProvider(fn /* or null */) {
  this._chartContextMenuItemsProvider = fn
}
```

- Single provider per `ChartController` instance. Main chart and grid-bot
  backtest chart have separate instances, so each registers its own provider.
- Provider signature: `({time, timezone, price}) → Descriptor[]`. `time` is
  raw unix seconds — not `offsetTime`.
- Returned descriptors use the same `{key, type, text, onClick}` shape as the
  built-in ones. Falsy entries are stripped by the same `filter(Boolean)` pass.
- Provider's items are **prepended** to the built-in list (matches TV's
  `contextMenu.concat(altradyItems)` order).

**Registration from the grid-bot backtest chart** is out of scope for this
PRD. The extension point is delivered, an open question documents what
registration will look like when the backtest chart is ported, and tasks
include a smoke test that confirms the provider wiring works without a real
backtest provider registered.

## `ChartContextMenu` component update

```js
// super-chart/chart-context-menu.js
import React, {useCallback, useEffect, useState, useMemo} from "react"
import {Popup, PopupItem} from "~/components/design-system/v2/popups"
import {ContextMenuPopup} from "~/components/elements/context-menu"
import {useSuperChart} from "./context"

const ChartContextMenu = () => {
  const {chartController} = useSuperChart()
  const [menuState, setMenuState] = useState(null)

  useEffect(() => {
    if (!chartController) return
    chartController.contextMenu.setChartContextMenuCallback(setMenuState)
    return () => chartController.contextMenu.setChartContextMenuCallback(null)
  }, [chartController])

  const close = useCallback(() => {
    chartController?.contextMenu.closeChartContextMenu()
  }, [chartController])

  const items = useMemo(
    () => (menuState ? chartController?.contextMenu.getChartContextMenuItems(menuState) || [] : []),
    [menuState, chartController],
  )

  if (!menuState) return null

  return (
    <ContextMenuPopup x={menuState.x} y={menuState.y} onClose={close} spanMobile={false}>
      <Popup>
        {items.map((item) => {
          if (item.type === "separator") {
            return <hr key={item.key} tw="my-1 border-t border-panel-border"/>  // ← uses existing separator styling
          }
          return (
            <PopupItem
              key={item.key}
              onClick={() => { close(); item.onClick() }}
            >
              {item.text}
            </PopupItem>
          )
        })}
      </Popup>
    </ContextMenuPopup>
  )
}
```

Open item: confirm the exact separator element. `OverlayContextMenu` may
already render separators via a specific component — use the same one to stay
consistent (tasks include a step to check and match).

## Predicate sourcing — what each flag reads

| Predicate              | Source in new SC codebase                                 |
|------------------------|-----------------------------------------------------------|
| `isMainChart`          | `this.c.isMainChart` boolean field set in ctor            |
| `isGridBotChart`       | `this.c.isGridBotChart` boolean field set in ctor         |
| `replayMode`           | `this.c.replay.replayMode` getter                         |
| `replayIsPlaying`      | `this.c.replay.isPlaying` getter                          |
| `replayIsLoading`      | `this.c.replay.isLoading` getter                          |
| `replayIntervalMs`     | `this.c.replay.intervalMs` (live property)                |
| `backtestIsFinished`   | `this.c._backtestIsFinished` (already used for overlay menu) |
| `inQuizzes`            | `Selectors.inQuizzes(state)` — router pathname check      |
| `inTrade`              | `Selectors.inTrade(state)` — router pathname check        |
| `exchangeApiKey`       | `this.c.getExchangeApiKey()` (existing helper)            |

If any of the `this.c.*` accessors listed above do not yet exist on the current
`ChartController`, tasks include adding them as thin pass-throughs — the
underlying data is already available, only the accessor may be missing.

## Closure safety and stale state

Because descriptors are built at render time (triggered by `menuState` flipping
to non-null), every descriptor closes over **today's** `this.c.getState()` and
`this.c.replay` references. The controller cannot be reassigned during a
popup's lifetime — symbol change, dispose, and unmount all close the popup,
which discards the descriptors. So there is no risk of an onClick firing
against a stale controller instance.

The TV hook's `util.useImmutableCallback` wrapping is not needed — the SC port
does not expose the builder to React's reference-identity checks.

## File changes

### New files

None. All changes extend existing files.

### Modified files

1. **`controllers/context-menu-controller.js`**
   - Extend `_onChartRightSelect` to capture `time`, `price`, `timezone`.
   - Add `getChartContextMenuItems(menuState)`.
   - Add `setChartContextMenuItemsProvider(fn)` + `_chartContextMenuItemsProvider` field.
   - Add ctor init for the provider field.
   - Import: `moment`, `BigNumber`, `i18n`, `conditionalCallback`, `createAlert`,
     `startOrder`, `OrderSide`, `setPositionStartTime`, `setPositionEndTime`,
     `INTERVAL_OPTIONS`, `Selectors`, `lodash` (for `_.defer`). `REPLAY_MODE`
     and `ReplayController` from `replay-controller.js`.

2. **`controllers/replay-controller.js`**
   - Add `handleSelectReplayStartTime(time)` public method (new).
   - Add `handleGoBackInTime(time, opts)` public method (new).
   - Verify `static minIntervalMs` / `static maxIntervalMs` are defined — add if missing.
   - Verify `resetTo` and `setStartTime({jumpTime, keepSession})` exist — add or
     adapt if missing. Cross-check against `phase-5/stepback` deliverables.

3. **`chart-context-menu.js`** (existing component, currently empty body)
   - Compute `items` via `useMemo` from `menuState`.
   - Map descriptors to `PopupItem`s / separators.
   - Wrap each item's `onClick` with a leading `close()` call.

4. **`chart-controller.js`**
   - Expose `isMainChart`, `isGridBotChart`, `getExchangeApiKey()`, `coinraySymbol`
     accessors as needed for the predicate pipeline. Verify each exists first —
     only add the ones missing.

5. **i18n — `src/locales/en/translation.yaml`** (and matching nl/es if
   customary for this repo — check existing TV keys to confirm translation
   parity was maintained)
   - Add `tradingView.replay.cantJumpFuture` / `.cantGoEarlierThanStart` toast
     keys under the existing replay namespace.
   - Remove the dead `createNewRecurringAlert` key.

6. **Cross-reference doc updates**
   - `phase-5/deferred.md` — mark "Start replay here" context-menu entry as
     delivered by `[sc-chart-ctx-menu-options]`.
   - `phase-5/replay/prd.md` — update the out-of-scope line referencing the
     chart context menu.
   - `phase-5/dialogs/prd.md` — flip "Deferred — no chart context menu yet" to
     delivered.
   - `phase-5/stepback/prd.md` — rewrite the non-requirement about "jump to
     here" chart context-menu entry.
   - `phase-5/stepback/tasks.md` — mark the deferred "Context-menu 'Jump back
     to here' entry point" task resolved.

## Open questions

1. **Separator component.** Does `OverlayContextMenu` use a `<PopupSeparator>`
   or an ad-hoc `<hr>`? The new component must match whichever it is. Tasks
   include an inspection step before writing the mapping.

2. **`_backtestIsFinished` exposure on the main chart.** The
   `ContextMenuController` already uses `this.c.replay?.smart?.backtest?.isFinished`
   internally (`context-menu-controller.js:107`). Reuse that same path for the
   predicate — do not duplicate.

3. **`isMainChart` / `isGridBotChart` on `ChartController`.** These need to be
   set by whoever instantiates the controller. Grid-bot passes `isGridBotChart:
   true` today through the grid-bot wrapper; main chart may default to
   `isMainChart: true`. Confirm exact wiring before writing tasks.

4. **Backtest extension-point smoke test.** Without a real backtest provider
   registered, how do we confirm the provider mechanism works end-to-end? Plan
   is a temporary ad-hoc `setChartContextMenuItemsProvider(() => [...])` in
   dev console during review, documented as a verification step — not shipped.

5. **Loss-of-trades confirm on `handleSelectReplayStartTime`.** Documented in
   the `ReplayController additions` section — the port deliberately matches
   the current SC pick-on-chart flow (no confirm) rather than TV's (with
   confirm), to avoid per-flow inconsistency. This should be flagged for
   review so the user can confirm the trade-off is acceptable.

6. **Predicate parity with TV under quiz mode.** TV's `showReplayControls`
   looked at `questionController?.active` and question modes to suppress
   controls during quiz play. The SC port leaves quiz handling out and sets
   `showQuizControls = false` unconditionally. If/when the quiz system is
   ported to SC, revisit the predicate.
