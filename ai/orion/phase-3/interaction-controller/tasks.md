---
id: phase-3-interaction-controller
doc: tasks
---

## Task 1 — Value types (`lib/core/interaction/interaction.dart`)
- `enum InteractionOrigin { user, programmatic }`.
- `@immutable class InteractionRecord` — `id`, `origin`, `at`, `payload?`, plus a
  `.line` one-line human-readable getter and `toString => line`.
- **Verify:** `flutter analyze` clean.

## Task 2 — Taxonomy (`lib/core/interaction/interaction_ids.dart`)
- `InteractionIds` with private ctor; consts `followMeTap`, `resetOrientationTap`,
  `mapTrackingDismissed`; `static const Set<String> all`.
- **Verify:** ids are `domain.subject.action`; `all` contains every const.

## Task 3 — Controller (`lib/core/interaction/interaction_controller.dart`)
- `InteractionController` with `static final instance`, public ctor (`capacity`).
- `InteractionHandler` typedef; `register`/`unregister`.
- `dispatch(...) → Future<Object?>` — asserts known id, records, runs handler,
  returns its value, throws if unregistered.
- `recent()`, `dump()`; ring buffer via `Queue` capped at `kInteractionLogCapacity`.
- `_record` echoes `devLog('interaction', r.line)`.
- **Verify:** `flutter analyze` clean (watch the public-API/private-typedef lint —
  typedef is public).

## Task 4 — Retrofit `map_screen.dart`
- Field `_interactions = InteractionController.instance`.
- `initState`: register the three handlers → `LocationController` methods.
  `dispose`: unregister all three.
- `_onLocationTap` dispatches `followMeTap`; keep the `permanentlyDenied` SnackBar.
- `CompassButton.onReset` and `onCameraTrackingDismissed` dispatch their ids.
- **Verify:** taps still behave exactly as before; each tap now prints an
  `orion.interaction` line.

## Task 5 — Unit test (`test/interaction_controller_test.dart`)
- Programmatic `dispatch` invokes the registered handler and returns its value.
- Record carries `origin: programmatic`; user dispatch carries `origin: user`.
- Ring buffer drops oldest past `capacity`.
- Dispatching an unregistered known id throws.
- **Verify:** `flutter test` green.

## Task 6 — Review doc + analyze
- Append numbered verification checklist to `review.md`.
- `flutter analyze` + `flutter test` before declaring done.

## Deferred (documented, not in this increment)
- Local persistence of the buffer across restart + on-disk export.
- Replay runner / in-app inspector.
