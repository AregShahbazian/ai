# Chart Background Context Menu — Altrady Entries — Tasks

PRD: `menu-options-prd.md` (`[sc-chart-ctx-menu-options]`).
Design: `menu-options-design.md`.

## Preflight

### Task 0a: Verify predicate sources exist on `ChartController`
**File:** `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`

Confirm each of these is already accessible from the controller or add a thin
accessor. Do not modify semantics — only surface existing data:

- `isMainChart` (bool)
- `isGridBotChart` (bool)
- `coinraySymbol` (string)
- `getExchangeApiKey()` or equivalent getter
- `replay.replayMode` / `replay.isPlaying` / `replay.isLoading` / `replay.intervalMs`

Grep the file for each. If a grid-bot wrapper passes `isGridBotChart: true`,
trace where `isMainChart` gets set (or inferred as `!isGridBotChart`). Do the
same for `getExchangeApiKey`.

**Verification:** All predicate sources resolve from `this.c.*` in a
copy-pasted snippet of `getChartContextMenuItems`. No runtime lookups needed
yet.

### Task 0b: Verify `ReplayController` dependencies
**File:** `src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js`

Confirm each of the following exists. For anything missing, mark it as a
blocker and add the minimum needed in Task 4:

- `static minIntervalMs` / `static maxIntervalMs`
- Instance getters: `replayMode`, `isPlaying`, `isLoading`, `intervalMs`, `time`, `startTime`
- `resetTo(time)` returning error-or-null
- `setStartTime(startTime, {jumpTime, keepSession})` with `keepSession` handling
- `setIntervalMs(intervalMs)`
- `handlePlayPause()` / `handleStop()`
- `_handleFirstReplay(time)` (already confirmed via prior read — still re-check)

**Verification:** List the results in-line as code comments in the task note
(or reply in chat before starting Task 4). If anything is missing, Task 4
adds it.

### Task 0c: Confirm separator element used by `OverlayContextMenu`
**Files:**
- `src/containers/trade/trading-terminal/widgets/super-chart/overlays/overlay-context-menu.js`
- `src/components/design-system/v2/popups` (index / separator component)

Read `OverlayContextMenu` and note the exact element used for separators (if
any). The new `ChartContextMenu` must use the same element for visual
consistency.

**Verification:** One-line note of the separator element (e.g. `PopupSeparator`,
`<hr>`, etc.) captured before Task 7.

## Controller additions

### Task 1: Extend `_onChartRightSelect` to capture `time`, `price`, `timezone`
**File:** `src/containers/trade/trading-terminal/widgets/super-chart/controllers/context-menu-controller.js`

- Update `_onChartRightSelect`:
  - After computing `x`/`y`, pull `result.point?.time` and `result.point?.price`
    (defensive — if SC ever fails to resolve `point`, skip opening).
  - Fetch `timezone` via `this.c._superchart?.getTimezone?.() || "Etc/UTC"`.
  - Normalize `"exchange"` → `"UTC"`.
  - Call `openChartContextMenu({x, y, time, price, timezone})`.

Do NOT compute `offsetTime` here — it is computed inside
`getChartContextMenuItems`.

**Verification:** Right-click delivers a menu state with the four new fields;
`x`/`y` still point-accurate; `timezone` defaults to `Etc/UTC` in the current
datafeed config (`coinray-datafeed.js:42`).

### Task 2: Add `setChartContextMenuItemsProvider` + provider field
**File:** `controllers/context-menu-controller.js`

- Add constructor init: `this._chartContextMenuItemsProvider = null`.
- Add method `setChartContextMenuItemsProvider(fn)` — takes a function or
  `null`.
- No other wiring — the provider is consumed in Task 3.

**Verification:** The method exists; can be called with a function or `null`;
no behavior change yet.

### Task 3: Add `getChartContextMenuItems(menuState)` method
**File:** `controllers/context-menu-controller.js`

- Implement the full builder per `menu-options-design.md` "`getChartContextMenuItems`
  implementation sketch".
- Imports: `moment-timezone`, `BigNumber`, `lodash`, `i18n`, `conditionalCallback`,
  `createAlert`, `startOrder`, `OrderSide`, `setPositionStartTime`,
  `setPositionEndTime`, `INTERVAL_OPTIONS` (from
  `../replay/replay-controls`), `REPLAY_MODE`, `ReplayController`,
  `Selectors`.
- Visibility predicates live at the top of the method — single source of truth
  per flag, matching TV's hook exactly.
- External provider call comes first, items are prepended via spread.
- Separators: trading-group separator is guarded by `showTradingOptions`; the
  always-on separator before the Replay group is **unconditional** — matches
  TV. Do not try to collapse adjacent separators.
- `indexOf` clamps for speed-up / slow-down use an explicit `idx < 0` guard.
- Each built-in entry is gated with `showX &&` and the final `.filter(Boolean)`
  strips falsy entries.
- i18n keys use the existing
  `containers.trade.market.marketGrid.centerView.tradingViewjs.*` namespace
  except for `common.*` fallbacks — per the PRD, play/pause use the
  `tradingViewjs.play` / `.pause` keys, not `common.*`.

**Verification (unit-style, to be done manually or with a quick repl):**
Call the method with a constructed menu state and various controller states;
assert the returned descriptor list matches the expected entries for each of
these scenarios. The Review doc will carry the full verification matrix —
here just smoke-test happy-path Alerts+Trading, and happy-path Replay-active.

## `ReplayController` additions

### Task 4: Add `handleSelectReplayStartTime(time)` public method
**File:** `controllers/replay-controller.js`

- Add as a new public handler next to `handleSelectReplayStartTimeClick`:
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
- No other changes to existing replay methods.

**Verification:** Typing into the menu-options `onClick: () => replay.handleSelectReplayStartTime(offsetTime * 1000)`
resolves. The method does not shadow `handleSelectReplayStartTimeClick`.

### Task 5: Add `handleGoBackInTime(time, opts)` public method
**File:** `controllers/replay-controller.js`

- Add the full method from `menu-options-design.md` "`handleGoBackInTime`".
- Use existing i18n-style toasts. If `cantJumpFuture` / `cantGoEarlierThanStart`
  keys do not yet exist in the YAML, add them in Task 8.
- Branch bodies:
  - `keepSession: true` path uses `this.resetTo(time)` then
    `this.setStartTime(this.startTime, {jumpTime: time, keepSession: true})`.
  - Non-`keepSession` path: `handleStop(cb)` → `_startReplay(startTime, {autoPlay, quickStart: true})`.
- If Task 0b flagged that `resetTo` or `setStartTime(..., {jumpTime, keepSession})`
  are missing, add them alongside this task — based on TV's equivalents in
  `release-5.2.x` replay-controller — before adding `handleGoBackInTime`.

**Verification:** The method exists and can be called from the menu entry. A
manual jump-back in a live replay session rewinds the engine visually without
tearing down the session. Check three boundary cases:
1. Click a point in the future → toast warning, no state change.
2. Click a point earlier than `startTime` → toast warning, no state change.
3. Click a point inside the valid range → replay visibly rewinds; trades on
   the rewound bars are restored / re-hidden.

### Task 6: Verify/add `ReplayController.minIntervalMs` / `maxIntervalMs`
**File:** `controllers/replay-controller.js`

- Grep for `minIntervalMs` / `maxIntervalMs`.
- If missing, add as `static minIntervalMs = 10` and `static maxIntervalMs = 10000`
  (values from TV — confirm these match `INTERVAL_OPTIONS[0]` and
  `INTERVAL_OPTIONS[INTERVAL_OPTIONS.length - 1]` in
  `super-chart/replay/replay-controls.js`).
- If already present, verify the values haven't drifted.

**Verification:** `ReplayController.minIntervalMs === INTERVAL_OPTIONS[0]` and
`ReplayController.maxIntervalMs === INTERVAL_OPTIONS[INTERVAL_OPTIONS.length - 1]`.

## Component changes

### Task 7: Render descriptors in `ChartContextMenu`
**File:** `src/containers/trade/trading-terminal/widgets/super-chart/chart-context-menu.js`

- Replace the empty `<Popup/>` body with a `useMemo` mapping of descriptors:
  ```js
  const items = useMemo(
    () => (menuState ? chartController?.contextMenu.getChartContextMenuItems(menuState) || [] : []),
    [menuState, chartController],
  )
  ```
- Map descriptors:
  - `type: "separator"` → the separator element confirmed in Task 0c.
  - `type: "item"` → `<PopupItem key={item.key} onClick={() => { close(); item.onClick() }}>{item.text}</PopupItem>`.
- Import `PopupItem` (already from `~/components/design-system/v2/popups`).
- Keep the existing `useEffect` subscribe/unsub and `close` callback untouched.
- Remove the "Intentionally empty — follow-up PRDs add PopupItems here"
  comment.

**Verification:** Empty list (e.g. grid-bot chart with no external provider)
renders a popup frame with nothing inside — still dismissible. Main chart
with Trading+Alerts visible renders all Group A + Group B entries with a
visible separator between the entries and the Replay group.

## i18n

### Task 8: i18n keys
**File:** `src/locales/en/translation.yaml` (+ nl/es if used for the existing
TV keys — check by grepping `createBuyOrder` across all three files; match
whichever convention is in place)

- **Add** under the existing replay toast namespace (path: match whatever
  TV currently uses for replay toasts — likely
  `containers.trade.market.marketGrid.centerView.tradingView.replay.*`):
  - `cantJumpFuture: Can't jump to the future`
  - `cantGoEarlierThanStart: Can't go back earlier than start-time`
- **Remove** the dead `createNewRecurringAlert` key under `tradingViewjs.*`
  (grep first to confirm no code references it anywhere; TV already had it
  orphaned).
- **Do not** add any new entry labels — all entry labels reuse existing
  `tradingViewjs.*` keys that TV left behind.

**Verification:** `grep -r createNewRecurringAlert src/ locales/` returns no
matches. `i18n.t("containers.trade...replay.cantJumpFuture")` resolves (dev
console test).

## Cross-reference doc updates

### Task 9: Flip deferred markers in phase-5 docs
**Files:**
- `ai/superchart-integration/phase-5/deferred.md`
- `ai/superchart-integration/phase-5/replay/prd.md`
- `ai/superchart-integration/phase-5/dialogs/prd.md`
- `ai/superchart-integration/phase-5/stepback/prd.md`
- `ai/superchart-integration/phase-5/stepback/tasks.md`

For each file, flip the "deferred — waiting on chart context menu" entries to
"delivered in `[sc-chart-ctx-menu-options]`" as described in the PRD
"Unblocks / references to update" section. Keep wording minimal — just the
resolution; don't rewrite surrounding content.

**Verification:** `grep -n "chart context menu" ai/superchart-integration/phase-5/` shows
no remaining "deferred" or "blocked on" phrases for this concern.

## Smoke testing the extension point

### Task 10: Manual smoke test of provider mechanism
(No code change — for the Review doc.)

Open dev console on the TT main chart, run:
```js
const cc = __SC_DEV_HANDLE__.chartController
cc.contextMenu.setChartContextMenuItemsProvider(({time, timezone, price}) => [
  {key: "dev-smoke", type: "item", text: `t=${time} p=${price}`, onClick: () => console.log("clicked", {time, price, timezone})},
])
```
Right-click — the smoke entry must appear at the top of the menu, above
Create New Alert. Click it and confirm the console logs the captured values.
Finally clear the provider with `cc.contextMenu.setChartContextMenuItemsProvider(null)`.

(If a `__SC_DEV_HANDLE__` shortcut does not exist, use whatever dev-mode handle
is available for grabbing the active controller — the review step can adjust.)

**Verification:** Entry appears, fires, clears. No leaks after clearing.

## Review coverage

After all tasks, `review.md` must include a matrix crossing each of the 13
built-in entries with at least these states:

- Normal main-chart, no replay, not in trade: expect Alerts+Trading visible,
  no Replay entries.
- Main-chart, DEFAULT replay active, not playing: expect no Alerts/Trading,
  Replay entries include Jump-Back, Play, Stop, Speed-Up, Slow-Down. Stop
  entry is visible (paused).
- Main-chart, DEFAULT replay, playing: same as above but no Stop entry,
  Play label reads Pause.
- Main-chart, SMART replay active: Alerts AND Trading should both still
  appear alongside the replay entries (only `isDefaultReplayMode` hides them).
- Main-chart, SMART replay finished (`backtestFinished=true`): Alerts and
  Trading hidden, Jump-Back hidden, other Replay entries still visible.
- Grid-bot chart: Alerts hidden, Trading hidden, Replay hidden. Only external
  provider entries appear (or empty popup if no provider).
- Replay speed at minimum: Speed-Up hidden.
- Replay speed at maximum: Slow-Down hidden.
- Not in trade (`inTrade = false`): Start replay entry fires without the
  `CenterView` widget gate.

Include the standard Trading Terminal context test cases from `ai/workflow.md`:
change TradingTab, change coinraySymbol, change resolution, change
exchangeApiKeyId — each while the popup is open AND between right-clicks.
