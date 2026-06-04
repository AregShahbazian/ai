# Phase 1 · Map Shell — Design

Implements [`prd.md`](prd.md) (`id: phase-1-map`). Part of Orion — see
[root overview](../../README.md). `track` is the reference implementation
(`~/git/track/lib/features/map/map_screen.dart`), not a base to fork.

## Architecture decisions

- **Fresh Flutter app** in `~/git/orion` (not forked from `track`). Latest stable
  Flutter/Dart at scaffold time.
- **Plugin:** `maplibre_gl: ^0.26.1` (decided — official, web-capable). Same API
  family `track` used (`MapLibreMap`, `styleString`, `CameraUpdate`).
- **Dev target: web-first** (`flutter run -d chrome`); phone (Zenfone 10) for the
  on-device check. Web is the only target that needs extra setup (JS/CSS include).
- **No state management lib** — Phase 1 has a single ephemeral flag (`isOnline`).
  Plain `StatefulWidget` is enough; no models, no DB, no persistence.
- **Identity replicated from `track`:** `applicationId`/iOS bundle `com.mby4m.orion`,
  app label **Orion**, reuse `track`'s launcher icon assets. iOS configured but not
  built (groundwork-clean).
- **Orientation:** do not lock — allow portrait + landscape.

## App structure (minimal)

```
lib/
  main.dart            // runApp(OrionApp())
  app.dart             // OrionApp: MaterialApp(title 'Orion', home: MapScreen())
  features/map/
    map_screen.dart    // Scaffold > Stack [ MapLibreMap, OfflineIndicator ]
    map_constants.dart // Philippines bounds, default style URL, fit padding
    offline_indicator.dart // connectivity-driven banner
```

No routes, no bottom bar, no second screen.

## Map widget (maplibre_gl)

```dart
MapLibreMap(
  styleString: 'https://tiles.openfreemap.org/styles/liberty',
  initialCameraPosition: CameraPosition(target: kPhCenter, zoom: 5), // rough; refined on create
  onMapCreated: _onMapCreated,
  onStyleLoadedCallback: _fitPhilippines,   // fit after style ready (see note)
  scrollGesturesEnabled: true,
  rotateGesturesEnabled: true,
  tiltGesturesEnabled: true,
  zoomGesturesEnabled: true,
  myLocationEnabled: false,                 // zero-permission Phase 1
  trackCameraPosition: false,               // not needed in Phase 1
)
```

- **Philippines framing** — don't rely on a single hardcoded zoom. Define
  `kPhBounds = LatLngBounds(southwest: LatLng(4.5,116), northeast: LatLng(21,127))`
  and in `_fitPhilippines` call
  `controller.moveCamera(CameraUpdate.newLatLngBounds(kPhBounds, left/top/right/bottom: 24))`.
  This frames the whole country consistently across screen sizes and on rotation.
  - **Note/risk:** `newLatLngBounds` needs the map laid out & style loaded; run it
    in `onStyleLoadedCallback` (and/or a post-frame callback). Verify timing.
- **No `myLocation`** — keeps Phase 1 permission-free.
- **Attribution** — leave the style's built-in attribution control visible; do not
  suppress it. Must show *OpenFreeMap © OpenMapTiles Data from OpenStreetMap*.

## Offline indicator

```dart
// state in MapScreen
bool _isOnline = true;
StreamSubscription? _sub;

// init: seed + listen (pattern from track)
final init = await Connectivity().checkConnectivity();
_isOnline = !init.contains(ConnectivityResult.none);
_sub = Connectivity().onConnectivityChanged.listen((r) =>
    setState(() => _isOnline = !r.contains(ConnectivityResult.none)));
```

- When `!_isOnline`, render a **small, non-intrusive banner/chip** (top, inside
  SafeArea): e.g. "Offline — showing cached map". Hidden when online. Never blocks
  the map or shows an error screen (PRD req. 8).
- **Caveat:** `connectivity_plus` reports interface reachability, not true internet
  reachability — acceptable for a simple indicator. Cancel `_sub` in `dispose`.

## Web specifics

- `web/index.html`: add MapLibre GL **JS + CSS** `<script>`/`<link>` (a
  `maplibre-gl` version compatible with `maplibre_gl` 0.26.1 — confirm in plugin
  docs). `track` never did this (it was mobile-only).
- CORS: OpenFreeMap serves CORS headers → browser fetch works.

## Dependencies

- `maplibre_gl: ^0.26.1`
- `connectivity_plus: ^6.x`
- (No `path_provider`, `sqflite`, `geolocator`, etc. in Phase 1.)

## Open questions (resolve during implementation)

1. Confirm `maplibre_gl` 0.26.1 widget/API names match `track` (`MapLibreMap`,
   `styleString`, `CameraUpdate.newLatLngBounds`) — adjust if renamed.
2. Best hook for `newLatLngBounds` so it fires reliably after first layout
   (`onStyleLoadedCallback` vs post-frame).
3. Exact `maplibre-gl` JS version to pin in `web/index.html`.
