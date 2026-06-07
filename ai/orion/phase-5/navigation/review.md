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
- **`lib/app/router.dart`** — `appRouter`: `settings` is a **child route of `/`**
  (the map); `goNamed('settings')` builds `[MapScreen, SettingsScreen]` so the
  parent map stays mounted/alive and the URL is `/settings` (see Round 2; an
  earlier cut used sibling routes + `push`).
  - `registerNavInteractions(appRouter)` wires `hud.settings.tap` →
    `goNamed('settings')`, `nav.screen.open {screen}` → `goNamed(screen)`,
    `nav.screen.close` → `pop()` if `canPop`.
- **`lib/app/nav_interaction_observer.dart`** — `NavInteractionObserver`
  (attached via `GoRouter(observers:)`) is the **single recorder** of navigation:
  every push/pop (cog, in-app back, Android system back, programmatic) becomes a
  `nav.screen.open/close` on `didPush`/`didPop`. The open/close commands are
  registered `record: false` so dispatch doesn't double-log (see Round 1). Web
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
- **Refactored to plain stacked routes + `push`** (later superseded by Round 2's
  nested child routes + `goNamed`). The map was the home route; screens pushed
  over it; `Navigator` kept it alive beneath. No `Stack`/`IgnorePointer`. See
  `design.md` "Nested child routes + `go`/`goNamed` — chosen".
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

## Round 1: code review — single-recorder refactor (2026-06-07)

High-effort multi-agent review of the nav diff. Headline finding addressed here;
the rest are triaged below.

### Fix: drop the `_fromDispatch` flag → observer is the single recorder
**Root cause:** the observer skipped dispatched navigations via a shared boolean
(`markDispatched()`/`_fromDispatch`) set synchronously before an *async*
`push`/`pop`. A system back landing in that window consumed the wrong flag →
swapped/dropped log entries (race). It also couldn't stop phantom records
(dispatch logs *before* the handler runs, so a no-op `close` or unknown-screen
`open` still logged).
**Fix:** the `NavigatorObserver` now records **all** push/pop; the
`nav.screen.open/close` commands are registered `record: false` so dispatch
executes them without logging (the observer logs the resulting push/pop). No
shared timing state → no race, no double entry, no phantom records. The cog still
logs `hud.settings.tap`, and now also yields a `nav.screen.open` via the observer
— so cog vs console vs system back are consistent.
**Files:** `lib/core/interaction/interaction_controller.dart` (`register(...,
record:)` + `_externallyRecorded`), `lib/app/nav_interaction_observer.dart`
(flag removed), `lib/app/router.dart` (`record: false`, no `markDispatched`).
**Test:** added `record:false runs the handler but does not log` to
`test/interaction_controller_test.dart` (7/7 pass). `flutter analyze` clean.

### Verification
1. ✅ `flutter analyze` clean; interaction tests 7/7.
2. Re-verify on device: cog/back/system-back each produce exactly one
   `nav.screen.close`/`open` in `orion.dump()` (no dup, no phantom).

### Triaged for follow-up (not in this round)
- **#8 (next):** push-based screens aren't URL-addressable (web refresh/share/
  browser-back). Architectural — to be discussed.
- Web HUD `Column` gap not wrapped in `PointerInterceptor` (tap-leak).
- `orion.webnav.to('/settings')` (path) fails name lookup; `to('/')` magic value.
- `navState()` can throw if called before first route resolves (both bridges).
- Scalability: adding a screen needs `_screenPaths` + `GoRoute` + id; `settingsTap`
  hardcodes `/settings` (could `pushNamed`/delegate to `navScreenOpen`).
- Duplication: `navState` shape across web/io bridges; `navto.sh`/`webnav.sh` vs
  `orion.sh`; `webnav.to` re-implements `dispatch`.
- Stale `ShellRoute` mention in `interaction_ids.dart` doc comment.

## Round 2: #8 — URL-addressable screens (2026-06-07)

**Change:** screens are now **child routes of `/`** and navigation uses
`goNamed`/`pop` (was sibling routes + imperative `push`). go_router matches `/`
**and** the child, so the stack is `[MapScreen, screen]` — the map (parent route)
stays mounted/alive beneath, **and** the URL reflects the screen.

**Fixes:**
- Web URL now tracks the screen → refresh/share and browser back/forward work
  (the #8 gap).
- Deep-link to `/settings` builds `[map, settings]`, so `canPop()` is true and
  back always works — removes the earlier "back-trap if reached via go/deeplink".
- Dropped `_screenPaths` (screen key == route `name` via `goNamed`) and the
  `unawaited`/`push`-Future hang workaround (`go`/`pop` return void).

**Verified on web + Android (2026-06-07):** map stays alive across open/close (no
remount/reload, instant, camera unchanged); URL shows `/settings` on web with
working browser-back and refresh-on-`/settings`; `orion.dump()` shows one
open/close per action. `flutter analyze` clean; interaction tests 7/7.

**Files:** `lib/app/router.dart`.

### Still triaged for the cleanup pass
- Web HUD `Column` gap not wrapped in `PointerInterceptor` (tap-leak).
- `orion.webnav.to('/settings')` (path) vs name; `to('/')` magic value.
- `navState()` can throw if called before first route resolves (both bridges).
- Duplication: `navState` shape (web/io); `navto.sh`/`webnav.sh` vs `orion.sh`;
  `webnav.to` re-implements `dispatch`.
- Stale `ShellRoute` mention in `interaction_ids.dart` doc comment.
