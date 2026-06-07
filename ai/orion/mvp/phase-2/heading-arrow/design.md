---
id: phase-2-heading-arrow
---

# Orion — Phase 2: Heading Arrow (Design)

> Part of Orion — see [`README.md`](../../README.md). PRD: [`prd.md`](prd.md).

## Approach

Use MapLibre's stock heading rendering — **`MyLocationRenderMode.compass`** — not a
custom widget/canvas (PRD req. 4). It draws the directional cone on the dot from the
**device compass** and the plugin handles the smoothing, so there's no filter to
write.

Today the map passes `MyLocationRenderMode.normal`. Switch to `compass`.

## The one gotcha — conditional render mode

`MapLibreMap` asserts `renderMode == normal || myLocationEnabled`
(`maplibre_map.dart:71`). Our `enabled` flag starts **false** (until permission is
granted), so a hardcoded `compass` would assert-crash on first build. So render mode
is **derived from `enabled`**:

```
enabled ? compass : normal
```

This lives on `LocationController` as a `renderMode` getter (keeps `MapScreen`
declarative, logic testable — consistent with the recent refactor).

## Platform behaviour (matches PRD's fallback)

- **Android/iOS:** compass mode → heading cone on the dot, smoothed by the SDK.
- **Web:** the plugin prints "myLocationRenderMode not available in web" and renders
  a plain dot — exactly the PRD's "fall back to plain dot when compass unavailable".

No new permission (compass sensor needs none), no dependency, no settings UI.

## Pairs with Follow Me

In `trackingCompass` the camera already rotates to heading; the cone makes that
legible. In plain follow / off, the cone shows facing without moving the map.

## Out of scope

GPS-course heading (`MyLocationRenderMode.gps`, unsupported on iOS), a custom arrow,
or persisting anything.
