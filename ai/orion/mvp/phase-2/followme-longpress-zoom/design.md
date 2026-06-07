---
id: phase-2-followme-zoom
---

# Design — Long-press follow-me FAB

## Constraints that shape this

- **No Dart-side user position.** The blue dot + follow are driven by MapLibre's
  native location engine; `LocationService` only wraps permission. So "center on
  me" cannot be a `newLatLngZoom(userLatLng, 15)` — we have no `userLatLng`. We
  must center via MapLibre's `tracking` mode (the SDK animates to the user) and
  control **zoom** separately with `CameraUpdate.zoomTo`.
- **Programmatic camera moves dismiss tracking.** As documented in
  `LocationController.resetOrientation`, any programmatic `animateCamera` while
  following makes the native SDK fire `onCameraTrackingDismissed`, which would
  knock us back to Off. The established fix is the `_suppressDismiss` guard +
  re-asserting the tracking mode afterward. The zoom step reuses that pattern.

## Approach

Long-press = "center + zoom to default", except in Follow+Heading where it's a
plain toggle to Off. Both the center and the zoom go through the existing
follow-mode machinery so we don't fight the native SDK:

1. **Follow+Heading** → delegate to the existing tap handler
   (`onFabPressed`), which cycles `trackingCompass → none` and resets
   orientation. Zero new behavior, full reuse.
2. **Off / Follow** → ensure we're in `tracking` (enabling + requesting
   permission first if needed, exactly like the tap's `_enableAndFollow`), which
   performs the center-me motion; then zoom to `kDefaultFollowZoom` while keeping
   the follow.

The center (tracking) and the zoom chain back-to-back, reading as one fluent
pan-into-zoom. Tracking keeps the camera locked on the user throughout the zoom,
so the user stays centered as it zooms in.

## Changes by file

### `lib/features/map/map_constants.dart`
Add the shared default-follow-zoom constant:
```dart
/// Street/neighborhood zoom the long-press "center on me" lands at — the app
/// opens whole-world (zoom 1) and plain follow keeps the current zoom, so this
/// is the one place the camera is taken to a usable street level. Parity with
/// the `track` POC's center-me zoom.
const double kDefaultFollowZoom = 15.0;
```

### `lib/core/interaction/interaction_ids.dart`
Add the new id + include it in `all`:
```dart
/// HUD location FAB long-pressed — center on the user and zoom to the default
/// follow zoom (Follow+Heading: plain toggle to Off, no zoom).
static const String followMeLongPress = 'hud.followMe.longPress';
```

### `lib/features/map/location_controller.dart`
New public method + a private zoom helper:
```dart
/// Long-press: center on the user and zoom to [kDefaultFollowZoom] as one
/// motion. In Follow+Heading it's a plain toggle to Off (delegates to the tap
/// handler) — no zoom. Returns the same result type as a tap so the UI can
/// surface the permission SnackBar.
Future<LocationTapResult> onFabLongPressed() async {
  // Follow+Heading → behave exactly like a tap (drop to Off, reset orientation).
  if (_trackingMode == MyLocationTrackingMode.trackingCompass) {
    return onFabPressed();
  }
  // Off (enabled or not): enable + follow to center on the user.
  if (!_enabled) {
    final result = await _enableAndFollow();
    if (result != LocationTapResult.following) return result; // denied
  } else if (_trackingMode == MyLocationTrackingMode.none) {
    await setTrackingMode(MyLocationTrackingMode.tracking);
  }
  // Now following → zoom in to the default level, keeping the follow.
  await _zoomToDefaultKeepingFollow();
  return LocationTapResult.following;
}

/// Zoom to [kDefaultFollowZoom] without dropping follow. A programmatic camera
/// move dismisses native tracking, so guard with [_suppressDismiss] and
/// re-assert tracking after — same pattern as [resetOrientation].
Future<void> _zoomToDefaultKeepingFollow() async {
  final map = _map;
  if (map == null) return;
  _suppressDismiss = true;
  try {
    await map.animateCamera(CameraUpdate.zoomTo(kDefaultFollowZoom));
    await map.updateMyLocationTrackingMode(MyLocationTrackingMode.tracking);
    _trackingMode = MyLocationTrackingMode.tracking;
    _notify();
  } finally {
    _suppressDismiss = false;
  }
}
```
Needs the `map_constants.dart` import.

### `lib/features/map/hud_button.dart`
Add optional long-press support (tap stays required):
```dart
final VoidCallback? onLongPress;
// ...
InkWell(
  customBorder: const CircleBorder(),
  onTap: onPressed,
  onLongPress: onLongPress,
),
```

### `lib/features/map/location_fab.dart`
Thread an optional `onLongPress` through to `HudButton`:
```dart
final VoidCallback? onLongPress;
// ...
HudButton(onPressed: onPressed, onLongPress: onLongPress, ...);
```

### `lib/features/map/map_screen.dart`
- Register/unregister `followMeLongPress` → `_location.onFabLongPressed`.
- New `_onLocationLongPress` that dispatches it; factor the
  permanently-denied-SnackBar tail out of `_onLocationTap` into a shared
  `_handleLocationResult(result)` used by both.
- Pass `onLongPress: _onLocationLongPress` to `LocationFab`.

## Open questions — RESOLVED on device (see review.md Round 1)

All three were real and fixed: the chained center→zoom *did* race (now waits for
`onCameraIdle` to settle before zooming), and `zoomTo` *did* dismiss tracking (now
zooms on a freed camera, `none` → zoom → re-enter follow). Net shape shipped:
**press-first cycling, mobile-only, settle-then-zoom over 1200 ms.** Original
notes kept below for history.

### Original open questions

- **Fluency of the chained center→zoom from Off.** Entering `tracking` triggers
  the SDK's center animation; the `zoomTo` then animates zoom. On device, confirm
  this reads as one continuous motion and the `zoomTo` doesn't visibly interrupt
  a half-finished center. If it stutters, options: await a short settle before
  zooming, or skip the intermediate tracking-center and rely on the zoom (camera
  already snaps to user under tracking).
- **Does `zoomTo` actually dismiss tracking** on the current plugin version? The
  re-assert is harmless if not, but verify the dot keeps following after the zoom.
- **Web**: confirm long-press fires (no native long-press conflict) and the zoom
  applies; the dot is plain (no native engine) but the camera should still zoom.
