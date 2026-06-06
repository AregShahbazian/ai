---
id: phase-2-follow-me
title: Follow Me — camera tracking toggle
status: implemented & verified on device (2026-06-06)
branch: feature/p2-follow-me
---

## Goal

Let the user lock the camera to their position so it auto-pans as they move,
and unlock it just as easily.

## Requirements

- A single **My Location button** lives in the HUD (bottom-right or similar,
  respecting safe areas).
- Tapping cycles through three modes — same pattern as the track/ POC:
  1. **Off** — dot visible, camera free.
  2. **Follow** (`tracking`) — camera centers on position as user moves.
  3. **Follow + heading** (`trackingCompass`) — camera also rotates to match
     device heading (requires heading-arrow feature to be meaningful).
- If the user pans/zooms manually while in Follow mode, tracking dismisses
  automatically (`onCameraTrackingDismissed`) and the button resets to Off.
- Button icon reflects current mode (e.g. `my_location` for Follow,
  `explore` or compass icon for Follow+heading, `location_searching` for Off).
- Use MapLibre's built-in `updateMyLocationTrackingMode` — no custom camera
  animation or position stream wiring.

## Dependency

Requires **My Location** (blue dot) to be implemented first.
