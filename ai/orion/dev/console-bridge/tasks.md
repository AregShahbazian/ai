---
id: dev-console-bridge
title: Console bridge — tasks
status: draft
---

> Tasks for [`design.md`](design.md). Commits reference `[dev-console-bridge]`.

## Task 1 — Web bridge reorg + hardening (`console_bridge_web.dart`)

- Add `command(body)` and `read(fn)` helpers (try/catch; body invoked inside the
  async run so sync throws become caught rejections).
- Build `orion` as nested namespaces: `bus` (`dispatch`, `ids`, `dump`, `hud`),
  `map`, `settings`, `tracks`, `webnav`; keep top-level `ready`.
- Route `settings.logEvents(on)` through `dispatch('settings.logEvents.set',
  {enabled})`; no-arg returns current `logEventsEnabled` (read).
- Move `clearTracks` under `tracks`, camera/moves under `map` (was `mapnav`),
  HUD taps under `bus.hud`.
- Update the dartdoc header block to the new surface.
- **Verify:** `flutter analyze` clean; web smoke (Task 6).

## Task 2 — Native bridge reorg + hardening (`console_bridge_io.dart`)

- Add `_cmd(name, body)` wrapper (try/catch → `invalidParams` on throw).
- Re-register every extension under dotted names: `bus.dispatch`, `bus.ids`,
  `bus.dump`, `bus.hud.followMe`, `bus.hud.resetOrientation`, `map.camera`,
  `map.move`, `map.moveKm`, `map.zoomBy`, `map.rotateBy`, `map.tiltBy`,
  `map.panTo`, `settings.logEvents`, `tracks.clearTracks`, `webnav.dump`,
  `webnav.location`, `webnav.to`, `webnav.back`.
- Route `settings.logEvents` through `dispatch('settings.logEvents.set')`.
- Add `map.moveKm`, `map.panTo`, `webnav.dump/location/to/back`,
  `tracks.clearTracks`, `bus.hud.*` to reach web parity.
- Update the dartdoc header block.
- **Verify:** `flutter analyze` clean.

## Task 3 — Mobile wrapper scripts

- `orion.sh` — example comments use dotted cmds (`bus.dispatch`,
  `map.move meters=… heading=…`, `settings.logEvents on=true`).
- `cleartracks.sh` — `dispatch id=data.tracks.clear` → `bus.dispatch
  id=data.tracks.clear` (or call `tracks.clearTracks` directly).
- `navto.sh` — `dispatch` → `bus.dispatch`.
- `webnav.sh` — `webnav` → `webnav.dump`; `location` branch → `webnav.location`.
- **Verify:** scripts call the new extension names (grep), shellcheck-clean.

## Task 4 — Tool + repo docs

- `tool/orion_remote.dart` — header examples → dotted names.
- `docs/architecture.md` — bridge surface description.
- `docs/playwright-testing.md` — any `orion.mapnav`/`orion.data` refs → `map`/`tracks`.
- **Verify:** grep finds no stale `mapnav` / `orion.data.` / bare `ext.orion.dispatch`/`moveBy` outside history.

## Task 5 — `flutter analyze`

- Whole-repo analyze clean.

## Task 6 — Smoke (review checklist seeds)

- Web: `await orion.ready`; `orion.bus.ids`; `orion.map.camera()`;
  `await orion.map.zoomBy(1)`; `orion.map.zoomBy(1)` **before** ready resolves →
  warns + resolves null, no uncaught error; `await orion.settings.logEvents(true)`
  then `orion.bus.dump()` shows a `settings.logEvents.set` record;
  `await orion.bus.hud.followMe()`; `await orion.webnav.to('settings')`;
  `await orion.tracks.clearTracks()`.
- Native (if a device is up): `./orion.sh bus.ids`, `./orion.sh map.camera`,
  `./orion.sh settings.logEvents on=true`, `./cleartracks.sh`, `./webnav.sh`.
