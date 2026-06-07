---
id: phase-4-hud-button
title: HudButton — tasks
---

## Task 1 — Add `HudButton` widget
- New `lib/features/map/hud_button.dart` per design (fixed 44 dp circle + shadow;
  params `backgroundColor`/`foregroundColor`/`child`/`onPressed`; `InkWell` tap).
- Verify: `flutter analyze` clean.

## Task 2 — Migrate `CompassButton`
- Replace `Container`+`GestureDetector` with `HudButton`; needle `CustomPaint`
  as child; keep `AnimatedSwitcher`+`visible`. `_size = HudButton.size`.
- Verify: compass looks/behaves identical — rotates to bearing, hides at 0, tap
  resets orientation.

## Task 3 — Migrate `LocationFab`
- Replace `FloatingActionButton.small` with `HudButton`; follow tint via
  `foregroundColor`.
- Verify: same size/shape as compass; follow-mode tint reads; icon legible on
  white; tap still toggles tracking.

## Task 4 — Analyze + visual parity
- `flutter analyze` whole repo clean.
- Visual parity on web + Android: compass unchanged, FAB matches compass size/
  shape, no follow-tint regression.
