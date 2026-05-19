# Tasks: SuperChart persistence endpoints

PRD: [prd.md](./prd.md) (id: `sc-endpoints`)
Design: [design.md](./design.md)

**Deploy-without-local-test workflow.** No local Rails env is available;
verification happens on staging. Every task below includes a static check
that can be run without booting the app, plus a staging smoke step.

Implement in order.

## 1. Migrations

**Files (new):**
- `db/migrate/<ts>_create_superchart_layouts.rb`
- `db/migrate/<ts>_create_superchart_drawings.rb`
- `db/migrate/<ts>_create_superchart_indicator_templates.rb`
- `db/migrate/<ts>_create_superchart_chart_layouts.rb`
- `db/migrate/<ts>_add_source_to_tradingview_drawing_templates.rb`

Shapes match `design.md` exactly:

- Blob columns are `t.text :col, size: :medium` (MEDIUMTEXT, 16MB), **not**
  `t.json`. ParamBuilder would corrupt nested object keys; we store JSON
  strings.
- `superchart_layouts`: unique index on `account_id`.
- `superchart_drawings`: unique index on `[:account_id, :coinray_symbol]`.
- `superchart_indicator_templates`: unique index on
  `[:account_id, :indicator, :name]`.
- `superchart_chart_layouts`: non-unique index on `[:account_id, :name]`.
- `tradingview_drawing_templates`: add `source` (null:false, default:"tv"),
  drop index `"lookup"`, add unique index `"lookup_source"` on
  `[:account_id, :source, :tool, :name]`.
- All five migrations use `ActiveRecord::Migration[8.0]`.

**Static check:** open each migration and confirm the `change` block is
fully reversible (`add_column` / `add_index` / `remove_index` / `create_table`
all auto-reverse). No `up`/`down` needed.

**Staging:**
```bash
bundle exec rails db:migrate
```
Then `bundle exec rails db:rollback STEP=5 && bundle exec rails db:migrate`
to prove reversibility on a non-prod environment.

## 2. Models

**New files:**
- `app/models/superchart_layout.rb`
- `app/models/superchart_drawing.rb`
- `app/models/superchart_indicator_template.rb`
- `app/models/superchart_chart_layout.rb`

Bodies per `design.md`. Each: `belongs_to :account` + presence validations.

**Modify `app/models/tradingview_drawing_template.rb`:** replace
`validates_uniqueness_of :name, scope: [:account_id, :tool, :version]` with
`validates :name, uniqueness: { scope: [:account_id, :source, :tool] }`.

**Modify `app/models/account.rb`:** add the four `has_one`/`has_many`
associations from `design.md`.

**Static check:**
- Each new model has `belongs_to :account` (Rails 8 makes `belongs_to`
  required by default — no `optional: true` because we always have an
  account).
- `Account` doesn't already define `superchart_layout` (grep first).

## 3. Update TV endpoints to scope by `source: "tv"`

**File:** `app/api/api_v3/tradingview.rb`.

In every query against `current_account.tradingview_drawing_templates`
(lines 28, 42, 56, 58, 72), append `.where(source: "tv")`.

In the POST handler (~line 39), set `source: "tv"` on the built record
**before** save. Easiest: `build(permitted_params.merge(source: "tv"))`.

**Static check:** grep `tradingview_drawing_templates` in
`app/api/api_v3/tradingview.rb` and confirm every chain has
`.where(source: "tv")` (or sets `source: "tv"` on writes).

**Staging smoke:** with an account that already has TV drawing templates,
`GET /api/v3/tradingview/drawing_templates?tool=trendline&version=...`
returns the same rows as before the migration.

## 4. Entities

**New files** under `app/api/api_v3/entities/`:
- `superchart_layout.rb`
- `superchart_drawing.rb`
- `superchart_indicator_template.rb`
- `superchart_drawing_template.rb`
- `superchart_chart_layout_meta.rb`
- `superchart_chart_layout.rb`

Bodies per `design.md`. **Critical:** declare fields snake_case; `BaseEntity`
auto-camelizes. Do not write `as: :savedAt` — `expose :saved_at` already
serializes as `"savedAt"`.

The `SuperchartChartLayout` entity inherits from `SuperchartChartLayoutMeta`
and adds `expose :state`.

**Static check:** grep the new entity files for any explicit `as:` option —
should be empty.

## 5. Grape API class

**New file:** `app/api/api_v3/superchart.rb`.

Body per `design.md` — copy the skeleton literally. Key invariants:

- Every route has a `params do ... use :auth; ... end` block.
- Body params for opaque blobs are `type: String`.
- `params[:expected_revision]` (snake_case after ParamBuilder).
- Response hashes built manually (`present({revision: ...})`,
  `error!({remoteState: ..., remoteRevision: ...})`) use camelCase keys —
  these don't go through entity auto-camelization.
- DELETE handlers explicitly `status 204` and return `""`.

**Mount:** add `mount Superchart` to `app/api/api_v3/mount.rb`, placed next
to `mount Tradingview` (line 222).

**Static checks:**
- File loads with no syntax errors:
  `ruby -c app/api/api_v3/superchart.rb`
- All five `mount Superchart`-touched files (mount.rb, superchart.rb, and
  the four entities) parse:
  `find app/api/api_v3 -name '*.rb' -newer .git/HEAD -exec ruby -c {} \;`
- The route table includes the new paths:
  `bundle exec rails routes | grep superchart` should list 19 routes
  (1 layout × 3 verbs + 1 drawings × 3 + 1 chart_layouts × 5 + 1
  indicator_templates × 5 + 1 drawing_templates × 5 = 21 actually — recount:
  3 + 3 + 5 + 5 + 5 = 21).

## 6. Request specs

**File:** `spec/api/api_v3/superchart_spec.rb` (new).

Per-endpoint coverage:

- Auth: 401 with no token.
- Account scoping: account A cannot read/write account B's rows (use two
  accounts via factories).
- 404 paths: GET layout with no row; GET drawing with no row; GET/PATCH/
  DELETE template with bad id.
- 409 layout PATCH: second save with stale `expected_revision`; body
  contains `remoteState` (string) and `remoteRevision` (int).
- 409 drawing PATCH: same, only when `expected_revision` is sent. Omitting
  it succeeds (last-write-wins).
- Indicator templates `?indicator=` filter works; unfiltered list returns
  all rows for the user.
- Drawing templates `?tool=` filter works; never returns `source: "tv"`
  rows. Confirm by seeding both `tv` and `sc` rows for the same account.
- Named chart layouts list is metas-only — assert `state` key absent;
  detail endpoint includes `state`.
- All response keys are camelCase (`savedAt`, `remoteState`, etc.).

**Static check:** `ruby -c spec/api/api_v3/superchart_spec.rb` parses.

**Staging:**
```bash
bundle exec rspec spec/api/api_v3/superchart_spec.rb
```
(Run as part of CI on the branch before merge.)

## 7. Pre-deploy verification checklist

Before pushing to staging, manually walk through:

1. `grep -n expectedRevision app/api/api_v3/superchart.rb` — must return
   **nothing** (camelCase would silently always-mismatch).
2. `grep -n 't\.json' db/migrate/*superchart*` — must return **nothing**
   (must be `t.text … size: :medium`).
3. `grep -n 'as: :' app/api/api_v3/entities/superchart_*.rb` — must return
   **nothing** (`BaseEntity` auto-camelizes; `as:` would double-camelize).
4. `grep -rn 'source: "tv"' app/api/api_v3/tradingview.rb` — must appear in
   every query against `tradingview_drawing_templates` (5 spots).
5. `ruby -c` every new file (zero syntax errors).
6. `bundle exec rails routes | grep superchart` lists 21 routes.

## 8. Staging smoke (manual curl)

After deploy, run from a workstation with a staging JWT in `$T`:

```bash
BASE=https://staging.altrady.com/api/v3
JWT="Bearer $T"

# 1. Empty state
curl -i -H "Authorization: $JWT" "$BASE/superchart/layout"     # → 404
curl -i -H "Authorization: $JWT" "$BASE/superchart/chart_layouts"  # → 200 []

# 2. Layout round-trip
curl -i -H "Authorization: $JWT" -H 'Content-Type: application/json' \
  -X PATCH "$BASE/superchart/layout" \
  -d '{"state":"{\"foo\":1}","expectedRevision":0}'
# → 200 {"revision":1}
curl -i -H "Authorization: $JWT" "$BASE/superchart/layout"
# → 200 {"state":"{\"foo\":1}","revision":1}

# 3. Conflict
curl -i -H "Authorization: $JWT" -H 'Content-Type: application/json' \
  -X PATCH "$BASE/superchart/layout" \
  -d '{"state":"{\"foo\":2}","expectedRevision":0}'
# → 409 {"remoteState":"{\"foo\":1}","remoteRevision":1}

# 4. Drawings, indicator templates, drawing templates, named layouts —
# create + list + get + patch + delete each.
```

Sanity items to verify in responses:

- All keys are camelCase (`remoteState`, not `remote_state`).
- `state` / `overlays` / `body` / `template` come back as the exact string
  that was sent (round-trip preserved — no inner-key mangling).
- `savedAt` is a Unix timestamp (integer).

## 9. Frontend integration

Out of repo, tracked for the rollout:

- Swap `LocalStorageAdapter` for an HTTP adapter in
  `crypto_base_scanner_desktop/.../super-chart/storage-adapter.js`.
- Adapter must `JSON.stringify` every blob (`state`, `overlays`, `body`,
  `template`) before sending and `JSON.parse` on receive.
- Smoke test: open chart → add indicator (autosave layout) → draw trendline
  (autosave drawing) → save named layout → save indicator template → save
  drawing template → reload → all five hydrate.

## Out of scope (not in this branch)

- Server-side snapshot upload (TV's `/snapshot`).
- TV → SC migration of stored layouts.
- Admin / cross-user views.
