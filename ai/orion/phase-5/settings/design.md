---
id: phase-5-settings
---

# Design — Settings page + persisted toggles

## Store

`SettingsController extends ChangeNotifier` (singleton `.instance`, matching the
app's other singletons: `InteractionController`, `MapNavigationController`).
Persistence via `shared_preferences` — a thin on-device key/value store, the
canonical minimal choice for a few booleans, no backend.

- `load()` — read keys (defaults: longPressZoom **true**, logEvents **false**),
  apply side effects (`InteractionController.instance.logEvents = …`), notify.
  Called in `main()` with `await` before `runApp` so the first frame is correct.
- `setLongPressZoomEnabled(bool)` / `setLogEventsEnabled(bool)` — guard no-op,
  update field, persist, (logEvents also pushes into the bus), notify.

Keys: `settings.longPressZoom.enabled`, `settings.logEvents.enabled`.

### Why logEvents moves here
`InteractionController.logEvents` was a runtime-only bool flipped from the dev
consoles — lost on restart. It's really a user/dev setting, so the persisted
owner is `SettingsController`; the bus keeps a plain `logEvents` field as the
hot-path consumer (checked per recorded interaction) that the controller drives.
The console bridges now call `SettingsController.setLogEventsEnabled`, so all
three entry points (in-app switch, web `orion.logEvents`, native `orion.sh
logEvents`) share one persisted source of truth.

## Interaction wiring

Two ids in the closed taxonomy, payload `{enabled: bool}`:
`settings.longPressZoom.set`, `settings.logEvents.set`.
`registerSettingsInteractions(SettingsController)` (called from `main`, mirroring
`registerNavInteractions`) binds them to the setters. The `SwitchListTile`s
**dispatch** these ids rather than calling the setters inline — so flips are
recorded and re-dispatchable (`orion.dispatch('settings.logEvents.set',
{enabled:true})`).

## UI

`SettingsScreen` wraps a `ListenableBuilder(listenable: SettingsController.
instance)` over a `ListView` of `SwitchListTile`s, so it reflects external
changes (e.g. a console toggle) live. The long-press tile is wrapped in
`if (!kIsWeb)`.

## Long-press gate

`MapScreen` listens to `SettingsController.instance` (alongside
`LocationController`) and rebuilds on change. The FAB's `onLongPress` becomes
`(kIsWeb || !settings.longPressZoomEnabled) ? null : _onLocationLongPress` — when
off, the gesture is truly absent (InkWell gets a null handler), matching
pre-feature behavior rather than a no-op handler.

## Files
- `lib/features/settings/settings_controller.dart` — new store + registration fn.
- `lib/features/settings/settings_screen.dart` — the two switches.
- `lib/main.dart` — `async`, `await load()`, register interactions.
- `lib/core/interaction/interaction_ids.dart` — two ids (+ `all`).
- `lib/core/interaction/console_bridge_{io,web}.dart` — logEvents → settings.
- `lib/features/map/map_screen.dart` — listen + gate `onLongPress`.
- `pubspec.yaml` — `shared_preferences`.
