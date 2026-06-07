---
id: phase-6-import-export
title: Import / Export Tracks — design
status: draft
branch: feature/p6-import-export
---

## Build-vs-buy verdict (read first)

We write **the canonical model, the wiring, and the UI**. Everything mechanical is
off-the-shelf or ported, not invented:

| Concern | Decision |
|---|---|
| GPX parse | **Port `track/`'s `parseGpx`** (`package:xml`, namespace-agnostic, multi-`<trk>`, color from both `gpx_style` + `topografix`, ele/time, synthetic-time fill). **Re-verify** against the two real samples (PRD note). |
| GPX write | Small `GpxWriter` we own (build a GPX 1.1 string). No lib needed. |
| Persistence | **Drift** (SQLite) — one API for **web (WASM) + mobile**. |
| Reactive list | **Drift `.watch()` stream** — the list updates itself as rows land. No hand-rolled `ChangeNotifier` for the list. |
| File picker | **`file_picker`** (`allowMultiple`, `allowedExtensions: ['gpx']`). |
| XML | **`package:xml`** (already what `track/` used). |
| Export delivery | **`share_plus`** on mobile (share sheet) + browser-download on web via `package:web` — behind a conditional-import `TrackExporter` (mirrors the existing `console_bridge_io/web`, `log/console_io/web` split). |
| HUD button | **Phase 4 `HudButton`** (reuse). |
| Navigation | **Phase 5 `go_router`** `push` (reuse). |
| Both-ways wiring | **Phase 3 `InteractionController`** (reuse). |

Nothing here re-implements a parser library, a DB, a router, or a state container.

## Module layout

```
lib/core/db/
  app_database.dart          # Drift DB: Tracks + TrackPoints tables, codegen
lib/features/tracks/
  gpx_parser.dart            # ported parseGpx → List<ParsedTrack>
  gpx_writer.dart            # ParsedTrack/Track → GPX 1.1 string
  track_model.dart           # canonical domain model + stats (ported from track/)
  tracks_repository.dart     # Drift ↔ domain; import, watchSummaries, getTrack, export read
  import_controller.dart     # app-global; runs picker→parse→store; exposes `pending` for the badge
  track_exporter.dart        # conditional import → _io (share_plus) / _web (download)
  track_exporter_io.dart
  track_exporter_web.dart
  tracks_screen.dart         # list page (AppBar import action + reactive list)
  track_detail_screen.dart   # full-stats page (/tracks/:id)
  track_list_tile.dart       # one summary row (tap body, ⋮ Export)
```

DB lives in `core/` (app infrastructure); everything track-specific in
`features/tracks/`.

## Canonical model (one model, both formats)

Parser output (pure, no persistence):

```dart
class ParsedPoint { double lat, lon; double? ele; DateTime? time; }
class ParsedTrack { String name; String? desc; String color; List<ParsedPoint> points; }
```

Both Gaia and MyTracks parse into this — format differences (time precision,
`gpx_style` vs `topografix:color`, CDATA) are flattened in the parser. Nothing
format-specific survives past parse.

Persisted (Drift), two tables:

- **`tracks`** — `id`, `name`, `desc?`, `color`, `startedAt`, `endedAt`, plus the
  **stats computed once at import** so the list/detail never recompute:
  `distanceMeters`, `pointCount`, `elevationGain`, `elevationLoss`, `elevMin?`,
  `elevMax?`, `maxSpeedMs`, `importedAt`. (avg speed = distance/duration, derived.)
- **`track_points`** — `id`, `trackId` (FK), `seq`, `lat`, `lon`, `ele?`, `time`.
  Stored at **full resolution** (re-export + Phase 7 render need every point).

Reads are split by weight:

- **List** → `watchSummaries()` returns a Drift **stream of `tracks` rows only**
  (no points) — cheap, even with 15 × 37k-point tracks present.
- **Detail / export** → `getTrack(id)` loads the row **plus its points** (the one
  place we pay for points; first time it's needed).

## Import flow (non-blocking)

Triggered by `tracks.import.start` (from the header icon, or a bridge dispatch):

1. `file_picker` → user picks one+ `.gpx` (`allowMultiple`, `allowedExtensions`).
2. **Validate after pick** (Android may ignore the filter): extension `.gpx` +
   parses to ≥1 track; else record a friendly error, skip the file.
3. For each file: read string → `parseGpx` → `N` `ParsedTrack`s. **Bump
   `ImportController.pending` by N** → badge shows it.
4. For each parsed track: `repository.import(track)` — a **batched Drift
   transaction** (one commit for all its points). **Decrement `pending`.** The
   Drift list stream emits → the row **appears in the list** immediately.
5. **No dedup** — always insert a new row (PRD). **Name = parsed `<name>`
   verbatim** (trimmed of pretty-print whitespace only; CDATA already unwrapped by
   `innerText`).

`ImportController` is **app-global (singleton)** so import continues if the user
navigates away mid-run, and so the badge state is one source of truth. It's a
`ChangeNotifier` exposing `int pending` (and a `lastError`); the header badge and
error SnackBars observe it.

**Concurrency / responsiveness:** await between files/tracks so the UI stays
live; for the known data (≤3.6 MB, 37k pts) main-isolate parse is fine
(`track/` did it synchronously without jank — PRD Performance). **Optional
hardening** if a file ever stutters: move `parseGpx` to a `compute()` isolate.
Not built unless needed.

## Export flow

Triggered by `tracks.export` `{id}` (from the ⋮ menu, or a bridge dispatch):

1. `repository.getTrack(id)` (row + points).
2. `GpxWriter` builds a **GPX 1.1** string: one `<trk>` with `<name>`, `<desc>`,
   a color `<extensions>` block, and `<trkpt lat lon><ele><time>` for each point.
   (Round-trips name/desc/color/points — PRD.)
3. `TrackExporter.export(filename, gpxString)`:
   - **mobile** (`_io`) → write a temp file, `share_plus` share sheet.
   - **web** (`_web`) → `package:web` Blob + anchor click → browser download.

No backend — generation is fully client-side (PRD).

Single-track only for now; **batch select / export deferred** (PRD).

## Navigation & HUD entry

- New route `GoRoute('/tracks')` → `TracksScreen`; `GoRoute('/tracks/:id')` →
  `TrackDetailScreen` (reads `state.pathParameters['id']`). Both `push` over the
  live map (Phase 5 pillar — map stays alive beneath).
- Add `'tracks': '/tracks'` to `router.dart`'s `_screenPaths` so
  `nav.screen.open {screen:'tracks'}` works too.
- **HUD:** add a **Tracks `HudButton`** to the bottom-right column in
  `map_screen.dart`, **between the follow-me FAB and the settings cog**
  (top→bottom: `LocationFab`, **Tracks**, settings). Icon: `Icons.route`
  (proposal). The web attribution clearance stays on the **column bottom** (cog
  is still lowest) — unchanged. `onPressed` → `dispatch(hud.tracks.tap)` (no
  inline push — interaction rule).

## Interaction taxonomy additions (Phase 3, both ways)

Add to `interaction_ids.dart` + `all`:

| id | payload | handler |
|---|---|---|
| `hud.tracks.tap` | — | `router.push('/tracks')` |
| `tracks.import.start` | — | `ImportController.run()` (picker→parse→store) |
| `tracks.open` | `{id}` | `router.push('/tracks/$id')` |
| `tracks.export` | `{id}` | `repository.getTrack` → `GpxWriter` → `TrackExporter` |

Wiring (`registerTracksInteractions(...)`, called in `main`, app-lifetime, like
`registerNavInteractions`): `hud.tracks.tap` records and pushes; the others run
their service. All four go through `InteractionController.dispatch`, so the whole
feature is **drivable from the bridges** (`orion.dispatch('tracks.export',{id})`,
etc.) — both-ways per the README interactions rule and `[[interaction-controller-convention]]`.

UI dispatch sites: header import `IconButton` → `tracks.import.start`; row body
tap → `tracks.open {id}`; ⋮ `PopupMenuButton` "Export" → `tracks.export {id}`;
HUD button → `hud.tracks.tap`. No inline handlers bypass the bus.

**Automation limit (noted, like Phase 5's web-back note):** the OS file picker is
user-gated — `tracks.import.start` opens it but can't be fully driven headlessly.
Export/open/list are fully drivable.

## UI

- **`TracksScreen`** — `Scaffold` + `AppBar(title: 'Tracks', actions: [import])`.
  The import action is an `IconButton(Icons.file_upload)` wrapped in a Material
  **`Badge`** showing `ImportController.pending` (hidden at 0) via an
  `AnimatedBuilder` on the controller. Body: `StreamBuilder` over
  `watchSummaries()` → `ListView` of `TrackListTile` (empty-state when none).
- **`TrackListTile`** — summary row: color swatch, **name**, **start date**,
  **distance**, **duration**. Whole body tappable → `tracks.open {id}`. Trailing
  `PopupMenuButton` (`Icons.more_vert`) with one item **"Export"** →
  `tracks.export {id}`. (Identical web/mobile — Flutter-rendered, anchored to ⋮.)
- **`TrackDetailScreen`** — `AppBar(title: name)` + back via `nav.screen.close`
  (Phase 5 pattern). Body: **full stats** (distance, duration, avg/max speed,
  elevation gain/loss, min/max elevation, point count, start/end time). Loads
  `getTrack(id)` once on open (first time points are needed). No map yet (Phase 7).

## Stats

Ported from `track/`'s `Track` getters (haversine distance, duration from
first→last time, avg speed = distance/duration, elevation gain/loss, formatters).
Add **max speed** (max of per-segment `dist/Δt`). All computed **once at import**
and stored on the `tracks` row; detail reads stored values (no recompute, no
needing points for the numbers — points load only for export / future render).

## Dependencies to add

- `drift`, `drift_flutter`, `sqlite3_flutter_libs`, `path_provider` (native DB);
  **web**: `drift`'s WASM path — drop `sqlite3.wasm` + `drift_worker.js` in
  `web/` (one-time setup, documented in Drift's web guide).
- `file_picker`, `xml`, `share_plus`.
- dev: `drift_dev`, `build_runner` (codegen).

## Re-verify `track/` parser (acceptance-relevant)

PRD flags `track/`'s import correctness as unverified. Verify the ported parser
against the real samples:

- `~/Downloads/temp/mindanao.gpx` (Gaia) → **15 tracks**, **37,775** points total.
- one `2022-12-mindanao/MyTracks_...27_...gpx` → **1 track, 3,403 points**.
- Both share the same first point (`11.919155, 121.976275`, ele `67.7`,
  `2022-12-27T01:22:50Z`) — sanity that name/color/ele/time parse identically
  across the two formats.

## Acceptance verification

1. Import `mindanao.gpx` → **15 entries** appear; re-import → **30** (no dedup).
2. Import the MyTracks folder (multi-select 15 files) → 15 entries; names verbatim.
3. Badge counts tracks-in-flight, fills as files parse, hits 0 and hides.
4. App stays responsive during import of the 3.6 MB file (no freeze).
5. Tap a row → detail shows plausible stats; ⋮ → Export → GPX downloads (web) /
   share sheet (mobile); the exported file re-imports to an equivalent track
   (round-trip name/desc/color/points).
6. Tracks HUD button opens `/tracks`; map still alive on return (Phase 5 pillar).
7. `orion.dispatch('tracks.export',{id})` from the web console exports — both-ways.

## Open questions carried to implementation

- Drift web setup specifics (wasm asset versions) — resolve during `pub add`.
- Export delivery on mobile: `share_plus` share sheet vs a save dialog — start
  with share sheet (simplest), revisit if a "save to Downloads" is wanted.
- Exact Tracks HUD icon (`Icons.route` proposed).
