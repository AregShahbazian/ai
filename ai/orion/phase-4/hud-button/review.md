---
id: phase-4-hud-button
title: HudButton — review
---

## Round 1: initial implementation (2026-06-07)

Implemented `HudButton` and migrated both existing HUD controls. `flutter
analyze` (changed files) clean. Settings cog deferred to `phase-5/navigation/`.

### Files
- `lib/features/map/hud_button.dart` — new shared widget.
- `lib/features/map/compass_button.dart` — uses `HudButton`.
- `lib/features/map/location_fab.dart` — uses `HudButton` (dropped `FAB.small`).

### Verification
1. `flutter analyze` clean across the repo.
2. Compass renders pixel-identical: 44 dp white circle, same shadow.
3. Compass needle rotates to bearing; hides via `AnimatedSwitcher` at bearing/
   tilt 0; tap dispatches `resetOrientationTap` and resets orientation.
4. LocationFab matches the compass size/shape exactly.
5. LocationFab follow-mode shows the primary tint (`foregroundColor`); icon
   stays legible on white when not following.
6. LocationFab tap still toggles tracking through its existing handler.
7. Tap feel (InkWell ripple) consistent on both buttons.
8. Visual parity verified on web.
9. Visual parity verified on Android.

## Round 2: edge-to-edge system bars (2026-06-07)

On Android the HUD buttons sat too close to the opaque system nav bar (portrait
bottom, landscape right). Rather than add per-edge padding, made the system bars
transparent and draw edge-to-edge, so the map fills the screen and the existing
single-SafeArea inset keeps the buttons clear on its own.

### Fix
- `lib/main.dart` — `WidgetsFlutterBinding.ensureInitialized()` +
  `SystemChrome.setEnabledSystemUIMode(edgeToEdge)` +
  transparent status/nav bar `SystemUiOverlayStyle`
  (`systemNavigationBarContrastEnforced: false`).

### Verification
10. ✅ Map draws under transparent status + nav bars; nav buttons usable.
11. ✅ HUD buttons stay clear of the nav bar via SafeArea alone — no extra
    padding needed (portrait bottom + landscape right).
