---
id: phase-3-interaction-controller
doc: design
---

## Architecture

A hand-rolled **command bus** living in `lib/core/interaction/`, app-global via a
single static instance. Three small pieces:

```
lib/core/interaction/
  interaction.dart             # value types: InteractionOrigin, InteractionRecord
  interaction_ids.dart         # the closed taxonomy (domain.subject.action consts)
  interaction_controller.dart  # registry + dispatch funnel + ring-buffer interceptor
```

### Data flow (the single funnel)

```
UI tap / automation
      │  dispatch(id, {payload, origin})
      ▼
InteractionController ──► record() ──► ring buffer (last N)  ──► devLog('interaction', line)
      │                                  (the interceptor)
      ▼
registered handler(payload)  ──►  existing controller method (LocationController, …)
      │
      └─► returns result (e.g. LocationTapResult) back to the dispatcher → caller
```

The funnel is the whole design: **features stop calling their handlers inline and
instead `dispatch` a registered id.** One entry point → one place to record
(diagnostics) and one place to inject (programmatic dispatch == replay). A
programmatic call hits the *same* handler as a user tap, so the effect is
identical by construction.

### Taxonomy (`interaction_ids.dart`)

Closed, enumerated set of hierarchical `domain.subject.action` string ids in one
place. Phase-2 coverage (must-have):

| id | meaning |
|----|---------|
| `hud.followMe.tap` | location FAB tapped (enable / cycle follow) |
| `hud.resetOrientation.tap` | compass/reset button tapped |
| `map.follow.dismissed` | follow dropped because the user panned/zoomed |

`InteractionIds.all` is the authoritative set; `register`/`dispatch` assert the id
is in it, so ad-hoc ids are a programming error. Adding an interaction = add a
const here. Ids are stable so old logs stay interpretable.

### `InteractionController`

- `static final instance` — the app-global bus the UI dispatches through.
  Constructor stays public so tests get isolated instances.
- `register(id, handler)` / `unregister(id)` — a feature binds its handler for an
  id (typically in `initState`, removed in `dispose`). `handler` is
  `FutureOr<Object?> Function(Map<String,Object?>? payload)`.
- `dispatch(id, {payload, origin = user}) → Future<Object?>` — records first, then
  runs the handler and returns its value (so the FAB's `LocationTapResult` still
  reaches the SnackBar logic). Throws if no handler is registered.
- `recent() → List<InteractionRecord>` and `dump() → String` — read the buffer
  for a bug report.
- Ring buffer: a `Queue<InteractionRecord>` capped at `capacity`
  (`kInteractionLogCapacity = 200`); oldest dropped past the cap.

### `InteractionRecord`

Immutable: `id`, `origin` (`user` | `programmatic`), `at` (`DateTime`), optional
`payload`. `.line` is the one-line human-readable form used for both the dev log
and `dump()`:

```
14:22:07.913 [user] hud.followMe.tap
14:22:09.044 [prog] hud.resetOrientation.tap
```

### Logging (the demonstration)

Every record is echoed through the existing `devLog('interaction', record.line)`
— so on web it's collapsable in the browser console and on native it's filterable
under the `orion.interaction` tag in the DevTools Logging tab. No new logging
infra; reuses the sanctioned `devLog` path.

### Retrofit points in `map_screen.dart`

- `initState`: register the three handlers onto `InteractionController.instance`,
  delegating to existing `LocationController` methods. `dispose`: unregister.
- `_onLocationTap`: `dispatch(followMeTap)`, await, keep the existing
  `permanentlyDenied` SnackBar branch on the returned result.
- `CompassButton.onReset`: `() => dispatch(resetOrientationTap)`.
- `MapLibreMap.onCameraTrackingDismissed`: `() => dispatch(mapTrackingDismissed)`.

## Open questions (deferred — not in this increment)

- **Persistence** of the ring buffer across restart (PRD requirement): pick
  SQLite/Drift vs a flat append log. This increment is **in-memory only** — enough
  to demonstrate live logging + programmatic dispatch; persistence + on-disk export
  is a follow-up task.
- **Replay runner** and any in-app inspector — out of scope here (PRD non-req).
- Per-interaction payload schemas beyond the current (mostly payload-free) set.

## Non-goals (unchanged from PRD)

No remote telemetry, no record/replay UI, no raw-input capture, no undo/redo.
