---
id: dev-console-bridge
title: Console bridge + controller organization — a stable, namespaced automation contract
status: draft
epic: dev
---

> Part of the **Dev** concept epic — see [`../../dev.md`](../../dev.md). Builds on
> the command bus from [`../../mvp/phase-3/interaction-controller/prd.md`](../../mvp/phase-3/interaction-controller/prd.md).

## Goal

Make `orion` (web `window.orion`; mobile `ext.orion.*`) a **stable, long-term
bridge for automation and diagnostics** — one contract a script can rely on
across releases. Today the bridge works but has drifted: the web side is nested
(`orion.mapnav.move`, `orion.data.clearTracks`), the native side is flat
(`ext.orion.moveBy`) with slightly different names, and a couple of calls reach
into controllers directly instead of going through the command bus. This task
defines one organizing principle, applies it to both platforms, and closes the
bus-bypass leaks.

## Background — what exists today

- **Web bridge** (`lib/core/interaction/console_bridge_web.dart`): `window.orion`
  with nested namespaces `mapnav.*`, `webnav.*`, `data.*`, plus flat
  `dispatch`/`ids`/`dump`/`followMe`/`resetOrientation`/`logEvents`/`ready`.
- **Native bridge** (`lib/core/interaction/console_bridge_io.dart`): flat VM
  service extensions `ext.orion.dispatch`, `ext.orion.moveBy`, `ext.orion.camera`,
  `ext.orion.webnav`, etc.
- **Command bus** (`InteractionController`): every meaningful action has a stable
  id; `dispatch` runs the registered handler and records it to a ring buffer.
- **Controllers**: `InteractionController` (the bus), `MapNavigationController`
  (programmatic camera/geo — already dispatches ids internally),
  `LocationController` (follow-me; currently no direct bridge namespace),
  `SettingsController`, `ImportController`; plus `TracksRepository` and go_router
  for tracks/navigation.

### Problems

1. **Two bridges, drifting contracts** — web (nested) and native (flat) expose
   the same capabilities under different shapes and names. A script can't target
   both without special-casing.
2. **Bus-bypass leak** — `logEvents()` calls `SettingsController` directly on
   both bridges even though a `settings.logEvents.set` id exists, so toggling it
   via the bridge is **not recorded/replayable** like every other state change.
3. **Naming** — `mapnav` is awkward and `location` is ambiguous (map GPS vs
   router route). Grouping is ad-hoc rather than mirroring the code.

## Core principle (the rule)

The command bus is a **command log, not a query channel**:

- **Every state change is a dispatched interaction id** — routed through
  `bus.dispatch` so it is recorded in the ring buffer and replayable. No bridge
  call may mutate state by reaching into a controller/repository directly.
- **Every query is a direct read** — reads (`camera`, `ids`, `dump`,
  `ready`, route/nav state) call the controller/getter directly and are **not**
  recorded; logging queries would pollute the action buffer and they aren't
  replayable anyway.

The JS/VM namespaces are **only an organizing layer over this** — plain objects
grouping closures, not classes. They should mirror the Dart logic structure
(which controller/area backs each call), nothing more.

## Requirements

### Namespace organization (mirrors the controllers/areas)

The bridge is grouped into namespaces that reflect the underlying code, the same
on both platforms:

- **`bus.*`** → InteractionController
  - `bus.dispatch(id, payload?)` — fire any registered id (the generic command).
  - `bus.ids` — list of valid ids *(read)*.
  - `bus.dump()` — dump/return the ring buffer *(read)*.
  - **`bus.hud.*`** — convenience shortcuts for HUD taps, each just
    `dispatch`ing its id (so still recorded): `hud.followMe()`,
    `hud.resetOrientation()`.
- **`map.*`** → MapNavigationController *(renamed from `mapnav`; owns all
  programmatic geo/camera/location-follow logic)*
  - `map.camera()` *(read)*.
  - `map.move`/`map.moveKm`/`map.zoomBy`/`map.rotateBy`/`map.tiltBy`/`map.panTo`
    *(commands — already dispatch ids internally)*.
- **`settings.*`** → SettingsController
  - `settings.logEvents(on?)` — **must dispatch `settings.logEvents.set`** (no
    arg = read current value).
- **`tracks.*`** → tracks data layer *(repository, not a controller)*
  - `tracks.clearTracks()` *(command — dispatches `data.tracks.clear`)*.
- **`webnav.*`** → go_router state *(not a controller)*
  - `webnav.dump()`/`webnav.location()` *(reads)*; `webnav.to(screen)`/
    `webnav.back()` *(commands — dispatch nav ids)*.
- **Top level** — `ready` (map-ready promise/await) stays ungrouped; it backs no
  controller.

> `LocationController` gets no direct bridge namespace: its user-facing actions
> are HUD taps under `bus.hud`, and its programmatic geo logic belongs in `map`.

### Bus discipline

- No bridge call mutates state except via `bus.dispatch` of a registered id —
  including `settings.logEvents` (close the leak on **both** web and native).
- Read-only calls do not touch the bus.
- Adding a new bridge command means adding/registering its interaction id first;
  the bridge call is a thin wrapper that dispatches it.

### Cross-platform parity

- **Web** (`window.orion`) is the primary target and the reference shape.
- **Mobile** (`ext.orion.*`, VM service extensions) exposes the **same
  capabilities under the same names**. VM extensions are a flat registry, so the
  namespace is encoded in the extension name (e.g. `ext.orion.map.move`,
  `ext.orion.bus.dispatch`) rather than nested objects — but the vocabulary
  (namespace + call + payload) matches the web contract one-to-one.
- Optionally provide **helper scripts/snippets** for mobile so a developer can
  drive `ext.orion.*` ergonomically (the VM-service protocol is clumsier than a
  browser console). Investigate; deliver if low-cost.
- Payload schemas and return shapes are identical across platforms so a single
  automation script is portable.

### Stability

- The `orion` contract (namespaces, call names, payloads) is treated as a
  **stable public API** for automation — renames are breaking and avoided; the
  ids it dispatches are the already-stable taxonomy.
- Installed on every build, all platforms, including release/prod (unchanged from
  today).

## Use cases (why)

- A scripted end-to-end flow drives the same calls on web and mobile without
  branching on platform.
- Every state change a script makes shows up in `bus.dump()` and can be replayed
  from the recorded `(id, payload)` — including settings toggles.
- A developer reads the namespace list and immediately sees which part of the app
  (which controller/area) each call exercises.

## Out of scope

- New app features or new interactions beyond what the bridge already exposes
  (this is reorganization + leak-closing, not feature work).
- Adopting a state-management framework or rewriting controllers — the bus and
  controllers stay as-is; only the bridge layer and the `settings.logEvents`
  routing change.
- Persisted/exported diagnostics beyond the existing ring buffer.

## Open questions

- Final name confirmation: `bus`, `map`, `settings`, `tracks`, `webnav`, plus
  `bus.hud` for shortcuts. (Working assumption; `map` chosen over `mapnav`.)
- How far to take mobile helper scripts vs. just documenting raw `ext.orion.*`.
- Keep `webnav` as its own namespace, or fold route navigation under `bus`
  shortcuts given it's bus-dispatched anyway.
