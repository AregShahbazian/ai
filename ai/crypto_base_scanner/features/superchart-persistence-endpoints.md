# Feature: SuperChart persistence endpoints

## Summary

The desktop app is migrating from TradingView to SuperChart (SC). SC's
chart persistence layer is currently wired against `localStorage` so we
can dogfood it. To ship, we need a set of backend endpoints that match
SC's `StorageAdapter` contract. Once these exist, the frontend will swap
the `LocalStorageAdapter` delegation in
`super-chart/storage-adapter.js` for an HTTP-backed adapter pointing at
these routes.

The frontend already enforces a TV-faithful split on top of SC's blob
model, so the backend mirrors that split rather than the single-blob
shape SC ships out of the box.

Routes follow Altrady's existing API conventions (`POST` create,
`GET` read, `PATCH` update, `DELETE` delete — no `PUT`).

## Persistence model

Five user-scoped namespaces, three of which back the live SC chart and
two of which back the templates UIs:

1. **Layout record** — *one row per user.* The "current working layout":
   indicators + panes + styles + preferences. Autosaved by SC as the user
   adds/removes indicators or changes settings. Same record is read by
   every chart instance the user has open. Optimistic-concurrency
   required (SC checks `expectedRevision` on save).

2. **Drawings record** — *one row per `(user, symbol)`.* Drawings live
   separate from layout, exactly like TV's `line_tools` storage. Switching
   markets swaps which drawings record loads. Last-write-wins is
   acceptable; a `revision` field still pays for itself if we later want
   to upgrade.

3. **Indicator templates** — *user-wide, many rows.* Named indicator
   configurations (e.g. "My RSI"). Scoped per indicator type (RSI / MACD /
   BOLL / …) so opening RSI's settings only lists RSI templates.

4. **Drawing templates** — *user-wide, many rows.* Named drawing styles
   per drawing tool (trendline, fib, ray, …).

5. **Named chart layouts** — *user-wide, many rows.* Full `ChartState`
   snapshots (layout + drawings) the user explicitly saves via SC's
   period-bar Layout button. Each row has a meta (name) and a body
   (applied when picked). New concept — TV didn't separate this from #1.

## Endpoints

### 1. Layout record

```
GET    /superchart/layout                  → 200 {state, revision} | 404
PATCH  /superchart/layout                  body: {state, expectedRevision}
                                           → 200 {revision}
                                           → 409 on revision mismatch (carry remote state + revision)
DELETE /superchart/layout                  → 204
```

- `state` is opaque JSON to the backend (frontend serialises a subset of
  SC's `ChartState`). Don't validate its inner shape.
- `revision` is a monotonically-increasing integer per user; bump on each
  successful write.
- 409 body shape: `{remoteState, remoteRevision}` so the frontend can run
  SC's merge-retry against the remote.

Replaces TV's `/api/v2/tradingview_charts/charts`.

### 2. Drawings record (per symbol)

```
GET    /superchart/drawings/:symbol        → 200 {overlays, revision} | 404
PATCH  /superchart/drawings/:symbol        body: {overlays, expectedRevision?}
                                           → 200 {revision}
DELETE /superchart/drawings/:symbol        → 204
```

- `:symbol` is the Coinray symbol string (`BINA_USDT_BTC`, etc.).
- `overlays` is an opaque JSON array.
- `expectedRevision` is optional; current frontend uses last-write-wins
  here, but accept and honor it if sent.

Replaces TV's `/api/v2/tradingview_charts/line_tools`.

### 3. Indicator templates

```
GET    /superchart/indicator_templates?indicator=…
                                           → 200 [{id, name, indicator, body}, …]
GET    /superchart/indicator_templates/:id → 200 {id, name, indicator, body} | 404
POST   /superchart/indicator_templates     body: {name, indicator, body}
                                           → 201 {id, name, indicator, body}
PATCH  /superchart/indicator_templates/:id body: any subset of {name, body}
                                           → 200 {id, name, indicator, body}
DELETE /superchart/indicator_templates/:id → 204
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
                                           → 200 [{id, tool, name, template}, …]
GET    /superchart/drawing_templates/:id   → 200 {id, tool, name, template} | 404
POST   /superchart/drawing_templates       body: {tool, name, template}
                                           → 201 {id, tool, name, template}
PATCH  /superchart/drawing_templates/:id   body: any subset of {name, template}
                                           → 200 {id, tool, name, template}
DELETE /superchart/drawing_templates/:id   → 204
```

- `tool` is the drawing tool name (`"trendLine"`, `"fibSegment"`, …).
- `template` is opaque overlay-properties JSON.

**Reuse the existing `tradingview_drawing_templates` table** if its row
shape (`tool`, `name`, `template`-JSON) is compatible — the SC format is
the same shape, just produced by a different consumer. Otherwise
version-tag and serve the same data via the new path.

### 5. Named chart layouts

```
GET    /superchart/chart_layouts           → 200 [{id, name, savedAt}, …]   (metas only)
GET    /superchart/chart_layouts/:id       → 200 {id, name, state}          (full body)
POST   /superchart/chart_layouts           body: {name, state}
                                           → 201 {id, name, savedAt}
PATCH  /superchart/chart_layouts/:id       body: any subset of {name, state}
                                           → 200 {id, name, savedAt}
DELETE /superchart/chart_layouts/:id       → 204
```

- `state` is opaque JSON — a full `ChartState` snapshot at save time
  (includes both layout + drawings).
- List endpoint returns metas only (no body) so the picker UI is cheap
  to populate.

New concept — no TV equivalent.

## Auth / scope

All routes are user-scoped via the standard Altrady auth. Server enforces
"can only read/write your own rows" on every endpoint. No admin views or
cross-user access required.

## Out of scope

- Server-side snapshot upload (TV had this; we explicitly decided to drop
  it — SC screenshots stay local).
- Quiz persistence (already covered by `QuizStorageAdapter` on the
  desktop side, talks to existing quiz endpoints).
- Migration of TV-format persisted state into SC format. We're starting
  clean — existing TV chart layouts won't follow users into SC.

## References

- Live frontend adapter:
  `crypto_base_scanner_desktop/src/containers/trade/trading-terminal/widgets/super-chart/storage-adapter.js`
- Endpoint spec (frontend's source of truth, mirrors this doc):
  `crypto_base_scanner_desktop/ai/superchart-integration/phase-6/sc-endpoints.md`
- TV endpoints being replaced:
  `crypto_base_scanner_desktop/ai/superchart-integration/phase-6/tv-endpoints.md`
- SC storage contract (upstream):
  `Superchart/src/lib/types/storage.ts`
