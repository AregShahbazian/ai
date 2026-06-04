---
name: project-orion-mvp-v01
description: Orion MVP (first release) scope; canonical spec at ~/ai/orion/mvp.md; screen-off recording is the acceptance gate
metadata:
  type: project
---

Orion's first-release MVP (defined 2026-06-03, **expanded 2026-06-04**). Canonical living spec: `~/ai/orion/mvp.md`. Clean rebuild — the `track` POC is inspiration only (it was buggy).

**In scope:** (1) track recording — start/stop/pause, **background/screen-off**, stored locally; (2) view tracks — stats (distance/duration/avg+max speed/elevation), polyline on map, list + toggle + rename/delete; (3) **export as GPX and KML**; (4) **offline map storage** — rectangle-draw region selection to download tiles, show downloaded + downloading regions (Google Maps / Gaia / track style).

**Out:** accounts/login/cloud sync (everything local), routing, waypoints, sharing/P2P.

**Acceptance gate:** a 2-hour screen-off, backgrounded walk must produce a continuous gap-free track surviving Android Doze/battery optimization. Spike this FIRST. `track` never tested screen-off recording — likely source of its bugs.

**Stack:** Flutter + MapLibre + local SQLite (consider Drift). Target Android/Play Store; primary device Asus Zenfone 10 / Android 15 (lenient stock-ish) — also validate on aggressive OEMs (Samsung/Xiaomi) before release.

Note: GPX export + offline tiles were originally *out* of the narrower v0.1 (`~/ai/orion/discussions/2026-06-03-mvp-v01-scope.md`); the 2026-06-04 expansion pulled them in. See also [[project-orion-mapping-app]], [[project-orion-decentralization-deprioritized]].
