# /charts SC implementation — code review

## What looks good

- The TT/CS/`/charts` chart variants share the same controller stack
  (`MarketTabSync`, `HeaderButtons`, `ContextMenu`, `Positions`,
  `TradeForm`, `Replay`) and only differ in flag set — same pattern
  across all three.
- `MarketTabSyncController` works for both `TradingTabsController` and
  `ChartTabsController` via the injected `tabsController`. Genuinely
  reusable.
- Replacing TV /charts' double `<ReplayHotkeys/>` per cell with a single
  page-level `<ChartsReplayHotkeys/>` keyed off
  `lastInteractedChartTabId` is a real improvement over what TV had.
- `lastInteractedChartTabId` lives in Redux so non-React code
  (`ChartTabsController.currentTab`, hotkeys, selectors) can read it
  without prop-drilling.

## Real issues

1. **`charts-page-chart.js` ↔ `trading-terminal-chart.js` duplicated
   boilerplate.** Both files have near-identical 80-line
   `useChartLifecycle({setup})` blocks, `setCurrentMarket` /
   sync-symbol / sync-resolution / mounted / resize / VR-persist
   effects, and overlay/controls subcomponents. The only material
   differences:
   - TT mounts `<TradingHotkeys/>`, `<ReplayHotkeys/>`, `EditOrders`,
     `ActionButtons`, `PickReplayStartButton`, fullscreen-on-landscape;
     passes `mainChart`.
   - /charts passes `forceDefaultMode: true`,
     `showTradingOptions: false`,
     `mainChart={false} showReplay showSettings`, `getChartSettings`
     override that locks order editing.

   This wants to be one parameterized component — say
   `<SuperChartWidget variant="tt|charts|cs"/>` (or a base component +
   thin wrappers). Right now any future change has to land in two
   places.

2. **Reaching into private fields from the React layer.**
   - `replay-hotkeys.js:32` reads `chartController?._currentMarket`.
     There's already a public `chartController.currentMarket` getter
     (`chart-controller.js:103`).
   - `replay-controls.js:238` reads `replayController?._forceDefaultMode`.
     Should be a public getter.

3. **Dead `useSelector` in `containers/market-tabs.js:42`.**
   `lastInteractedChartTabId` is selected but never read in the
   component. Subscribes to Redux for nothing — drop the line.

4. **Bump logic split across React and controller.**
   `market-tabs.js:50–56` dispatches `setLastInteractedChartTabId` in
   React, then calls `TabsController.handleTabClick`. But
   `ChartTabsController.switchChartWithCurrent` already dispatches the
   bump itself. Move the active-tab-click bump into
   `ChartTabsController.handleTabClick` — same place, symmetric, removes
   the `tabs` dep that caused the stale-closure bug.

5. **Three names for what is now one concept.** After dropping
   `ChartTab.selected`, "current chart" is referred to as
   `lastInteractedChartTabId` (Redux), `currentTab` (controller getter),
   and `selectedChartTab` (`charts-hotkeys.js` local). Worth renaming
   `selectedChartTab` → `currentChartTab` or similar so it's obviously
   the same thing.

6. **`ChartsHotkeys` `comboCallbackMap` has empty deps but reads
   `hotkeysMap`.** `charts-hotkeys.js:65` — keymap edits at runtime
   won't rebind. Pre-existing pattern, but it's wrong here too.

7. **Repeated `marketTab.market?.destroy(); delete marketTab.market`**
   four times in `chart-tabs-controller.js` (`removeMarketTab`,
   `removeOtherTabs`, `removeAllTabs`, `switchChartWithCurrent`). Push
   this into a `MarketTab.destroyMarket()` method.

8. **`MarketTabSyncController` takes the `tabsController` *class***
   (`ChartTabsController`) and calls `.get()` lazily inside
   `_onChartSymbolChange` etc. Passing the singleton instance directly
   (`tabsController: ChartTabsController.get()`) would be more
   conventional; the controller is initialized before the chart widget
   mounts. Either is OK, but mixing class-as-locator with instance
   fields is uncommon.

9. **`ChartTabsController.saveStateCallback` returns an empty async
   thunk** (lines 43–44). Looks like an unused parent-class hook —
   either delete the override or implement it.

10. **`HeaderButtons` flag triplet is awkward.**
    `<HeaderButtons mainChart={false} showReplay showSettings/>` reads
    as "not the main chart but with the main chart's replay/settings".
    Rename `mainChart` → `showTradingButtons` (it only gates Buy/Sell
    now), then the three flags are orthogonal.

11. **Stale comment in `market-tab-sync-controller.js:64`**
    ("context-menu close on tab change is handled at the React level…")
    predates the tabsController split. Verify still accurate.

## Verdict

Functionally solid. The two big-picture cleanups worth doing before this
leaves WIP are **(1) extracting the shared chart-widget body** from
TT/CS/charts and **(2) tightening encapsulation** (drop the
`_currentMarket` / `_forceDefaultMode` reaches, drop the dead
`useSelector`, move the bump into the controller). Everything else is
small.
