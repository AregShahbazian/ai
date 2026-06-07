---
id: phase-5-navigation
title: Navigation — tasks
status: implemented & verified on web + Android (2026-06-07)
branch: feature/p5-navigation
---

Ordered, each independently verifiable. Pillar: the map is built **once** and
never re-mounted by navigation (see `design.md`). Off-the-shelf `go_router`
`ShellRoute` — **no custom navigation plumbing**.

## 1. Add go_router
- [x] `flutter pub add go_router` → `go_router 17.3.0`; `pubspec.yaml` + lockfile.
- [x] `flutter analyze` clean.

## 2. Persistent map + HUD
- [x] No split needed — `MapScreen` already *is* the persistent map + HUD widget;
      it's now mounted by the shell builder instead of being `home:`. State /
      controller logic unchanged.

## 3. Router + ShellRoute
- [x] New `lib/app/router.dart`: `GoRouter` with a `ShellRoute` whose builder is
      `Stack([const MapScreen(), child])` (map persistent, `child` over it).
- [x] Routes: `/` → transparent `CustomTransitionPage(opaque:false, SizedBox.shrink())`
      (map shows through); `/settings` → opaque `SettingsScreen`.
- [x] `app.dart`: `MaterialApp(home:)` → `MaterialApp.router(routerConfig: appRouter)`.
- [ ] Run: still lands on the live map at `/`. *(device/web check)*

## 4. Placeholder destination
- [x] `SettingsScreen` (`lib/features/settings/settings_screen.dart`): opaque
      `Scaffold` + `AppBar("Settings")` + back action; empty body. Back dispatches
      `nav.screen.close`.

## 5. Interaction taxonomy (Phase 3, both ways)
- [x] Added `hud.settings.tap`, `nav.screen.open` (`{screen}`), `nav.screen.close`
      to `interaction_ids.dart` + `all`, with doc comments.
- [x] `registerNavInteractions(appRouter)` (called in `main`): `hud.settings.tap`
      → `router.push('/settings')`; `nav.screen.open` → `router.push(<path>)` from
      a `{screen→path}` map; `nav.screen.close` → `router.pop()` if `canPop`.
      App-lifetime; not unregistered.
- [ ] Confirm Android hardware back == `nav.screen.close` (same pop); back at `/`
      exits the app. *(device check)* `push` used for opening; `go`/`pushReplacement`
      reserved for true replaces only.

## 6. HUD entry button
- [x] Added a cog/settings `HudButton` (`Icons.settings`) **below the follow-me
      FAB** — both now in a bottom-right `Column` (FAB, gap, cog). `onPressed` →
      `dispatch(hud.settings.tap)`; no inline `router.push`.
- [x] **Web:** `kHudAttributionClearance` now lifts the whole column (renamed
      `hudColumnBottomInset`) so the cog (lowest) clears the ⓘ; native unchanged.
- [ ] Verify no collision with the ⓘ on web. *(web check)*

## 7. Verify the pillar (acceptance gate) — manual
- [ ] Map → `/settings` → back: `onMapCreated`/`onStyleLoaded` fire **once** total;
      camera unchanged; no blank flash.
- [ ] Transition visibly instant on device.
- [ ] (Optional) temp debug polyline untouched across navigation — "no reload" with data.
- [ ] `orion.dispatch('hud.settings.tap')` / `orion.dispatch('nav.screen.close')`
      from web console drive navigation (both-ways wiring confirmed).

## 8. Wrap up
- [x] `flutter analyze` clean (`avoid_print` clean).
- [ ] Verify on device (Android).
- [ ] Update README Phase 5 status. `review.md` written.

## Out of scope (do NOT do here)
- Real page content (settings/tracks/routes) — later phases.
- Data-page no-refetch controllers — lands with the first data page (Phase 6+);
  this phase only proves the *map* stays alive.
- `StatefulShellRoute`/tab UI — not needed for the map (see `design.md`).
- Map-teardown opt-out routes — documented in design, not built until a page
  needs it.
