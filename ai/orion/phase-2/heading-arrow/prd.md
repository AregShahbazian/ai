---
id: phase-2-heading-arrow
title: Heading Arrow — directional indicator on the dot
status: implemented & verified on device (2026-06-06); branch feature/p2-heading-accuracy
branch: (tbd)
---

## Goal

Show which direction the device (and therefore the user) is facing by
rendering a directional cone or arrow on the blue dot.

## Rationale

Without any heading cue the map is disorienting — the user cannot tell which
way they are walking or driving just from a dot. This is a must-have unless a
future feature provides an equivalent cue (e.g. a route arrow or a
north-locking compass that always keeps the map oriented).

## Requirements

- Heading indicator (cone/arrow) attached to the blue dot, pointing in the
  device's compass heading.
- Updates smoothly as device orientation changes; no jitter on small movements
  (apply a low-pass filter or use the platform's smoothed heading).
- Only visible when a heading reading is available; falls back to plain dot
  when compass is unavailable (e.g. some web browsers).
- Use `MyLocationRenderMode.compass` in MapLibre — no custom widget or
  canvas drawing. Only deviate if the stock mode is broken or unavailable.

## Dependency

Requires **My Location** (blue dot). Pairs naturally with **Follow Me**
`trackingCompass` mode.
