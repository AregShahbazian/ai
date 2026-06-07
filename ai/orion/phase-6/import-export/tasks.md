---
id: phase-6-import-export
title: Import / Export Tracks — tasks
status: draft
branch: feature/p6-import-export
---

Ordered, each independently verifiable. Reuse over reinvent: port `track/`'s
parser, stand up Drift, wire through the existing `InteractionController` /
`go_router` / `HudButton`. See `design.md`.

## 1. Dependencies
- [ ] `flutter pub add drift drift_flutter sqlite3_flutter_libs path_provider
      file_picker xml share_plus` and `dev:drift_dev build_runner`.
- [ ] Drift **web** setup: add `sqlite3.wasm` + `drift_worker.js` to `web/`
      (Drift web guide). `flutter analyze` clean.

## 2. Drift database
- [ ] `lib/core/db/app_database.dart`: Drift DB with `Tracks` (id, name, desc?,
      color, startedAt, endedAt, distanceMeters, pointCount, elevationGain,
      elevationLoss, elevMin?, elevMax?, maxSpeedMs, importedAt) and
      `TrackPoints` (id, trackId FK, seq, lat, lon, ele?, time) tables.
- [ ] `build_runner` codegen; opens on web + native.

## 3. Canonical model + ported parser
- [ ] `track_model.dart`: `ParsedPoint`/`ParsedTrack` + domain `Track` with stats
      (port `track/`'s haversine distance, duration, avg speed, elevation
      gain/loss, formatters; **add max speed**).
- [ ] `gpx_parser.dart`: port `parseGpx` (namespace-agnostic, multi-`<trk>`,
      color from `gpx_style` **and** `topografix:color`, ele/time, synthetic-time
      fill). Capture `<desc>`. Name = `<name>` verbatim (trim whitespace only).
- [ ] **Re-verify** against samples: `mindanao.gpx` → 15 tracks / 37,775 pts; a
      MyTracks file → 1 track / 3,403 pts; identical first point across both.

## 4. Repository
- [ ] `tracks_repository.dart`: `import(ParsedTrack)` — compute+store stats, then
      **batched transaction** insert of points; returns id. `watchSummaries()`
      → Drift stream of rows (no points). `getTrack(id)` → row + points.
- [ ] No dedup — every import inserts a new row.

## 5. Import controller (badge state)
- [ ] `import_controller.dart`: app-global `ChangeNotifier`; `run()` =
      picker → per-file parse (bump `pending` by track count) → per-track
      `repository.import` (decrement `pending`). Post-pick validation; `lastError`
      on bad file. Non-blocking (awaits between items; survives navigation away).

## 6. Exporter
- [ ] `gpx_writer.dart`: `Track` → GPX 1.1 string (one `<trk>`, name/desc/color
      extensions, `<trkpt>`/`<ele>`/`<time>`). Round-trips.
- [ ] `track_exporter.dart` (+ `_io` share_plus / `_web` package:web download)
      via conditional import.

## 7. Interaction taxonomy (Phase 3, both ways)
- [ ] Add `hud.tracks.tap`, `tracks.import.start`, `tracks.open` (`{id}`),
      `tracks.export` (`{id}`) to `interaction_ids.dart` + `all`, with doc comments.
- [ ] `registerTracksInteractions(...)` in `main` (app-lifetime): `goNamed('tracks')`,
      run import, `goNamed('trackDetail', pathParameters:{'id':id})`, export. All
      via `dispatch` — drivable from the bridges. (Trigger ids record by default;
      no `record:false` — that's only for `nav.screen.*`.)

## 8. Routes + HUD entry
- [ ] `router.dart`: add `tracks` (name `'tracks'`) and its child `:id` (name
      `'trackDetail'`) as **nested children of `/`** → `TracksScreen` /
      `TrackDetailScreen`. No `_screenPaths` (removed; `goNamed` resolves by name,
      so `nav.screen.open {screen:'tracks'}` works for free).
- [ ] `map_screen.dart`: add a Tracks `HudButton` (`Icons.route`) in the
      bottom-right column **between the follow-me FAB and the settings cog**;
      `onPressed` → `dispatch(hud.tracks.tap)`. Web attribution clearance stays on
      the column bottom (cog still lowest) — verify no ⓘ collision on web.

## 9. UI — list
- [ ] `tracks_screen.dart`: `Scaffold` + `AppBar(title:'Tracks', actions:[import])`.
      Import = `IconButton(Icons.file_upload)` in a Material `Badge` bound to
      `ImportController.pending` (hidden at 0). Body: `StreamBuilder(watchSummaries)`
      → `ListView` of `TrackListTile`; empty-state when none. Surface `lastError`
      via SnackBar.
- [ ] `track_list_tile.dart`: color swatch + name + start date + distance +
      duration; body tap → `tracks.open {id}`; trailing `PopupMenuButton`
      (`Icons.more_vert`) with one **"Export"** item → `tracks.export {id}`.

## 10. UI — detail
- [ ] `track_detail_screen.dart`: `AppBar(title:name)` + back → `nav.screen.close`.
      Loads `getTrack(id)` once; shows full stats (distance, duration, avg/max
      speed, elevation gain/loss, min/max elev, point count, start/end). No map.

## 11. Verify (acceptance gate) — manual
- [ ] Import `mindanao.gpx` → 15 entries; re-import → 30 (no dedup).
- [ ] Multi-select the 15 MyTracks files → 15 entries; names verbatim.
- [ ] Badge fills as files parse, counts down, hides at 0; app responsive during
      the 3.6 MB import.
- [ ] Row tap → detail stats plausible; ⋮ Export → download (web) / share sheet
      (mobile); exported GPX re-imports equivalently (round-trip).
- [ ] Tracks HUD button → `/tracks`; map alive on return (no second
      `onMapCreated`/`onStyleLoaded`).
- [ ] `orion.dispatch('tracks.export',{id})` from console works (both-ways).
- [ ] Web + Android.

## 12. Wrap up
- [ ] `flutter analyze` clean (`avoid_print` clean). `review.md` written.
- [ ] Update README Phase 6 status.

## Out of scope (do NOT do here)
- Folders / grouping; dedup; batch select/export — deferred (PRD + backlog).
- Rendering tracks on the map — Phase 7.
- Editing / deleting tracks (dropdown is Export-only for now).
- Waypoints / routes (`<wpt>`/`<rte>`) — tolerate/skip on import.
