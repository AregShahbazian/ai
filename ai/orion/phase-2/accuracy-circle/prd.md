---
id: phase-2-accuracy-circle
title: Accuracy Circle — location uncertainty halo
status: implemented & verified (2026-06-06): web circle visible; Android heading-arrow works, circle not shown — accepted; branch feature/p2-heading-accuracy
branch: (tbd)
---

## Goal

Give the user a visual sense of how confident the GPS fix is by drawing a
translucent circle around the blue dot whose radius equals the reported
accuracy in metres.

## Requirements

- Semi-transparent blue halo centred on the blue dot, radius = accuracy value
  from the location stream.
- Shrinks as GPS locks in, expands when signal is weak (indoors, urban canyon).
- Does not obscure map detail at high accuracy — circle becomes tiny once GPS
  locks to <5 m.
- Web: browser geolocation reports an accuracy value too; same rendering path.

## Notes

Nice to have — deliver after My Location and Follow Me are stable. Prefer
MapLibre's built-in rendering over a custom layer; only add a custom layer if
the stock circle is absent or insufficient.
