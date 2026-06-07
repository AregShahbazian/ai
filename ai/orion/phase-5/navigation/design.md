---
id: phase-5-navigation
title: Navigation — design
status: implemented & verified on web + Android (2026-06-07)
branch: feature/p5-navigation
---

## Build-vs-buy verdict (read first)

**We are NOT building custom navigation plumbing.** Navigation uses
**`go_router`** (off-the-shelf). The only thing we write is the *composition*
(a `Stack` with the persistent map at the bottom) and the *wiring* of our
existing `InteractionController` ids to go_router's API — not a router, not a
back-stack, not keep-alive machinery.

The single design choice is **which go_router shell** realizes the map-alive
pillar. Evaluated below.

### `StatefulShellRoute.indexedStack` — evaluated, NOT used for the map

`StatefulShellRoute.indexedStack` keeps each branch alive in an `IndexedStack`
(all branches mounted, only the active one shown). It's the idiomatic answer for
**bottom-nav / tab** UIs where branches are peers.

Rejected for our map because:

1. **Wrong mental model.** The map is not a *peer tab* of Settings/Tracks — it's
   the persistent **backdrop**. In an `IndexedStack`, only the active branch is
   shown; while on Settings the map branch is **offstage**, not behind. That
   contradicts the Gaia/Google "panels over a still-present map" model.
2. **Re-introduces the GL-teardown risk.** `IndexedStack` keeps inactive
   children in the tree but wraps them `Offstage` (not painted). The map's Dart
   `State`/controller survive (good), but a fully-offstage **native GL platform
   view** is exactly the lifecycle that already forced
   `translucentTextureSurface: true` — so we'd be fighting surface teardown the
   whole time the user is off-map.

It stays a *future* candidate for a **cluster of data pages** (e.g. a
tracks/routes tab group) whose widget state we want preserved — but even there
our no-refetch guarantee comes from long-lived controllers (below), so it's
optional, not load-bearing.

### Nested child routes + `go`/`goNamed` — chosen

The map is the `/` route; **screens are its child routes**. Navigating to one
(`goNamed('settings')` → URL `/settings`) makes go_router match `/` **and**
`settings`, building the Navigator stack `[MapScreen, SettingsScreen]` — so the
map (the **parent** route) stays matched and mounted beneath the screen, never
disposed or reloaded, **and** the URL reflects the screen (deep-linkable,
refresh-safe, browser-back correct). Popping returns to the same live map. No
`Stack`, no overlay juggling, no custom plumbing.

```
GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(path: '/', name: 'map', builder: (_, __) => const MapScreen(), routes: [
      GoRoute(path: 'settings', name: 'settings', builder: (_, __) => const SettingsScreen()),
      // later: tracks, routes … (children of '/' keep the map alive)
    ]),
  ],
)
```

Why this and **not `ShellRoute`** (rejected): `ShellRoute` is built for *shared
chrome* — its `child` is meant to **be** the page body, with persistent UI (a nav
bar / drawer) wrapped around it. Using it to hold the map as a *backdrop* under an
always-present `child` overlay is off-label: it forces a transparent home route
and an `IgnorePointer` (the smell we removed in an earlier cut). Nested child
routes give the map-alive guarantee idiomatically.

Why it fits:
- The map (parent route) is created **once** and stays mounted beneath every child
  screen — controller/camera/layers preserved. Returning is instant: no remount,
  no reload, no re-fit. (`goNamed` reuses the parent page via its stable key.)
- **URL-addressable**: the address bar tracks the screen, so web refresh/share and
  browser back/forward work — production-grade for web, free on Android.
- Deep-linking straight to `/settings` builds `[map, settings]`, so the parent is
  always present and `canPop()` is true — back always works (no "trap").
- Pure go_router configuration; standard `goNamed`/`pop`.

(History: an earlier cut used sibling routes + imperative `push` — map alive via
`maintainState`, but the URL never updated, so web refresh/share/back broke. The
nested-child form fixes that with no loss of the keep-alive guarantee.)

Trade-off: an opaque child screen leaves the map **offstage** (kept alive, not
painted) — fine here, since Settings is opaque. A map **visible behind a
translucent panel** (Gaia-style) is a different need, met later with a deliberate
persistent `Stack` / bottom sheet — still not `ShellRoute`.

## How the pillars map to mechanism

| Pillar (README "Persistent state, transient screens") | Realized by |
|---|---|
| Map never unmounts/reloads | Map is the `/` parent route; child screens stack above it, the parent stays matched/mounted |
| Data pages don't re-fetch on mount (unless first time) | **Long-lived controllers**, not widget keep-alive — pages observe a `ChangeNotifier` that fetched once; covered when data pages land (Phase 6+), not this phase |
| Tearing the map down for a page = explicit opt-out | A future destination is a **top-level** route (not a child of `/`), so the map isn't matched and is disposed — an explicit, structural choice |

## App wiring changes

- `pubspec.yaml`: add `go_router` (17.3.0).
- `app.dart`: `MaterialApp(home: MapScreen())` → `MaterialApp.router(routerConfig: appRouter)`.
- New `lib/app/router.dart`: the `GoRouter` (routes above) + `registerNavInteractions`.
- **No `MapScreen` split** — `MapScreen` already *is* the map + HUD; it's just the
  `/` route now. State/controller logic unchanged.
  - Verify `onMapCreated` / `onStyleLoaded` fire **once** across navigations
    (controller identity stable) — the concrete proof of the pillar.

## Interaction taxonomy additions (Phase 3, both ways)

Add to `interaction_ids.dart` (and `all`):

- `hud.settings.tap` → opens the settings destination. Handler:
  `router.goNamed('settings')`. No payload.
- `nav.screen.open` → open a named screen. Payload `{screen: String}` = the
  GoRoute `name` (e.g. `'settings'`). Handler: `router.goNamed(screen)`.
- `nav.screen.close` → **pop** the current screen (`router.pop()` when
  `canPop`), returning to whatever's beneath (the live map). No payload.

### Navigation verbs: `goNamed` to open, back = `nav.screen.close`

- **Opening a screen uses `goNamed`** — because screens are child routes of `/`,
  this builds `[map, screen]` (URL-addressable) while keeping the parent map
  alive. The screen key is the route `name`, so there's no separate path table.
- **Android hardware back, the in-app back/close button, and
  `nav.screen.close` are the same action — a pop.** The back/close button
  dispatches `nav.screen.close`; the system back button hits the same pop
  (go_router's `BackButtonDispatcher` → root `Navigator`). They must never
  diverge. Back collapses screens one at a time and only exits the app at `/`.
- This makes back **intuitive by default**; future modals (bottom sheets /
  dialogs) close on back press for free as pushed routes.
- **`pushReplacement` / a top-level (non-child) route are reserved for true
  replaces / map-teardown** — flows that intentionally erase history or drop the
  map. The exception, called out per use, never the default.

All three go through `InteractionController.dispatch` so navigation is
**programmatically drivable** from the web `window.orion` bridge and native
`ext.orion.*` extensions — automation can open/close screens. The HUD cog
button dispatches `hud.settings.tap` instead of calling `router.push` inline (no
inline-handler bypass — see README interactions rule).

### Recording navigation — the observer is the single source of truth

A `NavigatorObserver` (`lib/app/nav_interaction_observer.dart`, attached via
`GoRouter(observers:)`) records **every** push/pop as `nav.screen.open/close` on
`didPush`/`didPop` — no matter the trigger: the cog, the in-app back button,
**Android system back**, or a programmatic dispatch. One recorder, so the log is
complete and consistent by construction.

To avoid a *second* entry when navigation is dispatched through the bus, the
`nav.screen.open/close` commands are registered **`record: false`**
(`InteractionController.register(..., record: false)`): dispatching them executes
the navigation but doesn't log at the dispatch site — the observer logs the
resulting push/pop instead. (The cog still records its own `hud.settings.tap`.)

This replaced an earlier `markDispatched()`/`_fromDispatch` flag that the observer
consumed to skip dispatched navigations: a shared boolean set synchronously before
an *async* push/pop, so a system back in that window mis-attributed the log
(race). The `record: false` approach has no shared timing state — there is exactly
one recording site, so no race and no double entry. It also removes the phantom
records the flag couldn't prevent (a no-op `close` or an unknown-screen `open` no
longer logs, since dispatch doesn't record these at all).

(Limitation: on web, browser back/forward is a declarative route rebuild and may
not surface as `didPop`; Android hardware back does.)

Registration lives wherever the router is reachable (e.g. an `AppShell`
`State`, or a small nav controller that holds the `GoRouter`), registered once at
app start and never unregistered (app-lifetime).

## HUD entry point

Add one `HudButton` (the Phase 4 shared base) to the existing single SafeArea
HUD `Stack` — a **cog / settings icon** (`Icons.settings`), placed **below the
follow-me `LocationFab`** in the bottom-right vertical stack (FAB on top, cog
beneath it). `onPressed` → dispatch `hud.settings.tap`.

**Web-only gap with the attribution ⓘ.** On web our own attribution lives
bottom-right (`map_attribution.dart`), and the FAB is currently lifted clear of
it by `kHudAttributionClearance` (`map_screen.dart`, `fabBottomInset`). Adding
the cog *below* the FAB makes the **cog** the lowest control on web, so the
attribution clearance must move to the cog (the lowest control) — it, not the
FAB, is what now has to clear the ⓘ. On native (attribution is bottom-left)
no extra clearance is needed. Build the two as a bottom-right `Column`
(FAB, cog) and apply the web clearance to the column's bottom.

## Placeholder destination

`SettingsScreen`: opaque `Scaffold` with an `AppBar` (title "Settings") + back
button that dispatches `nav.screen.close`. **Empty body** for now. Its only job
is to prove navigate-away / navigate-back keeps the map alive.

## Acceptance verification

1. Map → `/settings` → back: **no** second `onMapCreated`/`onStyleLoaded`, camera
   unchanged, no blank flash. (Log/assert controller identity.)
2. Snappiness gate: transition is visibly instant on device.
3. Ideally test with a stand-in layer on the map so "no reload" is meaningful
   with data present (a temporary debug polyline is enough; remove before merge).
4. `orion.dispatch('hud.settings.tap')` and `orion.dispatch('nav.screen.close')`
   from the web console drive navigation — confirms the both-ways wiring.

## Open questions carried to implementation

- Exact `go_router` version vs SDK `^3.10.8` — resolve with `flutter pub add`.
- Where the `GoRouter`/registration lives (free function + `AppShell` State vs a
  dedicated `NavController` singleton). Lean to the smallest thing that lets the
  interaction handlers reach `router`.

(Settled: `push` for opening screens, back = `nav.screen.close` = a pop — see
"Navigation verbs" above. No longer open.)
