---
id: sc-screenshots
---

# PRD: Screenshots — SuperChart Migration

## Overview

Migrate the chart screenshot system from TradingView's async event-based API (`tvWidget.takeScreenshot()` + `onScreenshotReady` subscription) to SuperChart's synchronous `getScreenshotUrl()`. The screenshot feature is used in two places: programmatic capture for notes, and a share modal triggered by the chart's screenshot button. Both need to work with SC instead of TV.

## Background: Current System

### TV screenshot flow

`screenshot.js` manages all TV screenshot interactions:

1. **`takeScreenshot(callback)`** — exported function used by notes-form. Calls `tvWidget.takeScreenshot()`, subscribes to `onScreenshotReady`, and passes the resulting URL to the callback. A `silenceScreenShot` flag suppresses the share modal during programmatic use.
2. **`Screenshot` component** — mounted inside `tradingview-component.js`. Subscribes to `onScreenshotReady` on the `tvWidget` instance. When TV's built-in screenshot button is clicked (and not silenced), displays a share modal with copy URL, Facebook, and X/Twitter share buttons.
3. **TV returns a hosted URL** — `tvWidget.takeScreenshot()` uploads the image to TradingView's servers and returns a URL via the `onScreenshotReady` event.

### Snapshot upload endpoint

`POST /api/v2/tradingview_charts/snapshot` (`Api::V2::TradingviewChartsController#snapshot`):

- Accepts `preparedImage` (file upload) and `symbol` (coinray symbol)
- Creates a `SavedImage` record, attaches the image via ActiveStorage
- Kicks off `SavedImageJob` (thumbnail generation)
- Returns a hosted Altrady URL: `https://app.altrady.com/x/:externalId`

This is the endpoint TV's native screenshot button uses. The share modal displays the returned URL for copy/Facebook/X sharing. This endpoint is chart-engine-agnostic — it accepts any image file.

### Where screenshots are used

| Consumer | How it uses screenshots |
|---|---|
| **Notes widget** (`notes-form.js`) | "Add screenshot" button calls `takeScreenshot(callback)`, attaches the URL to the note as `screenshotUrl` |
| **Share modal** (`screenshot.js`) | Shows URL + copy/Facebook/X buttons when TV's screenshot button is clicked |
| **Screenshot viewer page** (`containers/screenshot.js`) | Public page at `/share/:externalId` — displays a saved screenshot fetched from API. Unaffected by this migration. |
| **Share position modal** (`share-position-modal.js`) | Does NOT use `takeScreenshot` — chart image is generated server-side. Unaffected. |
| **Social page** (`social.js`) | Public page for shared items. Backend-driven. Unaffected. |

### No-chart guard

When TV is not mounted in the trading terminal (e.g., CenterView widget removed), `takeScreenshot` calls `callback(false)` because `tvWidget` is undefined. The notes-form's `conditionalCallback` checks for `{widgets: {widget: "CenterView"}}` and shows an error toast if the widget is missing. This prevents attempting a screenshot when there's no chart.

## Requirements

### R1 — Replace TV screenshot API with SC

Replace `tvWidget.takeScreenshot()` + `onScreenshotReady` subscription with SC's `getScreenshotUrl(type?, backgroundColor?)`.

- SC's `getScreenshotUrl()` returns a data URL synchronously — no async event pattern needed
- The `silenceScreenShot` flag and `onScreenshotReady` subscription logic are removed entirely

### R2 — Programmatic screenshot for notes

The notes-form "Add screenshot" button must capture the current chart as an image:

- Call SC's `getScreenshotUrl()` on the active chart's SC instance
- Upload the image to `POST /api/v2/tradingview_charts/snapshot` (same as the share modal)
- Fetch the `SavedImage` via `GET /api/v3/saved_images/:externalId` to get the direct `imageUrl`
- Store the direct image URL (with `?platform=original`) as the note's `screenshotUrl`
- The direct image URL is renderable in `<img src>` — unlike the page URL or a base64 data URL (which exceeds backend body size limits)

### R3 — Share modal

The share modal (copy URL, Facebook, X buttons) is preserved. The flow with SC:

1. Capture the chart image via SC's `getScreenshotUrl()`
2. Convert the data URL to a file/blob
3. Upload to `POST /api/v2/tradingview_charts/snapshot` with the image and current symbol
4. Backend returns a hosted Altrady URL (`https://app.altrady.com/x/:externalId`)
5. Display the share modal with that URL for copy/Facebook/X sharing

This endpoint is already chart-engine-agnostic — it accepts any PNG image upload. No backend changes needed.

### R3.1 — Share button in SC toolbar

SC's built-in screenshot button stays as-is (save to file). A separate "Share" button is added to the SC toolbar via `superchart.createButton()`. Clicking it captures the chart, uploads to the snapshot endpoint, and opens the share modal. This is semantically distinct — "Screenshot" saves locally, "Share" publishes and shares.

### R4 — No-chart guard

When no SC instance is mounted, attempting to take a screenshot must show an error toast, same as the current TV behavior:

- The guard must check for SC presence, not TV
- The `conditionalCallback` widget check in notes-form references `SuperChart` (not `CenterView`)
- The toast message and UX remain the same

### R5 — Screenshot viewer and share pages unaffected

The public screenshot viewer (`containers/screenshot.js`), social page (`social.js`), and share position modal are backend-driven and require no changes.

### R6 — Custom chart colors applied to SC

SC must use the user's custom chart colors from Chart Settings → Colors. Colors are stored in `state.chartSettings.chartColors` and merged with theme defaults. The following must be applied via klinecharts `chart.setStyles()` and SC container inline styles:

- Background (solid and gradient)
- Grid lines (horizontal and vertical)
- Candle colors (up/down body, border, wick)
- Current price line color, with reactive text contrast (black on light, white on dark)
- Axis text and line colors (foreground, scaleLine)

Colors must apply on first chart load, update on save from settings, and reapply after theme toggle.

### R7 — ChartRegistry

A singleton `ChartRegistry` (`src/models/chart-registry.js`) provides global access to `ChartController` instances. Controllers register on mount and unregister on unmount. The context provider reads from the registry via a `chartId` prop. This replaces the previous pattern of separate module-level refs for external access. Prepares for multi-chart support (phase 9).

## Non-requirements

- No changes to the screenshot viewer page or social page
- No changes to the share position modal
- No changes to the notes data model or API
- No new screenshot UI beyond what already exists
- No multi-chart screenshot support (screenshot targets the single chart in TT; multi-chart behavior is out of scope until phase 9)
