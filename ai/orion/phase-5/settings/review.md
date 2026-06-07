---
id: phase-5-settings
---

# Review — Settings page + persisted toggles

## Implementation summary (2026-06-07)

First real Phase 5 Settings page. `SettingsController` (ChangeNotifier singleton,
`shared_preferences`-backed) loaded in `main` before `runApp`; two
`SwitchListTile`s dispatched through the interaction bus. `logEvents` ownership
moved out of `InteractionController` into the persisted setting; all three toggle
entry points share it. Long-press tile native-only; long-press gesture gated on
the setting in `MapScreen`.

## Verification

1. ✅ `flutter analyze` clean.
2. **Settings page:** cog → Settings shows two switches — Long-press-to-zoom
   **on**, Log interaction events **off** (native). On **web**, only the
   logEvents switch shows (long-press tile hidden).
3. **Long-press gate:** turn Long-press-to-zoom **off** → long-press on the
   follow FAB does nothing (tap still cycles). Turn **on** → center+zoom returns.
4. **logEvents toggle:** turn **on** → interactions echo to the dev log (watch
   `orion.sh logs scope=interaction`); **off** → they stop.
5. **Persistence:** flip both, kill & relaunch → values retained.
6. **Cross-channel (logEvents):** `orion.sh logEvents on=true` (native) /
   `orion.logEvents(true)` (web) → the in-app switch flips to match, and the
   value survives a restart. Flipping the in-app switch is reflected back by
   `orion.sh logEvents` (no arg) reporting the new state.
7. **Re-dispatch:** `orion.dispatch('settings.longPressZoom.set',{enabled:false})`
   flips the setting + switch (proves the interaction-bus wiring both ways).

### Context tests
8. **Open Settings → toggle → back → re-open:** state persists across the
   nav (map stays alive beneath — Phase 5 navigation).
9. **Background → resume (Android):** settings intact; toggles still work.

## Notes
- Default-follow-**zoom level** is still a constant; making it adjustable is a
  separate open backlog item ("Make the default zoom level configurable…").
