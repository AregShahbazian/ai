# Orion — Phase 2: Reset-orientation button (Design)

> PRD: [`prd.md`](prd.md) (`id: phase-2-reset-orientation`)

## Approach

Disable the native compass (`compassEnabled: false`) and render a single Flutter
**compass / reset-orientation button** in the existing `SafeArea` HUD layer of
`MapScreen`. The button is both a north indicator (needle rotates with bearing)
and the reset control (tap → bearing 0 + tilt 0).

## Why replace the native compass

The native compass only tracks bearing; it cannot be shown on pitch nor reset
tilt. To satisfy "one button for rotate **and** tilt" (PRD req. 3) the control
must be ours. `safe-area-hud` already built the HUD layer and named this exact
move as its deferred follow-up.

## State & camera tracking

`MapLibreMap` needs `trackCameraPosition: true` so `controller.cameraPosition` is
populated. Register a listener in `onMapCreated`:

```dart
_controller.addListener(_onCameraChanged);
```

Two `ValueNotifier`s drive the UI without rebuilding the map:

- `_bearingNotifier` (double) — current bearing, rotates the needle (live).
- `_orientedNotifier` (bool) — `bearing.abs() > 0.5 || tilt > 0.5`; shows/hides
  the button.

`_onCameraChanged` reads `cameraPosition` once and sets both. 0.5° dead-zones
avoid flicker from sub-degree float noise (same thresholds track used).

## Reset action

```dart
void _resetOrientation() {
  final pos = _controller?.cameraPosition;
  if (pos == null) return;
  _controller!.animateCamera(CameraUpdate.newCameraPosition(
    CameraPosition(target: pos.target, zoom: pos.zoom, bearing: 0, tilt: 0),
  ));
}
```

## Widget

A new `CompassButton` widget (own file `compass_button.dart`) takes the two
notifiers + an `onReset` callback. Internally:

- `ValueListenableBuilder<bool>` on `_orientedNotifier` → wraps in
  `AnimatedSwitcher` (≈150 ms fade) so it appears/disappears nicely (PRD req. 2),
  rather than popping via `SizedBox.shrink`.
- White circular 44 dp button, drop shadow, `_CompassNeedlePainter` (red north /
  grey south), rotated by `-bearing` via `_bearingNotifier`.
- `GestureDetector(onTap: onReset)`.

Painter is ported verbatim from track (`_CompassNeedlePainter`) — proven, trivial.

## Placement

Inside the existing `SafeArea` HUD `Stack`, add
`Align(alignment: Alignment.topRight, child: CompassButton(...))`. The offline
banner is `topCenter`, so no collision. The native compass margins
(`compassViewMargins`/`compassViewPosition`) are removed with the compass.

## Open questions

- None blocking. Fade duration (150 ms) and dead-zone (0.5°) are tunable during
  verification.
