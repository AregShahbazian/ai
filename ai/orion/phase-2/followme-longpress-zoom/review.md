---
id: phase-2-followme-zoom
---

# Review — Long-press follow-me FAB

## Implementation summary (2026-06-07)

Long-press on the location FAB centers on the user and zooms to
`kDefaultFollowZoom` (15) as one motion; in Follow+Heading it delegates to the
tap handler (plain toggle to Off). Routed through the InteractionController via
the new `hud.followMe.longPress` id.

**Files:**
- `lib/features/map/map_constants.dart` — `kDefaultFollowZoom = 15.0`.
- `lib/core/interaction/interaction_ids.dart` — `followMeLongPress` id (+ `all`).
- `lib/features/map/location_controller.dart` — `onFabLongPressed()` +
  `_zoomToDefaultKeepingFollow()`.
- `lib/features/map/hud_button.dart` — optional `onLongPress`.
- `lib/features/map/location_fab.dart` — `onLongPress` passthrough.
- `lib/features/map/map_screen.dart` — register/unregister + `_onLocationLongPress`
  + shared `_handleLocationResult`.

## Verification

1. ✅ `flutter analyze` — no issues.
2. **Off → long-press (permission granted):** camera pans to the user then zooms
   to ~15 as one fluent motion; FAB shows Follow (`my_location`); dot follows.
3. **Off (already enabled) → long-press:** centers + zooms to 15, ends in Follow.
4. **Follow → long-press:** stays centered on the user, zooms to 15, stays Follow.
5. **Follow+Heading → long-press:** drops straight to Off, camera restores
   north-up/flat, no zoom change. (Identical to a tap in that mode.)
6. **Tap unchanged:** single taps still cycle Off → Follow → Follow+Heading → Off.
7. **Permission permanently denied → long-press:** "enable in Settings" SnackBar
   appears (same as tap); no camera move.
8. **Follow kept after zoom:** after a long-press zoom, the dot keeps following
   (the programmatic zoom's tracking-dismiss is suppressed + re-asserted) — pan
   by hand still drops to Off as before.
9. **Manual pan during the center→zoom:** interrupting mid-motion behaves sanely
   (drops to Off via the normal dismiss path; no stuck state).
10. **Web:** long-press fires and the camera zooms to 15; dot is plain (no native
    engine). Verify no conflict with browser long-press/context menu.
11. **InteractionController:** `hud.followMe.longPress` is recorded in the log on
    long-press and is re-dispatchable (`orion.dispatch('hud.followMe.longPress')`
    on web) — drives the same center+zoom.

### Trading-terminal-style context (N/A)
Orion has no TradingTab/symbol/resolution; the closest context actions are
nav screen open/close and app resume:

12. **Open Settings then back:** long-press still works after returning to the
    map (map stays alive under the route — Phase 5).
13. **Background → resume (Android):** after the GL surface is recreated, a
    long-press still centers + zooms.

## Round 1: device testing — two camera races (2026-06-07)

Driven on-device with `devLog('location', …)` traces streamed headless via the
new `./scripts/mobile/orion.sh logs scope=location` (added this round). Both the
original open questions turned out to be real bugs.

### Bug 1: zoom cancelled by active tracking — never reaches 15
**Root cause:** `_zoomToDefaultKeepingFollow` animated `zoomTo(15)` *while still
in `tracking`*. A programmatic camera move dismisses native tracking
(`map.follow.dismissed` fired mid-zoom), and the dismissal + re-assert stomped
the in-flight animation — the `await` returned early at **zoom ~4.4** (38 ms for
what should be a ~300 ms zoom).
**Fix:** mirror `resetOrientation` — drop to `none` → `animateCamera(zoomTo)` on a
free camera → re-enter the follow mode. Re-entering re-centers on the user at the
new zoom (tracking only pans, never zooms).

### Bug 2: Off path races the center transition — inconsistent zoom
**Root cause:** after Bug 1's fix, **Follow** worked every time but **Off** was
inconsistent (zoom landed anywhere from 1.4 to 15 on identical gestures). Entering
`tracking` from rest starts an **async center-to-user transition**; firing the
zoom immediately raced it. (Follow was reliable because it was already centered —
no pending transition.)
**Fix:** wait for the center transition to settle before zooming. Added an
`onCameraIdle`-driven signal (`LocationController.onMapIdle`, pumped from
`MapScreen._onCameraIdle`) that the long-press awaits (1.5 s timeout backstop)
between the press and the zoom. Matches the PRD's "let center-me play out, *then*
zoom."

### Decisions this round
- **Mobile-only.** Web already center+zooms on a tap via GL JS `GeolocateControl`
  (`fitBoundsOptions.maxZoom` 15); the long-press gesture/id/handler are gated
  `!kIsWeb`. PRD updated.
- **Press-first cycling.** Long-press now does the tap action first (advancing the
  cycle), then zooms if following — so Follow→Follow+Heading+zoom, not "stay
  Follow". PRD requirement matrix updated.
- **Zoom duration 1200 ms** (`kDefaultFollowZoomDuration`) — the SDK's ~300 ms
  default felt too fast.
- Debug `devLog` scaffolding removed after verification; the `logs` tooling kept
  and documented in `scripts/README.md`.

### Verification (device, all ✅)
1. ✅ `flutter analyze` clean (app + `tool/orion_remote.dart`).
2. ✅ **Off → long-press:** centers, then glides to zoom 15 — consistent across
   repeated presses (Bug 2 gone).
3. ✅ **Follow → long-press:** → Follow+Heading, zoom 15.
4. ✅ **Follow+Heading → long-press:** → Off, north-up, no zoom.
5. ✅ Tap cycle unchanged; follow kept after the zoom; manual pan still drops to Off.
