# Orion — Dev (Concept Epic)

> An **ongoing concept epic**, not a phase. Phases (`mvp/phase-N/`) deliver the
> [MVP](mvp.md) and are finite; Dev is continuous developer-experience and
> internal-tooling work that outlives any single release. Sits at the same level
> as [DevOps](devops.md). Detailed task docs live in [`dev/`](dev/).

**Status:** active concept epic
**Scope owner doc:** this file (the epic); [`dev/`](dev/) holds per-task PRDs and
design detail.

## What this epic is

Everything about how Orion is *developed and driven from the inside*: the
automation/diagnostics bridge (`orion` global / `ext.orion.*`), the controller
and command-bus organization that the bridge mirrors, dev-only console tooling,
test/automation scaffolding, and the conventions that keep all of it consistent.
It grows with the app rather than being "done."

Distinct from **DevOps** (build/ship/host/operate — see [`devops.md`](devops.md)):
Dev is about working *on and inside* the running app, not delivering it.

## Relationship to the MVP

The MVP doesn't depend on this epic — the app ships without any of it. But the
bridge is the substrate for scripted testing and bug-report diagnostics, so it's
worth keeping stable and well-organized as features land.

## Ongoing workstreams (high level)

- **Automation bridge** — the long-term, stable `orion` contract for driving and
  inspecting the app from a console or script (web + mobile).
- **Controller / command-bus organization** — the Dart structure the bridge
  mirrors; the convention that every state change is a dispatched id and every
  query is a direct read.
- **Dev tooling** — diagnostics dumps, replay, scripted flows.

## Tasks

- [`dev/console-bridge/prd.md`](dev/console-bridge/prd.md) — Console bridge +
  controller organization: a single stable `orion` contract, namespaced to
  mirror the controllers (`bus`/`map`/`settings`/`tracks`/`webnav`), with commands
  routed through the bus and queries read directly. Web + mobile (VM-service) at
  parity; adds crash-safety (no sync throws across interop, no unhandled
  rejections) and closes the `settings.logEvents` bus-bypass leak. ✅ implemented
  on `dev/console-bridge` (full PRD→design→tasks→review).
- [`dev/testing/prd.md`](dev/testing/prd.md) — Testing setup: a durable test
  strategy for an agent-developed, map-heavy Orion, with ≥1 useful test per
  category. ✅ **done for now** (merged to `main`, `dev/testing`): `integration_test`
  e2e harness (web + mobile, `ORION_E2E` deterministic boot, `e2e.sh` + `all_tests`
  aggregate), unified `ci.yml` (test+build+deploy per push), widget-Key=interaction-id
  convention, and a landed test in each category — unit (GPX round-trip on real
  MyTracks+Gaia samples), widget (settings toggle), e2e (compass-reset web+mobile,
  settings-nav mobile), golden (track-list row, local-only). Navigation e2e is
  mobile-only (web flutter_driver loses its result channel on route change).
