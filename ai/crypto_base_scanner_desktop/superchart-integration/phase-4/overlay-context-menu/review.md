# Overlay Context Menu — Review

## Round 1: Initial implementation (2026-04-02)

### Bug 1: Popup closed immediately after opening
**Root cause:** Right-click `mouseup` triggered `onClick` on the backdrop, closing the popup instantly.
**Fix:** Changed backdrop from `onClick` to `onMouseDown`. Added `onMouseDown stopPropagation` on the popup container so clicks on menu items don't bubble to the backdrop.

### Bug 2: Popup positioned at wrong location
**Root cause:** klinecharts `event.x`/`event.y` are canvas-relative coordinates, not page coordinates.
**Fix:** Use `event.pageX`/`event.pageY` instead, which are page-absolute.

### Bug 3: Browser contextmenu event closes popup
**Root cause:** Native `contextmenu` DOM event bubbled to the portal backdrop's `onContextMenu` handler which called `close()`.
**Fix:** Changed `onContextMenu` to only `preventDefault()` without closing.

### Bug 4: priceLevelLine/box overlays don't receive right-click
**Root cause:** These SC overlay templates hardcode `ignoreEvent: true` on all figures, blocking all mouse events.
**Fix:** Made `ignoreEvent` configurable via `extendData` property in coinray-chart's `priceLevelLine.ts` and `box.ts` (default still `true`). Desktop app passes `ignoreEvent: false` in `_createPriceLevelLine` and `_createBaseSegment`.

### Bug 5: Base segments don't receive right-click
**Root cause:** `styledSegment` defaults `ignoreEvent: true`. Bases didn't override it (trendline alerts did).
**Fix:** Pass `ignoreEvent: false` in `_createBaseSegment` extendData.

### Verification

**Context menu items per overlay type (order: Edit/Save/Delete, separator, Settings/Color, separator, Info):**
1. ✅ **Right-click time alert** — "Edit alert", Delete, separator, Settings, Color, separator, Info
2. ✅ **Right-click trendline alert** — same as time alert
3. ✅ **Right-click triggered price alert** — Settings, Color, separator, Info (no Edit/Save/Delete)
4. ✅ **Right-click triggered time alert** — same as triggered price alert
5. ✅ **Right-click triggered trendline alert** — same as triggered price alert
6. ✅ **Right-click bid/ask line** — Settings, Color, separator, Info (no Edit/Save/Delete)
7. ✅ **Right-click break-even line** — Settings, Color, separator, Info (no Edit/Save/Delete)
8. ✅ **Right-click base segment** — Settings, Color, separator, Info (no Edit/Save/Delete)
9. ✅ **Right-click submitted entry condition** — "Edit position", separator, Settings, Color, separator, Info (no Save/Delete)
10. ✅ **Right-click submitted entry expiration** — same as entry condition
11. ✅ **Right-click trigger price line** — Settings, Color, separator, Info (no Edit/Save/Delete)
12. ✅ **Right-click editing time alert** — Save, Cancel edit, separator, Settings, Color, separator, Info (no Edit)
13. ✅ **Right-click editing trendline alert** — same as editing time alert
14. ✅ **Right-click editing condition time line** — same as editing time alert
15. ✅ **Right-click editing expiration time line** — same as editing time alert

**Actions:**
16. ✅ **Edit action on time alert** — alert enters edit mode in alert form
17. ✅ **Edit action on trendline alert** — alert enters edit mode
18. ✅ **Delete action on time alert** — alert is deleted
19. ✅ **Delete action on trendline alert** — alert is deleted
20. ✅ **Save action on editing alert** — alert is saved (same as submit button)
21. ✅ **Cancel edit on editing alert** — edit mode exits
22. ✅ **Save action on editing condition** — position is saved
23. ✅ **Cancel edit on editing condition** — trade form edit cancelled
24. ✅ **Edit action on entry condition** — position enters edit mode in trade form

**Edit label:**
25. ✅ **Edit on time/trendline alert** — button text is "Edit alert"
26. ✅ **Edit on entry condition/expiration** — button text is "Edit position"

**Settings integration:**
27. ✅ **Settings option** — opens settings modal on General Settings tab, relevant section highlighted
28. ✅ **Color option** — opens settings modal on Colors tab, specific color row highlighted (if mappable), otherwise section highlighted
29. ✅ **Settings highlight: time alert** — Alerts section highlighted
30. ✅ **Settings highlight: bid/ask** — Miscellaneous section highlighted
31. ✅ **Settings highlight: bases** — Bases section highlighted
32. ✅ **Color highlight: time alert** — "Alert" color row highlighted
33. ✅ **Color highlight: triggered alert** — "Closed Alert" color row highlighted
34. ✅ **Color highlight: break-even** — "Break Even" color row highlighted
35. ✅ **Color highlight: bases** — Bases color section highlighted (no single color key)

**Settings respect:**
36. ✅ **alertsEnableEditing=false** — Edit option hidden on time/trendline alerts, drag disabled, overlay locked
37. ✅ **alertsEnableCanceling=false** — Delete option hidden on time/trendline alerts
38. ✅ **openOrdersEnableEditing=false** — Edit option hidden on entry conditions/expirations

**Info modal:**
39. ✅ **Info on time alert** — shows Type ("Time Alert"), Alert ID, Time value, divider, Overlay name, Overlay ID
40. ✅ **Info on trendline alert** — shows Type ("Trendline Alert"), Alert ID, both points (price @ time)
41. ✅ **Info on triggered price alert** — shows Type ("Triggered Price Alert"), Alert ID, Price value
42. ✅ **Info on editing alert** — shows Type ("Time Alert (editing)"), Alert ID (from form state)
43. ✅ **Info on entry condition** — shows Type ("Entry Condition"), Position ID, Price or Time value
44. ✅ **Info on bid/ask** — shows Type ("Bid/Ask"), Price value
45. ✅ **Info on base** — shows Type ("Base"), Price value
46. ✅ **Info modal divider** — horizontal line before Overlay/Overlay ID fields
47. ✅ **Info modal closes** — click background to close

**Refactoring:**
48. ✅ **ContextMenuPopup** — shared component used by both ContextMenu (DOM events) and OverlayContextMenu (programmatic), verify existing context menus (market tab right-click) still work
49. ✅ **_createOverlay wrapper** — all createOverlay calls go through `_createOverlay`, verify all overlay types still render correctly
50. ✅ **ChartSettingsSection** — extracted component in general-settings, verify settings modal renders identically to before
51. ✅ **i18n shorthand** — general-settings and color-settings use `t()` shorthand, verify all labels render correctly

**i18n:**
52. ✅ **English** — all menu items display correct English text
53. ✅ **Spanish** — switch language to ES, all menu items display Spanish text
54. ✅ **Dutch** — switch language to NL, all menu items display Dutch text

**General:**
55. ✅ **Popup positioning** — right-click near edges of screen, popup stays within viewport
56. ✅ **Popup dismissal** — click outside (mousedown), scroll, or right-click elsewhere — popup closes
57. ✅ **No context menu on createOrderLine overlays** — right-click price alert (order line), no popup
58. ✅ **No context menu on createTradeLine overlays** — right-click trade arrow, no popup
59. ✅ **Browser context menu suppressed** — right-clicking an overlay does not show browser context menu
60. ✅ **Tab switch** — switch market tabs, right-click overlay on new market, correct behavior
61. ✅ **Base box** — no context menu (ignoreEvent not overridden for box)
62. ✅ **Menu closes after action** — clicking any menu item closes the popup before executing the action
63. ✅ **Settings highlight: entry condition** — Open Orders section highlighted
64. ✅ **Color highlight: entry condition** — Orders and Alerts color section highlighted
65. ✅ **Info on editing trendline alert** — shows Type ("Trendline Alert (editing)"), Alert ID, both points
66. ✅ **alertsEnableEditing=false + right-click time alert** — context menu still opens but without Edit/Delete, overlay is not draggable
