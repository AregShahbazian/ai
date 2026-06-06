---
id: phase-2-follow-me
---

# Orion — Phase 2: Follow Me — camera tracking toggle (Tasks)

> Part of Orion — see [`README.md`](../../README.md). PRD: [`prd.md`](prd.md) ·
> Design: [`design.md`](design.md).

## Checklist

- [ ] Extract `lib/features/map/location_service.dart` (request / permanently-denied
      / openSettings), mirroring track. Point `my-location`'s `_initLocation` at it.
- [ ] `map_screen.dart`: add `_trackingMode` state (`MyLocationTrackingMode.none`).
- [ ] Wire map: `myLocationTrackingMode: _trackingMode` +
      `onCameraTrackingDismissed: _onCameraTrackingDismissed`.
- [ ] `_locationFabIcon` getter + `_onLocationFabPressed` cycle (none → tracking →
      trackingCompass → none); permission request when disabled; SnackBar +
      Settings when permanently denied.
- [ ] Location `FloatingActionButton.small` in the SafeArea HUD, `Align(bottomRight)`,
      foreground = primary when following.
- [ ] Move native attribution to bottom-left so the FAB owns bottom-right.
- [ ] `flutter analyze` clean.
- [ ] On-device verify (see `review.md`).
