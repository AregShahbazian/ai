---
id: phase-2-heading-arrow
---

# Orion — Phase 2: Heading Arrow (Tasks)

> Part of Orion — see [`README.md`](../../README.md). PRD: [`prd.md`](prd.md) ·
> Design: [`design.md`](design.md).

## Checklist

- [x] `LocationController`: add a `renderMode` getter (`enabled ? compass : normal`)
      to satisfy the plugin assertion when the dot isn't enabled yet.
- [x] `map_screen.dart`: pass `myLocationRenderMode: _location.renderMode` (was a
      hardcoded `normal`); update the stale "no heading cone yet" comment.
- [x] `flutter analyze` clean.
- [ ] On-device verify (see `review.md`).
