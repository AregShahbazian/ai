# TV Storage Endpoints — Backend Persistence Overview

All chart-related persistence in the TV implementation is server-side. Two
flavors are used:

## Flavor A — TV's own SaveLoadAdapter

Configured in `controllers/setup.js:95` via:

```
charts_storage_url: API_HOST + "/api/v2/tradingview_charts"
charts_storage_api_version: "2.1"
```

TV constructs the paths itself. Endpoints (all under
`/api/v2/tradingview_charts/`):

- **Chart layouts** — `/charts` (list / CRUD)
- **Indicator (study) templates** — `/study_templates`
- **Drawings** — `/line_tools` (separated from layouts via the
  `saveload_separate_drawings_storage` enabled feature)

## Flavor B — Altrady CRUD adapters

Defined in `actions/chart-settings.js:67–101`, using the app's internal
`api.{create,get,update,delete}Resource` against the path prefix
`tradingview/...`.

- **Drawing templates** — `tradingview/drawing_templates`
  (`createTemplate` / `updateTemplate` / `deleteTemplate` / `loadTemplates`).
  Consumed by `tradingview-enhancements` for the floating-toolbar template
  menu.
- **Generic storage wrappers** — `tradingview/${storageType}/${id}?version=…`
  via `getTvStorage` / `updateTvStorage` / `deleteTvStorage`. Called by
  `LocalSaveLoadAdapter` (and the trading-feature-less path of
  `setupSaveLoadAdapter`) to reach the same `study_templates` /
  `drawing_templates` storage from outside TV's adapter.

## Summary table

| Asset                 | Endpoint                                              | Adapter            |
|-----------------------|-------------------------------------------------------|--------------------|
| Chart layouts         | `/api/v2/tradingview_charts/charts`                   | TV SaveLoadAdapter |
| Drawings              | `/api/v2/tradingview_charts/line_tools`               | TV SaveLoadAdapter |
| Indicator templates   | `/api/v2/tradingview_charts/study_templates`          | TV SaveLoadAdapter |
| Drawing templates     | `tradingview/drawing_templates` (Altrady API)         | Altrady actions    |
