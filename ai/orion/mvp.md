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
   - Export a track as **GPX** (first release). KML and other formats come later.
4. **Offline map storage**
   - **Rectangle-draw selection** to choose a map region to download for offline use
   - Show **downloaded regions** and regions **queued / currently downloading**
   - **User interactions and choices mirror the `track` POC** (same flow: draw
     rectangle → pick zoom range → download with progress → per-region size
     estimate). UX also in line with Google Maps / Gaia GPS.
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
- **Target: a wide range of common Philippine Android phones** must record reliably
  in the background — not just the dev device. Common PH brands include **Xiaomi /
  Redmi, Samsung, Realme, Oppo, Vivo** (most are aggressive background-app killers).
- Therefore background recording **must include OEM battery-killer mitigations** as
  a requirement: foreground service + persistent notification, request "ignore
  battery optimizations", and follow per-OEM guidance (cf. dontkillmyapp.com).
- Primary dev device: **Asus Zenfone 10 / Android 15** (close to stock = *lenient*;
  passing here is necessary but NOT sufficient).
- **Validate on aggressive-OEM devices common in PH (Xiaomi/Redmi, Samsung, Realme,
  Oppo) before public release** — these are the real acceptance bar.

## Open questions

1. ~~GPX + KML both, or GPX first?~~ **Resolved:** **GPX first** release; KML and
   other formats added later.
2. ~~Offline tiles: zoom range / size estimate / interactions?~~ **Resolved:**
   **mirror the `track` POC** — same user interactions and choices (draw rectangle
   → pick zoom range → download with progress → per-region size estimate).
3. ~~Which OEMs do testers use?~~ **Resolved:** target a **wide range of common PH
   Android phones** (Xiaomi/Redmi, Samsung, Realme, Oppo, Vivo) — background
   recording must be robust across aggressive OEMs, not just the stock-ish Zenfone.
   (Raises the bar: OEM battery-killer mitigations are now a recording requirement —
   see Target / test devices.)
4. ~~Tile-source licensing for bulk offline download?~~ **Resolved:** OpenFreeMap's
   **public server** has no request limits and permits commercial use (attribution
   `OpenFreeMap © OpenMapTiles Data from OpenStreetMap` required). For **MVP1** (a
   handful of testers) the public server is fine — negligible load. **Self-hosting
   is deferred to AFTER MVP1**, before any real-scale public launch: OpenFreeMap
   publishes **weekly full-planet MBTiles** intended for self-hosting, so we'd host
   PH-region tiles from those rather than scraping the public server at scale.
   (`track` already bulk-downloads OpenFreeMap `liberty` via `downloadOfflineRegion`.)

## Related discussions
- `discussions/2026-06-03-mvp-v01-scope.md` — earlier (now superseded) narrower scope
- `discussions/2026-06-03-decentralization-priority.md` — why P2P/decentralization is post-MVP
