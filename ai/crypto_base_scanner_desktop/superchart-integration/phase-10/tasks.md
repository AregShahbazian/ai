# Phase 10 — Tasks

Tasks T1–T9 are already implemented. The tasks below (T10–T14) cover the new
CenterView removal and Charts page changes.

---

## T10 — CandleChart page-awareness

### Files
- `src/containers/trade/trading-terminal/widgets/candle-chart.js`

### Changes
1. Add `toggleable` prop (default `true`)
2. Accept optional TV callback props (`handleTVSymbolChanged`,
   `handleTVIntervalChanged`, `handleTVVisibleRangeChanged`)
3. When `toggleable={false}`: always render `DefaultTradingWidget` with forwarded
   TV props, no toggle UI, ignore Redux `useSuperChart`
4. When `toggleable={true}` (existing behavior): show toggle, render SC or
   `MainChartTradingWidget` based on Redux state
5. Import `DefaultTradingWidget` from `./center-view/tradingview`

### Verify
- TT: toggle works as before (SC default, switch to TV)
- Charts page: always renders TV, no toggle visible, Redux toggle state ignored

---

## T11 — Charts page default layout migration

### Files
- `src/models/flex-layout/default-chart-layouts.js` — change `"CenterView"` →
  `"CandleChart"` in all default chart layouts

### Changes
1. Replace all `"component": "CenterView"` with `"component": "CandleChart"`

### Verify
- Fresh install Charts page layouts contain `CandleChart`, no `CenterView`

---

## T12 — Charts page custom layout migration

### Files
- `src/models/flex-layout/chart-layouts-controller.js` — add `correctLayoutOnce`,
  update `syncWithChartTabs`
- `src/models/flex-layout/grid-to-flex-migration.js` — update legacy migration

### Changes
1. Add `correctLayoutOnce` to `ChartLayoutsController`:
   ```js
   static correctLayoutOnce = (layout) => {
     const model = FlexLayout.Model.fromJson(layout.serializedSettings.flexLayout)
     ChartLayoutsController.getModelNodesByType(model, {type: "tab"})
       .filter(t => t.getComponent() === "CenterView")
       .forEach(t => model.doAction(Actions.updateNodeAttributes(t.getId(), {component: "CandleChart"})))
     layout.serializedSettings.flexLayout = model.toJson()
     return layout
   }
   ```
2. In `syncWithChartTabs` (line 142): change `component: "CenterView"` →
   `component: "CandleChart"`
3. In `grid-to-flex-migration.js`: change `component: "CenterView"` →
   `component: "CandleChart"`

### Verify
- Existing Charts page custom layouts with `CenterView` are migrated on load
- Adding a new chart tab creates a `CandleChart` node (not `CenterView`)
- Migration is idempotent

---

## T13 — Charts page rendering via CandleChart

### Files
- `src/containers/trade/trading-terminal/grid-layout/flex-grid/charts-grid-item.js` —
  use `CandleChart` instead of `DefaultTradingWidget`

### Changes
1. Import `CandleChart` from `../../widgets/candle-chart`
2. Replace `DefaultTradingWidget` render with:
   ```jsx
   <CandleChart toggleable={false}
                handleTVSymbolChanged={handleTVSymbolChanged}
                handleTVIntervalChanged={handleTVIntervalChanged}
                handleTVVisibleRangeChanged={handleTVVisibleRangeChanged}/>
   ```
3. Remove `DefaultTradingWidget` import (no longer used here)

### Verify
- Charts page renders TV via CandleChart
- No toggle visible on Charts page
- Multi-chart layouts work correctly
- Symbol/interval/visible-range callbacks still function

---

## T14 — CenterView removal

### Files
- `src/actions/constants/layout.js` — remove `CenterView` from `WIDGET_SETTINGS`
- `src/containers/trade/trading-terminal/grid-layout/grid-content.js` — remove
  `CenterView` case + `MainChartTradingWidget` import
- `src/containers/trade/trading-terminal/grid-layout/grid-item-settings.js` — remove
  `CenterView` from `COMPONENTS_WITH_SETTINGS` and switch case
- `src/containers/trade/trading-terminal/grid-layout/grid-item-refresh.js` — remove
  `CenterView` case
- `src/locales/en/translation.yaml` — remove `widgets.CenterView` key

### Changes
1. Remove `CenterView` entry from `WIDGET_SETTINGS` proxy object
2. Remove `case "CenterView"` from `grid-content.js` switch, remove
   `MainChartTradingWidget` import
3. Remove `"CenterView"` from `COMPONENTS_WITH_SETTINGS` array
4. Remove `case "CenterView":` from `GridItemSettings` switch (keep `CandleChart`
   case)
5. Remove `"CenterView"` from `offsetFromTop` check (keep `CandleChart`)
6. Remove `case "CenterView":` from `grid-item-refresh.js` (keep `CandleChart`)
7. Remove `widgets.CenterView` from `en/translation.yaml`

### Verify
- No remaining `CenterView` references in widget registration/rendering code
- `CenterView` only remains in migration code (`correctLayoutOnce`,
  `stateMergeAndReset`, `grid-to-flex-migration.js`, `legacy-default-layouts.js`,
  `validateLayout`)
- App loads without errors on fresh install and with migrated layouts

---

## Task order

T10–T14 build on the already-implemented T1–T9.

1. **T10** (CandleChart page-awareness) — no dependencies
2. **T11** (Charts default layouts) — no dependencies, can parallel with T10
3. **T12** (Charts custom layout migration) — no dependencies, can parallel with T10
4. **T13** (Charts page rendering) — depends on T10, T11, T12
5. **T14** (CenterView removal) — depends on T11, T12, T13
