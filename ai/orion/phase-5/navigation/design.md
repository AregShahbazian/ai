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

### Plain stacked routes + `push` — chosen

The map is the **home route**; screens are `push`ed **over** it. Flutter's
`Navigator` keeps the route beneath a pushed page alive (`maintainState` defaults
to true), so the map — controller, camera, follow mode, future layers — is never
disposed or reloaded while a screen is open. Popping returns to the exact same
live map. No `Stack`, no overlay juggling, no custom plumbing.

```
GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(path: '/',         builder: (_, __) => const MapScreen()),     // home: the map
    GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen()), // pushed over it
    // later: /tracks, /routes …
  ],
)
```

Why this and **not `ShellRoute`** (rejected): `ShellRoute` is built for *shared
chrome* — its `child` is meant to **be** the page body, with persistent UI (a nav
bar / drawer) wrapped around it. Using it to hold the map as a *backdrop* under an
always-present `child` overlay is off-label: it forces a transparent home route
(so the map shows through `child`) **and** an `IgnorePointer` (so taps reach the
map under `child`). That machinery is a smell — the wrong tool for "persistent
backdrop." Plain stacked routes give the same map-alive guarantee with none of it.

Why it fits:
- The map is created **once** (home route) and stays mounted beneath every pushed
  screen — controller/camera/layers preserved. Returning is instant: no remount,
  no reload, no re-fit.
- Pure go_router configuration; standard `push`/`pop`.

Trade-off accepted: an opaque pushed screen leaves the map **offstage** (kept
alive, but not painted) — fine here, since Settings is opaque and you don't see
the map behind it anyway. If we later want the map **visible behind a translucent
panel** (Gaia-style), that's a *different* need met with a deliberate persistent
`Stack` or a bottom sheet (`showModalBottomSheet` floats over the home body with
no `IgnorePointer`) — still not `ShellRoute`.

## How the pillars map to mechanism

| Pillar (README "Persistent state, transient screens") | Realized by |
|---|---|
| Map never unmounts/reloads | Map is the home route; pushed screens sit above it, `Navigator` keeps it alive (`maintainState`) |
| Data pages don't re-fetch on mount (unless first time) | **Long-lived controllers**, not widget keep-alive — pages observe a `ChangeNotifier` that fetched once; covered when data pages land (Phase 6+), not this phase |
| Tearing the map down for a page = explicit opt-out | A future destination uses `go`/`pushReplacement` (replaces the stack, disposing the map) instead of `push` — an explicit per-call choice |

## App wiring changes

- `pubspec.yaml`: add `go_router` (17.3.0).
- `app.dart`: `MaterialApp(home: MapScreen())` → `MaterialApp.router(routerConfig: appRouter)`.
- New `lib/app/router.dart`: the `GoRouter` (routes above) + `registerNavInteractions`.
- **No `MapScreen` split** — `MapScreen` already *is* the map + HUD; it's just the
  home route now. State/controller logic unchanged.
  - Verify `onMapCreated` / `onStyleLoaded` fire **once** across navigations
    (controller identity stable) — the concrete proof of the pillar.

## Interaction taxonomy additions (Phase 3, both ways)

Add to `interaction_ids.dart` (and `all`):

- `hud.settings.tap` → opens the settings destination. Handler:
  `router.push('/settings')`. No payload.
- `nav.screen.open` → open a named screen. Payload `{screen: String}` (route
  key, e.g. `'settings'`). Handler: `router.push(<resolved path>)`.
- `nav.screen.close` → **pop** the current page (`context.pop()` /
  `Navigator.maybePop`), returning to whatever's beneath (the live map). No
  payload.

### Navigation verbs: settled on `push` + back = `nav.screen.close`

- **Opening a page/modal uses `push`** (never `go`), so every destination is a
  real entry on the navigator stack.
- **Android hardware back, the in-app back/close button, and
  `nav.screen.close` are the same action — a pop.** Wire the back/close button to
  dispatch `nav.screen.close`, and let the system back button hit the same pop
  (go_router's `BackButtonDispatcher` → the root `Navigator`). They must never
  diverge. Back collapses pages one at a time and only exits the app at `/`.
- This makes back **intuitive by default** and means **future modals
  (bottom sheets / dialogs) close on back press** for free, since they're pushed
  routes too.
- **`go` / `pushReplacement` are reserved for true replaces only** — flows where
  erasing a history step is the intent (e.g. a future login → home). They are the
  exception, called out per use, never the default for opening a screen.

All three go through `InteractionController.dispatch` so navigation is
**programmatically drivable** from the web `window.orion` bridge and native
`ext.orion.*` extensions — automation can open/close screens. The HUD cog
button dispatches `hud.settings.tap` instead of calling `router.push` inline (no
inline-handler bypass — see README interactions rule).

### Capturing system back (the observe half)

Dispatch covers what the UI/automation *initiates*, but **Android hardware /
edge-swipe back** is popped by go_router directly — it never reaches the bus. So,
like native map gestures, it's captured with the **observe half**: a
`NavigatorObserver` (`lib/app/nav_interaction_observer.dart`, attached via
`GoRouter(observers:)`) calls `interactions.observe(nav.screen.open/close)` on
`didPush`/`didPop`.

To avoid double-recording the *dispatched* navigations (whose dispatch already
logged them), each dispatch handler calls `observer.markDispatched()` right before
it navigates; the observer consumes that flag and skips the matching push/pop —
the exact `_programmaticCamera` guard pattern. Net result: the cog tap is logged
as `hud.settings.tap`, the in-app back / console close as `nav.screen.close`, and
**system back as an observed `nav.screen.close`** — each once.

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
