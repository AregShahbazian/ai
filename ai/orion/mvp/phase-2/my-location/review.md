---
id: phase-2-my-location
---

# Orion — Phase 2: My Location — blue dot (Review)

> PRD: [`prd.md`](prd.md) · Design: [`design.md`](design.md) · Tasks: [`tasks.md`](tasks.md)

## Round 1: initial implementation (2026-06-06)

MapLibre's built-in dot, enabled after a one-time foreground-permission request on
native; on web the plugin's geolocate (tap-to-locate) button is shown. Render mode
`normal` (plain dot), tracking mode `none` (no camera follow). `flutter analyze` clean.

**Files:**
- `pubspec.yaml` — add `permission_handler: ^11.4.0`
- `android/app/src/main/AndroidManifest.xml` — `ACCESS_FINE/COARSE_LOCATION`
- `ios/Runner/Info.plist` — `NSLocationWhenInUseUsageDescription`
- `lib/features/map/map_screen.dart` — `_locationEnabled` state, `_initLocation()`,
  map wired to `myLocationEnabled / renderMode: normal / trackingMode: none`

### Verification

1. **Android, grant:** launch → permission prompt → Allow → blue dot appears at
   current position; camera stays on the Philippines (no jump/follow).
2. **Android, deny:** launch → Deny → no dot, app keeps working, **no crash, no
   repeat prompt** on the same session.
3. **Move:** walk / mock-move → dot tracks the new position in real time.
4. **Resume:** background → foreground → dot still present, no stale state.
5. **No follow:** pan/zoom freely — the camera is never yanked back to the dot
   (that's the Follow-Me task, not yet built).
6. **No heading cone:** the dot is a plain circle, not a direction wedge
   (heading-arrow task).
7. **Web preview:** the MapLibre locate button shows bottom-right; tap → browser
   permission prompt → Allow → dot appears. (Auto-show + follow arrives with
   Follow-Me.)
8. **Permission already granted (re-launch):** dot appears without a prompt.

### Known / by design
- Web shows the dot only after the user taps the locate button (plugin limitation —
  see design.md "Platform split"). Native shows it automatically.
- Denied-permission recovery UI (a "tap to enable location" affordance) is
  intentionally deferred — denial is silent for now.
