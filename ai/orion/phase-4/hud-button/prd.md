---
id: phase-4-hud-button
title: Shared HudButton — one consistent HUD control style
status: implemented
branch: feature/p4-hud-button
---

## Goal

Introduce one shared **`HudButton`** widget that all map-HUD controls are built
from, so every HUD button has the **same size, shape, and styling** by default,
with only **background/foreground color** varying per button. Today each HUD
control styles itself independently (the compass is a raw `Container`; the
location FAB delegates to `FloatingActionButton.small`), so they don't match and
each new button (the Phase 5 settings cog) would reinvent its look.

This is a small foundation phase ahead of Phase 5 Navigation: the settings cog
button should be built **on `HudButton` from the start**, so `HudButton` lands
first.

## Requirements

- A reusable `HudButton` widget is the single source of HUD button styling:
  - **Fixed across all instances:** size, shape (circular), and drop shadow —
    matching the **current compass button** (44 dp circle, white, `Colors.black26`
    blur 4 / offset (0,2)). The compass size is the reference all buttons adopt.
  - **Per-instance:** `backgroundColor` (some buttons use a different bg color),
    an optional `foregroundColor`, the `child` (icon or custom paint), and the
    `onPressed` callback.
- **Tap handling** lives in `HudButton` (one consistent tap target / ripple or
  gesture), so callers only provide `onPressed` + child.
- **Existing HUD controls are migrated onto it** so everything is consistent:
  - **CompassButton** — render the needle `CustomPaint` as the `HudButton`
    child; keep its rotate-to-bearing and visibility (`AnimatedSwitcher`)
    behavior wrapping the button.
  - **LocationFab** — reskin onto `HudButton` (drop `FloatingActionButton.small`)
    so it matches size/shape exactly; the current "following" primary tint
    becomes a `foregroundColor`/`backgroundColor` variation.
  - **Settings cog** (Phase 5 navigation) — built on `HudButton` from the start
    (`Icons.settings`).
- Buttons remain individually placeable in the existing single SafeArea HUD
  `Stack` (no layout/positioning change mandated here).

## Non-requirements

- **No new HUD controls** beyond migrating the existing two (the settings cog is
  delivered by the navigation task, just built on this base).
- **No HUD layout/positioning redesign** — only the per-button visual base.
- **No theming system / design tokens** — a single widget with params is enough;
  don't over-abstract.
- **Not an interaction-taxonomy change** — buttons still dispatch their existing
  ids; this is purely the view layer.

## Dependencies / relationships

- **Lands before the settings cog button** in Phase 5 Navigation so the cog uses
  it immediately (`phase-5/navigation/`).
- Touches `lib/features/map/compass_button.dart` and `location_fab.dart`; new
  widget likely `lib/features/map/hud_button.dart`.
- Visual parity to verify on web + Android (the FAB reskin must not regress the
  follow-mode tint or tap feel).

## Open questions (resolve in design)

- Ripple vs plain tap: keep Material `InkWell` ripple, or the compass's current
  plain `GestureDetector`? Pick one for all.
- Whether `HudButton` owns the visibility/animation (compass shows/hides) or that
  stays in the caller (lean: stays in caller — not all buttons hide).
- Exact color API: `backgroundColor` + `foregroundColor` params vs a small set of
  named variants (default / accent). Lean to plain color params for now.
