# Orion — Phase 2: Reset-orientation button (Review)

> PRD: [`prd.md`](prd.md) · Design: [`design.md`](design.md) · Tasks: [`tasks.md`](tasks.md)

## Round 1: initial implementation (2026-06-06)

Single Flutter `CompassButton` replaces the native compass. Appears on
`bearing≠0 || tilt≠0`, needle tracks bearing, tap animates back to bearing 0 +
tilt 0. `flutter analyze` clean. ✅ Verified on device 2026-06-06.

**Files:**
- `lib/features/map/compass_button.dart` (new) — button + needle painter
- `lib/features/map/map_screen.dart` — camera notifiers, `_onCameraChanged`,
  `_resetOrientation`, native compass disabled, button in HUD

### Verification

1. **Rotate** the map (twist gesture) → button fades in, needle points to north
   as the map turns; tap → animates back to north, button fades out.
2. **Two-finger pan** (tilt) with no rotation → same button appears; tap →
   map flattens (tilt 0), button fades out. (The original gap.)
3. **Rotate + tilt** together → button appears once; tap → both reset in one
   animation.
4. **Re-focused state** (bearing & tilt ~0) → button hidden; no flicker at rest.
5. Native MapLibre compass no longer shows on rotation (fully replaced).
6. Button sits inside the safe area top-right (status bar / cutout clear) in
   **portrait and both landscapes**; survives orientation change.
7. Attribution "i" still inset bottom-right (unchanged by this work).
8. Resume from background (Android) → map restores, button reflects current
   orientation, no stale state.
