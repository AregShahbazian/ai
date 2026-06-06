---
id: phase-2-dev-logging
---

# Orion — Phase 2: Dev Logging (Design)

> PRD: [`prd.md`](prd.md)

## Shape

A tiny `lib/core/log/` module, conditional-import split by platform, with one
public function on top that owns tagging.

```
lib/core/log/
  dev_log.dart       # public API: devLog(scope, data) — builds the tag, delegates
  console.dart       # conditional export of consoleLog(tag, data)
  console_web.dart   # web   → window.console.log({tag: data}) as a live JS object
  console_io.dart    # native→ dart:developer.log(prettyJson, name: tag)
```

### Public API

```dart
void devLog(String scope, Object? data);
```

- `scope` = feature area, e.g. `'map'`, `'location'`, or `''` for app-wide.
- Emitted tag = `orion` when scope is empty, else `orion.<scope>`.
- Root tag is the const `kLogRoot = 'orion'`.

### Platform impls (`consoleLog(tag, data)`)

- **web** (`console_web.dart`): `web.console.log(<String,Object?>{tag: data}.jsify())`
  — one keyed live object so DevTools shows `▶ {orion.map: {…}}`, collapsable.
  (This version's `console.log` binding takes a single arg, hence the keyed map.)
- **native** (`console_io.dart`): `developer.log(JsonEncoder.withIndent('  ')
  .convert(data), name: tag)` — indented JSON, named by tag so the DevTools
  Logging tab filters on it.

`dev_log.dart` imports `console.dart` (the conditional export) so only the public
file is imported by app code.

## Enforcing the funnel

`analysis_options.yaml`: enable `avoid_print` as an **error**. Raw `print`
becomes a build-blocking lint, pushing every log through `devLog`. (No built-in
rule bans `dart:developer` directly; the `core/log` module is the only place that
imports it, enforced by convention + review.)

## Trade-offs

- **Keyed-map on web** (`{tag: data}`) instead of two console args — required by
  the single-arg binding; costs one extra wrapper level in the tree, acceptable.
- **Native isn't a fold-tree** in DevTools — indented JSON only. A true tree
  would need an in-app overlay or piping to the browser console; deferred (see
  PRD out-of-scope), not worth it now.
- **No levels yet** — keeps the call site trivial; add `level`/severity later
  without breaking `devLog(scope, data)` if needed.
