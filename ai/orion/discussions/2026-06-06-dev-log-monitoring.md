# Dev-mode log monitoring (web + Android), one structured path

**Date:** 2026-06-06

## Summary

Explored how to monitor Orion in dev across web and Android without filtering out
anything potentially useful. `flutter run` already forwards Dart `print` /
`debugPrint` to the terminal on *both* platforms — but as flat `toString()` text:
not collapsable, not reliably tagged, and on Android buried under native logcat
noise (HWUI, GMS, Mbgl) that web doesn't have. The shared denominator is the Dart
log line. A test confirmed plain `print(map)` is **not** collapsable on web; handing
the browser a **live JS object** via `console.log` (JS-interop) **is**
collapsable/expandable/copyable. On Android the proven inspector is **Flutter
DevTools → Logging tab** (open the `…/devtools/?uri=…` URL `flutter run` prints,
filter by tag) — filterable + copyable, though indented-JSON rather than a fold-tree.

Decision: standardize on one helper, `devLog(scope, data)`, conditional-import
split — web → `console.log({tag: data})`, native → `dart:developer.log(json,
name: tag)`. Every line tagged `orion` + optional feature scope (`orion.map`).
`avoid_print` elevated to an analyzer **error** to force all logging through the
path. Implemented same day on branch `feature/p2-dev-logging`; docs in
`phase-2/dev-logging/`.

## Conclusions

- One `devLog(scope, data)` is the only sanctioned logging call; raw `print` is a
  build error.
- Web = collapsable browser-console object; Android = DevTools Logging tab.
- No log levels/filtering for now — log anything useful for future debugging.
- DevTools URL rotates port/token each `flutter run`; grab fresh.

## Open questions

- Do we want a true fold-tree on Android (in-app overlay, or pipe native logs to
  the browser console via the VM service)?
- When to add levels/severity + timestamps?

## Ideas to realize

- **Structured dev logger `devLog(scope, data)`** — one path, tagged `orion` +
  feature scope, collapsable on web / DevTools Logging on Android. ✅ implemented
  2026-06-06 (`feature/p2-dev-logging`).
- **Funnel enforcement** — `avoid_print: error`; later also discourage direct
  `dart:developer` use outside `core/log`. ✅ print part done.
- **Log levels / severity + timestamps** — extend `devLog` without breaking the
  `(scope, data)` call site. (deferred)
- **Android fold-tree inspection** — in-app log overlay, or route native logs to
  the browser console via the VM service, for the same expand/collapse UX as web.
  (deferred)
- **Bug-report capture** — attach the last N `devLog` records to bug reports;
  overlaps **Phase 3 — Interaction Controller** (interaction log). (deferred)
