---
id: sc-settings-preview
---

# PRD: Chart Settings Preview — SuperChart Integration

## Overview

Replace the TradingView-based chart at the top of the **chart settings modal**
(`tradingpreview.js`) with a new SuperChart variant. The preview is a small,
non-interactive chart whose job is to showcase the user's custom chart colors
(and eventually other settings) live as they edit them in the modal — without
pressing Save.

Scope of this PRD is intentionally narrow:

- A new SC widget variant (`PreviewSuperChartWidget`) alongside
  `SuperChartWidget` (main TT chart) and `GridBotSuperChartWidget` (grid bot).
- A static datafeed that serves hardcoded candles — no live data, no Coinray.
- A fixed symbol, resolution, and visible range — no user control.
- Disabled scroll/zoom — fully display-only.
- Colors driven by the modal's local (unsaved) `chartSettings` copy.
- Main-chart unmount coordination so only one SC instance exists at a time.

**No overlays** are ported from the TV preview — this preview starts empty.
Overlay content (bases, trades, alerts, orders, bid/ask, break-even, etc.)
will be rebuilt from scratch in follow-up PRDs.

## Current Behavior (TradingView)

### Where the preview lives

`settings.js` renders `<TradingPreview chartSettings={...}/>` at the top of the
chart settings modal body when the "Preview" toggle (`showPreview`) is on. The
modal itself is mounted from `grid-item-settings.js` via `GridItemSettings`
when `component === "CenterView"`. The preview is hidden on mobile
(`hidden tablet:flex`) and the modal is a fixed-width desktop modal.

`TradingPreview` (`tradingpreview.js`) spins up a second TV widget in parallel
with the main TT chart. It uses `DummyDataProvider` for static candles and
`ChartContext` + `VisibleRangeContext` providers so the TT overlay components
can render on top.

### What matters for this PRD

- **Candles**: hardcoded in `settings/dummy-data.js` (`candles`), ~75 bars,
  resolution `60`, symbol `BINA_USDT_BTC`. Candle times are already in ms
  (SC's `Bar` format).
- **Visible range**: effectively "everything" —
  `{from: 0, to: moment().unix()}` in the TV `VisibleRangeContext`.
- **Interactivity**: TV's preview disables the `left_toolbar`,
  `timeframes_toolbar`, and `bottom_toolbar` features and overlays a
  click-blocker div. Scroll/zoom still technically works on the TV canvas.
- **Settings reactivity**: the modal keeps a **local** `chartSettings` copy
  (starting from Redux), updated in-place by the form (`changeSettings`,
  `updateColors`, `onPreviewSetting`). That local copy is passed to
  `TradingPreview`, which re-applies TV overrides on every change. Saving
  the modal writes the local copy back to Redux — only then do changes
  reach the main TT chart and every other chart in the app.

## Requirements

### R1 — `PreviewSuperChartWidget` (new SC variant)

New widget at `super-chart/preview-super-chart.js`, alongside
`super-chart.js` and `grid-bot-super-chart.js`. Behaviour:

- Mounts a single `Superchart` instance on mount, disposes on unmount.
- Symbol: hardcoded `BINA_USDT_BTC` via a minimal inline `SymbolInfo`
  (`ticker`, `name`, `shortName`, `pricePrecision: 2`, `volumePrecision: 0`).
  Do not use `toSymbolInfo(...)` — the coinray cache has no live market in
  this context.
- Period: hardcoded `toPeriod("60")`.
- DataLoader: wraps `PreviewDatafeed` (R2).
- Theme: synced from `ThemeContext` (same pattern as the other variants).
- Wraps children in `SuperChartContextProvider` so it can evolve later, even
  though no overlay components are mounted in this PRD.
- Registers with `ChartRegistry` under `preview-<uuid>` (per-mount — same
  pattern and rationale as `GridBotSuperChartWidget`).
- Receives a `chartSettings` prop (the modal's local copy) instead of reading
  Redux. The `ChartController` uses this prop to resolve colors (R5).
- Renders no header buttons, no screenshot UI, no hotkeys, no action bar,
  no context menu, no overlay children.

### R2 — `PreviewDatafeed` (static data source)

New datafeed at `super-chart/preview-datafeed.js`:

- `getBars` returns the full `candles` array from `settings/dummy-data.js`
  on the first request (`firstDataRequest`), and `{noData: true}` on
  subsequent calls. No pagination.
- `subscribeBars` / `unsubscribeBars`: no-ops.
- `resolveSymbol`: returns a minimal `LibrarySymbolInfo` matching the
  hardcoded symbol.
- `searchSymbols`: returns no results.
- `onReady`: calls back with a minimal config (`supported_resolutions: ["60"]`)
  on the next tick.

### R3 — Fixed visible range

After `superchart.onReady`, set a fixed visible range via
`superchart.setVisibleRange({from, to})` that frames the entire dummy-candle
span (first candle time → last candle time, converted to unix seconds). No
right-side "live" padding — there is no live data.

The preview does not subscribe to `onVisibleRangeChange` and does not
persist range anywhere.

### R4 — Disabled user interaction

After `superchart.onReady` (so `getChart()` is non-null):

- `chart.setScrollEnabled(false)`
- `chart.setZoomEnabled(false)`

The period-bar is hidden entirely on the preview via
`periodBarVisible: false` on the `Superchart` constructor — this is
display-only, no interactive chrome.

### R5 — Colors from local (unsaved) settings

- The preview's `chartSettings` comes from the modal's local state, not
  Redux.
- On every `chartColors` change in that prop, the controller re-applies
  styles — the component wires this via `useEffect` on `chartColors +
  theme._name`, calling `controller.syncChartColors()`. Same mechanism
  used by the TT and grid-bot widgets, the only difference is the source
  of `chartColors` (prop vs Redux).
- The modal's Save button is unchanged: `editChartSettings` +
  `saveChartColors` still write to Redux and close the modal.

Other chart settings (hideAmounts, candle style overrides, etc.) are out
of scope for this PRD — they will be handled when their corresponding
overlays/features are added.

### R6 — Single-instance coordination with the TT main chart

SC's shared singleton store prevents two SC instances from coexisting
cleanly (INTEGRATION.md Phase 9b). The settings modal opens *over* the
Trading Terminal, so without coordination both the TT main SC and the
preview SC would be mounted simultaneously.

Rule: exactly one of them is mounted at any time.

- The TT side (`super-chart.js` — `SuperChartWidgetWithProvider`, or
  `candle-chart.js`) reads `GridItemSettingsContext`. When
  `isOpen && component === "CenterView"` **and** the modal's
  `showPreview` is on, it unmounts the inner `SuperChartWidget`.
- The preview side only mounts when the modal is open and `showPreview`
  is on.
- Transitions (modal open/close, `showPreview` toggle) must leave
  `ChartRegistry` consistent: the TT controller unregisters on unmount,
  the preview registers itself, and the TT controller re-registers on
  remount.
- `showPreview` state lives in the settings modal. To let the TT side see
  it without prop-drilling, extend `GridItemSettingsContext` with a
  `previewShown` flag (set by the settings modal when it toggles
  `showPreview`, cleared when the modal closes). Keep the existing
  `component` / `isOpen` / `onToggle` API untouched.
- No attempt to preserve TT chart scroll/VR across the unmount — remount
  is a fresh load (matches the grid-bot workaround).

### R7 — Visibility gating

- The preview mounts only when the settings modal is open for
  `CenterView` **and** `showPreview === true` in that modal's state.
- Desktop only. The existing `hidden tablet:flex` wrapper in `settings.js`
  stays — mobile will not mount the preview at all.

## Data Sources

| Piece | Source |
|---|---|
| Candles | `settings/dummy-data.js` → `candles` |
| Symbol / resolution | Hardcoded constants in `preview-super-chart.js` |
| Colors / chart settings | Modal-local `chartSettings` prop (not Redux) |

No overlay data sources — no overlays in this PRD.

## File Structure

```
super-chart/
  preview-super-chart.js          # PreviewSuperChartWidget variant
  preview-datafeed.js             # Static datafeed over dummy candles
```

Modified:

```
containers/trade/trading-terminal/
  grid-layout/grid-item-settings.js          # extend context with previewShown
  widgets/center-view/tradingview/settings.js # swap TradingPreview → PreviewSuperChartWidget; publish previewShown
  widgets/super-chart/super-chart.js          # unmount when previewShown
```

## Incremental Implementation Plan

### Step 1: `PreviewDatafeed` + `PreviewSuperChartWidget` skeleton

Create both files. Mount a bare SC with the hardcoded symbol/period and the
static datafeed. Verify candles render. Swap `TradingPreview` →
`PreviewSuperChartWidget` in `settings.js`. At this step both charts (TT +
preview) may be mounted — fix in Step 4.

**Files:** `preview-datafeed.js`, `preview-super-chart.js`, `settings.js`.

### Step 2: Fixed visible range + disabled interaction

After `onReady`: call `setVisibleRange` (from first→last dummy candle) and
`chart.setScrollEnabled(false)` / `chart.setZoomEnabled(false)`. Verify the
full dummy span is framed and scroll/zoom no longer respond.

**Files:** `preview-super-chart.js`.

### Step 3: Colors from local settings

Pass the modal's local `chartSettings` as a prop and wire
`controller.syncChartColors()` on every `chartColors` change. Verify that
changing a color in the form updates the preview canvas immediately, and
that the main TT chart (once Step 4 lands) does not change until Save.

**Files:** `preview-super-chart.js`, possibly `chart-controller.js` (only
if the existing Redux-driven sync needs a prop override).

### Step 4: Single-instance coordination

Extend `GridItemSettingsContext` with `previewShown`. Publish it from
`settings.js` (mirror of the existing `showPreview` state). Consume it in
`super-chart.js` / `candle-chart.js` to unmount `SuperChartWidget` while
the preview is up. Verify only one SC instance exists at any time,
`ChartRegistry` stays consistent, and TT overlays redraw correctly on
remount.

**Files:** `grid-item-settings.js`, `settings.js`, `super-chart.js` (or
`candle-chart.js`).

### Step 5: Overlays (future — separate PRDs)

Preview overlay content is rebuilt from scratch in follow-up PRDs, not
here.

### Step 6: Remove TV preview (future — Phase 10f)

`tradingpreview.js` and `DummyDataProvider` stay untouched in this PRD.
Deletion happens in the broader TV-removal task.

## Non-Requirements

- **No overlays.** None of the TV preview's overlays (bases, trades,
  alerts, orders, bid/ask, break-even) are ported. The preview is a bare
  candle chart in this PRD.
- No live data, subscribeBars, or Coinray wiring.
- No persistence — `StorageAdapter` not used, no `tvStorage`, no VR
  persistence.
- No MarketTabContext, TradingTabsController, or symbol/resolution sync
  with any tab state.
- No replay, quiz, grid-bot, or trading-terminal widgets on the preview
  (header buttons, screenshot, action buttons, hotkeys, context menu,
  replay controls — all excluded).
- No mobile preview. Matches the current TV behaviour — the modal
  preview row is desktop-only.
- No resize handling beyond SC's built-in `resize()` — the modal is
  fixed-width on desktop and not mounted on mobile.
- No changes to the settings modal's tab layout, Save/Cancel wiring, or
  form components.
- No removal of `tradingpreview.js` / `DummyDataProvider` — handled by
  Phase 10f (TV removal).
