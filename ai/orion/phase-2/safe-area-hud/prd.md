---
id: phase-2-safe-area
---

# Orion — Phase 2: Safe-area HUD (PRD)

> Part of Orion — see [`README.md`](../../README.md) (root overview).

**Date:** 2026-06-06
**Phase:** 2 (map polish, builds on Phase 1 map shell)
**Status:** implemented & verified on device (2026-06-06); branch `feature/p2-safe-areas`

## Problem

On Android the map's controls collide with system chrome: the native MapLibre
compass (top-right) overlaps the status bar and front-camera cutout, and the
attribution "i" (bottom-right) is hidden behind the nav bar or falls outside the
screen's rounded corners.

## Requirements

1. All on-screen map controls must stay inside the device **safe area** — clear of
   the status bar, navigation bar, display cutout/camera, and rounded corners.
2. Must hold across **orientation changes** (portrait + both landscapes) and
   different device insets, recomputing as the safe area changes.
3. The **native** MapLibre controls (compass, attribution) must be inset too, not
   just Flutter widgets — they live in the platform view, outside Flutter's tree.
4. Provide a **single, scalable inset mechanism** for future Flutter HUD (buttons,
   panels) so new controls inherit safe-area insets without per-widget math.
5. No new permissions, no added user-facing UI beyond what already exists
   (Phase 1 is still "just the map"; this is polish).

## Non-requirements

- Replacing the native compass/attribution with Flutter equivalents (track's
  approach). Deferred until real HUD controls exist; native controls stay as the
  documented exception, inset via the plugin's margin params.
- Any new buttons/panels themselves — this phase only establishes the layout.
