# Map flashes empty on resume from background (Android)

**Date:** 2026-06-06
**Branch:** feature/p1-map
**Status:** fixed

## Symptoms
On Android (Zenfone 10 / ASUS_AI2302), every time the app returned from blur
(home screen, sleep/lock), the map flashed quickly to empty and then back.

## Diagnosis
Added `[bugfix-flash]` diagnostic logs on the app-lifecycle transition
(`WidgetsBindingObserver.didChangeAppLifecycleState`), `onMapCreated`,
`onStyleLoadedCallback` (`_fitPhilippines`), the connectivity listener, and
`build()`. Reproduced via background→resume on the device over `flutter run`.

On resume the logs showed:
- **None** of the Dart-side suspects fired — no `build` (no rebuild), no
  `onStyleLoaded` (no style reload), no `onMapCreated` (controller not
  recreated), no connectivity event (no `setState`).
- The **native** GL stack re-initialized: `Mbgl-EGLConfigChooser` picking a new
  EGL config + Adreno GLES driver re-init + gralloc surface allocation.

So the flash originates entirely below the Flutter layer.

## Cause
The native MapLibre GL render surface tears down its GL/EGL context when the app
is backgrounded and rebuilds it from scratch on resume; the recreated surface is
blank for a frame until the first re-render → the "empty, then back" flash. The
Android plugin already hardcodes `textureMode(true)`
(`maplibre_gl/android/.../MapLibreMapBuilder.java`), so the usual SurfaceView→
TextureView remedy was already in effect — the blank frame happens anyway.

## Solutions Tried
- Ruled out (via logs) widget rebuild, style reload, controller recreation, and
  the connectivity `setState` as triggers.
- `translucentTextureSurface: true` on `MapLibreMap` — **worked** (confirmed-by-fix
  on device; flash gone). `foregroundLoadColor` was the fallback, not needed.

## Final Solution
Set `translucentTextureSurface: true` on the `MapLibreMap` widget so the
recreated texture surface composites without showing the blank frame.

## Edited Files
- lib/features/map/map_screen.dart
