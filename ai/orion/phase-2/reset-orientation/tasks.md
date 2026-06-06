# Orion — Phase 2: Reset-orientation button (Tasks)

> Design: [`design.md`](design.md)

## T1 — `compass_button.dart` (new)

- New file `lib/features/map/compass_button.dart`.
- `CompassButton` stateless widget: params `bearing` (`ValueListenable<double>`),
  `visible` (`ValueListenable<bool>`), `onReset` (`VoidCallback`).
- `AnimatedSwitcher` (150 ms) keyed on visibility; child = 44 dp white circular
  button with shadow + rotated `_CompassNeedlePainter`.
- Port `_CompassNeedlePainter` from track verbatim.
- **Verify:** `flutter analyze` clean.

## T2 — wire camera state into `MapScreen`

- Add `_bearingNotifier` (`ValueNotifier<double>(0)`) and `_orientedNotifier`
  (`ValueNotifier<bool>(false)`); dispose both.
- `MapLibreMap`: set `trackCameraPosition: true`; set `compassEnabled: false`;
  remove `compassViewPosition` / `compassViewMargins` (native compass gone).
- In `_onMapCreated`, `controller.addListener(_onCameraChanged)`.
- `_onCameraChanged`: read `cameraPosition`; update bearing + oriented notifiers
  with 0.5° dead-zones.
- `_resetOrientation()` per design (animate bearing 0 + tilt 0).
- **Verify:** map still loads, native compass no longer appears on rotate.

## T3 — place the button in the HUD

- In the `SafeArea` HUD `Stack`, add
  `Align(alignment: Alignment.topRight, child: CompassButton(bearing: …, visible: …, onReset: _resetOrientation))`.
- **Verify:** rotate → button fades in, needle tracks north, tap resets;
  two-finger tilt → same button appears, tap flattens; both reset → button fades out.

## T4 — review doc + manual test

- Write `review.md` with the basic test checklist (Round 1).
- Run `flutter analyze`; manual on-device pass.
