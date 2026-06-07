---
id: phase-5-navigation
title: Navigation — app shell (persistent map + screens)
status: implemented (device verification pending)
branch: feature/p5-navigation
---

## Goal

Stand up Orion's **app shell**: the plumbing that lets the user leave the map for
a full-screen page (settings, tracks, routes — none built here) and come back.
This phase ships only the **navigation scaffolding** + one trivial placeholder
destination to prove it; the real pages arrive in later phases.

The navigation is built around one non-negotiable architectural pillar (below).

## Pillar: the map stays alive

**Navigating away from the map must never unmount, dispose, re-create, or
re-render the map.** Returning to the map must be instant — same
`MapLibreMapController`, same camera, same sources/layers/data already on it. No
remount, no reload, no blank flash, no re-fit.

Why this is a pillar and not a "nice to have":
- The map is the heart of the app and the most expensive thing it owns (native
  GL surface + style + every future track/route/waypoint layer).
- Re-mounting means re-creating the controller, re-loading the style, and
  **re-adding all track/route/waypoint data** — cost that grows with the user's
  data. `~/git/track` (the POC) suffered exactly this once tracks/routes and
  their syncing were introduced; navigation became sluggish.
- Concurrents (Gaia GPS, Google Maps) keep a single persistent map instance and
  present panels/sheets/pages **over** it rather than swapping it out. We match
  that model deliberately.

### What "alive" means concretely

- The map widget's `State` and its `MapLibreMapController` are created **once**
  for the app's lifetime and never disposed by navigation.
- Map-owned state (camera, follow mode, location dot, future data layers) is
  preserved across navigation with **zero** rebuild on return.
- Caveat to handle in design: keeping the Dart `State` alive is the default for
  `Navigator.push` (an opaque page does **not** dispose the route beneath it),
  but a fully-covered **platform view** (the native GL surface) may still be
  torn down/recreated by the OS when offstage — the same lifecycle that already
  forced `translucentTextureSurface: true`. Design must decide how far we go:
  controller/data preservation is mandatory; avoiding GL-surface recreation is a
  goal, weighed against memory/battery of keeping the surface warm.

### Default presentation = over the map, not instead of it

- The **default** navigation pattern keeps the map mounted underneath: pages are
  presented **above** the persistent map (push/overlay/shell), never by
  swapping the map widget out of the tree.
- **Exception pages are allowed in the future** — a destination may legitimately
  want the map gone (e.g. a heavy full-screen editor). That must be a
  deliberate, opt-in exception per destination, **not** the default, and clearly
  marked as such. The shell defaults to map-alive; opting a page out is explicit.

## Requirements

### Shell structure

- Introduce an **app shell** that owns the persistent map and hosts navigation,
  replacing today's `MaterialApp(home: MapScreen())` single-screen setup.
- The map is mounted by the shell **once** and survives every navigation.
- A destination is reached from a **HUD button** (new entry point in the map
  HUD) and returns to the live map via back/close.
- This phase ships **one placeholder destination** (e.g. an empty "Menu" or
  "Settings" page with a title + back) — enough to prove navigate-away /
  navigate-back keeps the map alive. No real page content.

### Snappiness (acceptance gate)

- Navigating map → page → map is **visibly instant** and causes **no map
  redraw/remount**. This is a pass/fail gate, verified on device — ideally with
  data on the map (a stand-in layer) so the no-reload guarantee is meaningful,
  not just true on an empty map.

### Modelled in the interaction taxonomy (Phase 3) from the start

- Every navigation action wires through the `InteractionController` **both ways**
  (capture + programmatic dispatch), per the standing interaction rule — no
  inline-handler bypass.
- Add the navigation ids the Phase 3 PRD already anticipated
  (`nav.screen.open` / `nav.screen.close`, plus the HUD entry-point tap) to the
  closed taxonomy in `interaction_ids.dart`, with payload carrying which screen.
- Opening/closing a screen must be programmatically dispatchable (so automation
  and the web/native dev bridges can drive navigation).

## Non-requirements (scope boundaries)

- **No real destination content** — settings, tracks list, routes, etc. are
  later phases. Only the shell + a placeholder page here.
- **Not GPS/A→B routing.** "Navigation" here is *app-screen* navigation only
  (see `mvp.md` / README note). Turn-by-turn remains out of scope.
- **No deep-linking / URL routing** beyond what the shell needs internally.
- **No bottom-nav/tab redesign** mandated — pick the lightest structure in
  design that satisfies the map-alive pillar.

## Dependencies / relationships

- Builds on Phase 3 (`InteractionController`) — navigation is the first
  interaction domain added *after* the controller existed, so it's modelled in
  the taxonomy from day one.
- The HUD entry point lives in the existing single SafeArea HUD layer in
  `map_screen.dart` (where the compass button + location FAB already are).
- Sets the stage for Phase 6+ (tracks/routes pages) and Phase 8 (recording
  controls) — those become destinations hosted by this shell.

## Build-vs-buy directive (design must answer first)

Before designing any custom shell, **design.md must evaluate
`go_router`'s `StatefulShellRoute`** (persistent, keep-alive branches backed by
an `IndexedStack` — the off-the-shelf realization of this PRD's
"persistent state, transient screens" pillar). Prefer existing
API/configuration over hand-rolled navigation.

**If design concludes we should build navigation plumbing ourselves instead of
relying on `go_router`/an existing API, that must be called out explicitly and
loudly in design.md** — with the specific reason the off-the-shelf option
doesn't fit — so the choice to reinvent is a conscious, reviewed decision, not a
default.

## Open questions (resolve in design)

- **Shell mechanism**: first evaluate `go_router` `StatefulShellRoute` (above).
  Only if it doesn't fit, compare: persistent map behind a nested `Navigator`
  (pages pushed as opaque routes over the map) vs an `IndexedStack`/`Offstage`
  shell vs a root `Stack` with the map always at the bottom. Which best
  guarantees the controller is never disposed *and* minimizes GL-surface
  recreation?
- **Offstage platform view**: do we accept native GL-surface teardown when a
  page fully covers the map (controller/data still preserved), or keep the
  surface warm (memory/battery cost)? Measure both.
- **Exception-page opt-out API**: how a future destination declares "tear the
  map down for me" cleanly, without weakening the default.
- **Transition/animation** for entering/leaving a destination (slide, fade,
  sheet) — and whether it should hint that the map is still there underneath.
