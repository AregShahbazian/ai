---
id: phase-2-follow-me
---

# Orion — Phase 2: Follow Me — camera tracking toggle (Design)

> Part of Orion — see [`README.md`](../../README.md). PRD: [`prd.md`](prd.md).

## Approach

Mirror `track`'s location FAB as closely as possible. MapLibre already implements
camera-follow through `myLocationTrackingMode`; this task is the **HUD button + the
mode state machine** on top of the My-Location dot — no custom camera animation or
position stream.

### Mode state machine (identical to track)

```
none ──tap──▶ tracking ──tap──▶ trackingCompass ──tap──▶ none
                  ▲                                          │
                  └──────── manual pan/zoom (auto) ──────────┘  → none
```

- **none** — dot visible, camera free.
- **tracking** (`MyLocationTrackingMode.tracking`) — camera centers on the user.
- **trackingCompass** (`MyLocationTrackingMode.trackingCompass`) — camera also
  rotates to device heading (fully meaningful once heading-arrow lands; works now).
- Manual pan/zoom while following → MapLibre fires `onCameraTrackingDismissed` →
  reset to **none** (track's exact behavior).

`updateMyLocationTrackingMode(mode)` drives the camera; we also pass
`myLocationTrackingMode: _trackingMode` on the widget so a rebuild stays in sync.

### Button — ported from track

`FloatingActionButton.small`, icon by mode (track's `_locationFabIcon` verbatim):

| State | Icon | Foreground |
|---|---|---|
| location off / denied | `Icons.location_disabled` | default |
| none (dot only) | `Icons.location_searching` | default |
| tracking | `Icons.my_location` | primary |
| trackingCompass | `Icons.explore` | primary |

Tap logic (track's `_onLocationFabPressed`):
- **Location not yet enabled** → request permission. Granted → enable + jump to
  `tracking`. Permanently denied → SnackBar with a **Settings** action (user
  *tapped* the button, so guidance here is wanted — not the silent denial of the
  passive my-location path).
- **Enabled** → cycle to the next mode.

## Placement

Orion routes all Flutter HUD through the single `SafeArea` layer in `map_screen`.
The FAB goes there, `Align(bottomRight)` — inherits the safe-area inset, no manual
`MediaQuery` math (track had to compute `padding.bottom + 16`; our HUD already does).

The native attribution "i" currently sits bottom-right; move it **bottom-left** so
the action button owns the bottom-right corner (track's control zone; most map apps
put controls bottom-right, attribution opposite). One-line change to
`attributionButtonPosition` + its margins.

The compass / reset-orientation button stays **top-right** — untouched.

## Permission service (small refactor)

Extract a `LocationService` (mirror of track's) so the permission logic lives in one
place instead of inline:

```dart
class LocationService {
  Future<bool> requestPermission();      // locationWhenInUse.request().isGranted
  Future<bool> isPermanentlyDenied();
  Future<void> openSettings();           // openAppSettings()
}
```

`my-location`'s `_initLocation()` is updated to call this too (DRY) — same behavior,
no functional change to that task.

## Web

On web, flipping tracking mode is exactly what *does* show + follow the dot (the
geolocate control enters its active-lock state). So the FAB cycling naturally makes
web follow work — the piece my-location deferred. `permission_handler` is skipped on
web (browser handles the prompt via the control).

## Out of scope

Heading cone on the dot (heading-arrow), accuracy circle, a speed/altitude bar
(track's `LocationBar`), persisting the mode across launches.
