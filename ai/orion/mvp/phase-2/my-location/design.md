---
id: phase-2-my-location
---

# Orion — Phase 2: My Location — blue dot (Design)

> Part of Orion — see [`README.md`](../../README.md). PRD: [`prd.md`](prd.md).

## Approach

Use MapLibre's **built-in** location dot — don't draw our own. The plugin renders a
platform-native blue dot when `myLocationEnabled: true`, so this task is mostly
permission plumbing + a per-platform enable, not custom rendering.

```
myLocationEnabled:      _locationEnabled   // state flag, flipped on after grant
myLocationRenderMode:   normal             // plain dot — no heading cone (that's heading-arrow)
myLocationTrackingMode: none               // no camera follow (that's follow-me)
```

Changing `_locationEnabled` rebuilds `MapLibreMap`; the plugin diffs its options and
calls `setMyLocationEnabled` — no controller call needed.

## Permission flow (native)

`permission_handler` (same dep `track` used), requested **once** on screen init:

1. `initState` → `_initLocation()`.
2. Native: `Permission.locationWhenInUse.request()`.
   - Granted → `setState(_locationEnabled = true)` → dot appears, no follow.
   - Denied / permanently denied → leave `_locationEnabled = false`. Dot simply
     absent. **No crash, no SnackBar, no nagging** (PRD: graceful denial). A future
     "enable location" affordance can re-request; out of scope here.

We request **before** enabling so the native SDK never enables the layer without a
grant (avoids a platform crash on Android).

## Platform split (the one real nuance)

The `maplibre_gl` web backend implements location differently from native, and this
shapes the design:

| | Android / iOS | Web |
|---|---|---|
| `myLocationEnabled: true` | renders the dot immediately (once permission granted) | **adds** a standard MapLibre *geolocate control* (tap-to-locate button, bottom-right) but does **not** auto-show the dot |
| permission | `permission_handler` prompt | browser prompt, fired by the geolocate button |
| dot appears | automatically | after the user taps the locate button |

Why: on web the plugin only *triggers* geolocation through a tracking-mode change
(`setMyLocationTrackingMode != none`) or a location-engine-properties change — both
of which also turn on **camera follow**. There is no public "show a static,
non-following dot" trigger. Forcing one would either jump the camera off the
Philippines framing on load or bleed into the **Follow-Me** task.

**Decision:** on web, ship the plugin's built-in locate button (user taps → grant →
dot). Auto-show + live follow on web arrives *for free* with Follow-Me, which legitimately
flips tracking mode. So:

- `_initLocation()` short-circuits on `kIsWeb`: skip `permission_handler` (no real web
  impl), just set `_locationEnabled = true` so the locate button is present.
- Native does the permission request.

This keeps the blue dot working on all three platforms (PRD req.) while honoring the
task boundaries — the *automatic* dot is native-only by design, not by omission.

## Platform manifests

- **Android** (`AndroidManifest.xml`): add `ACCESS_FINE_LOCATION` +
  `ACCESS_COARSE_LOCATION`.
- **iOS** (`Info.plist`): add `NSLocationWhenInUseUsageDescription` (foreground only —
  no "Always" key, no background mode).
- **Web**: nothing; browser geolocation needs no manifest.

## Dependency

Add `permission_handler: ^11.4.0` (already resolved in pub-cache; `_html` variant
compiles cleanly for web, so the import is safe even though we gate it at runtime).

## Out of scope (separate tasks)

Follow-me camera, heading cone (`render mode: compass`), accuracy circle, a HUD
"locate me" FAB. This task is only: *the dot exists*.
