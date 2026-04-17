# Review: Screenshots — SuperChart Migration

## Verification

### Share button & modal
1. ✅ "Share" button appears in SC toolbar (right-aligned, FA share icon with 4px right margin + "Share" text)
2. ✅ Share button tooltip shows translated "Share Chart" text
3. ✅ Clicking Share button captures chart, uploads to `/api/v2/tradingview_charts/snapshot`, shows share modal with hosted Altrady URL (`https://app.altrady.com/x/:externalId`)
4. ✅ Share modal "Copy link" button copies the hosted URL to clipboard
5. ✅ Share modal Facebook button opens Facebook sharer with the hosted URL
6. ✅ Share modal X button opens X/Twitter intent with the hosted URL
7. ✅ Share modal closes when clicking the overlay/X button
8. ✅ Clicking Share when no market is loaded does nothing (guarded by `if (symbol)`)
9. ✅ Share button works after symbol change (reads current `coinraySymbol` from controller, not stale closure)

### Notes screenshot
10. ✅ Notes "Add screenshot" button uploads to snapshot endpoint, fetches direct image URL from saved_images API, stores hosted image URL as `screenshotUrl`
11. ✅ Screenshot displays correctly in note form inline preview (edit screen)
12. ✅ Screenshot displays correctly in note modal preview (full-size)
13. ✅ Saving a note with screenshot persists correctly — no 500 error (hosted URL, not data URL)
14. ✅ Editing an existing note — saved screenshot still displays, can be deleted
15. ✅ Error toast shows when attempting screenshot with no SC chart mounted (conditionalCallback widget guard for `SuperChart`)
16. ✅ Screenshot image loads correctly when viewing the note after save + reload

### SC native screenshot
17. ✅ SC's built-in screenshot button (camera icon) still works independently — opens save-to-file modal. Known: uses hardcoded bg color, not custom.

### Edge cases
18. ✅ Share button works on first chart load (no prior interaction needed)
19. ✅ Screenshot uses correct background color from user's custom chart colors (not hardcoded)
20. ✅ Share button works after switching market tabs
21. ✅ Opening share modal while notes form is open does not conflict
22. ✅ Uploaded screenshot is viewable at the returned `/x/:externalId` URL in a browser
23. ✅ Share button text/tooltip updates on language change without losing icon
24. ✅ PnL handle body background matches chart background color (not grid color)

### Custom chart colors applied to SC
25. ✅ Background color (solid) — custom color applied on load and after changing in settings
26. ✅ Background gradient — start/end colors applied when backgroundType is "gradient"
27. ✅ Grid lines — horizontal and vertical grid color matches custom setting
28. ✅ Candle up color (body fill)
29. ✅ Candle down color (body fill)
30. ✅ Candle up border color
31. ✅ Candle down border color
32. ✅ Wick up color
33. ✅ Wick down color
34. ✅ Current price line color
35. ✅ Current price line y-axis label text color is black on light backgrounds, white on dark backgrounds (reactive to priceLine color changes)
36. ✅ X-axis text color (foreground)
37. ✅ Y-axis text color (foreground)
38. ✅ X-axis line color (scaleLine)
39. ✅ Y-axis line color (scaleLine)
40. ✅ Colors apply on first chart load (not just after settings change)
41. ✅ Colors update when user saves new colors in Chart Settings → Colors (not live preview — TV preview still uses TV, SC updates on save)
42. ✅ Colors reapply correctly after theme toggle (dark ↔ light)
43. ✅ Screenshot (both Share and Notes) captures the custom colors, not defaults

### ChartRegistry & overlays after refactor
44. ✅ All overlays still render correctly — bid/ask, break-even, orders, alerts, bases, PnL
45. ✅ Notes "Add screenshot" still works
46. ✅ Share button still works
47. ✅ Grid bot chart overlays still render correctly (grid bot prices, orders, trades, backtest times)

## Round 1: Bug fixes (2026-03-31)

### Bug 1: `state.app.account` → `state.account`
**Root cause:** Wrong Redux state path for account external ID.
**Fix:** Changed to `state.account.externalId` in `chart-controller.js`.

### Bug 2: Screenshot background color missing
**Root cause:** `getScreenshotUrl("png")` called without backgroundColor — defaults to white regardless of theme.
**Fix:** Background color now read from `chartController.colors.background` (user's custom chart colors).

### Bug 3: Language change overwrites icon with text
**Root cause:** `querySelector("span")` grabbed the icon span (first child) instead of the text span (second child). Setting `textContent` on it replaced the icon HTML.
**Fix:** Use `querySelectorAll("span")[1]` to target the text span.

### Bug 4: Custom chart colors not applied to SC
**Root cause:** `syncThemeToChart` only called `setTheme()` (dark/light preset) without applying user's custom color overrides. No effect watching `chartColors` changes.
**Fix:** Added `syncChartColors()` to `ChartController` — maps Altrady `chartColors` to klinecharts `chart.setStyles()` and SC background via inline styles on `.superchart-widget`. Called on init (after chart ready) and via `useEffect` watching `[chartColors, theme?._name]`.
**Files:** `chart-controller.js`, `super-chart.js`

### Bug 5: Grid line colors reset after theme toggle
**Root cause:** `setTheme()` resets klinecharts styles to defaults. `syncChartColors()` was called synchronously after, but klinecharts applies the reset on the next frame.
**Fix:** Removed `syncChartColors()` from `syncThemeToChart`. The React effect for `chartColors` now also depends on `theme?._name`, so it re-fires after theme change and reapplies custom colors.
**Files:** `chart-controller.js`, `super-chart.js`

### Bug 6: Notes screenshot 500 error — body too large
**Root cause:** Storing the raw base64 data URL as `screenshotUrl` exceeded backend's request body size limit.
**Fix:** Notes screenshots now upload to `/api/v2/tradingview_charts/snapshot` (like the share modal), then fetch the direct image URL via `GET /api/v3/saved_images/:externalId`. The hosted image URL is stored instead of the data URL.
**Files:** `actions/screenshots.js`, `chart-controller.js`, `screenshot.js`, `notes-form.js`

### Bug 7: Note edit screen shows broken image
**Root cause:** The snapshot endpoint returns a page URL (`/x/CODE`), not a direct image URL. `<img src>` can't render an HTML page.
**Fix:** After upload, fetch the `SavedImage` via V3 API to get `imageUrl`, append `?platform=original`, and store that as `screenshotUrl`.
**Files:** `actions/screenshots.js`, `chart-controller.js`

### Bug 8: PnL handle body color wrong
**Root cause:** `bodyBackgroundColor` used `this.colors.grid` which is a light color in dark theme.
**Fix:** Changed to `this.colors.background`.
**Files:** `chart-controller.js`

### Refactor: Screenshot architecture cleanup
**Motivation:** `chartController.dispatch` and `chartController.getState` were being used outside the controller in `screenshot.js`.
**Fix:** Moved upload/fetch logic to `actions/screenshots.js` as Redux thunks. Controller orchestrates via its own `dispatch`. `screenshot.js` is now thin — delegates to controller methods.
**New rule:** Added to `context.md` — do not use `chartController.dispatch` or `chartController.getState` outside the controller.
**Files:** `actions/screenshots.js` (new), `actions/api.js` (V2 helpers, skipAuth, handleResponse fix), `chart-controller.js`, `screenshot.js`, `context.md`

### Refactor: ChartRegistry
**Motivation:** Controller was accessed via three separate mechanisms: React context ref, module-level ref in screenshot.js, and `storeGlobal` for dev console. The screenshot.js ref duplicated the context ref solely for external access. Phase 9 will need multi-chart support with a proper registry.
**Fix:** Created `src/models/chart-registry.js` — singleton Map keyed by chart ID. Controllers register on mount, unregister on unmount. `getActive()` returns the most recently registered controller. `setActive(id)` prepared for click-to-focus (phase 9). Context provider now accepts `chartId` prop and reads controller from the registry instead of maintaining its own ref. Removed `_register` from context and all call sites.
**Files:** `models/chart-registry.js` (new), `context.js`, `super-chart.js`, `grid-bot-super-chart.js`, `screenshot.js`
