# SC Backend Endpoints — Proposed

New Altrady backend endpoints needed to back SC's persistence layer.

Reflects the live `AltradyStorageAdapter`
(`src/containers/trade/trading-terminal/widgets/super-chart/storage-adapter.js`)
which splits SC's `ChartState` into two on-disk records to match TV's
persistence shape:

- **Layout** (indicators + panes + styles + preferences) — one global
  record per user, shared across every chart instance and every symbol.
- **Drawings** (overlays) — one record per symbol, shared across every
  chart instance on that symbol.

Plus two template namespaces (drawing + indicator) and a named
chart-layout namespace, all user-wide.

All routes follow existing Altrady API conventions
(`api.createResource` → POST, `api.getResource` → GET,
`api.updateResource` → PATCH, `api.deleteResource` → DELETE). No PUT.

## 1. Layout record (global per user)

One row per user, contains the layout half of `ChartState` (no overlays).
Optimistic-concurrency via `revision`.

- `GET    /superchart/layout`                  — returns `{state, revision}` or 404
- `PATCH  /superchart/layout`                  — body `{state, expectedRevision}`; 409 on mismatch
- `DELETE /superchart/layout`

Replaces TV's `/api/v2/tradingview_charts/charts` (plus the study config
that lived in TV's chart layout).

## 2. Drawings record (per symbol)

One row per `(user, symbol)`. Last-write-wins is acceptable per the
current adapter behavior; a `revision` field is still cheap and lets us
upgrade to optimistic-concurrency later.

- `GET    /superchart/drawings/:symbol`        — returns `{overlays, revision}` or 404
- `PATCH  /superchart/drawings/:symbol`        — body `{overlays, expectedRevision?}`
- `DELETE /superchart/drawings/:symbol`

Replaces TV's `/api/v2/tradingview_charts/line_tools`.

## 3. Indicator templates (user-wide)

Named save/load of indicator configurations. Replaces TV's
`/api/v2/tradingview_charts/study_templates`. SC's contract allows
filtering by `indicatorName`.

- `GET    /superchart/indicator_templates?indicator=…`
- `POST   /superchart/indicator_templates`
- `PATCH  /superchart/indicator_templates/:id`
- `DELETE /superchart/indicator_templates/:id`

## 4. Drawing templates (user-wide)

Named save/load per drawing tool. Replaces TV's existing Altrady
`tradingview/drawing_templates` endpoint.

- `GET    /superchart/drawing_templates?tool=…`
- `POST   /superchart/drawing_templates`
- `PATCH  /superchart/drawing_templates/:id`
- `DELETE /superchart/drawing_templates/:id`

**Reuse** the existing `tradingview_drawing_templates` table if its row
shape (`tool`, `name`, `template`-JSON) is compatible with SC's
overlay-properties JSON — same schema, different consumer. Otherwise
version it.

## 5. Named chart layouts (user-wide)

User-saved "Layout" snapshots from SC's period-bar Layout button. Each
is a full `ChartState` (layout + drawings) under a user-chosen name.

- `GET    /superchart/chart_layouts`            — list metas
- `GET    /superchart/chart_layouts/:id`        — full body
- `POST   /superchart/chart_layouts`            — body `{name, state}`
- `PATCH  /superchart/chart_layouts/:id`        — rename or replace body
- `DELETE /superchart/chart_layouts/:id`

No analog in TV (TV had only the single-layout-per-user model). Wholly new.

## Summary table

| Asset                  | Endpoint                                         | Scope        | TV equivalent                                    |
|------------------------|--------------------------------------------------|--------------|--------------------------------------------------|
| Layout record          | `/superchart/layout`                             | user-wide    | `/api/v2/tradingview_charts/charts`              |
| Drawings record        | `/superchart/drawings/:symbol`                   | per symbol   | `/api/v2/tradingview_charts/line_tools`          |
| Indicator templates    | `/superchart/indicator_templates[/:id]`          | user-wide    | `/api/v2/tradingview_charts/study_templates`     |
| Drawing templates      | `/superchart/drawing_templates[/:id]`            | user-wide    | `tradingview/drawing_templates` (reuse table)    |
| Named chart layouts    | `/superchart/chart_layouts[/:id]`                | user-wide    | — (new in SC)                                    |
