---
id: sc-endpoints
---

# PRD: SuperChart persistence endpoints

## Summary

The desktop app is migrating from TradingView (TV) to SuperChart (SC). SC's
chart persistence layer is currently wired against `localStorage` so we can
dogfood it. To ship, the backend needs endpoints matching SC's
`StorageAdapter` contract. Once these exist, the frontend will swap the
`LocalStorageAdapter` delegation in `super-chart/storage-adapter.js` for an
HTTP-backed adapter pointing at these routes.

The frontend already enforces a TV-faithful split on top of SC's blob model,
so the backend mirrors that split rather than the single-blob shape SC ships
out of the box.

Routes follow Altrady's existing API conventions (`POST` create, `GET` read,
`PATCH` update, `DELETE` delete — no `PUT`). All routes mount under the
existing Grape `ApiV3` API and authenticate via the standard Altrady auth
(`current_account`).

## Persistence model

Five user-scoped namespaces, three of which back the live SC chart and two
of which back the templates UIs:

1. **Layout record** — *one row per user.* The "current working layout":
   indicators + panes + styles + preferences. Autosaved by SC as the user
   adds/removes indicators or changes settings. Same record is read by every
   chart instance the user has open. Optimistic-concurrency required (SC
   checks `expectedRevision` on save).

2. **Drawings record** — *one row per `(account, coinray_symbol)`.* Drawings
   live separate from layout, exactly like TV's `line_tools` storage.
   Switching markets swaps which drawings record loads. Last-write-wins is
   acceptable; a `revision` field still pays for itself if we later want to
   upgrade.

3. **Indicator templates** — *user-wide, many rows.* Named indicator
   configurations (e.g. "My RSI"). Scoped per indicator type (RSI / MACD /
   BOLL / …) so opening RSI's settings only lists RSI templates.

4. **Drawing templates** — *user-wide, many rows.* Named drawing styles per
   drawing tool (trendline, fib, ray, …).

5. **Named chart layouts** — *user-wide, many rows.* Full `ChartState`
   snapshots (layout + drawings) the user explicitly saves via SC's
   period-bar Layout button. Each row has a meta (name) and a body (applied
   when picked). New concept — TV didn't separate this from #1.

## Naming conventions

- Use `coinray_symbol` (not `symbol`) everywhere — consistent with the rest
  of the Altrady codebase (e.g. `tradingview_drawings.coinray_symbol`,
  `Market#coinray_symbol`).
- All routes under `/superchart/...`.
- **All responses are JSON objects, never bare arrays.** Collection
  endpoints wrap their results under a plural-camelCase root
  (`superchartIndicatorTemplates`, `superchartDrawingTemplates`,
  `superchartChartLayouts`). Single-record endpoints with a corresponding
  list wrap under the singular root (`superchartIndicatorTemplate`, …).
  Layout and per-symbol drawings have no list endpoint and stay un-rooted.

## Endpoints

### 1. Layout record

```
GET    /superchart/layout                        → 200 {state, revision} | 404
PATCH  /superchart/layout                        body: {state, expectedRevision}
                                                 → 200 {revision}
                                                 → 409 {remoteState, remoteRevision} on mismatch
DELETE /superchart/layout                        → 204
```

- `state` is opaque JSON to the backend (frontend serialises a subset of
  SC's `ChartState`). Don't validate its inner shape.
- `revision` is a monotonically-increasing integer per user; bump on each
  successful write.
- 409 body shape is `{remoteState, remoteRevision}` so the frontend can run
  SC's merge-retry against the remote.

Replaces TV's `/api/v2/tradingview_charts/charts`.

### 2. Drawings record (per symbol)

```
GET    /superchart/drawings/:coinray_symbol      → 200 {overlays, revision} | 404
PATCH  /superchart/drawings/:coinray_symbol      body: {overlays, expectedRevision?}
                                                 → 200 {revision}
DELETE /superchart/drawings/:coinray_symbol      → 204
```

- `:coinray_symbol` is the Coinray symbol string (`BINA_USDT_BTC`, etc.).
- `overlays` is an opaque JSON array.
- `expectedRevision` is optional; current frontend uses last-write-wins
  here, but accept and honor it if sent (mirror layout's 409 shape).
- Scope rows directly by `(account, coinray_symbol)` — **do not** reuse TV's
  `tradingview_drawings` table. TV keys drawings by `(chart_id,
  coinray_symbol)` via `TradingviewChart`; SC has no parent chart record, so
  use a fresh `superchart_drawings` table keyed by `(account_id,
  coinray_symbol)`.

Replaces TV's `/api/v2/tradingview_charts/line_tools`.

### 3. Indicator templates

```
GET    /superchart/indicator_templates?indicator=…
                                                 → 200 {superchartIndicatorTemplates: [{id, name, indicator, body}, …]}
GET    /superchart/indicator_templates/:id       → 200 {superchartIndicatorTemplate: {id, name, indicator, body}} | 404
POST   /superchart/indicator_templates           body: {name, indicator, body}
                                                 → 201 {superchartIndicatorTemplate: {…}}
PATCH  /superchart/indicator_templates/:id       body: any subset of {name, body}
                                                 → 200 {superchartIndicatorTemplate: {…}}
DELETE /superchart/indicator_templates/:id       → 204
```

- `indicator` is the indicator type name (`"RSI"`, `"MACD"`, `"BOLL"`, …).
- `body` is opaque JSON (SC's `calcParams` + per-template metadata).
- List endpoint MUST support the `?indicator=` filter — SC sends it when
  opening an indicator's settings cog, and an unfiltered list causes
  irrelevant templates to appear under the wrong indicator.

Replaces TV's `/api/v2/tradingview_charts/study_templates`.

### 4. Drawing templates

```
GET    /superchart/drawing_templates?tool=…
                                                 → 200 {superchartDrawingTemplates: [{id, tool, name, template}, …]}
GET    /superchart/drawing_templates/:id         → 200 {superchartDrawingTemplate: {id, tool, name, template}} | 404
POST   /superchart/drawing_templates             body: {tool, name, template}
                                                 → 201 {superchartDrawingTemplate: {…}}
PATCH  /superchart/drawing_templates/:id         body: any subset of {name, template}
                                                 → 200 {superchartDrawingTemplate: {…}}
DELETE /superchart/drawing_templates/:id         → 204
```

- `tool` is the drawing tool name (`"trendLine"`, `"fibSegment"`, …).
- `template` is opaque overlay-properties JSON.

**Reusing `tradingview_drawing_templates`:** the row shape (`tool`, `name`,
`template`-JSON) is compatible, but TV rows have a `version` column that
gates TV-format payloads (see `ApiV3::Tradingview#drawing_templates`).
Either:

- Add a `source` column (`"tv"` / `"sc"`) and scope the new endpoints to
  `source: "sc"`, leaving TV endpoints scoping to `"tv"`; or
- Keep the table TV-only and create a new `superchart_drawing_templates`
  table.

Prefer the `source` column path — same shape, no duplicate model — but the
SC endpoints must never return TV-format rows and vice versa.

### 5. Named chart layouts

```
GET    /superchart/chart_layouts                 → 200 {superchartChartLayouts: [{id, name, savedAt}, …]}   (metas only)
GET    /superchart/chart_layouts/:id             → 200 {superchartChartLayout: {id, name, state}}   (full body)
POST   /superchart/chart_layouts                 body: {name, state}
                                                 → 201 {superchartChartLayout: {id, name, savedAt}}
PATCH  /superchart/chart_layouts/:id             body: any subset of {name, state}
                                                 → 200 {superchartChartLayout: {id, name, savedAt}}
DELETE /superchart/chart_layouts/:id             → 204
```

- `state` is opaque JSON — a full `ChartState` snapshot at save time
  (includes both layout + drawings).
- List endpoint returns metas only (no body) so the picker UI is cheap to
  populate.

New concept — no TV equivalent.

## Auth / scope

All routes are user-scoped via the standard Altrady auth. Server enforces
"can only read/write your own rows" on every endpoint (scope by
`current_account`). No admin views or cross-user access required.

## Out of scope

- Server-side snapshot upload (TV had this via
  `TradingviewChartsController#snapshot`; explicitly dropped — SC
  screenshots stay local).
- Quiz persistence (already covered by `QuizStorageAdapter` on the desktop
  side, talks to existing quiz endpoints).
- Migration of TV-format persisted state into SC format. Starting clean —
  existing TV chart layouts won't follow users into SC.

## References

- Live frontend adapter:
  `crypto_base_scanner_desktop/src/containers/trade/trading-terminal/widgets/super-chart/storage-adapter.js`
- Endpoint spec (frontend's source of truth):
  `crypto_base_scanner_desktop/ai/superchart-integration/phase-6/sc-endpoints.md`
- TV endpoints being replaced:
  `crypto_base_scanner_desktop/ai/superchart-integration/phase-6/tv-endpoints.md`
- SC storage contract (upstream): `Superchart/src/lib/types/storage.ts`
- Existing TV backend (this repo):
  - `app/api/api_v3/tradingview.rb`
  - `app/controllers/api/v2/tradingview_charts_controller.rb`
  - models: `TradingviewChart`, `TradingviewDrawing`,
    `TradingviewDrawingTemplate`
