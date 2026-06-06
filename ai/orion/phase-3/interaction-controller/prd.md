---
id: phase-3-interaction-controller
title: Interaction Controller — app-global command bus + interaction log
status: in progress
branch: feature/p2-dev-logging
---

## Decision: hand-rolled command bus (not flutter_bloc)

Orion's state is plain `ChangeNotifier`s with no DI/bloc. Adopting
`flutter_bloc` + `BlocObserver` would force rewriting app-wide state into
events/states just to gain a diagnostics channel — overkill and lock-in. We
instead ship a thin hand-rolled **`InteractionController`** (a command bus):
a taxonomy registry + a single `dispatch` funnel + a ring-buffer interceptor.
It layers over the existing controllers with zero rewrite, stays
serializable/replayable, and keeps the door open to swap in bloc later if the
app ever goes that way. (`BlocObserver` would only have won had we already
been on bloc.)

## Goal

Introduce one app-global controller that is the single channel for **every**
meaningful user interaction with Orion. It can (1) **dispatch** interactions
programmatically — as if the user performed them — and (2) **observe and record**
the last N interactions locally. This becomes the substrate for diagnostics
(attach recent interactions to bug reports) and for automated/scripted testing.

The proven pattern this realizes is the **Command pattern + an interceptor/event
log** (a command bus with telemetry). Each interaction is a named, serializable
Command; a central dispatcher executes it and an interceptor records it.

## Requirements

### Interaction taxonomy

- Every interaction the app permits has a **stable, unique, hierarchical
  identifier** — a namespaced string so events can be defined and looked up
  efficiently. Proposed shape: `domain.subject.action`, e.g.:
  - `hud.followMe.tap`
  - `hud.resetOrientation.tap`
  - `map.camera.move` (pan/zoom/rotate/tilt)
  - `map.gesture.longPress`
  - `nav.screen.open` / `nav.screen.close`
- The taxonomy is **closed and enumerated in one place** — adding a new user
  interaction means registering it here; ad-hoc/unregistered events are not
  allowed.
- Each interaction defines its **payload schema** (e.g. `map.camera.move`
  carries target lat/lng/zoom/bearing/tilt; a button tap carries no payload).
- Identifiers are stable over time so recorded logs remain interpretable across
  versions.

### Dispatch (programmatic interaction)

- Any registered interaction can be **invoked programmatically** through the
  controller and produces the **same effect as the real user action** — it
  routes through the same handler the UI uses, not a parallel code path.
- Initial coverage (must-have): the interactions that exist as of Phase 2 —
  HUD buttons (Follow-Me, reset-orientation), map camera moves, and screen
  navigation once Phase 4 lands.
- Dispatch is **fire-and-acknowledge**: the caller learns whether the
  interaction was accepted/executed.

### Observation & local log

- The controller **monitors all interactions** flowing through it (whether
  user- or programmatically-originated) and stores the **last N** locally.
  - N is a **configurable cap** (ring buffer; oldest dropped). Default TBD in
    design (order of a few hundred entries).
  - Each record carries: interaction id, payload, timestamp, and **origin**
    (`user` vs `programmatic`).
- The log is **persisted locally** so it survives an app restart and can be
  retrieved for a bug report.
- The log can be **exported/dumped** in a human- and machine-readable form
  (for attaching to diagnostics).
- Real user interactions in existing features are **routed through the
  controller** so they are captured — features stop calling their handlers
  directly and instead dispatch the registered interaction.

## Use cases (why)

- **Diagnostics:** when a bug is reported, the last N interactions describe how
  the user got there — attachable to a `.fix.md` investigation.
- **Automation/testing:** scripts (driven by me or by Claude) can replay or
  synthesize interaction sequences to reproduce states and exercise the app.

## Non-requirements (scope boundaries)

- **No remote/cloud telemetry.** Local only; no backend, no account, no network
  upload. (Decentralization/sync remain post-MVP.)
- **No record/replay UI** in this phase — exporting the log is enough; a replay
  runner and any in-app inspector are follow-ups.
- **No analytics product** — this is diagnostics/automation plumbing, not
  product metrics or funnels.
- **Does not capture raw input events** (every touch/pixel) — only the
  registered, semantic interactions.
- **No undo/redo** is implied by using the Command pattern here.

## Dependencies / relationships

- Sits beneath the existing Phase 2 HUD; those features get **retrofitted** to
  dispatch through the controller.
- Should be in place **before Phase 4 (Navigation)** so screen-navigation
  interactions are modelled in the taxonomy from the start.
- Relates to the deferred **Runtime-state inspection** brainstorm
  (`discussions/2026-06-04-runtime-state-inspection.md`) — the interaction log
  is one half of inspecting/driving the app; state inspection is the other.

## Open questions (resolve in design)

- Exact dispatch mechanism in Flutter: plain command bus vs `flutter_bloc`
  events vs a Redux-style action stream — pick one in design.
- Local persistence backend for the ring buffer (SQLite/Drift vs a flat
  append log).
- Default N and per-interaction payload schemas.
