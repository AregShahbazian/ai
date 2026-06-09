---
id: dev-testing
title: Testing setup — a durable test strategy for an agent-developed Orion
status: draft
epic: dev
---

> Part of the **Dev** concept epic — see [`../../dev.md`](../../dev.md). Leans on
> the [console bridge](../console-bridge/prd.md) (the `orion` automation contract)
> as Orion's end-to-end harness, and on the
> [interaction controller](../../mvp/phase-3/interaction-controller/prd.md) as the
> spine most worth pinning down with tests.

## Goal

Stand up a testing strategy that fits how Orion is actually built — largely
Claude-coded, offline-first, map-heavy — so changes can be verified without
eyeballing every one on a device. Pick the right test *types* for each part of
the app, wire the tooling, and make writing/running tests a standard motion.

## Where we are today

Two test files, both effectively **unit tests**:

- `test/interaction_controller_test.dart` — real value; locks down the app spine
  (dispatch runs handlers, payload/origin recorded, ring buffer evicts). High
  leverage since every action routes through the bus.
- `test/widget_test.dart` — misnamed; a plain unit test asserting the map style
  URL constant. Marginal but cheap. The full-screen map is a MapLibre **platform
  view**, not meaningfully testable headless — the file's comment admits this.

No widget, golden, or integration tests yet.

## The four types, and where each fits Orion

| Type | What it is | Priority for Orion |
|------|-----------|--------------------|
| **Unit** | Pure logic, no device. | ✅ **Grow first.** GPX parse/serialize round-trips, Drift queries, track stats (distance / duration / speed / elevation), settings. Deterministic, fast, and the most agent-verifiable. |
| **Widget** | Mount one widget/screen headless, pump frames, assert. | **High.** Settings, track list, import/export dialogs, follow-me button states — everything **except** the MapLibre platform view. |
| **Integration** | Drive the whole running app end-to-end. | **Medium-High.** Use Flutter's official **`integration_test`** package (+ **Patrol** for native permission/dialog flows). Runs on mobile and web (`flutter drive` + chromedriver) from one suite, and sees the widget tree. Golden path: record → persist → export GPX → re-import → assert identity. **The console bridge is not a testing tool** — it stays for manual diagnostics/driving, not tests. |
| **Golden** | Render widget to PNG, diff vs committed image. | **Medium, last.** Only deterministic non-map UI (track rows, stat cards). **Skip map screens** — platform views + tiles make them flaky/non-deterministic. |

## Scope (proposed order)

1. **Unit** — GPX import/export round-trips on the real sample files, track-stat
   math, Drift repository queries. Cheapest, highest ROI.
2. **Widget** — the non-map UI listed above.
3. **Integration** — adopt `integration_test` (+ Patrol for native dialogs) as
   the E2E harness, mobile and web (`flutter drive` + chromedriver) from one
   suite; codify one or two golden-path flows.
4. **Golden** — non-map widgets only, once their UI is stable.

## How E2E uses the InteractionController

`integration_test` does **not** make the controller redundant — the bus is
app-internal plumbing, not a test rig, and the tests exercise it either way:

- **Indirectly (normal path):** tests tap real widgets via Finders
  (`tester.tap(find.byKey(...))`). Because every action routes through the bus,
  that tap flows through the InteractionController exactly as a user tap would —
  no explicit call needed.
- **Directly (our advantage):** a test *can* call `dispatch(...)` to drive an
  action programmatically (skip fiddly gestures for setup), and read the **ring
  buffer** to assert the right interaction fired with the right payload/origin —
  a cleaner check than asserting on-screen pixels alone. The `InteractionIds`
  enum (what the bridge exposes as `orion.ids`) is imported directly — it's the
  ready-made catalog of interaction targets; `integration_test` has no equivalent
  registry of its own.

This is in-process and reuses our own plumbing — **no console bridge involved.**

## Non-goals

- Headless/widget/golden coverage of the map view itself — it's a platform view;
  verified by running the app manually (`devLog`, eyeballing), not headless tests.
- A CI pipeline to run all this — that's **DevOps** ([`../../devops.md`](../../devops.md)),
  not this task. This task is about the tests and local tooling.

## Open questions

- ~~`integration_test` vs console bridge for E2E?~~ → **`integration_test`** (+
  Patrol), in-process, mobile + web. The console bridge is **not** used for tests.
- Golden-test toolchain (stock `matchesGoldenFile` vs `alchemist`/`golden_toolkit`)
  — defer until we actually want goldens.
