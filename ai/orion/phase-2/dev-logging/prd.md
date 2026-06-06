---
id: phase-2-dev-logging
title: Dev Logging — one structured, inspectable log path
status: planned
branch: feature/p2-dev-logging
---

> Part of Orion — see [README.md](../../README.md)

## Goal

Give Orion **one** debug-logging path that produces inspectable, copyable,
structured logs on **both** web and Android — so debugging any feature is the
same motion and nothing logged is ever lost to flat terminal text.

## Rationale

`flutter run` already forwards Dart logs to the terminal on both platforms, but
as plain `toString()` text: not collapsable, not reliably tagged, easy to drown
in native noise. A live JS object handed to the browser console *is*
collapsable/copyable; `dart:developer.log` records show up structured in the
Flutter DevTools **Logging** tab on Android. We standardize on a single helper
that picks the right path per platform and tags every line.

## Requirements

- **Single entry point:** `devLog(scope, data)` — the only sanctioned logging
  call in app code.
- **Always tagged:** every line carries the root tag `orion`, plus an optional
  **feature scope** (e.g. `orion.map`, `orion.location`) for filtering.
- **Inspectable per platform:**
  - Web → live JS object in the browser console (collapsable / expandable /
    copyable).
  - Native → `dart:developer.log` (named by tag) → Flutter DevTools Logging tab
    (filterable + copyable).
- **No filtering / no levels gate today:** log anything that may help future
  debugging; keep it dead simple. (Levels can come later.)
- **Enforced funnel:** lint bans raw `print` so logs don't bypass the path.
- **Zero behavior change** to features; remove the temporary `initState` test
  log.

## Out of scope (later)

- Log levels / severity, timestamps formatting, in-app log overlay, routing
  native logs into a fold-tree, persisting logs, attaching to bug reports
  (that overlaps **Phase 3 — Interaction Controller**).
