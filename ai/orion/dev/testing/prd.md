---
id: dev-testing
title: Testing setup — useful tests in every category for an agent-developed Orion
status: in-progress
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

**The task is not just the harness — it is to land genuinely useful tests in
*each* category** (unit, widget, integration/e2e, and golden). "Useful" has a
bar (see [Definition of done](#definition-of-done--a-useful-test-per-category)):
a test must be **deterministic**, assert **real behaviour** (not a tautology or a
constant), **fail if the feature regresses**, and **run in CI**. A passing suite
that asserts nothing meaningful does not count. The category is only "done" when
at least one such test exists and is exercised by `./scripts/...` + CI.

## Where we are today

**Unit:** two files, both effectively unit tests —
`test/interaction_controller_test.dart` (real value; locks down the app spine:
dispatch runs handlers, payload/origin recorded, ring buffer evicts) and
`test/widget_test.dart` (misnamed; asserts the map style URL constant — marginal).
Coverage of GPX/stats/Drift is still missing.

**Integration/e2e:** harness is **built and green in CI** — `integration_test`
+ `flutter drive`, web (`-d web-server`, headless-capable) and mobile (real
device), an `ORION_E2E` define for a deterministic fixed-camera boot, an
`all_tests.dart` aggregate entrypoint, and `./scripts/{web,mobile}/e2e.sh`. Two
real suites landed: **compass-reset** (rotate → confirm → tap reset → verify
north-up) and **settings-nav** (open `/settings` → native back → home). The
widget-Key-as-interaction-id convention is adopted for HUD controls.

**Widget:** none yet. **Golden:** none yet.

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

## Definition of done — a useful test per category

The task ships when **every** category below has at least one test meeting the
"useful" bar (deterministic · asserts real behaviour · fails on regression · runs
in CI). Each must be wired into the standard run (`flutter test` or
`./scripts/.../e2e.sh`) so CI exercises it.

- [ ] **Unit** — e.g. a GPX import→export **round-trip** on a staged real sample
      asserting points/name/colour survive, plus track-stat math
      (distance/elevation) on a known input. *(Spine unit tests already exist.)*
- [ ] **Widget** — e.g. the Settings screen: toggling a `SwitchListTile`
      dispatches the right id and flips persisted state; or a track-list row
      renders its stats. Non-map UI only.
- [x] **Integration/e2e** — compass-reset + settings-nav suites (above). Add a
      **tracks import** flow (stub `file_picker` with a staged fixture GPX →
      assert one track imported via the repository) to cover the data path.
- [ ] **Golden** — one deterministic non-map widget (e.g. a track stat card /
      list row) pinned with `matchesGoldenFile`. Never the map.

"Useful" anti-examples to avoid: asserting a constant equals itself, a test with
no `expect`, or one that passes whether or not the feature works.

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

**Widget Key convention:** a widget that is the 1:1 trigger for one interaction
gets `key: ValueKey(InteractionIds.<that>)`, so a test locates it with
`find.byKey` using the same string the bus/console bridge use — one vocabulary,
no parallel naming, and the bridge keeps driving via `dispatch` regardless. Add
the key when a test first needs the widget; skip it where a widget fires
several/no interactions. First adopter: `CompassButton` (`hud.resetOrientation.tap`).

## Where it runs (VPS / CI)

- **Web E2E runs headless on a plain VPS.** `flutter drive -d web-server
  --browser-name=chrome --headless` needs only Chrome + a version-matched
  chromedriver, no display. The `ORION_E2E` define makes the boot deterministic,
  so it's CI-ready as-is.
- **Mobile E2E effectively needs an emulator host.** `flutter drive -d <device>`
  requires a real device or an Android emulator, and the emulator needs
  KVM/nested virtualization — absent on most basic VPSes (software ARM emulation
  is too slow). Options: a nested-virt-capable host, or a device farm (Firebase
  Test Lab, BrowserStack). The runner/CI wiring itself is **DevOps**
  ([`../../devops.md`](../../devops.md)), not this task.

## Non-goals

- Headless/widget/golden coverage of the map view itself — it's a platform view;
  verified by running the app manually (`devLog`, eyeballing), not headless tests.
- *Designing* the CI/deploy infrastructure — that's **DevOps**
  ([`../../devops.md`](../../devops.md)). The CI workflow already runs these tests
  on every push; this task owns the tests themselves and their local tooling, and
  only requires that each lands *in* CI — not how the runner is built.
- Mobile e2e in CI (needs an emulator host / device farm) — deferred to DevOps;
  mobile suites run locally for now.

## Open questions

- ~~`integration_test` vs console bridge for E2E?~~ → **`integration_test`** (+
  Patrol), in-process, mobile + web. The console bridge is **not** used for tests.
- Golden-test toolchain (stock `matchesGoldenFile` vs `alchemist`/`golden_toolkit`)
  — defer until we actually want goldens.
