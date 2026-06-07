---
id: phase-5-settings
---

# Tasks — Settings page + persisted toggles

## T1 — Persistence dep + store
- `pubspec.yaml`: add `shared_preferences`.
- `settings_controller.dart`: `SettingsController` singleton; `load()`,
  `setLongPressZoomEnabled`, `setLogEventsEnabled`; keys + defaults
  (longPressZoom true, logEvents false). `registerSettingsInteractions`.
- **Verify:** analyze clean; load applies logEvents to the bus.

## T2 — Interaction ids
- `interaction_ids.dart`: `settingsLongPressZoomSet`, `settingsLogEventsSet` (+ `all`).

## T3 — Boot wiring
- `main.dart`: `async`; `await SettingsController.instance.load()`;
  `registerSettingsInteractions(...)` before `runApp`.

## T4 — Move logEvents to the setting
- `console_bridge_io.dart` / `console_bridge_web.dart`: `logEvents` toggle →
  `SettingsController.setLogEventsEnabled`, report the setting's value.

## T5 — Settings UI
- `settings_screen.dart`: `ListenableBuilder` + two `SwitchListTile`s dispatching
  the ids; long-press tile wrapped `if (!kIsWeb)`.

## T6 — Gate the long-press
- `map_screen.dart`: listen to `SettingsController`; `onLongPress =
  (kIsWeb || !enabled) ? null : _onLocationLongPress`.

## T7 — Verify
- `flutter analyze`; device checks per `review.md`.
