---
id: phase-2-accuracy-circle
---

# Orion — Phase 2: Accuracy Circle (Tasks)

> Part of Orion — see [`README.md`](../../README.md). PRD: [`prd.md`](prd.md) ·
> Design: [`design.md`](design.md).

## Checklist

- [x] Confirm the stock accuracy ring is provided by the plugin (native default +
      web `showAccuracyCircle: true`) — **no code needed**.
- [ ] On-device verify the ring shows at street zoom and resizes with accuracy
      (see `review.md`). If genuinely absent on native → fall back to a custom
      `CircleLayer` (deferred per design).
