---
id: dev-console-bridge
title: Console bridge — review
status: draft
---

> Review for [`prd.md`](prd.md) / [`design.md`](design.md). Implemented on branch
> `dev/console-bridge` (worktree `~/git/orion-console-bridge`), **not** on `main`.

## Round 1: namespaced reorg + bus discipline + crash-safety (2026-06-09)

### Change summary
- **Web** (`console_bridge_web.dart`) rebuilt as nested namespaces: `bus`
  (`dispatch`/`ids`/`dump`/`hud.followMe`/`hud.resetOrientation`), `map`
  (camera + relative moves, was `mapnav`), `settings.logEvents`,
  `tracks.clearTracks` (was `data.clearTracks`), `webnav`, top-level `ready`.
- **Native** (`console_bridge_io.dart`) re-registered under matching dotted
  extension names (`ext.orion.bus.dispatch`, `ext.orion.map.move`, …) and brought
  to web parity (added `map.moveKm`, `map.panTo`, `bus.hud.*`,
  `tracks.clearTracks`, `webnav.to/back/location`).
- **Bus-bypass leak closed:** `settings.logEvents` now dispatches
  `settings.logEvents.set` on both platforms (was a direct `SettingsController`
  call) — so a bridge toggle is recorded/replayable like every other state change.
- **Crash-safety:** web `command`/`read` wrappers (body runs inside the async
  closure → a synchronous controller throw becomes a caught rejection + warn, no
  unhandled promise rejection); native `_cmd` wrapper turns any throw into an
  `invalidParams` response.
- Callers updated: `scripts/mobile/{orion,cleartracks,navto,webnav}.sh`,
  `tool/orion_remote.dart`, `docs/{architecture,playwright-testing}.md`,
  `scripts/{README.md,web/run.sh}`, `lib/app/router.dart` doc.

### Bug/risk register (from the audit, all addressed)
1. **Sync throw across interop (web).** Relative moves built the future as an
   *argument*, so a not-ready-map `StateError` escaped as a raw throw. Fixed by
   invoking `nav.*` inside `command`'s async body. **Files:** `console_bridge_web.dart`.
2. **Unhandled promise rejections (web).** Dispatch/handler errors surfaced as
   "Uncaught (in promise)". Fixed by try/catch → `console.warn` + resolve null.
3. **Native handlers didn't catch.** Thrown `StateError` became an opaque RPC
   failure. Fixed by `_cmd` → `invalidParams`. **Files:** `console_bridge_io.dart`.

### Verification

`flutter analyze lib tool` → **No issues found.** ✅ (1)

Runtime checks (need a running app — to be done by the user):

2. **Web reorg works.** `flutter run -d chrome`; in console: `await orion.ready`,
   `orion.bus.ids` (array), `orion.map.camera()` (object), `await
   orion.map.zoomBy(1)` zooms.
3. **Crash-safety — sync-throw.** Immediately on load, *before* `await
   orion.ready` resolves, call `orion.map.zoomBy(1)` → resolves to `null` with a
   single `orion: …` warning; **no** uncaught exception / red error in console.
4. **No unhandled rejection.** `orion.bus.dispatch('not.a.real.id')` → warns,
   returns null, no "Uncaught (in promise)".
5. **Bus discipline / leak closed.** `await orion.settings.logEvents(true)` then
   `orion.bus.dump()` → a `settings.logEvents.set` record (origin programmatic)
   is present; the in-app Settings switch reflects `true`.
6. **HUD shortcuts.** `await orion.bus.hud.followMe()` cycles follow mode;
   `await orion.bus.hud.resetOrientation()` resets orientation.
7. **webnav.** `await orion.webnav.to('settings')` opens Settings;
   `orion.webnav.location()` → `/settings`; `await orion.webnav.back()` closes it.
8. **tracks.** `await orion.tracks.clearTracks()` empties the tracks list.
9. **Native parity (if a device is up).** `./scripts/mobile/orion.sh bus.ids`,
   `… map.camera`, `… settings.logEvents on=true` (then `… bus.dump` shows the
   record), `./scripts/mobile/cleartracks.sh`, `./scripts/mobile/webnav.sh`,
   `./scripts/mobile/navto.sh settings`.
10. **Native error-shape.** `./scripts/mobile/orion.sh map.zoomBy` (missing
    `delta` ⇒ parse path) / call a move before the map is ready → clean
    `invalidParams` error JSON, app stays up.
