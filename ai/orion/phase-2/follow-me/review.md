---
id: phase-2-follow-me
---

# Orion — Phase 2: Follow Me — camera tracking toggle (Review)

> PRD: [`prd.md`](prd.md) · Design: [`design.md`](design.md) · Tasks: [`tasks.md`](tasks.md)

## Round 1: initial implementation (2026-06-06)

Location FAB ported from track. Cycles none → tracking → trackingCompass → none via
`updateMyLocationTrackingMode`; manual pan exits follow (`onCameraTrackingDismissed`).
Permission request + Settings SnackBar on the FAB path. Attribution moved bottom-left
so the FAB owns bottom-right. `flutter analyze` clean.

**Files:**
- `lib/features/map/location_service.dart` (new) — permission wrapper (track parity)
- `lib/features/map/map_screen.dart` — `_trackingMode`, `_locationFabIcon`,
  `_onLocationFabPressed`, `_setTrackingMode`, `_onCameraTrackingDismissed`; FAB in
  HUD; attribution → bottom-left; `_initLocation` now uses `LocationService`

### Verification

1. **Cycle (granted):** tap FAB → `my_location` (camera centers + follows as you
   move) → tap → `explore` (camera also rotates to heading) → tap → `location_searching`
   (free). Icon + tint (primary while following) match each state.
   - **Exit from Follow+heading** also flattens the view: leaving `trackingCompass`
     → off animates back to north-up / no-tilt (same as the reset-orientation button).
2. **Auto-dismiss:** while following, pan/zoom by hand → follow stops, icon returns to
   `location_searching` (no fight between gesture and camera).
3. **Permission off, tap FAB:** prompt appears → Allow → jumps straight to follow.
4. **Permanently denied, tap FAB:** SnackBar "enable in Settings" with a **Settings**
   action that opens the app settings page.
5. **Placement:** FAB bottom-right inside the safe area (clears nav bar / cutout);
   attribution "i" now bottom-left; compass/reset still top-right. No overlaps;
   survives rotation (portrait + both landscapes).
6. **Web:** tap FAB → browser prompt → dot appears and camera follows (the auto-show
   my-location deferred to here).
7. **Resume from background:** mode and icon survive; no stale follow.

### Known / by design
- `trackingCompass` rotates the camera to heading now; the on-dot heading **cone** is
  the separate heading-arrow task.
- Mode is not persisted across launches (out of scope).
