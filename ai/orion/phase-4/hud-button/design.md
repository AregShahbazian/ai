---
id: phase-4-hud-button
title: HudButton — design
---

## Architecture

One stateless widget `lib/features/map/hud_button.dart` owns all HUD button
styling. The two existing HUD controls (`CompassButton`, `LocationFab`) compose
it; the Phase 5 settings cog will too. No theming system / tokens — plain params.

### `HudButton` API

```dart
class HudButton extends StatelessWidget {
  const HudButton({
    required Widget child,
    required VoidCallback onPressed,
    Color backgroundColor = Colors.white,
    Color? foregroundColor,
  });
  static const double size = 44; // the reference compass size
}
```

- **Fixed:** 44 dp circle, `Colors.black26` shadow (blur 4, offset (0,2)) —
  copied verbatim from the old compass `Container`, so the compass is pixel-
  identical after migration.
- **Per-instance:** `backgroundColor` (default white), optional `foregroundColor`,
  `child`, `onPressed`.

### Open questions — resolved

- **Ripple vs plain tap → Material `InkWell` ripple.** One consistent tap feel
  for all buttons. The shadow is kept as an explicit `BoxShadow` (not Material
  elevation) so it exactly matches the original compass; the `Material` is
  `type: transparency` + `CircleBorder` clip, with `InkWell` inside for the
  ripple. The compass loses its bare `GestureDetector` but gains the same feel
  as the FAB.
- **Visibility/animation ownership → stays in the caller.** `HudButton` is just
  the button; `CompassButton` keeps its `AnimatedSwitcher` + `visible` wrapper,
  since not every button hides.
- **Color API → plain `backgroundColor`/`foregroundColor` params.** No named
  variants. `foregroundColor` is applied via `IconTheme.merge` so `Icon`
  children inherit it; the compass `CustomPaint` keeps its own red/grey colors
  (unaffected, as intended).

## Migration

- **CompassButton** — drop the `Container` + `GestureDetector`; render the
  rotating-needle `CustomPaint` as `HudButton`'s child. `_size` now aliases
  `HudButton.size`. `AnimatedSwitcher`/`visible` unchanged.
- **LocationFab** — drop `FloatingActionButton.small` (and its `heroTag`); use
  `HudButton` with `foregroundColor: following ? colorScheme.primary : null`.
  Background becomes white (matching the compass) instead of the FAB theme
  surface — verify the icon stays legible and the follow tint still reads.
- **Settings cog** — delivered by `phase-5/navigation/`; no-op `onPressed` for
  now, just built on `HudButton(Icons.settings)`.

## Files

- `lib/features/map/hud_button.dart` — new.
- `lib/features/map/compass_button.dart` — migrate.
- `lib/features/map/location_fab.dart` — migrate.
- `map_screen.dart` — no change (buttons keep their `Align` slots in the HUD
  `Stack`).
