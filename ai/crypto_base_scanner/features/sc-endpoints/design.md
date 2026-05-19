# Design: SuperChart persistence endpoints

PRD: [prd.md](./prd.md) (id: `sc-endpoints`)

## Framework-level facts (verified against the live code)

Three behaviors of the existing `ApiV3::Mount` shape every decision below:

1. **Incoming params are deep-underscored** by `ApiV3::ParamBuilder#build_params`
   (`params.deep_transform_keys!(&:underscore)`). Inside handlers all keys are
   snake_case: `params[:expected_revision]`, not `params[:expectedRevision]`.
   Nested Hash values are *also* underscored, which would silently corrupt SC's
   opaque blobs — see "Opaque blobs as JSON strings" below.

2. **`ApiV3::Entities::BaseEntity#expose` auto-camelizes** the JSON key
   (`options[:as] = field.to_s.camelize(:lower)`). Define entity fields in
   snake_case Ruby; output keys come out camelCase. Do **not** write
   `expose :saved_at, as: :savedAt` — that double-camelizes to `savedAt`
   correctly here but breaks the convention for readers.

3. **Auth is global.** `ApiV3::Mount.before { authenticate! }` runs for every
   request. Sub-API classes inherit `current_account` via
   `Helpers::AccountHelpers`. New endpoints get auth for free; the
   `use :auth` named param block is included only for the optional `token`
   query param + swagger.

4. **404 is rescued globally.** `rescue_from ActiveRecord::RecordNotFound`
   returns `{error: {code: 404, message: "Not found"}}`. Use `find` (which
   raises) for known-id lookups; manually `error!({}, 404)` only for "no row"
   GETs (layout / drawing).

## Mount

Single Grape file `app/api/api_v3/superchart.rb`, class `ApiV3::Superchart`.

Add `mount Superchart` to `app/api/api_v3/mount.rb` next to `mount Tradingview`.

Final URL prefix: `/api/v3/superchart/...`.

## Opaque blobs as JSON strings

`state`, `overlays`, `body`, `template` are SC-internal JSON whose keys must
round-trip verbatim. Because ParamBuilder underscores every Hash key passed
in the body, we cannot accept them as JSON objects. Two consequences:

- **Wire format:** the frontend `JSON.stringify(...)`s each blob before
  sending; the backend stores the string as-is; the response carries the
  same string back; the frontend `JSON.parse(...)`s on receive. This matches
  how TV stores `content` and `template` (`t.text`).
- **Param declarations** use `type: String` for these fields.

The PRD's "opaque JSON" wording is honored — the body is JSON-encoded, just
transmitted as a string field rather than a nested object.

## Models / tables

All new migrations `ActiveRecord::Migration[8.0]`.

### `superchart_layouts` — one row per account

```ruby
create_table :superchart_layouts do |t|
  t.references :account, null: false, foreign_key: true, index: { unique: true }
  t.text :state, size: :medium      # MEDIUMTEXT (16MB) — matches TV charts
  t.integer :revision, null: false, default: 0
  t.timestamps
end
```

### `superchart_drawings` — one row per (account, coinray_symbol)

```ruby
create_table :superchart_drawings do |t|
  t.references :account, null: false, foreign_key: true
  t.string :coinray_symbol, null: false
  t.text :overlays, size: :medium
  t.integer :revision, null: false, default: 0
  t.timestamps
end
add_index :superchart_drawings, [:account_id, :coinray_symbol], unique: true
```

### `superchart_indicator_templates`

```ruby
create_table :superchart_indicator_templates do |t|
  t.references :account, null: false, foreign_key: true
  t.string :indicator, null: false
  t.string :name, null: false
  t.text :body
  t.timestamps
end
add_index :superchart_indicator_templates, [:account_id, :indicator, :name], unique: true
```

### `superchart_chart_layouts` — named full snapshots

```ruby
create_table :superchart_chart_layouts do |t|
  t.references :account, null: false, foreign_key: true
  t.string :name, null: false
  t.text :state, size: :medium
  t.timestamps
end
add_index :superchart_chart_layouts, [:account_id, :name]
```

### `tradingview_drawing_templates` — add `source` column

```ruby
add_column :tradingview_drawing_templates, :source, :string, null: false, default: "tv"
add_index  :tradingview_drawing_templates, [:account_id, :source, :tool, :name],
           name: "lookup_source"   # non-unique — pre-existing TV rows may
                                   # have same (tool, name) across versions.
                                   # App-layer validation enforces uniqueness.
remove_index :tradingview_drawing_templates, name: "lookup"
```

Existing rows backfill to `source: "tv"` via default. TV endpoints scope
every query by `source: "tv"`; SC endpoints write/read `source: "sc"`.

## Grape endpoints

File: `app/api/api_v3/superchart.rb`. Skeleton (final code matches this
literally; deviations introduce risk):

```ruby
module ApiV3
  class Superchart < Base
    helpers Helpers::NamedParams

    # --- Layout (one per user) ---

    desc_endpoint "Get current SuperChart layout", %w(SuperChart)
    params do
      use :auth
    end
    get "/superchart/layout" do
      layout = current_account.superchart_layout
      error!({ error: "not_found" }, 404) unless layout
      present layout, with: Entities::SuperchartLayout
    end

    desc_endpoint "Save current SuperChart layout", %w(SuperChart)
    params do
      use :auth
      requires :state,             type: String
      optional :expected_revision, type: Integer
    end
    patch "/superchart/layout" do
      layout = current_account.superchart_layout ||
               current_account.build_superchart_layout(revision: 0)

      if params[:expected_revision].present? && params[:expected_revision] != layout.revision
        error!({
          remoteState:    layout.state,
          remoteRevision: layout.revision,
        }, 409)
      end

      layout.update!(state: params[:state], revision: layout.revision + 1)
      present({ revision: layout.revision })
    end

    desc_endpoint "Delete SuperChart layout", %w(SuperChart)
    params do
      use :auth
    end
    delete "/superchart/layout" do
      current_account.superchart_layout&.destroy
      status 204
      ""
    end

    # --- Drawings (one per (account, coinray_symbol)) ---

    desc_endpoint "Get drawings for a market", %w(SuperChart)
    params do
      use :auth
      requires :coinray_symbol, type: String
    end
    get "/superchart/drawings/:coinray_symbol" do
      drawing = current_account.superchart_drawings
                               .find_by(coinray_symbol: params[:coinray_symbol])
      error!({ error: "not_found" }, 404) unless drawing
      present drawing, with: Entities::SuperchartDrawing
    end

    desc_endpoint "Save drawings for a market", %w(SuperChart)
    params do
      use :auth
      requires :coinray_symbol,    type: String
      requires :overlays,          type: String
      optional :expected_revision, type: Integer
    end
    patch "/superchart/drawings/:coinray_symbol" do
      drawing = current_account.superchart_drawings
                               .find_or_initialize_by(coinray_symbol: params[:coinray_symbol])

      if params[:expected_revision].present? && params[:expected_revision] != drawing.revision
        error!({
          remoteOverlays: drawing.overlays,
          remoteRevision: drawing.revision,
        }, 409)
      end

      drawing.update!(overlays: params[:overlays], revision: drawing.revision + 1)
      present({ revision: drawing.revision })
    end

    desc_endpoint "Delete drawings for a market", %w(SuperChart)
    params do
      use :auth
      requires :coinray_symbol, type: String
    end
    delete "/superchart/drawings/:coinray_symbol" do
      current_account.superchart_drawings
                     .where(coinray_symbol: params[:coinray_symbol])
                     .delete_all
      status 204
      ""
    end

    # --- Indicator templates ---

    desc_endpoint "List indicator templates", %w(SuperChart)
    params do
      use :auth
      optional :indicator, type: String
    end
    get "/superchart/indicator_templates" do
      scope = current_account.superchart_indicator_templates
      scope = scope.where(indicator: params[:indicator]) if params[:indicator].present?
      present scope, with: Entities::SuperchartIndicatorTemplate
    end

    desc_endpoint "Get indicator template", %w(SuperChart)
    params do
      use :auth
      requires :id, type: Integer
    end
    get "/superchart/indicator_templates/:id" do
      tpl = current_account.superchart_indicator_templates.find(params[:id])
      present tpl, with: Entities::SuperchartIndicatorTemplate
    end

    desc_endpoint "Create indicator template", %w(SuperChart)
    params do
      use :auth
      requires :indicator, type: String
      requires :name,      type: String
      requires :body,      type: String
    end
    post "/superchart/indicator_templates" do
      tpl = current_account.superchart_indicator_templates.create!(
        indicator: params[:indicator], name: params[:name], body: params[:body],
      )
      present tpl, with: Entities::SuperchartIndicatorTemplate
    end

    desc_endpoint "Update indicator template", %w(SuperChart)
    params do
      use :auth
      requires :id,   type: Integer
      optional :name, type: String
      optional :body, type: String
    end
    patch "/superchart/indicator_templates/:id" do
      tpl = current_account.superchart_indicator_templates.find(params[:id])
      updates = params.slice(:name, :body).to_h.compact
      tpl.update!(updates) if updates.any?
      present tpl, with: Entities::SuperchartIndicatorTemplate
    end

    desc_endpoint "Delete indicator template", %w(SuperChart)
    params do
      use :auth
      requires :id, type: Integer
    end
    delete "/superchart/indicator_templates/:id" do
      current_account.superchart_indicator_templates.find(params[:id]).destroy
      status 204
      ""
    end

    # --- Drawing templates (reuse TradingviewDrawingTemplate, source='sc') ---

    desc_endpoint "List drawing templates", %w(SuperChart)
    params do
      use :auth
      optional :tool, type: String
    end
    get "/superchart/drawing_templates" do
      scope = current_account.tradingview_drawing_templates.where(source: "sc")
      scope = scope.where(tool: params[:tool]) if params[:tool].present?
      present scope, with: Entities::SuperchartDrawingTemplate
    end

    desc_endpoint "Get drawing template", %w(SuperChart)
    params do
      use :auth
      requires :id, type: Integer
    end
    get "/superchart/drawing_templates/:id" do
      tpl = current_account.tradingview_drawing_templates.where(source: "sc").find(params[:id])
      present tpl, with: Entities::SuperchartDrawingTemplate
    end

    desc_endpoint "Create drawing template", %w(SuperChart)
    params do
      use :auth
      requires :tool,     type: String
      requires :name,     type: String
      requires :template, type: String
    end
    post "/superchart/drawing_templates" do
      tpl = current_account.tradingview_drawing_templates.create!(
        source: "sc", tool: params[:tool], name: params[:name], template: params[:template],
      )
      present tpl, with: Entities::SuperchartDrawingTemplate
    end

    desc_endpoint "Update drawing template", %w(SuperChart)
    params do
      use :auth
      requires :id,       type: Integer
      optional :name,     type: String
      optional :template, type: String
    end
    patch "/superchart/drawing_templates/:id" do
      tpl     = current_account.tradingview_drawing_templates.where(source: "sc").find(params[:id])
      updates = params.slice(:name, :template).to_h.compact
      tpl.update!(updates) if updates.any?
      present tpl, with: Entities::SuperchartDrawingTemplate
    end

    desc_endpoint "Delete drawing template", %w(SuperChart)
    params do
      use :auth
      requires :id, type: Integer
    end
    delete "/superchart/drawing_templates/:id" do
      current_account.tradingview_drawing_templates.where(source: "sc").find(params[:id]).destroy
      status 204
      ""
    end

    # --- Named chart layouts ---

    desc_endpoint "List named chart layouts (metas only)", %w(SuperChart)
    params do
      use :auth
    end
    get "/superchart/chart_layouts" do
      present current_account.superchart_chart_layouts.order(updated_at: :desc),
              with: Entities::SuperchartChartLayoutMeta
    end

    desc_endpoint "Get a named chart layout (full body)", %w(SuperChart)
    params do
      use :auth
      requires :id, type: Integer
    end
    get "/superchart/chart_layouts/:id" do
      layout = current_account.superchart_chart_layouts.find(params[:id])
      present layout, with: Entities::SuperchartChartLayout
    end

    desc_endpoint "Create a named chart layout", %w(SuperChart)
    params do
      use :auth
      requires :name,  type: String
      requires :state, type: String
    end
    post "/superchart/chart_layouts" do
      layout = current_account.superchart_chart_layouts.create!(
        name: params[:name], state: params[:state],
      )
      present layout, with: Entities::SuperchartChartLayoutMeta
    end

    desc_endpoint "Update a named chart layout", %w(SuperChart)
    params do
      use :auth
      requires :id,    type: Integer
      optional :name,  type: String
      optional :state, type: String
    end
    patch "/superchart/chart_layouts/:id" do
      layout  = current_account.superchart_chart_layouts.find(params[:id])
      updates = params.slice(:name, :state).to_h.compact
      layout.update!(updates) if updates.any?
      present layout, with: Entities::SuperchartChartLayoutMeta
    end

    desc_endpoint "Delete a named chart layout", %w(SuperChart)
    params do
      use :auth
      requires :id, type: Integer
    end
    delete "/superchart/chart_layouts/:id" do
      current_account.superchart_chart_layouts.find(params[:id]).destroy
      status 204
      ""
    end
  end
end
```

Key shape decisions:

- **404 body:** `{error: "not_found"}` for GETs that resolve to nil
  (`/layout`, `/drawings/:coinray_symbol`). For `find(:id)` lookups, the
  global `rescue_from RecordNotFound` returns the standard
  `{error: {code: 404, message: "Not found"}}`. Frontend treats any 4xx as
  "no row" — the body shape difference is acceptable.
- **204 bodies:** Grape needs an explicit `""` return after `status 204` so
  it doesn't try to render `nil` as JSON.
- **`expected_revision` for first-ever PATCH:** layout starts at `revision:
  0` whether persisted or freshly built. Frontend sends
  `expected_revision: 0` for the first save.
- **Optimistic locking:** app-level compare-and-set. The unique index on
  `account_id` (layout) and `(account_id, coinray_symbol)` (drawings)
  serializes concurrent inserts. Concurrent racing PATCHes that both pass
  the revision check can clobber each other by one revision — acceptable
  for our load; SC re-detects on the next save. If we observe drift we'd
  wrap the read+update in `with_lock`.

## Entities

All under `app/api/api_v3/entities/`. `BaseEntity#expose` auto-camelizes:
declare fields in snake_case Ruby.

**Root wrappers on list-bearing entities.** Altrady's convention: every API
response is a JSON object, never a bare array. The three entities serving
list endpoints declare a `root` so Grape wraps collections (and single
records) under a keyed envelope. `SuperchartLayout` and `SuperchartDrawing`
are single-record-only and stay un-rooted (already objects).

```ruby
# superchart_layout.rb
class SuperchartLayout < BaseEntity
  expose :state
  expose :revision
end

# superchart_drawing.rb
class SuperchartDrawing < BaseEntity
  expose :overlays
  expose :revision
end

# superchart_indicator_template.rb
class SuperchartIndicatorTemplate < BaseEntity
  root "superchart_indicator_templates", "superchart_indicator_template"
  expose :id
  expose :indicator
  expose :name
  expose :body
end

# superchart_drawing_template.rb
class SuperchartDrawingTemplate < BaseEntity
  root "superchart_drawing_templates", "superchart_drawing_template"
  expose :id
  expose :tool
  expose :name
  expose :template
end

# superchart_chart_layout_meta.rb
class SuperchartChartLayoutMeta < BaseEntity
  root "superchart_chart_layouts", "superchart_chart_layout"
  expose :id
  expose :name
  expose :saved_at do |o, _| o.updated_at.to_i end   # → "savedAt"
end

# superchart_chart_layout.rb (inherits + adds state)
class SuperchartChartLayout < SuperchartChartLayoutMeta
  expose :state
end
```

## Account associations

In `app/models/account.rb`:

```ruby
has_one  :superchart_layout, dependent: :destroy
has_many :superchart_drawings, dependent: :delete_all
has_many :superchart_indicator_templates, dependent: :delete_all
has_many :superchart_chart_layouts, dependent: :delete_all
```

`tradingview_drawing_templates` association already exists.

## Model files

```ruby
class SuperchartLayout < ApplicationRecord
  belongs_to :account
  validates :revision, presence: true
end

class SuperchartDrawing < ApplicationRecord
  belongs_to :account
  validates :coinray_symbol, presence: true
end

class SuperchartIndicatorTemplate < ApplicationRecord
  belongs_to :account
  validates :indicator, :name, presence: true
  validates :name, uniqueness: { scope: [:account_id, :indicator] }
end

class SuperchartChartLayout < ApplicationRecord
  belongs_to :account
  validates :name, presence: true
end
```

And in `app/models/tradingview_drawing_template.rb` — replace the existing
uniqueness scope:

```ruby
class TradingviewDrawingTemplate < ApplicationRecord
  belongs_to :account
  validates :name, presence: true
  validates :name, uniqueness: { scope: [:account_id, :source, :tool] }
end
```

## TV endpoint scoping fix

`app/api/api_v3/tradingview.rb` — every `current_account.tradingview_drawing_templates`
query gets `.where(source: "tv")`, and the `create`/`build` path sets
`source: "tv"` explicitly (don't rely on the column default in case it's
removed later).

## Open questions

1. **`state` size ceiling.** MySQL MEDIUMTEXT is 16MB — far above any
   realistic chart layout. No app-level clamp lives in `ApiV3::Mount`;
   confirm none in Rack/Puma config.
2. **`savedAt` casing.** Frontend expects camelCase; `BaseEntity` produces
   it automatically. No special handling — `expose :saved_at` → `savedAt`.
