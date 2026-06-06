---
id: phase-2-heading-arrow
---

# Orion — Phase 2: Heading Arrow (Review)

> PRD: [`prd.md`](prd.md) · Design: [`design.md`](design.md) · Tasks: [`tasks.md`](tasks.md)

## Round 1: initial implementation (2026-06-06)

Stock `MyLocationRenderMode.compass`, gated on `enabled` via
`LocationController.renderMode` (avoids the plugin's `compass requires
myLocationEnabled` assert). `flutter analyze` clean; tests pass.

**Files:**
- `lib/features/map/location_controller.dart` — `renderMode` getter
- `lib/features/map/map_screen.dart` — `myLocationRenderMode: _location.renderMode`

### Verification (on device)

1. Grant location → the dot shows a **heading cone** pointing where the phone
   faces.
2. Rotate the phone in place → cone rotates smoothly to match; no jitter at rest.
3. Pairs with Follow+heading: the camera rotates to heading and the cone stays
   aligned.
4. Before permission is granted (dot off) → no crash (render mode is `normal`
   while disabled).
5. Web → plain dot, no cone (expected; render mode unsupported on web).
