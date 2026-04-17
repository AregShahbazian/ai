# Tasks: Screenshots — SuperChart Migration

## Task 1: Rewrite `takeScreenshot` to use SC

**File:** `src/containers/trade/trading-terminal/widgets/center-view/tradingview/screenshot.js`

1. Replace module-level `tvWidget` with module-level `chartController`
2. Export `registerChartController(controller)` and `unregisterChartController()` functions
3. Rewrite `takeScreenshot(callback)`:
   - If `chartController` is null, call `callback(false)` and return
   - Call `chartController._superchart.getScreenshotUrl('png')` to get data URL
   - Call `callback(dataUrl)`
4. Remove `silenceScreenShot` flag and all `onScreenshotReady` subscription logic

**Verify:** `takeScreenshot` returns a data URL string when SC is mounted, `false` when not.

## Task 2: Add `takeAndUploadScreenshot` for share modal

**File:** `src/containers/trade/trading-terminal/widgets/center-view/tradingview/screenshot.js`

1. Add helper to convert data URL to Blob
2. Add `takeAndUploadScreenshot(coinraySymbol)` function:
   - Call `getScreenshotUrl('png')` to get data URL
   - Convert to Blob/File
   - POST to `/api/v2/tradingview_charts/snapshot?user_id={accountExternalId}` with `preparedImage` (file) and `symbol` (coinray symbol) as multipart form data
   - `accountExternalId` from Redux state (same value TV used via `accountId` prop in widget constructor)
   - Return the hosted Altrady URL from the response (plain text, not JSON)
3. Update `Screenshot` component to use `takeAndUploadScreenshot` instead of subscribing to TV events
   - Remove `tvWidget.subscribe("onScreenshotReady", ...)` logic
   - Expose a trigger mechanism (e.g., an imperative call or event) for the SC header to invoke

**Verify:** Uploading produces a valid `https://app.altrady.com/x/:externalId` URL. Share modal displays with correct URL.

## Task 3: Wire SC widget to register/unregister chart controller

**File:** SC widget component (e.g., `super-chart.js`)

1. On mount (after ChartController is created): call `registerChartController(controller)`
2. On unmount: call `unregisterChartController()`

**Verify:** Module-level ref is set when SC mounts, cleared when it unmounts.

## Task 4: Add screenshot trigger to SC header

SC has no built-in screenshot button (TV did). Add a screenshot button/action to the SC header bar that triggers `takeAndUploadScreenshot` and shows the share modal.

**Verify:** Button visible in SC header. Clicking it captures the chart, uploads, and shows the share modal with the Altrady URL.

## Task 5: Update notes-form screenshot integration

**File:** `src/containers/trade/trading-terminal/widgets/notes-form.js`

1. Remove `.png` suffix append: change `screenshotUrl: url + ".png"` to `screenshotUrl: url`
2. Update `conditionalCallback` widget check if SC widget name differs from `CenterView`
3. Update import path for `takeScreenshot` if file moves (Task 7)

**Verify:** "Add screenshot" button captures SC chart as data URL. Image displays correctly in the note form and modal preview. Error toast shows when no chart is mounted.

## Task 6: Remove `<Screenshot/>` from TV component

**File:** `src/containers/trade/trading-terminal/widgets/center-view/tradingview/tradingview-component.js`

1. Remove `<Screenshot/>` rendering and its import
2. Ensure `Screenshot` is rendered in the SC widget component or shared parent instead

**Verify:** No duplicate Screenshot components. SC screenshot works end-to-end.

## Task 7: Move screenshot.js out of tradingview directory

The file currently lives in `.../tradingview/screenshot.js` but is no longer TV-specific. Move to a more appropriate location (e.g., `.../super-chart/screenshot.js` or `.../center-view/screenshot.js`).

1. Move file
2. Update all import paths (`notes-form.js`, SC widget component)

**Verify:** All imports resolve. No broken references.
