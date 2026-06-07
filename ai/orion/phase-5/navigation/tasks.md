---
id: phase-5-navigation
title: Navigation — tasks
status: draft
branch: TBD
---

Ordered, each independently verifiable. Pillar: the map is built **once** and
never re-mounted by navigation (see `design.md`). Off-the-shelf `go_router`
`ShellRoute` — **no custom navigation plumbing**.

## 1. Add go_router
- [ ] `flutter pub add go_router` (latest stable for SDK `^3.10.8`); commit
      `pubspec.yaml` + lockfile.
- [ ] `flutter analyze` clean.

## 2. Extract persistent map + HUD from `MapScreen`
- [ ] Split `lib/features/map/map_screen.dart` so the `MapLibreMap` + the
      SafeArea HUD `Stack` live in a widget the shell mounts once (e.g.
      `MapView` + keep the HUD inline). State/controller logic unchanged.
- [ ] No behavior change yet (still the only thing on screen). Verify the app
      runs identically on web.

## 3. Router + ShellRoute
- [ ] New `lib/app/router.dart`: `GoRouter` with a `ShellRoute` whose builder is
      `Stack([MapView, HUD, child])` (map+HUD persistent, `child` painted over).
- [ ] Routes: `/` → `SizedBox.shrink()` (map only); `/settings` →
      `SettingsScreen` (next task).
- [ ] `app.dart`: `MaterialApp(home:)` → `MaterialApp.router(routerConfig:)`.
- [ ] Run: still lands on the live map at `/`.

## 4. Placeholder destination
- [ ] `SettingsScreen`: opaque `Scaffold` + `AppBar("Settings")` + back action;
      empty body. Back dispatches `nav.screen.close`.

## 5. Interaction taxonomy (Phase 3, both ways)
- [ ] Add `hud.settings.tap`, `nav.screen.open` (`{screen}`), `nav.screen.close`
      to `interaction_ids.dart` + `all`, with doc comments.
- [ ] Register handlers once at app start (wherever `GoRouter` is reachable):
      `hud.settings.tap`/`nav.screen.open` → `router.push(<path>)`; `nav.screen.close`
      → pop (`context.pop()`/`Navigator.maybePop`). App-lifetime; not unregistered.
- [ ] Confirm Android hardware back == `nav.screen.close` (same pop); back at `/`
      exits the app. `push` for opening, `go`/`pushReplacement` reserved for true
      replaces only (see `design.md` "Navigation verbs").

## 6. HUD entry button
- [ ] Add a cog/settings icon button (`Icons.settings`) to the SafeArea HUD
      `Stack` (top-left). `onPressed` → `dispatch(hud.settings.tap)` — **no**
      inline `router.push`.

## 7. Verify the pillar (acceptance gate)
- [ ] Map → `/settings` → back: assert/log `onMapCreated` + `onStyleLoaded` fire
      **once** total; camera unchanged; no blank flash.
- [ ] Transition visibly instant on device.
- [ ] (Temporary) add a debug polyline to the map, confirm it's untouched across
      navigation, then remove before merge — proves "no reload" with data.
- [ ] `orion.dispatch('hud.settings.tap')` / `orion.dispatch('nav.screen.close')`
      from web console drive navigation (both-ways wiring confirmed).

## 8. Wrap up
- [ ] `flutter analyze` clean; `avoid_print` clean.
- [ ] Verify on device (Android).
- [ ] Update README Phase 5 status; write `review.md`.

## Out of scope (do NOT do here)
- Real page content (settings/tracks/routes) — later phases.
- Data-page no-refetch controllers — lands with the first data page (Phase 6+);
  this phase only proves the *map* stays alive.
- `StatefulShellRoute`/tab UI — not needed for the map (see `design.md`).
- Map-teardown opt-out routes — documented in design, not built until a page
  needs it.
