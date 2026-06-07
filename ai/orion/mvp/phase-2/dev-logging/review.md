---
id: phase-2-dev-logging
---

# Orion — Phase 2: Dev Logging (Review)

> PRD: [`prd.md`](prd.md) · Design: [`design.md`](design.md) · Tasks: [`tasks.md`](tasks.md)

## Round 1: initial implementation (2026-06-06)

Single structured-logging path landed. `flutter analyze` clean, all tests pass.

**Files:**
- `lib/core/log/dev_log.dart` — public `devLog(scope, data)` + `kLogRoot = 'orion'`;
  builds `orion` / `orion.<scope>`.
- `lib/core/log/console.dart` — conditional export of `consoleLog`.
- `lib/core/log/console_web.dart` — `window.console.log({tag: data})` (collapsable).
- `lib/core/log/console_io.dart` — `dart:developer.log(indentedJson, name: tag)`.
- `analysis_options.yaml` — `avoid_print: error` (funnel enforcement).
- `lib/features/map/map_screen.dart` — temp test removed; dropped unused
  `kIsWeb` import. No call sites remain — the logger is infrastructure, added
  where debugging needs it.
- `pubspec.yaml` — `web: ^1.1.1` as a direct dep.

## Verification (on device / browser)

Drop a temporary `devLog('test', {'hello': 1})` somewhere on startup, then:

1. **Web:** run, open the browser DevTools console → see `▶ {orion.test: {…}}`,
   expandable / collapsable / copyable.
2. **Android:** run, open the `…/devtools/?uri=…` URL `flutter run` prints →
   **Logging** tab → filter `orion` → `orion.test` record present, copyable.
3. **Funnel:** add a stray `print('x')` anywhere → `flutter analyze` now fails
   with `avoid_print` (error). Remove it → clean again.
4. App behaviour unchanged (logging-only change).

## Notes / follow-ups

- Native is indented-JSON in DevTools, not a fold-tree (deferred per design).
- Levels/severity, timestamps, in-app overlay, and attaching recent logs to bug
  reports are out of scope here — the last overlaps **Phase 3 — Interaction
  Controller**.
