---
id: phase-2-dev-logging
---

# Orion — Phase 2: Dev Logging (Tasks)

> PRD: [`prd.md`](prd.md) · Design: [`design.md`](design.md)

1. [x] Split the module: `console_web.dart` / `console_io.dart` each expose
   `consoleLog(tag, data)`; `console.dart` conditionally exports one.
2. [x] `dev_log.dart`: public `devLog(scope, data)` + `kLogRoot = 'orion'`;
   builds `orion` / `orion.<scope>` and delegates to `consoleLog`.
3. [x] Enforce funnel: `avoid_print` → error in `analysis_options.yaml`.
4. [x] Remove the temporary `initState` test log (and the example that replaced
   it); drop the now-unused `kIsWeb` import. No call sites left — the logger is
   infrastructure, added at call sites as debugging needs arise.
5. [x] `web: ^1.x` kept as a direct dependency (browser console interop).
6. [x] `flutter analyze` clean; existing tests pass.
7. [ ] On-device verify (web console collapsable + DevTools Logging tab on
   Android) — see review.
