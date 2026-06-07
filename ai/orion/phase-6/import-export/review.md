---
id: phase-6-import-export
title: Import / Export Tracks — review
status: implemented; pending device verification
branch: feature/p6-import-export
---

## Implementation summary (2026-06-07)

All tasks implemented on `feature/p6-import-export`. `flutter analyze` clean;
existing test suite (8 tests) green; **web build succeeds**; GPX parser
**re-verified against the real samples**.

### What landed
- **Drift DB** (`lib/core/db/app_database.dart` + generated `.g.dart`):
  `Tracks` (stats stored at import) + `TrackPoints` (full-res, `seq`-ordered),
  cross-platform via `drift_flutter` (native file + web WASM). Web assets
  `web/sqlite3.wasm` + `web/drift_worker.js` added (drift 2.33.0-matched).
- **Canonical model + parser** (`track_model.dart`, `gpx_parser.dart`): one
  `ParsedTrack`/`ParsedPoint` shape for both formats; `TrackStats.from` computes
  all aggregates in one pass; ported `track/`'s parser (multi-`<trk>`,
  namespace-agnostic color from `gpx_style` **and** `topografix:color`,
  `<desc>`, synthetic-time fill). Name verbatim.
- **Repository** (`tracks_repository.dart`): `import` (stats + batched
  transaction), `watchSummaries` (reactive stream, no points), `getTrack` /
  `getPoints` (points only for detail/export). No dedup.
- **Import controller** (`import_controller.dart`): app-global; picker →
  per-file parse → per-track store; `pending` drives the badge; post-pick
  validation; `lastError` for SnackBars; yields between tracks.
- **Export** (`gpx_writer.dart`, `track_exporter*.dart`): client-side GPX 1.1
  build; conditional `exportGpx` → share sheet (mobile) / browser download (web).
- **Interactions** (`interaction_ids.dart`, `tracks_interactions.dart`):
  `hud.tracks.tap`, `tracks.import.start`, `tracks.open {id}`,
  `tracks.export {id}` — wired in `main`, drivable via `orion.dispatch`.
- **Routes + HUD** (`router.dart`, `map_screen.dart`): nested `/tracks` +
  `/tracks/:id` (map stays alive); Tracks `HudButton` (`Icons.route`) between
  follow-me FAB and settings cog.
- **UI** (`tracks_screen.dart`, `track_detail_screen.dart`, `track_list_tile.dart`,
  `track_format.dart`): list with import-badge header + empty state; ⋮ → Export;
  tap → detail full-stats page.

### Toolchain note
`build_runner` codegen must be run with **`dart run build_runner build --force-jit`**
on this toolchain (Flutter 3.38.9 / Dart 3.10.8): `sqlite3` 3.x ships a
native-assets build hook that the default AOT entrypoint compile rejects
("'dart compile' does not support build hooks"). `--force-jit` sidesteps it.
Also `dependency_overrides: path_provider_foundation: 2.4.1` to drop `objective_c`
(another hook; Apple-only, unused — iOS deferred).

### Parser re-verification (done ✅)
- `mindanao.gpx` (Gaia) → **15 tracks, 37,775 points**.
- a MyTracks file → **1 track, 3,403 points**.
- Same first point across both (`11.919155, 121.976275`, ele `67.7`); track 27
  name `"Mindanao 2022-12-27 09:22"`, color `#2D3FC7`; stats sane (~375 km,
  3,801 m gain).

## Verification checklist

### Automated (done)
1. ✅ `flutter analyze` — no issues.
2. ✅ `flutter test` — 8/8 pass (no regressions).
3. ✅ `flutter build web` — succeeds.
4. ✅ GPX parser verified against both real sample sets (counts + first point).

### Manual — web (`flutter run -d chrome`)
5. Tracks HUD button (between FAB and cog) → opens `/tracks`; empty state shown.
6. Import `~/Downloads/temp/mindanao.gpx` → badge climbs to ~15 then counts to 0;
   **15 entries** appear; app stays responsive during import.
7. Re-import the same file → **30 entries** (no dedup).
8. Import the 15 MyTracks files (multi-select) → 15 more entries; names verbatim.
9. Tap a row → detail page shows full stats (distance, duration, avg/max speed,
   elevation gain/loss, min/max, points, start/end).
10. Row ⋮ → Export (and detail ⌃ Export) → GPX **downloads**; re-importing it
    yields an equivalent track (round-trip name/desc/color/points).
11. Back from detail → list → map; map still live (no reload/re-fit).
12. `orion.dispatch('tracks.export', {id:1})` from the console exports (both-ways);
    `orion.webnav.dump()` shows `/tracks` / `/tracks/1`.
13. Pick a non-GPX file (force "All files") → friendly SnackBar, no crash.

### Manual — Android (`flutter run -d <device>`)
14. Same import flow; picker multi-select; badge; list updates.
15. Export → **share sheet** appears with the `.gpx`.
16. Android hardware back collapses detail → list → map (intuitive).
17. Persistence: kill + relaunch → imported tracks still listed (Drift on device).

## Round notes

### Round 1: off-thread import (no UI freeze) (2026-06-07)

Device/web testing surfaced import jank. Fixes (branch `feature/p6-import-export`):

- **Badge consistency** — parse the whole selection first, set the badge to the
  **total** track count, then store; so 15 one-track files and one 15-track file
  both show the real total (was per-file, stuck at 1/0).
- **Off-thread parsing** — the parse blocked the UI thread. Now
  `parseGpxOffThread(bytes)` (conditional `gpx_offthread_io/web.dart`):
  - **native** → `compute()` (background isolate).
  - **web** → a **real Web Worker** (`web/gpx_worker.dart` → `gpx_worker.dart.js`),
    because dart2js has no isolates (`compute` runs inline). dropped an interim
    cooperative-yield parser in favour of the worker since **web is a production
    target**, not just the dev loop.
  - Required making the parse chain Flutter-free (moved the Drift-backed
    `TrackFormatting` extension out of `track_model.dart` into `track_format.dart`)
    so the worker compiles to JS.
- **Build step** — the worker is a separate entrypoint flutter doesn't compile:
  run `scripts/build_web_worker.sh` (`dart compile js`) and commit
  `web/gpx_worker.dart.js` whenever the parser changes.
- **file_picker** — auto-pinned to ancient 3.0.4 (no AGP namespace → Android
  build failed). Bumped to **8.3.7** + **share_plus 10.1.4** (resolves a `win32`
  clash; adjusted exporter to `Share.shareXFiles`). Bonus: web wasm dry-run now
  passes.
- **Android picker** — custom `gpx` filter is unsupported (no MIME) and threw;
  use `FileType.any` on mobile + read by path; `.gpx` accept-hint stays on web.
- **`orion.data.clearTracks()`** + `scripts/mobile/cleartracks.sh` — wipe all
  tracks (dev/data op via the bus).

#### Verification
1. ✅ `flutter analyze` clean; web build + Android debug APK build both succeed.
2. ✅ Android: import (15-track file & 15 files) — no freeze, badge shows total.
3. Web: confirm the Web Worker keeps the page smooth during import (no jank).
4. ✅ Picker shows/selects `.gpx` (they were under DocumentsUI "Recent"; browse to the folder).
5. Round-trip export re-imports equivalently (web + Android). *(pending)*
