# Design: Screenshots — SuperChart Migration

## Overview

Replace the TV-based screenshot system with SC's `getScreenshotUrl()`. TV returned a hosted URL via an async event; SC returns a base64 data URL synchronously. Two consumers have different needs:

- **Notes**: store the data URL directly — the backend stores `screenshot_url` as a plain string with no validation (confirmed in `$CRYPTO_BASE_SCANNER_DIR`), so data URLs work as-is.
- **Share modal**: needs a hosted URL for social sharing — upload the image to `POST /api/v2/tradingview_charts/snapshot` which returns an Altrady URL.

## Key difference: hosted URL vs data URL

- **TV**: `tvWidget.takeScreenshot()` → uploads to TV servers → fires `onScreenshotReady` with a hosted URL (e.g., `https://www.tradingview.com/x/ABC123/`)
- **SC**: `superchart.getScreenshotUrl('png', backgroundColor)` → returns a base64 data URL synchronously (e.g., `data:image/png;base64,...`)

## Architecture

### `takeScreenshot` function replacement

The current `takeScreenshot(callback)` in `screenshot.js` uses a module-level `tvWidget` variable set by the `Screenshot` component. Replace with a function that:

1. Gets the SC instance from `ChartController`
2. Calls `getScreenshotUrl('png', backgroundColor)` where `backgroundColor` comes from the chart theme
3. Returns the data URL synchronously (no callback pattern needed, but keep callback signature for minimal consumer changes)

Access to ChartController: the `takeScreenshot` function is called from `notes-form.js` which is outside the `SuperChartContextProvider`. Currently it works via a module-level `tvWidget` variable set by the `Screenshot` component. The same pattern works for SC — a module-level reference to the current `ChartController`, set when the SC widget mounts and cleared on unmount.

### Notes integration

`notes-form.js` calls `takeScreenshot((url) => editNote({...note, screenshotUrl: url + ".png"}))`. With SC:

- The callback receives the data URL directly
- Drop the `.png` suffix append — data URLs are self-describing
- The `screenshotUrl` field stores the data URL string
- Display in `<img src={screenshotUrl}>` works identically

### Share modal — preserved via snapshot upload

The share modal is kept. The flow changes from TV-hosted to Altrady-hosted:

**Current (TV):**
1. TV's native screenshot button fires `onScreenshotReady` with a TV-hosted URL
2. The `Screenshot` component shows the share modal with that URL

**New (SC):**
1. User triggers screenshot (via a button in the SC header or equivalent)
2. Call `getScreenshotUrl('png')` to get a data URL
3. Convert data URL to a Blob/File
4. POST to `/api/v2/tradingview_charts/snapshot` with `preparedImage` (file) and `symbol` (coinray symbol)
5. Backend creates a `SavedImage`, attaches via ActiveStorage, runs `SavedImageJob`, returns `https://app.altrady.com/x/:externalId`
6. Show the share modal with the returned URL

The snapshot endpoint is chart-engine-agnostic — it accepts any PNG file. No backend changes needed.

**Auth:** The endpoint uses `user_id` query param (account `external_id`). Currently configured as `snapshot_url` in TV widget constructor options: `API_HOST + '/api/v2/tradingview_charts/snapshot?user_id=' + accountId`. TV handled the POST internally. With SC, the frontend must make the POST itself, including `user_id` as a query param. The `accountId` (external_id) is available from Redux state (`state.app.account.externalId` or similar).

**Data URL to Blob conversion:**
```js
const dataUrlToBlob = (dataUrl) => {
  const [header, base64] = dataUrl.split(",")
  const mime = header.match(/:(.*?);/)[1]
  const binary = atob(base64)
  const array = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) array[i] = binary.charCodeAt(i)
  return new Blob([array], {type: mime})
}
```

### No-chart guard

`notes-form.js:56` uses `{widgets: {widget: "CenterView"}}` in `conditionalCallback`. The SC chart widget needs to be recognized by whatever name it registers as in the widget system. If SC replaces TV as the chart in the center view, the widget name may stay `CenterView` or change — the guard must match the SC widget's registered name.

The `takeScreenshot` function also guards internally: if no SC instance is available (module-level ref is null), call `callback(false)`.

### Screenshot trigger

TV had a native screenshot button in its toolbar that fired the `onScreenshotReady` event. SC has no built-in screenshot button. The trigger needs to come from the Altrady UI — either a button in the SC header bar, or an action menu item. This replaces the TV-native button.

When triggered:
1. Call `getScreenshotUrl()` → data URL
2. Convert to blob, upload to snapshot endpoint
3. Show share modal with returned URL

This is separate from the notes `takeScreenshot` flow (which is silent, no modal).

## Files

### Modified

- **`src/containers/trade/trading-terminal/widgets/center-view/tradingview/screenshot.js`**
  - Keep both `takeScreenshot` function and `Screenshot` component (share modal)
  - Replace module-level `tvWidget` with module-level `chartController` ref
  - `takeScreenshot(callback)`: get data URL from `chartController._superchart.getScreenshotUrl()`, pass to callback. If no chartController, call `callback(false)`.
  - Export `registerChartController(controller)` / `unregisterChartController()` for SC widget mount/unmount
  - Remove `silenceScreenShot` flag and `onScreenshotReady` subscription
  - Add `takeAndUploadScreenshot()` function: gets data URL, converts to blob, uploads to snapshot endpoint, returns hosted URL. Used by the share modal trigger.
  - `Screenshot` component: no longer subscribes to TV events. Instead, expose a way for the SC header to trigger `takeAndUploadScreenshot` and show the modal with the result.

- **`src/containers/trade/trading-terminal/widgets/notes-form.js`**
  - Update import path if `takeScreenshot` moves
  - Remove `.png` suffix append: `screenshotUrl: url` instead of `screenshotUrl: url + ".png"`
  - Update `conditionalCallback` widget check if SC widget name differs from `CenterView`

- **`src/containers/trade/trading-terminal/widgets/center-view/tradingview/tradingview-component.js`**
  - Remove `<Screenshot/>` rendering (moved to SC widget or shared parent)
