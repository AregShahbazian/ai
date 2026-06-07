---
id: phase-2-followme-zoom
title: Long-press follow-me FAB — center + zoom to default level
status: implemented & verified on device (2026-06-07)
branch: feature/followme-longpress-zoom
---

## Goal

Give the user a one-gesture "take me to my location, properly zoomed in" action.
A **long-press** on the location FAB centers on the user (the normal center-me
motion) and then zooms to a sensible default street-level zoom, as one fluent
motion — so the user doesn't have to tap-to-follow and then pinch-zoom in.

## Background

Today the FAB only handles a **tap**, which cycles Off → Follow → Follow+Heading
→ Off (see `mvp/phase-2/follow-me`). Follow centers the camera on the user but keeps
**whatever zoom is current** — and the app opens at a whole-world view
(`zoom: 1`). So enabling follow from a fresh launch leaves the user as a dot in a
world map; they must zoom in by hand. Long-press fixes that in one gesture.

## Requirements

- **Mobile (native) only.** Web already does center+zoom on a single tap — its
  MapLibre **GL JS `GeolocateControl`** flies to the user with a default
  `fitBoundsOptions.maxZoom` of 15. Native (`maplibre-native`) follow only pans
  at the current zoom, so the long-press synthesizes the zoom there. The gesture,
  its interaction id, and its handler are **not wired on web**.
- The location FAB gains a **long-press** gesture, in addition to the existing
  tap. Tap behavior is **unchanged**.
- **Long-press = the tap action first, then zoom** (if that left us following):
  1. **Off** → press cycles to **Follow** (centers on the user) → zoom to the
     **default follow zoom**. End: Follow, centered at default zoom.
  2. **Follow** (`tracking`) → press cycles to **Follow + Heading**
     (`trackingCompass`) → zoom to the default zoom. End: Follow+Heading, zoomed.
  3. **Follow + Heading** (`trackingCompass`) → press cycles to **Off** (restores
     north-up/flat) → **no zoom**.
  So long-press always advances the tap cycle, and additionally zooms whenever
  the press ended in a following mode.
- The center-me + zoom reads as **one fluent motion**: the press's center-on-user
  transition is allowed to **settle** before the zoom starts (otherwise the two
  camera animations race and the zoom stops short).
- **Default follow zoom = 15** (neighborhood/street level — parity with the
  `track` POC's center-me zoom). One shared constant `kDefaultFollowZoom`.
- The zoom glides over **`kDefaultFollowZoomDuration` (1200 ms)** rather than the
  SDK's fast ~300 ms default, for a smoother, more legible motion.
- Permission handling on the Off path mirrors the tap's enable path: a
  permanently-denied user gets the same "enable in Settings" SnackBar.
- The gesture routes through the **InteractionController** like every other
  interaction — a new id `hud.followMe.longPress` (capture + dispatch), so it's
  recorded/logged and re-dispatchable. (See the interaction-controller convention.)

## Non-requirements

- **No web implementation** — web's tap already covers it (see above).
- No change to the **tap** cycle or to any other HUD control.
- No new "default zoom" applied on app launch or on a plain tap — the default
  zoom is **only** reached via long-press. App launch stays whole-world.
- No configurable/user-adjustable default zoom yet (single constant — a settings
  toggle is captured separately in the backlog).
- No haptic feedback or long-press visual affordance beyond the platform's
  default ink response (can be revisited later).
