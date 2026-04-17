# Review: Chart Settings Preview — `sc-settings-preview`

## Round 1: initial implementation (2026-04-17)

### Implemented

- `PreviewDatafeed` (new) — static datafeed over the existing dummy
  candles. Exports `PREVIEW_SYMBOL`, `PREVIEW_RESOLUTION`,
  `PREVIEW_RANGE_FROM`, `PREVIEW_RANGE_TO`. No-op
  `subscribeBars`/`unsubscribeBars`/`dispose`.
- `PreviewSuperChartWidget` (new) — standalone SC variant with a fixed
  symbol/period/VR, disabled scroll/zoom, no sub-controllers,
  registered as `preview-<uuid>` in `ChartRegistry`. Colors driven
  synchronously via `setColorsOverride(prop-derived)` pre-onReady and
  via an effect on `chartSettings.chartColors` / `theme._name`.
- `ChartController.setColorsOverride(colors)` + `get colors()` falls
  back to Redux only when no override is set.
- `GridItemSettingsContext` extended with `previewShown` /
  `setPreviewShown` + defensive reset when `isOpen → false`.
- `TradingviewSettings` (class) now consumes
  `GridItemSettingsContext` via `contextType` and publishes its
  `showPreview` state via `componentDidMount` / `componentDidUpdate` /
  `componentWillUnmount`. Renders `<PreviewSuperChartWidget/>` in
  place of the TV preview.
- `CandleChart` unmounts `SuperChartWidgetWithProvider` when
  `isOpen && component === "CenterView" && previewShown && toggleable`.

### Verification

1. Open the Trading Terminal — TT SC renders as usual.
2. Open the chart settings modal (Ctrl+Shift+S or the gear icon on the
   chart widget).
3. Preview SC renders at the top of the modal with the dummy candles
   framed across the full visible range.
4. TT SC unmounts (the chart area behind the modal goes blank, no
   console warnings about two SC instances).
5. Preview SC: scroll horizontally → no movement. Mouse-wheel zoom →
   no movement.
6. Toggle "Preview: No" in the modal header → preview SC unmounts, TT
   SC remounts (fresh load).
7. Toggle "Preview: Yes" again → preview remounts, TT unmounts.
8. Change a candle color (e.g. Candle Up) in the modal → preview
   updates live without Save. TT SC is unmounted so visibly unaffected.
9. Click Save → modal closes, preview unmounts, TT SC remounts with
   the saved color.
10. Reopen the modal, edit a color, click Cancel → modal closes
    without persisting; TT SC remounts unchanged.
11. Mobile: the preview row is hidden (`hidden tablet:flex`). Open the
    modal → TT SC stays mounted (no `setPreviewShown(true)` fires
    because the preview JSX is not rendered).
12. Trading Terminal context tests:
    - Change TradingTab while modal closed → TT SC syncs tab normally.
    - Change coinraySymbol within a tab → TT SC syncs normally.
    - Change resolution within a tab → TT SC syncs normally.
    - Change exchangeApiKeyId within a tab → TT SC syncs normally.
    - For each of the above, open the settings modal afterwards →
      preview mounts, TT unmounts, settings reapply without Save.

### Apply steps

- HMR should pick up React changes.
- `chart-controller.js` is a class module — HMR may reload but SC
  instances created before the change retain the old class; reload
  the page to be sure.
- No Superchart build needed (no library source changes).
