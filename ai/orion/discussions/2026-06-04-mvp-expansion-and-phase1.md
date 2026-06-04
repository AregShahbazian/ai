# Discussion — MVP expansion, app identity, release phases & Phase 1

**Date:** 2026-06-04
**Mode:** discussion (answers-only)
**Outcome:** First-release MVP expanded; app identity locked; releases are organized into phases; Phase 1 defined as a single map screen focused on the Philippines.

## Summary / conclusions

- **MVP expanded** beyond the earlier narrow "local-only tracker." First release now also includes **GPX/KML export** and **offline map storage** (rectangle-draw region selection, showing downloaded + downloading regions — Google Maps / Gaia / `track` style). Canonical spec lives in `~/ai/orion/mvp.md`, which supersedes `discussions/2026-06-03-mvp-v01-scope.md`.
- **App identity locked:** public name = **Orion** (final, not a working title). `applicationId` / namespace = **`com.mby4m.orion`** — reused from the `track` POC, which was **never published**, so the id is free. Permanent once published; `mby4m` must remain a namespace the user controls.
- **Releases are split into phases.** Each release is delivered in phases.
- **Stack discipline:** build on the **most stable, proven stack / dependencies / versions** available. `track` is **inspiration only** — for implementation reference and to understand intent — not gospel. Where track's approach was wrong/buggy, propose and use better ways.

## Phase 1 (first phase of the MVP) — definition

A single-screen map app, nothing else:

- Working Flutter app that launches straight to a **full-screen map**
- Camera **hardcoded to focus on the Philippines** — implement as a fit to the
  country bounding box (≈ lat 4.5°–21°N, lng 116°–127°E; center ~12.8°N, 122°E,
  ~zoom 5–6) rather than a single fixed zoom, so it frames consistently across
  screen sizes
- **No other pages, no navigation**
- Basic map gestures: **zoom / pan / scroll / rotate**
- Map provider / tile source taken from `track` (OpenFreeMap outdoor via MapLibre)
- **App logo:** user will provide later
- Purpose: de-risk the foundation (Flutter + MapLibre rendering end-to-end) before any features

## Open questions

1. KML *and* GPX both at first release, or GPX first then KML?
2. Offline tiles: zoom range(s) per region + storage-size estimate shown to user?
3. Tile-source licensing for bulk offline download (OpenFreeMap terms vs. self-hosted)?
4. Keep the superseded `2026-06-03-mvp-v01-scope.md` as history? (leaning yes — cheap record + explorer fodder)

## Ideas to realize

- **Phase 1:** Flutter + MapLibre single-screen map, hardcoded Philippines focus (bbox fit), basic gestures only, OpenFreeMap outdoor tiles, no navigation. (Next build target.)
- **Track recording:** start/stop/pause, reliable background/screen-off recording (foreground service, ACCESS_BACKGROUND_LOCATION, Doze survival) — the MVP acceptance gate.
- **Track viewing:** stats (distance/duration/avg+max speed/elevation), polyline on map, saved-tracks list with toggle/rename/delete.
- **Export:** GPX and KML export of tracks.
- **Offline map storage:** rectangle-draw region selection, download tiles for offline, show downloaded vs. downloading regions, seamless offline use.
- **App logo / branding:** integrate logo once user provides it.
- **Phased release structure:** define Phase 2+ later (recording → viewing → export → offline, sequencing TBD).
- **Stack-validation discipline:** pick stable/proven dep versions; revisit any `track` approach that was buggy.

## Related discussions
- `discussions/2026-06-03-mvp-v01-scope.md` — earlier (superseded) narrower MVP scope
- `discussions/2026-06-03-decentralization-priority.md` — P2P/decentralization is post-MVP
- Spec: `~/ai/orion/mvp.md`
