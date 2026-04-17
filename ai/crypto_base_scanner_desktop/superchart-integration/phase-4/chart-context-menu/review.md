# Chart Background Context Menu — Review

## Round 1: Initial implementation (2026-04-15)

### Summary

Landed `[sc-chart-ctx-menu]`: plumbing for the chart-background context menu. The
popup opens on right-click on empty chart area and renders with an **empty body** —
follow-up PRDs will add `PopupItem`s for "Start replay here", "Jump back to here", etc.

Implementation follows `design.md`:
- `ContextMenuController` gains chart-background state + `mount`/`dispose` +
  `_onChartRightSelect` handler, subscribed directly to `sc.onRightSelect` (not via
  `InteractionController`).
- Gate on `chartController.interaction.active` so one-shot consumers (replay picker,
  future drawing tools) keep their right-click semantics.
- Canvas → page coord bridging inline with a TODO comment pointing at
  `InteractionController._enrichResult` as the companion site to remove once SC adds
  native `pageX`/`pageY` to `PriceTimeResult`.
- New `chart-context-menu.js` React component mirrors `overlay-context-menu.js` shape
  and mounts inside `SuperChartOverlays` next to `<OverlayContextMenu/>`.
- Five phase-5 md files updated so the blocker is marked resolved; menu entries
  themselves remain pending follow-ups.

### Files changed

- `src/containers/trade/trading-terminal/widgets/super-chart/controllers/context-menu-controller.js`
- `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`
- `src/containers/trade/trading-terminal/widgets/super-chart/chart-context-menu.js` (new)
- `src/containers/trade/trading-terminal/widgets/super-chart/super-chart.js`
- `ai/superchart-integration/phase-5/deferred.md`
- `ai/superchart-integration/phase-5/stepback/prd.md`
- `ai/superchart-integration/phase-5/stepback/tasks.md`
- `ai/superchart-integration/phase-5/dialogs/prd.md`
- `ai/superchart-integration/phase-5/replay/prd.md`

### Verification

1. Right-click on an empty area of the TT main chart opens an empty
   `ContextMenuPopup` at the click location.
2. The popup is visibly framed even though it has no items inside.
3. Mousedown outside the popup dismisses it.
4. Scrolling the chart dismisses it.
5. Pressing Escape dismisses it.
6. Right-clicking on an **overlay** (alert, base, bid/ask, position line, etc.) still
   opens the **overlay** context menu (phase 4a-2 behavior unchanged).
7. While a replay start-time picker is active
   (`ReplayController.handleSelectReplayStartTimeClick`), right-click cancels the
   picker and does **NOT** open the chart-background menu (gated on
   `interaction.active`).
8. Right-clicking again after dismissing reopens the menu at the new position.
9. Switching TradingTab while the menu is open: the popup closes cleanly (no lingering
   popup on the new tab).
10. Changing `coinraySymbol` within the same tab while the menu is open:
    `syncSymbolToChart` calls `closeChartContextMenu()` and the popup disappears.
11. Changing `resolution` within the same tab: popup behavior unaffected (popup only
    needs to track screen position, not chart data).
12. Changing `exchangeApiKeyId`: popup unaffected (account change does not rebuild
    the chart).
13. Closing the tab / unmounting the chart: `ContextMenuController.dispose` unsubs
    `onRightSelect`; `useEffect` cleanup clears the React callback. No console errors.
14. No regression in overlay context menu: edit/save/delete/settings/color/info on all
    supported overlay groups still work.
15. `grep -rn "blocked on chart context menu\|no chart context menu yet\|deferred until chart context menu" ai/` returns only the chart-context-menu PRD/tasks docs (historical references), no stale blocker markers in phase-5 files.
