---
id: phase-2-followme-zoom
---

# Tasks — Long-press follow-me FAB

## T1 — Default-follow-zoom constant
- `map_constants.dart`: add `const double kDefaultFollowZoom = 15.0;` with doc.
- **Verify:** `flutter analyze` clean; constant referenced in T3.

## T2 — Interaction id
- `interaction_ids.dart`: add `followMeLongPress = 'hud.followMe.longPress'`
  with doc; add to `all`.
- **Verify:** `all` contains it; analyze clean.

## T3 — Controller: long-press handler
- `location_controller.dart`: import `map_constants.dart`; add
  `onFabLongPressed()` and `_zoomToDefaultKeepingFollow()` per design.
- **Verify by reasoning:**
  - Off (disabled) → permission requested; granted → tracking + zoom 15; denied
    → returns denied/permanentlyDenied, no camera move.
  - Off (enabled, none) → tracking + zoom 15.
  - Follow → zoom 15, stays tracking.
  - Follow+Heading → delegates to `onFabPressed` → none + reset orientation, no zoom.

## T4 — HudButton long-press
- `hud_button.dart`: add `final VoidCallback? onLongPress;` ctor param; wire to
  `InkWell.onLongPress`.
- **Verify:** existing buttons (compass, settings) pass no `onLongPress` → still
  compile, long-press is a no-op for them.

## T5 — LocationFab passthrough
- `location_fab.dart`: add `final VoidCallback? onLongPress;` ctor param; pass to
  `HudButton`.
- **Verify:** analyze clean.

## T6 — Wire into MapScreen
- `map_screen.dart`:
  - `initState`: `register(followMeLongPress, (_) => _location.onFabLongPressed())`.
  - `dispose`: `unregister(followMeLongPress)`.
  - Extract `_handleLocationResult(LocationTapResult)` from `_onLocationTap`'s
    permanently-denied SnackBar tail; reuse in both tap + long-press handlers.
  - Add `_onLocationLongPress` → dispatch `followMeLongPress` → `_handleLocationResult`.
  - Pass `onLongPress: _onLocationLongPress` to `LocationFab`.
- **Verify:** analyze clean; tap path unchanged.

## T7 — Analyze + device/web check
- `flutter analyze` (whole project) clean.
- Manual checks per `review.md` checklist (device for native follow nuances).
