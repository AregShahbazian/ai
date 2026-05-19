# Review: SuperChart persistence endpoints

PRD: [prd.md](./prd.md) (id: `sc-endpoints`)
Design: [design.md](./design.md)
Tasks: [tasks.md](./tasks.md)

## Round 1: initial implementation (2026-05-19)

### Files added

- Migrations:
  - `db/migrate/20260519154800_create_superchart_layouts.rb`
  - `db/migrate/20260519154801_create_superchart_drawings.rb`
  - `db/migrate/20260519154802_create_superchart_indicator_templates.rb`
  - `db/migrate/20260519154803_create_superchart_chart_layouts.rb`
  - `db/migrate/20260519154804_add_source_to_tradingview_drawing_templates.rb`
- Models:
  - `app/models/superchart_layout.rb`
  - `app/models/superchart_drawing.rb`
  - `app/models/superchart_indicator_template.rb`
  - `app/models/superchart_chart_layout.rb`
- Grape API:
  - `app/api/api_v3/superchart.rb`
- Entities:
  - `app/api/api_v3/entities/superchart_layout.rb`
  - `app/api/api_v3/entities/superchart_drawing.rb`
  - `app/api/api_v3/entities/superchart_indicator_template.rb`
  - `app/api/api_v3/entities/superchart_drawing_template.rb`
  - `app/api/api_v3/entities/superchart_chart_layout_meta.rb`
  - `app/api/api_v3/entities/superchart_chart_layout.rb`
- Factories + specs:
  - `spec/factories/superchart_*.rb` (4 files)
  - `spec/requests/api_v3/superchart_spec.rb`

### Files modified

- `app/api/api_v3/mount.rb` — `mount Superchart` added next to `Tradingview`.
- `app/api/api_v3/tradingview.rb` — every `tradingview_drawing_templates`
  query scoped by `source: "tv"`; POST sets `source: "tv"` explicitly.
- `app/models/account.rb` — four superchart associations added.
- `app/models/tradingview_drawing_template.rb` — uniqueness scope changed
  from `[:account_id, :tool, :version]` → `[:account_id, :source, :tool]`.

### Static checks (already passed locally)

1. ✅ `ruby -c` clean across all 20 new/modified files.
2. ✅ No `expectedRevision` literal anywhere in `superchart.rb` (would have
   silently always-mismatched after ParamBuilder underscoring).
3. ✅ No `t.json` in superchart migrations — opaque blobs are `t.text`.
4. ✅ No explicit `as:` in superchart entities — `BaseEntity` auto-camelizes.
5. ✅ `source: "tv"` appears in every TV drawing-template query (7 spots).

### Pre-deploy verification (staging)

Run before pushing the branch to staging:

1. CI passes: `bundle exec rspec spec/requests/api_v3/superchart_spec.rb`
   and `bundle exec rspec spec/api/api_v3/tradingview_spec.rb` (if present).
2. Route table includes the new paths:
   `bundle exec rails routes | grep superchart` lists 21 routes
   (3 layout + 3 drawings + 5 indicator_templates + 5 drawing_templates +
   5 chart_layouts).

### Staging smoke (manual curl)

With a valid staging JWT in `$T` and `BASE=https://staging.altrady.com/api/v3`:

1. `GET /superchart/layout` → 404 for a fresh account.
2. `PATCH /superchart/layout` with `{state: "{\"foo\":1}", expectedRevision: 0}` → 200 `{revision: 1}`.
3. Repeat (2) with `expectedRevision: 0` → 409 `{remoteState: "{\"foo\":1}", remoteRevision: 1}`.
4. `GET /superchart/layout` → 200 echoes the state string verbatim (no inner-key mangling).
5. `PATCH /superchart/drawings/BINA_USDT_BTC` with `{overlays: "[]"}` (no `expectedRevision`) → 200, repeated → 200 (last-write-wins).
6. Same call with `expectedRevision: 0` after revision is already 1 → 409.
7. `POST /superchart/indicator_templates` with `{indicator: "RSI", name: "My RSI", body: "{}"}` → 201 includes the row.
8. `GET /superchart/indicator_templates?indicator=RSI` → list contains the new row; without `?indicator=` lists all.
9. `POST /superchart/drawing_templates` → row in DB has `source="sc"`.
10. `GET /superchart/drawing_templates` does **not** return any pre-existing `source="tv"` rows.
11. `POST /superchart/chart_layouts` then `GET /superchart/chart_layouts` → metas only (no `state` key); `GET /superchart/chart_layouts/:id` → full body with `state`.

### TV regression check on staging

1. Existing `GET /api/v3/tradingview/drawing_templates?tool=trendline&version=2.1`
   for an account with stored TV templates still returns the same rows
   (the new `source: "tv"` scope is a no-op for pre-existing data because
   the migration backfills via column default).

### Trading Terminal context test cases

Not applicable here — these endpoints are exercised by the desktop
`storage-adapter.js` swap, which happens in the desktop repo. Trading
Terminal regression checks belong with that PR.

### Frontend integration step (separate branch in `crypto_base_scanner_desktop`)

1. Swap `LocalStorageAdapter` → HTTP adapter in
   `super-chart/storage-adapter.js`.
2. Adapter must `JSON.stringify` every blob (`state`/`overlays`/`body`/
   `template`) before sending and `JSON.parse` on receive.
3. Smoke flow: open chart → add indicator (autosave layout) → draw
   trendline (autosave drawing) → save named layout → save indicator
   template → save drawing template → reload → all five hydrate.
