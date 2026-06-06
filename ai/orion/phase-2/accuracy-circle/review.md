---
id: phase-2-accuracy-circle
---

# Orion — Phase 2: Accuracy Circle (Review)

> PRD: [`prd.md`](prd.md) · Design: [`design.md`](design.md) · Tasks: [`tasks.md`](tasks.md)

## Round 1 (2026-06-06)

**No code.** The accuracy ring is built into MapLibre's location component on native
(default) and into the web GeolocateControl (`showAccuracyCircle: true`). Enabling
the dot already provides it on all platforms; the plugin exposes no toggle to add.

### Verification (on device)

1. Grant location, then **zoom to street level** → a translucent ring is centred on
   the dot. (At the PH-wide zoom it's metric and sub-pixel, so invisible — expected.)
2. Move indoors / weak signal → ring **grows**; back to open sky with a sharp GPS
   fix → ring **shrinks** to a few metres.
3. Web → ring present around the dot after locating.
4. **If the ring is genuinely absent on native** (not just too small to see) → the
   stock circle is insufficient; fall back to a custom `CircleLayer` sized from
   `onUserLocationUpdated.horizontalAccuracy` (deferred per design — reopen this task).
