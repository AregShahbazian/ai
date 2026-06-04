# Orion — MVP (First Release) Definition

> Part of Orion's planning docs — see [`README.md`](README.md) (root overview:
> phases, discussions, and the ideas-to-realize backlog).

**Last updated:** 2026-06-04
**Status:** active MVP definition
**Supersedes:** the narrower "v0.1 local-only tracker" scope in
`discussions/2026-06-03-mvp-v01-scope.md` (which had GPX export and offline tiles
explicitly *out*). This is now the canonical first-release scope.

## Goal

Ship a real, useful GPS tracking + offline-maps app to the **Google Play Store**
for a known group of willing testers. Clean build — the `~/git/track` POC is
**inspiration only** (it was buggy), not a foundation.

## In scope (first release)

1. **Track recording**
   - Start / stop / pause toggle
   - **Background recording (screen off, app backgrounded, phone locked)**
   - Store locally
2. **View tracks**
   - Stats: distance, duration, avg/max speed, elevation gain/loss
   - Polyline on map (over base-map tiles)
   - List of saved tracks; tap to open; visibility toggle; rename/delete
3. **Export**
   - Export a track as common filetypes — **GPX** and **KML**
4. **Offline map storage**
   - **Rectangle-draw selection** to choose a map region to download for offline use
   - Show **downloaded regions** and regions **queued / currently downloading**
   - UX modeled on Google Maps / Gaia GPS / the `track` POC
   - Use downloaded tiles seamlessly when offline

## Out of scope (first release)

- Accounts / login / cloud sync — **everything local, no login system yet**
- Routing (A→B, hiking/moto routing) — explicitly deferred (offline routing is a
  rabbit hole; see `discussions/2026-06-03-decentralization-priority.md` notes)
- Waypoints
- Sharing / P2P / decentralized features (post-MVP — see decentralization discussion)

## Acceptance gate

**A 2-hour walk with the screen off and the app backgrounded produces a
continuous, gap-free track** — no dropped segments, accurate distance, surviving
Android Doze / battery optimization on a real device.

- **Spike this FIRST**, before stats/UI/export/offline work.
- Android requirements: foreground service + persistent notification,
  `ACCESS_BACKGROUND_LOCATION`, Doze survival.
- `track` never tested screen-off recording → unvalidated unknown, likely source
  of its bugs.

## Stack (confirmed)

- **Flutter** — cross-platform (free iOS later), strong plugins, existing experience.
- **MapLibre** — GPU vector tiles, free OSM/OpenFreeMap, no API key; future-proof
  for offline vector tiles (the offline-storage feature needs this).
- **Local storage: SQLite** — consider **Drift** (type-safe) over raw `sqflite`
  for high-volume track points and offline-region metadata.
- Biggest risk is **background GPS reliability** (stack-agnostic) — use a
  battle-tested location plugin and budget time.

## Target / test devices

- Platform: **Android**, Google Play.
- Primary test device: **Asus Zenfone 10 / Android 15** (close to stock = lenient
  background management).
- Validate background recording on an **aggressive-OEM device** (Samsung / Xiaomi /
  Huawei) before public release.

## Open questions

1. KML *and* GPX both at first release, or GPX first then KML? (GPX is the de-facto
   standard; KML is nice-to-have.)
2. Offline tiles: which zoom range(s) to download per region, and storage budget /
   size estimate shown to the user?
3. Which OEMs do the testers actually use? (determines real difficulty of the
   acceptance gate)
4. Tile source licensing for bulk offline download (OpenFreeMap terms vs. self-hosted)?

## Related discussions
- `discussions/2026-06-03-mvp-v01-scope.md` — earlier (now superseded) narrower scope
- `discussions/2026-06-03-decentralization-priority.md` — why P2P/decentralization is post-MVP
