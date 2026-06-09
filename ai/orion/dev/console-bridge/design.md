---
id: dev-console-bridge
title: Console bridge — design
status: draft
---

> Design for [`prd.md`](prd.md). Reorganises both bridges into one namespaced,
> bus-disciplined, crash-safe contract.

## The shape (both platforms, one vocabulary)

```
orion
├─ ready                         (read)   Promise — map usable
├─ bus
│  ├─ dispatch(id, payload?)     (cmd)    fire any registered id
│  ├─ ids                        (read)   valid ids
│  ├─ dump()                     (read)   ring-buffer records
│  └─ hud
│     ├─ followMe()              (cmd)    dispatch hud.followMe.tap
│     └─ resetOrientation()      (cmd)    dispatch hud.resetOrientation.tap
├─ map                                    → MapNavigationController
│  ├─ camera()                   (read)   live camera | null
│  ├─ move(headingDeg, metres)   (cmd)
│  ├─ moveKm(headingDeg, km)     (cmd)
│  ├─ zoomBy(delta)              (cmd)
│  ├─ rotateBy(deg)              (cmd)
│  ├─ tiltBy(deg)                (cmd)
│  └─ panTo(lat, lng)            (cmd)
├─ settings
│  └─ logEvents(on?)             (cmd/read) dispatch settings.logEvents.set; returns current
├─ tracks
│  └─ clearTracks()              (cmd)    dispatch data.tracks.clear
└─ webnav                                 → go_router
   ├─ dump()                     (read)
   ├─ location()                 (read)
   ├─ to(screen)                 (cmd)    dispatch nav.screen.open
   └─ back()                     (cmd)    dispatch nav.screen.close
```

Native maps one-to-one onto flat dotted extension names (VM extensions are a flat
registry): `ext.orion.bus.dispatch`, `ext.orion.bus.ids`, `ext.orion.bus.dump`,
`ext.orion.bus.hud.followMe`, `ext.orion.bus.hud.resetOrientation`,
`ext.orion.map.camera`, `ext.orion.map.move` (`meters`,`heading`),
`ext.orion.map.moveKm` (`km`,`heading`), `ext.orion.map.zoomBy` (`delta`),
`ext.orion.map.rotateBy` (`degrees`), `ext.orion.map.tiltBy` (`degrees`),
`ext.orion.map.panTo` (`lat`,`lng`), `ext.orion.settings.logEvents` (`on`),
`ext.orion.tracks.clearTracks`, `ext.orion.webnav.dump`,
`ext.orion.webnav.location`, `ext.orion.webnav.to` (`screen`),
`ext.orion.webnav.back`.

`ext.orion.$cmd` in `tool/orion_remote.dart` already forwards the first arg as the
extension suffix, and that suffix may contain dots — so `./orion.sh map.move
meters=5000 heading=90` works with no tool change.

## Bus discipline (the rule, enforced)

| call | kind | routing |
|------|------|---------|
| `bus.dispatch`, `bus.hud.*`, `map.*` moves, `settings.logEvents(on)`, `tracks.clearTracks`, `webnav.to/back` | command | `bus.dispatch(id, origin: programmatic, …)` |
| `bus.ids`, `bus.dump`, `map.camera`, `settings.logEvents()` (no arg), `webnav.dump/location`, `ready` | read | direct getter, **not** recorded |

The only behavioural change vs. today: `settings.logEvents` stops calling
`SettingsController` directly and dispatches `settings.logEvents.set` instead
(the id + handler already exist — `registerSettingsInteractions`). The read half
(no-arg) still reads `SettingsController.instance.logEventsEnabled` directly.
Because the set now goes through an async dispatch, `settings.logEvents(on)`
returns a Promise (web) resolving to the resulting value.

## Robustness design

Two shared helpers per bridge replace the ad-hoc inline closures:

**Web** (`console_bridge_web.dart`):

```dart
// Command: run an action and resolve; never throws across interop, never leaves
// an unhandled rejection. Returns a Promise<result|null>.
JSPromise<JSAny?> command(Future<JSAny?> Function() body) {
  Future<JSAny?> run() async {
    try {
      return await body();
    } catch (e) {
      web.console.warn('orion: $e'.toJS);
      return null;
    }
  }
  return run().toJS;   // body() invoked INSIDE run(), so a sync throw → rejection→caught
}
```

- `map.*` helpers become `command(() async { await nav.zoomBy(d); return nav.camera?.toMap().jsify(); })` — the `nav.*` call (which may throw synchronously via `_require()`) now runs inside the async body, so a not-ready map yields a warned, resolved `null` instead of a raw thrown `StateError`.
- `bus.dispatch`/`hud`/`tracks`/`webnav.to`/`back`/`settings.logEvents(on)` all go through `command`.
- Reads (`map.camera`, `bus.ids`, `bus.dump`, `webnav.*`) already tolerate null and are synchronous — left as direct closures, wrapped in a tiny `read(() => …)` try/catch that returns `null` on failure for safety.

**Native** (`console_bridge_io.dart`):

```dart
void _cmd(String name, Future<Map<String, Object?>> Function(Map<String,String>) body) {
  _register(name, (_, params) async {
    try {
      return _ok(await body(params));
    } catch (e) {
      return developer.ServiceExtensionResponse.error(
        developer.ServiceExtensionResponse.invalidParams, '$e');
    }
  });
}
```

Every handler uses `_cmd`, so a thrown `StateError` (map not ready, bad param)
returns a clean `invalidParams` response rather than an opaque RPC failure.

## Stability of `ready` (web)

Unchanged: `orion.ready` stays a single pre-resolved Promise property, awaitable
repeatedly. The `_mapReady` completer is top-level and idempotent
(`signalMapReady` no-ops after first complete).

## Files

- `lib/core/interaction/console_bridge_web.dart` — full reorg + `command`/`read`.
- `lib/core/interaction/console_bridge_io.dart` — full reorg + `_cmd`.
- `scripts/mobile/orion.sh` — example comments → dotted names.
- `scripts/mobile/cleartracks.sh` — `dispatch` → `bus.dispatch`.
- `scripts/mobile/navto.sh` — `dispatch` → `bus.dispatch`.
- `scripts/mobile/webnav.sh` — `webnav` → `webnav.dump` / `webnav.location`.
- `tool/orion_remote.dart` — doc examples → dotted names.
- `docs/architecture.md`, `docs/playwright-testing.md` — bridge surface refs.

No change to `interaction_ids.dart`, `interaction_controller.dart`,
`map_navigation_controller.dart`, `settings_controller.dart`, `main.dart`
(install signature unchanged). The `data.tracks.clear` id keeps its name (the
*namespace* is `tracks`, the *id* stays in the stable taxonomy).

## Open implementation notes

- Keep `dispatch` returning `null` (not a Promise) for an unknown id on web — it
  warns and is a no-op; awaiting `null` is harmless. Documented, not changed.
- `settings.logEvents` parsing on native: `on=true/false` string → bool.
