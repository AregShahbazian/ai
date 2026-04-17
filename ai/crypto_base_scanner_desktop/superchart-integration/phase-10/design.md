# Phase 10 — Design

## D1 — CandleChart widget component (page-aware)

### Existing file

**`src/containers/trade/trading-terminal/widgets/candle-chart.js`** — already created.
Needs a `toggleable` prop to control page behavior.

```jsx
const CandleChart = ({toggleable = true}) => {
  const useSuperChart = useSelector(state => state.chartSettings.useSuperChart)
  const replayMode = useSelector(state => state.replay.replayMode)

  const showSC = toggleable && useSuperChart
  const showToggle = toggleable
  const toggleDisabled = !!replayMode

  return <div>
    {showToggle && <BooleanInput isSwitch .../>}
    {showSC
      ? <SuperChartWidgetWithProvider key="sc"/>
      : <MainChartTradingWidget key="tv"/>}
  </div>
}
```

- `toggleable={true}` (default) — TT behavior: reads Redux, shows toggle, SC/TV
- `toggleable={false}` — Charts page behavior: always TV, no toggle, ignores Redux

### Charts page integration

`ChartsGridItem` (`charts-grid-item.js`) currently renders `DefaultTradingWidget`
directly. Replace with `CandleChart` passing `toggleable={false}` plus the TV
callbacks (`handleTVSymbolChanged`, `handleTVIntervalChanged`,
`handleTVVisibleRangeChanged`).

Problem: `CandleChart` currently renders `MainChartTradingWidget` (which doesn't
accept these callbacks — it reads from `MarketTabContext`). But `ChartsGridItem`
renders `DefaultTradingWidget` (which takes callbacks as props).

Solution: when `toggleable={false}`, `CandleChart` renders `DefaultTradingWidget`
with forwarded props. When `toggleable={true}`, it renders `MainChartTradingWidget`
(TT) or `SuperChartWidgetWithProvider` (SC). This means `CandleChart` accepts
optional TV callback props that are passed through to `DefaultTradingWidget`.

```jsx
const CandleChart = ({toggleable = true, ...tvProps}) => {
  const showSC = toggleable && useSuperChart

  if (showSC) return <SuperChartWidgetWithProvider key="sc"/>
  if (toggleable) return <MainChartTradingWidget key="tv"/>
  return <DefaultTradingWidget {...tvProps}/>
}
```

## D2 — SC single-instance guard

No changes from current implementation. `DevWidgetGuard` already checks
`useSuperChart` + `CandleChart` presence in layout.

## D3 — Widget registration & FlexLayout migration

### CenterView removal

After migration code is in place:
- Remove `CenterView` from `WIDGET_SETTINGS` in `layout.js` constants
- Remove `CenterView` case from `grid-content.js` switch (no longer needed —
  all layouts migrated to `CandleChart`)
- Remove `CenterView` from `COMPONENTS_WITH_SETTINGS` and switch in
  `grid-item-settings.js`
- Remove `CenterView` case from `grid-item-refresh.js`

### Charts page default layouts

In `default-chart-layouts.js`, change all `"component": "CenterView"` to
`"component": "CandleChart"`.

### Charts page custom layout migration

Add `correctLayoutOnce` to `ChartLayoutsController`:

```js
static correctLayoutOnce = (layout) => {
  const model = FlexLayout.Model.fromJson(layout.serializedSettings.flexLayout)

  // Migrate CenterView → CandleChart
  ChartLayoutsController.getModelNodesByType(model, {type: "tab"})
    .filter(t => t.getComponent() === "CenterView")
    .forEach(t => model.doAction(Actions.updateNodeAttributes(t.getId(), {component: "CandleChart"})))

  layout.serializedSettings.flexLayout = model.toJson()
  return layout
}
```

### syncWithChartTabs

In `ChartLayoutsController.syncWithChartTabs`, change the hardcoded
`component: "CenterView"` to `component: "CandleChart"` when adding new tab nodes.

### grid-to-flex-migration.js

Change `component: "CenterView"` to `component: "CandleChart"` in the legacy
migration code so newly migrated layouts already use the new name.

## D4 — Mobile layout migration

No changes from current implementation. Already renames `CenterView` → `CandleChart`
and removes `SuperChart` from mobile defaults.

## D5 — Screenshots

No changes from current implementation. Already chart-agnostic.

## D6 — Charts page rendering

`ChartsGridItem` currently renders `DefaultTradingWidget` directly. Replace with
`CandleChart` passing `toggleable={false}` and the TV callback props.

The `MarketHeaderBar` rendering stays in `ChartsGridItem` (not moved into
`CandleChart`).

## Open questions

1. **Toggle placement:** Exact position of the `BooleanInput` switch — currently
   absolute positioned top-right. May need adjustment during review.
