# Phase 10 — Review

## Status: partially decommissioned

Phase 10's original goal was TV/SC coexistence in the Trading Terminal —
ship a toggleable `CandleChart` widget so users could switch between
implementations while SC was validated. That coexistence layer was
dismantled in Phase 5 when the Trading Terminal switched to SC-only. The
layout migration and the `CandleChart` wrapper itself survive because
they're still used by the Charts page, but the toggle surface and its
supporting state were removed.

See "Undone / Decommissioned" below for the full list.

## Verification

1. ✅ Web build compiles successfully
2. ✅ Toggle switch appears on CandleChart widget (top-right, overlaying chart)
3. ✅ Toggle defaults to SC (on)
4. ✅ Toggling off switches to TV with full unmount/remount
5. ✅ Toggle disabled during replay mode (with native title tooltip)
6. ✅ Dev widget (SuperChart) shows placeholder when CandleChart is set to SC
7. ✅ Dev widget shows SC normally when CandleChart is set to TV
8. ✅ Dev widget shows SC when CandleChart is removed from layout
9. ✅ Existing desktop TT layouts with CenterView are migrated to CandleChart on load
10. ✅ Existing Charts page layouts with CenterView are migrated to CandleChart on load
11. ✅ Default trading layouts use CandleChart
12. ✅ Default chart layouts use CandleChart
13. ✅ Mobile widgetTabs migrate CenterView → CandleChart on rehydrate
14. ✅ Mobile removes SuperChart from widgetTabs on rehydrate
15. ✅ Symbol change on mobile auto-switches to CandleChart tab
16. ✅ Notes screenshot works when SC is active (CandleChart=SC or dev widget=SC)
17. ✅ Notes screenshot: CandleChart=TV, no dev widget → yellow warning "Toggle to SuperChart" with toggle highlight
18. ✅ Notes screenshot: no CandleChart in layout → yellow warning "Activate Chart widget" with widget dropdown highlight
19. ✅ TV share modal still works via TV's built-in screenshot button
20. ✅ Chart settings modal opens from CandleChart widget header (both TV and SC)
21. ✅ Replay backtests widget checks for CandleChart widget presence
22. ✅ Price select on mobile forms activates CandleChart tab
23. ✅ Charts page renders TV via CandleChart (no toggle visible)
24. ✅ Charts page multi-chart layouts work correctly
25. ✅ Adding a new chart tab on Charts page creates CandleChart node
26. ✅ Grid bot pages unaffected (SC-only, no CandleChart)
27. ✅ CenterView only remains in migration/legacy code
28. ✅ Migration saves to backend immediately (not in-memory only)

## Version rollback

Migration is one-way (CenterView → CandleChart in layout JSON). If a user
downgrades to a version before this change:

- **TT:** Custom layouts show "Unknown component CandleChart". User can recover
  by switching to a default layout (Simple/Advanced), which is defined in code
  and still has CenterView on the old version.
- **Charts page:** Same — custom layouts show unknown component. Switching to a
  default chart layout recovers.
- **Mobile:** `CandleChart` tab id is not in old WIDGET_SETTINGS, so the tab
  gets filtered out (disappears). Not a crash. User can re-add via widget tabs
  modal, or it resets on next MOBILE_LAYOUT_VERSION bump.

Acceptable: users who downgrade see broken custom layouts but can recover via
default layouts. No data loss, no crashes.

### Testing plan

Test thoroughly before release:

1. ✅ On old version, create custom layouts for TT, Charts page, and mobile with
   various widget configurations (single chart, multi-widget, custom ordering)
2. ✅ Upgrade to new version — verify migration runs without errors:
   - TT custom layouts load correctly, CenterView becomes CandleChart with toggle
   - Charts page custom layouts load correctly, CenterView becomes CandleChart (TV)
   - Mobile tabs migrate (CenterView → CandleChart, SuperChart removed), ordering preserved
3. ✅ Verify migrated layouts work correctly (toggle, screenshots, settings, replay)
4. ✅ Downgrade back to old version — verify:
   - TT: custom layouts show "Unknown component", default layouts still work
   - Charts page: renders normally (ChartsGridItem ignores component name)
   - Mobile: CandleChart tab disappears, remaining tabs work, custom tab
     ordering preserved for non-migrated tabs, no crash when switching tabs
5. ✅ Upgrade again — verify no double-migration issues (idempotent)

## Undone / Decommissioned

The pieces below were introduced by Phase 10 and removed in Phase 5
(`sc-smart-replay` commit). They are no longer part of the codebase; this
section exists so future readers understand why related references in
older docs or commit messages may not match current code.

### Removed in Phase 5

- **CandleChart toggle UI** — header-mounted button that swapped between
  SC and TV in the Trading Terminal. The `toggleable=true` branch in
  `widgets/candle-chart.js` now unconditionally renders
  `SuperChartWidgetWithProvider`; the TV branch is only reachable with
  `toggleable=false` (Charts page). Keys, labels, and header buttons for
  the toggle are gone.
- **`chartSettings.useSuperChart` Redux state** — boolean stored per
  device that controlled the toggle. Action type `SET_USE_SUPER_CHART`,
  the reducer slice, and the application-settings persistence entry were
  all removed.
- **`DevWidgetGuard` and standalone `SuperChart` dev widget** — the dev
  widget that let users place a bare SC instance alongside `CandleChart`.
  The single-instance guard existed to prevent two SC instances from
  coexisting in the Trading Terminal. Both the guard and the dev widget
  were deleted; legacy layouts that still reference `SuperChart` resolve
  to `UnknownWidget`.
- **TV path inside the Trading Terminal's `CandleChart`** — the TV render
  branch was removed from the TT code path. TV rendering still exists in
  the file but is only exercised when `toggleable=false` (Charts page).
- **TV share modal in the Trading Terminal** — the `Screenshot` component
  inside `TradingViewComponent` was never un-mounted in Phase 5, but it's
  no longer reachable from TT (TT never renders TV). It remains for the
  Charts page and other TV consumers.
- **TV hotkeys in the Trading Terminal** — `TradingviewHotkeys` was
  deleted entirely in Phase 4 (`sc-hotkeys`). Replaced by SC's
  `TradingHotkeys` mapper. All shift+b/s/a/p bindings now go through
  mousetrap; no `tvWidget.onShortcut` calls remain anywhere in the app.

### Still in effect from Phase 10

- **Layout migration** (`10c`) — the one-way rename of `CenterView` →
  `CandleChart` in TT, Charts, mobile, and default layouts. Still runs
  on app load and stays idempotent. `CenterView` remains removed from
  the widget palette.
- **`CandleChart` wrapper component** — lives in
  `widgets/candle-chart.js`, branches on `toggleable`. Used by the
  Trading Terminal (SC) and the Charts page (TV). Will lose the
  `toggleable` prop when the Charts page migrates to SC.
- **Screenshot behavior** — notes screenshots are SC-only via
  `ChartRegistry.getActive()`. Still correct; simplified because TT
  always has a CandleChart → always has an active SC.

### Why the undoing was necessary

The coexistence layer was a safety harness during SC rollout. Once smart
replay landed and SC reached feature parity with TV in the TT, keeping
the toggle became a cost: two render paths to maintain, two hotkey
systems, two screenshot paths, and duplicate logic in `useSuperChart`
gating. Phase 5's `sc-smart-replay` commit rolled that cost back by
hard-wiring TT to SC. TV remains available only where it's still
needed — and will be fully removed before release.
