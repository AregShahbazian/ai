---
name: project-orion-dev-stack
description: Orion dev-loop & map-plugin decisions — web-first dev, maplibre_gl v0.26.1, iOS deferred
metadata:
  type: project
---

Orion stack/dev decisions (2026-06-04):

- **Dev loop = web-first.** Develop map/UI in Flutter **web** (fast reload, browser DevTools for tile/style/CORS). Test anything **native on the phone (Asus Zenfone 10)** — GPS/location, background/screen-off recording, and offline-region downloads do NOT run on web/desktop. Laptop has no GPS (only coarse, unreliable GeoClue WiFi/IP on Linux).
- **Desktop rejected for the loop:** the newer `maplibre` plugin runs desktop via maplibre-gl-js in a WebView (no parity gain over web), and Linux support is uncertain.
- **Map plugin = `maplibre_gl`, pinned v0.26.1** (track used ^0.25.0 — bump). Chosen over the newer josxha `maplibre` because: user principle is stable/proven; `maplibre_gl` is the official maplibre.org plugin, actively maintained (v0.26.1 ~2026-05-14, ~63.7k weekly downloads), web-capable, iOS-ready, and `track`'s reference code already uses it. Desktop (the new plugin's only real edge) is moot under web-first. Revisit `maplibre` as a future successor.
- **iOS = deferred, kept clean.** No Apple release/testing for a long time; pick iOS-capable deps and isolate platform-specific code so iOS can be added later. Both plugins support iOS, so it doesn't constrain the choice.

Full discussion: `~/ai/orion/discussions/2026-06-04-dev-loop-and-map-plugin.md`. See also [[project-orion-mvp-v01]], [[project-orion-mapping-app]].
