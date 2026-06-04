---
id: phase-1-map
---

# Orion — Phase 1: Map Shell (PRD)

**Date:** 2026-06-04
**Phase:** 1 of the first-release MVP (see `~/ai/orion/mvp.md`)
**Scope of this doc:** requirements only — no design or implementation choices.

## Purpose

Deliver the smallest possible working Orion app: a single full-screen map. This
phase de-risks the foundation (Flutter + MapLibre rendering end-to-end on a real
device) before any product features are built. No tracking, no other pages.

## Requirements

### Map display
1. The app launches **directly to a single full-screen map**. There are no other
   pages, no navigation, no tab/drawer/bottom bar.
2. The map uses the **OpenFreeMap `liberty`** style
   (`https://tiles.openfreemap.org/styles/liberty`) — free, no API key, no usage
   limits. A **single** style only.
3. On first launch the camera is **framed on the Philippines** — the whole country
   is visible, fit to its geographic bounds (approx. SW `4.5°N, 116°E`, NE
   `21°N, 127°E`). Framing must look correct across phone screen sizes (fit to
   bounds, not a single hardcoded zoom).
4. Visible **map attribution** for OpenStreetMap / OpenFreeMap is always shown
   (licensing requirement).

### Interaction
5. All standard map gestures are **enabled**: pan/scroll, pinch-zoom,
   double-tap-zoom, **rotate**, and **tilt/pitch**.
6. Camera movement is **free** — no min/max zoom lock and no panning bounds; the
   user can move anywhere on the globe.

### Offline / connectivity behavior
7. The app is **online-tile-based**. Tiles are fetched over the network and
   **cached automatically** by the rendering engine; no explicit offline
   download/storage exists in this phase.
8. **The app launches and remains usable offline.** Connectivity never gates the
   UI. When offline:
   - Previously cached tiles (and the cached map style) **render normally**.
   - Areas/zoom levels not yet cached show **blank tiles** — this is acceptable;
     there is **no error screen** and the app does not block.
   - A **simple, non-intrusive offline indicator** is shown while the device has
     no connectivity, and disappears when connectivity is restored. Its role is
     purely to explain blank areas — it never obstructs the map.
9. **Cold-start caveat (acceptable):** on a first-ever launch with no prior
   connectivity, the map style has never been fetched, so the map may appear
   empty. This is expected; the offline indicator explains it. No special
   handling is required beyond the indicator.

### Branding
10. The app ships with the correct application identity: name **Orion**,
    `applicationId` **`com.mby4m.orion`**.
11. The **app logo** will be provided by the user later. Phase 1 may ship with a
    placeholder launcher icon; the requirement is that the logo is swappable when
    delivered.

### Quality
12. The app must build and run on the primary test device (**Asus Zenfone 10,
    Android 15**) and render/pan/zoom the map smoothly.
13. Built on a **stable, proven stack and dependency versions**. (Specific
    package and version selection — including the MapLibre Flutter plugin choice —
    is a design-phase decision, not fixed by this PRD.)

## Non-requirements (explicitly out of Phase 1)

- Track recording, pausing, or storage
- Viewing tracks, stats, or polylines
- GPX / KML export
- Explicit offline map storage / rectangle-select region download & management
- User location / GPS, location permissions, "my location" indicator
- Multiple map styles, layer switching, or light/dark theming
- Accounts, login, cloud sync
- Routing / navigation
- Any secondary screen, settings, or menu

## Open questions

1. Supported orientations — portrait only, or portrait + landscape?
2. Should a placeholder launcher icon ship in Phase 1, or wait for the real logo
   before any Play upload?

## Related
- `~/ai/orion/mvp.md` — first-release MVP definition
- `~/ai/orion/discussions/2026-06-04-mvp-expansion-and-phase1.md` — Phase 1 decisions
- `~/git/track` — POC, inspiration only (default style/camera/gestures reference)
