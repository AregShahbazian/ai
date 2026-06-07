---
id: phase-5-navigation
title: Navigation — design
status: draft
branch: TBD
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

### `ShellRoute` — chosen

`ShellRoute` builds a **persistent shell widget** around the routed `child`. We
put the map (and HUD) in the shell builder, once; the routed page renders on top:

```
ShellRoute(
  builder: (context, state, child) => Stack(children: [
    const MapView(),     // persistent: built ONCE, never disposed by navigation
    const MapHud(),      // compass / FAB / location — persistent with the map
    child,               // the current route's page, painted OVER the map
  ]),
  routes: [
    GoRoute(path: '/',         builder: (_, __) => const SizedBox.shrink()), // map only
    GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen()),  // placeholder
    // later: /tracks, /routes …
  ],
)
```

Why it fits:
- The map is created **once** in the shell builder and stays mounted for every
  child route — controller, camera, follow mode, future layers all preserved.
  Returning to `/` is instant: no remount, no reload, no re-fit.
- A page can be **opaque** (covers the map — map still alive underneath) or
  **partial/translucent** (Gaia-style panel — map visible behind), purely by how
  the page widget paints. The shell doesn't care; both keep the map alive.
- Pure go_router configuration. No custom plumbing.

Trade-off accepted: `ShellRoute` disposes a **page** when it's popped (pages are
not kept alive across navigation). That's fine — see the data-page rule next; we
deliberately do **not** rely on widget keep-alive for data freshness.

## How the pillars map to mechanism

| Pillar (README "Persistent state, transient screens") | Realized by |
|---|---|
| Map never unmounts/reloads | `ShellRoute` persistent builder (map built once) |
| Data pages don't re-fetch on mount (unless first time) | **Long-lived controllers**, not widget keep-alive — pages observe a `ChangeNotifier` that fetched once; covered when data pages land (Phase 6+), not this phase |
| Tearing the map down for a page = explicit opt-out | A future destination renders **outside** the `ShellRoute` (a top-level `GoRoute`), so it isn't wrapped by the persistent map. Default routes live inside the shell |

The map-alive default and the opt-out fall straight out of "inside the
`ShellRoute` = map alive; outside it = map gone." No special API to invent.

## App wiring changes

- `pubspec.yaml`: add `go_router` (latest stable for SDK `^3.10.8`).
- `app.dart`: `MaterialApp(home: MapScreen())` → `MaterialApp.router(routerConfig: appRouter)`.
- New `lib/app/router.dart` (or `lib/core/nav/router.dart`): the `GoRouter` with
  the `ShellRoute` above.
- **Split `MapScreen`**: today it's both the screen *and* the map. Extract the
  map + HUD into a persistent widget(s) the shell builder mounts once
  (`MapView` + the existing HUD `Stack`); the old `MapScreen` shell role is
  replaced by `ShellRoute`. The map's `State`/controller logic is unchanged —
  it just no longer sits under a per-navigation route.
  - Verify `onMapCreated` / `onStyleLoaded` fire **once** across navigations
    (controller identity stable) — this is the concrete proof of the pillar.

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
  (go_router's `BackButtonDispatcher` → inner `ShellRoute` Navigator). They must
  never diverge. Back collapses pages one at a time and only exits the app at `/`.
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
