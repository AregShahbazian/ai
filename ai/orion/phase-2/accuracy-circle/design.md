---
id: phase-2-accuracy-circle
---

# Orion — Phase 2: Accuracy Circle (Design)

> Part of Orion — see [`README.md`](../../README.md). PRD: [`prd.md`](prd.md).

## Finding: it's already rendered — built in on both platforms

The PRD says prefer MapLibre's built-in circle, custom only if the stock one is
absent. It is **not** absent:

- **Android/iOS:** MapLibre's `LocationComponent` draws the translucent accuracy
  ring **by default**, sized to the fix's reported accuracy and animated as it
  changes. The `maplibre_gl` plugin (0.26.1) exposes **no** option to toggle or
  restyle it — it's simply on whenever the dot is on.
- **Web:** the GeolocateControl is created with `showAccuracyCircle: true` hardcoded
  (`maplibre_web_gl_platform.dart:772`).

So there is **no code to write** — enabling the dot (My Location) already gives the
accuracy circle on every platform.

## Why it "looked absent" on mobile

The ring is **metric** (radius = accuracy in metres). At the Philippines-wide initial
zoom, even a 100 m fix is sub-pixel, so it's invisible. Web appeared to show it
because triggering its GeolocateControl also zooms toward the user. The circle
becomes visible once you're at street-level zoom (and, with high-accuracy GPS now
locking to ~5–16 m, it's correctly small). This is the desired behaviour, not a bug.

## Decision

Ship the **stock** circle — no custom `Circle`/`FillLayer`. A custom layer would
duplicate what the SDK already does, add per-frame work, and drift from the dot. Only
revisit if on-device verification shows the native ring is genuinely missing (then a
custom `CircleLayer` sized from `onUserLocationUpdated.horizontalAccuracy` would be
the fallback — explicitly deferred).

## Out of scope

Custom colour/animation, a separate uncertainty readout, web-vs-native parity tuning.
