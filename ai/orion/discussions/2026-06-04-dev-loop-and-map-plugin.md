# Discussion — Dev loop (web-first) & map plugin choice

**Date:** 2026-06-04
**Mode:** discussion (answers-only)
**Outcome:** Dev loop is **web-first** (phone for native features); map plugin locked to **`maplibre_gl` v0.26.1**; iOS is a deferred-but-kept-clean target.

## Summary / conclusions

### Dev environment: web-first
- For Phase 1 and all map/UI work, develop **in the browser (Flutter web)** — fastest reload, great DevTools (watch tile/style/CORS network requests), zero device friction.
- **Desktop was rejected** for the loop: on the newer `maplibre` plugin, Windows/macOS run the *same* maplibre-gl-js engine via WebView (no fidelity gain over web, more build setup), and **Linux support is uncertain**. (Correction logged: an earlier claim that "desktop = native engine = better parity" was wrong — desktop is the JS/WebView path, like web.)
- **Anything native must be tested on the phone (Asus Zenfone 10):** GPS/location, background/screen-off recording, and offline-region downloads do **not** run on web/desktop.
- Laptop location is unreliable anyway — no GPS chip; Linux only offers coarse WiFi/IP location via GeoClue (degraded). Real movement/tracking = phone only.
- CORS: OpenFreeMap serves CORS headers, so browser use is fine.

### Map plugin: `maplibre_gl` (locked)
- **Decision: `maplibre_gl`, pinned to v0.26.1** (track used `^0.25.0` — bump it).
- Why over the newer `maplibre` (josxha):
  - User principle is **stable & proven**: `maplibre_gl` is the official community plugin (verified `maplibre.org` publisher), ~63.7k weekly downloads, 108 likes, v0.26.1 published ~2026-05-14, 542 commits, no deprecation — actively maintained, not stale.
  - The newer `maplibre`'s main edge was desktop — moot once we chose web-first (both support web).
  - Both support **iOS** and **offline regions**, so neither differentiates there.
  - `track`'s working reference code is already on `maplibre_gl` → less translation friction.
- Both plugins' platform/offline facts (verified):
  - `maplibre_gl`: Android, iOS, web (no desktop). Offline regions: yes (proven).
  - `maplibre` (josxha) v0.3.5: Android/iOS native; web + Windows/macOS via gl-js WebView; Linux unclear. Offline regions via `OfflineManager` (downloadRegion/list/get/merge, progress stream) — **not on web**.
- Re-evaluate `maplibre` later as the likely long-term successor, but don't take the bleeding edge now.

### iOS
- Kept in mind for stack choices (pick iOS-capable deps, isolate platform-specific code), but **no Apple release/testing for a long time**. Both plugin options already support iOS, so the choice isn't constrained by it. iOS = deferred, groundwork-clean.

## Open questions
1. Phase 1 PRD open items still stand: supported orientations; placeholder launcher icon vs. wait for logo.
2. When iOS is eventually introduced, confirm `maplibre_gl` iOS setup is still current (CocoaPods/SDK versions).

## Ideas to realize
- **Dev workflow:** set up Flutter **web** as the primary dev/debug target for map & UI; reserve the phone for location/recording/offline testing.
- **Phase 1 stack:** Flutter + **`maplibre_gl` v0.26.1**, OpenFreeMap `liberty`, web-first.
- **iOS groundwork:** keep platform-specific code abstracted/isolated so iOS can be added later without rework (no Apple builds/tests for now).
- **Plugin re-evaluation (future):** revisit the newer `maplibre` plugin as a possible migration once it (and the project's needs) mature.
- **Offline regions (MVP, on device):** use `maplibre_gl`'s proven offline-region download API; test only on phone.

## Related
- `~/ai/orion/phase-1/prd.md` — Phase 1 PRD (`phase-1-map`)
- `~/ai/orion/mvp.md` — first-release MVP definition
- `~/ai/orion/discussions/2026-06-04-mvp-expansion-and-phase1.md`
