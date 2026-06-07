---
id: phase-5-navigation
title: Navigation — review
status: implemented & verified on web + Android (2026-06-07)
branch: feature/p5-navigation
---

## Implementation summary (2026-06-07)

App shell stood up with off-the-shelf `go_router` (17.3.0) — **no custom
navigation plumbing**. The map stays alive across navigation (the pillar).

### What landed
- **`lib/app/router.dart`** — `appRouter`: **plain stacked routes**, no
  `ShellRoute`. `/` → `MapScreen` (home), `/settings` → `SettingsScreen` pushed
  over it. `Navigator` keeps the home route alive (`maintainState`) beneath the
  pushed page, so the map is never disposed/reloaded.
  - `registerNavInteractions(appRouter)` wires `hud.settings.tap` →
    `push('/settings')`, `nav.screen.open {screen}` → `push(<path>)` via a
    `{screen→path}` map, `nav.screen.close` → `pop()` if `canPop`.
- **`lib/app/nav_interaction_observer.dart`** — `NavInteractionObserver`
  (attached via `GoRouter(observers:)`) records **system back** (Android
  hardware/edge-swipe) as an observed `nav.screen.open/close` on `didPush`/
  `didPop`. Dispatched navigations call `markDispatched()` first so the observer
  skips them (the `_programmaticCamera` guard pattern) — no double entries. Web
  browser-back may not surface as `didPop` (declarative rebuild); Android does.
- **`lib/features/settings/settings_screen.dart`** — opaque `Scaffold`,
  `AppBar("Settings")`, empty body; back button dispatches `nav.screen.close`.
- **`interaction_ids.dart`** — added `settingsTap`, `navScreenOpen`,
  `navScreenClose` (+ to `all`).
- **`app.dart`** — `MaterialApp(home:)` → `MaterialApp.router(routerConfig:)`.
- **`main.dart`** — `registerNavInteractions(appRouter)` before `runApp`.
- **`map_screen.dart`** — settings cog `HudButton` added **below** the location
  FAB; both now in a bottom-right `Column` (FAB, gap, cog). Cog dispatches
  `hud.settings.tap`.
- **`map_constants.dart`** — added `kHudControlGap`; reworded
  `kHudAttributionClearance` (now lifts the bottom-right column so the cog, the
  lowest control, clears the web ⓘ).

### Design evolution
- **First cut used a `ShellRoute`** with the map persistent in the shell builder
  (`Stack([MapScreen, child])`). It worked but required two off-label tricks —
  a transparent `opaque:false` home page (so the map shows through the always-
  present `child`) and an `IgnorePointer` at `/` (because the shell's full-screen
  `Navigator` `child` swallowed all map/HUD touches, which froze interaction on
  the first build). `ShellRoute` is meant for shared chrome (its `child` is the
  page body), not a backdrop overlay — so this was the wrong tool.
- **Refactored to plain stacked routes + `push`** (current). The map is the home
  route; screens push over it; `Navigator` keeps it alive beneath. No `Stack`, no
  transparent route, no `IgnorePointer`. Simpler and idiomatic; same map-alive
  guarantee. See `design.md` "Plain stacked routes + `push` — chosen".
- **No `MapScreen` split** — it already *is* the map + HUD; it's just the home
  route now.
- **Open handlers fire-and-forget the `push`.** `router.push()`'s Future only
  completes when the screen is *popped*, so returning it from the dispatch handler
  hung the dispatch (and any remote RPC / web Promise) until the user went back —
  `navto.sh` never exited. Fixed with `unawaited(router.push(...))`; the handler
  returns immediately (the screen still shows synchronously).

`flutter analyze`: clean (`avoid_print` clean).

## Verification checklist

Code-verified:
1. ✅ `flutter analyze` clean after the change.
2. ✅ Taxonomy closed: new ids registered and in `InteractionIds.all`.
3. ✅ No inline `router.*` in widgets — cog and back dispatch through the bus.

Manual (device/web) — ✅ verified on web + Android (2026-06-07):
4. ✅ App opens on the live map at `/`; cog visible bottom-right below the FAB.
5. ✅ Tap cog → Settings opens over the map; back arrow returns to the map.
6. ✅ **Pillar:** map stays alive across map→settings→back (no remount/reload,
   camera unchanged, no blank flash, instant return).
7. ✅ Android **hardware back** from Settings returns to the map; back at `/`
   exits the app.
7a. ✅ **Hardware back is recorded:** `orion.dump()` shows `nav.screen.close`;
    cog shows `hud.settings.tap`; in-app back arrow shows one `nav.screen.close`
    (no observer duplicate).
8. ✅ **Web:** settings cog clears the attribution ⓘ; tap-through to the map
   works at `/`.
9. ✅ Bridge: web `orion.webnav.to('settings')` / `orion.dispatch(...)` and
   mobile `scripts/mobile/navto.sh` drive navigation; `nav.screen.close` / `to('/')`
   return to the map.
10. (Not run) temp debug polyline across navigation — deferred; covered when real
    map data lands (Phase 7).
