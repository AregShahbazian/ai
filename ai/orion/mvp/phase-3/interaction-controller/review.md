---
id: phase-3-interaction-controller
doc: review
---

## Round 1: hand-rolled command bus, in-memory + live logging (2026-06-06)

Implemented the `InteractionController` command bus, the closed taxonomy, value
types, retrofitted `map_screen.dart`, and a unit test. `flutter analyze` clean;
`flutter test` green (5/5). In-memory only this increment — persistence/export
deferred (see design open questions).

**Files:**
- `lib/core/interaction/interaction.dart`
- `lib/core/interaction/interaction_ids.dart`
- `lib/core/interaction/interaction_controller.dart`
- `lib/features/map/map_screen.dart` (retrofit)
- `test/interaction_controller_test.dart`

### Verification
1. ✅ `flutter analyze` — no issues.
2. ✅ `flutter test test/interaction_controller_test.dart` — 5/5 pass
   (dispatch return value, payload pass-through, origin recorded, ring-buffer
   eviction, throw on unregistered known id).
3. Tap the location FAB → follow cycles exactly as before, and a
   `orion.interaction` line `… [user] hud.followMe.tap` prints.
4. Rotate/tilt the map, tap the compass button → resets as before, prints
   `… [user] hud.resetOrientation.tap`.
5. While following, pan by hand → follow drops as before, prints
   `… [user] map.follow.dismissed`.
6. Verify log is collapsable in the browser console (web) / under the
   `orion.interaction` tag in the DevTools Logging tab (native).
7. Programmatic parity (covered by test #2/#3): a `programmatic`-origin dispatch
   hits the same handler as a user tap; the log line shows `[prog]`.

### Trading-terminal-style context cases (Orion equivalents)
8. Switch online → offline (airplane mode) while interacting → interactions
   still dispatch and log; offline banner unaffected.
9. Background → resume the app (Android GL surface recreated) → taps still
   dispatch and log; no duplicate/lost registrations (handlers unregister on
   `dispose`, re-register on the new `initState`).

### Deferred (next increment)
- Persist the ring buffer across restart + on-disk export (`dump()` is the seam).
- Replay runner / in-app inspector.
