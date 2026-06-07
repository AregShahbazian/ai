# Phase 1 · Map Shell — Tasks

Implements [`prd.md`](prd.md) per [`design.md`](design.md). Commit messages should
carry the PRD id: `[phase-1-map]`.

> Order matters: scaffold → deps → shell → framing → offline → branding → device.
> Develop on **web** (`flutter run -d chrome`); device check at the end.

## T1 — Scaffold the Flutter project
- `flutter create` in `~/git/orion` with org `com.mby4m`, project `orion`,
  platforms `android,web,ios` (ios scaffolded, not built).
- Keep `CLAUDE.md`, `.gitignore`, `gpt/` already in the repo.
- **Verify:** `flutter run -d chrome` shows the default counter app.

## T2 — Dependencies + web setup
- Add to `pubspec.yaml`: `maplibre_gl: ^0.26.1`, `connectivity_plus: ^6.x`.
- Add MapLibre GL **JS + CSS** include to `web/index.html` (version per design).
- **Verify:** `flutter pub get` clean; `flutter run -d chrome` still builds.

## T3 — App shell (single map screen)
- `main.dart` → `runApp(OrionApp())`; `app.dart` → `MaterialApp(title: 'Orion',
  home: MapScreen())`.
- `features/map/map_screen.dart`: `Scaffold > Stack` with `MapLibreMap`
  (liberty style, gestures all enabled, `myLocationEnabled: false`).
- `map_constants.dart`: style URL, `kPhCenter`, `kPhBounds`, fit padding.
- **Verify (web):** map renders OpenFreeMap tiles; pan, pinch/double-tap zoom,
  rotate, and tilt all work.

## T4 — Philippines framing
- `kPhBounds = LatLngBounds(SW(4.5,116), NE(21,127))`; `_fitPhilippines` calls
  `moveCamera(newLatLngBounds(kPhBounds, padding:24))` from `onStyleLoadedCallback`
  (+ post-frame fallback if needed).
- **Verify:** on launch the whole Philippines is framed; correct across window
  sizes (web) and after device rotation.

## T5 — Offline indicator
- Add `_isOnline` state in `MapScreen`: seed via `checkConnectivity()`, update via
  `onConnectivityChanged`; cancel sub in `dispose`.
- `offline_indicator.dart`: small SafeArea banner shown only when offline
  ("Offline — showing cached map"); never blocks the map.
- **Verify:** browse online (tiles cache) → turn network off → indicator appears,
  cached tiles still render, **no error screen**, app stays usable → back online →
  indicator hides.

## T6 — Branding, identity, orientation
- Set `applicationId`/label = `com.mby4m.orion` / **Orion**; reuse `track`'s
  launcher icon assets.
- Ensure **no orientation lock** (portrait + landscape allowed).
- **Verify:** correct app name + icon on launcher; rotating the device keeps the
  map framed and usable in both orientations.

## T7 — On-device build (Zenfone 10)
- `flutter run` on the Asus Zenfone 10 (Android 15).
- **Verify:** builds and installs; map pans/zooms smoothly; offline indicator works
  on device (toggle airplane mode).

## T8 — Attribution check
- **Verify:** the OpenFreeMap/OpenMapTiles/OSM attribution control is visible on
  both web and device; not suppressed.

## Definition of done (Phase 1 / map-shell)
- Single full-screen map, framed on the Philippines, all gestures, no other UI.
- Offline indicator behaves per T5; no permissions requested.
- Runs on web (dev loop) and on the Zenfone 10; correct Orion identity + icon.
