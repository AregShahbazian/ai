# Discussion — Viewing the app's runtime state in the dev flow

**Date:** 2026-06-04
**Mode:** discussion (answers-only)
**Outcome:** Brainstorm only — no decision yet. The approach will be chosen once the app is actually running. Captured for later.

## Summary

The user wants, at some point, a way to **observe Orion's runtime state during
development** — e.g. via a browser console, Playwright, or some mobile-appropriate
mechanism. No decision made; options gathered to revisit when there's a running app.

## Options raised

- **Flutter DevTools** — widget inspector, state, logging; works for both web and device.
- **Web + Playwright** — drive Chrome to read console output and take screenshots;
  expose Dart state to `window` via `dart:js` interop so Playwright `evaluate` can
  read it programmatically.
- **VM Service protocol** — Flutter/Dart's built-in runtime introspection API for
  programmatic state access.
- **Mobile** — `flutter logs`, or a small debug HTTP/WebSocket endpoint in the app
  that dumps current state on request.

## Open questions (to decide once the app runs)

1. Should **Claude** read runtime state autonomously, or is this just easier
   inspection for the developer?
2. **Live** state streaming, or **snapshot-on-demand**?
3. Which mechanism per target — web vs. the Zenfone (mobile)?

## Ideas to realize

- **Runtime-state inspection in the dev flow** — pick a mechanism once the app is
  running. Candidates: Flutter DevTools; Web + Playwright reading state exposed on
  `window` via `dart:js`; VM Service protocol; a mobile debug HTTP/WebSocket
  endpoint. Goal: let the dev (and possibly Claude) view live or snapshot state.
  Aligns with the web-first dev loop ([[project-orion-dev-stack]]) — Playwright +
  Flutter web is the most promising starting point.

## Related
- `~/ai/orion/discussions/2026-06-04-dev-loop-and-map-plugin.md` — web-first dev loop
