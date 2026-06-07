---
id: phase-2-my-location
---

# Orion — Phase 2: My Location — blue dot (Tasks)

> Part of Orion — see [`README.md`](../../README.md). PRD: [`prd.md`](prd.md) ·
> Design: [`design.md`](design.md).

## Checklist

- [x] Add `permission_handler: ^11.4.0` to `pubspec.yaml`; `flutter pub get`.
- [x] Android manifest: add `ACCESS_FINE_LOCATION` + `ACCESS_COARSE_LOCATION`.
- [x] iOS `Info.plist`: add `NSLocationWhenInUseUsageDescription`.
- [x] `map_screen.dart`: add `_locationEnabled` state + `_initLocation()` called
      from `initState` (native = permission_handler request; web = enable directly).
- [x] Wire `myLocationEnabled / renderMode: normal / trackingMode: none` on the map.
- [x] Graceful denial: denied → flag stays false, dot absent, no crash/nag.
- [x] `flutter analyze` clean.
- [ ] On-device verify (see `review.md`).
