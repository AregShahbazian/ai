# Compass reset doesn't work on web with touch input

**Date:** 2026-06-07
**Branch:** feature/p4-hud-button
**Status:** fixed

## Symptoms
On web in a touch context (Chrome responsive/touch-simulation mode), tapping the
compass button didn't reset orientation — the camera made only a tiny step toward
north, or didn't move at all. With a real mouse click (non-touch) the same button
reset correctly. The interaction log still showed `hud.resetOrientation.tap` on
every tap, so the dispatch itself was firing.

## Diagnosis
Added temporary `devLog('reset', …)` lines in `LocationController.resetOrientation`
(serialized with `jsonEncode` so the browser console didn't collapse them to
`{…}`), plus the existing `orion.logEvents(true)` interaction log.

- **Touch:** `start` bearing == `after-animate` bearing (unchanged), and
  `map.rotate.changed` **never fired** → the camera never moved.
- **Click:** `after-animate` also showed the old bearing (the `animateCamera`
  await resolves before the ease finishes), but ~500 ms later
  `map.rotate.changed {bearing: 0}` fired → the animation played out to north.

So the reset `animateCamera` was being cancelled before its first frame under
touch, while completing under mouse.

## Cause
A Flutter-web platform-view quirk: pointer events on widgets layered over the
MapLibre platform view (the map) leak through to it. A touch tap on the compass
emits a trailing synthetic pointer/mouse event that reaches the MapLibre canvas,
whose `touchstart`/`mousedown` handler calls `map.stop()` — cancelling the
in-flight `animateCamera` reset. A mouse click is absorbed by the Flutter
`InkWell` and never reaches the canvas, so its animation survives.

## Solutions Tried
1. **`pointer_interceptor` (first attempt)** — added the package and wrapped the
   HUD controls, but it was tested via hot-restart only. A new web plugin needs
   `pub get` + a full rebuild/restart, so the interceptor never actually loaded —
   it appeared not to work.
2. **`moveCamera` instead of `animateCamera`, web-touch only** — detected the
   tap's `PointerDeviceKind` and jumped (instant, uninterruptible) instead of
   animating for web touch. Worked, but lost the reset animation on touch.

## Final Solution
Re-applied **`pointer_interceptor`** (the canonical Flutter fix for widgets over a
web platform view) and verified it after a full `flutter run -d chrome`. Wrapped
the compass button, location FAB, and web attribution in `PointerInterceptor`
(no-op off web) so their taps can't reach the map canvas. The reset animation now
survives on touch, and HUD taps no longer leak to the map (e.g. the FAB tap can't
pan the map underneath). Reverted the `moveCamera`/pointer-kind approach and
removed all temporary logs.

Key lesson: adding a web plugin requires a full restart, not a hot restart.

## Edited Files
- pubspec.yaml / pubspec.lock — added `pointer_interceptor`
- lib/features/map/map_screen.dart — wrap compass / FAB / attribution in `PointerInterceptor`
