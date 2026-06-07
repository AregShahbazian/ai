# API container release: downtime & scaling

**Date:** 2026-06-08
**Context:** Same-day follow-on to the Phase 12 Docker discussions
([`2026-06-08-docker-deploy-strategy.md`](2026-06-08-docker-deploy-strategy.md),
[`2026-06-08-staging-topology.md`](2026-06-08-staging-topology.md)). Covers what
actually happens when a new API/DB image is released, the brief downtime that
causes, and how it's eliminated at larger scale.

## Summary

We walked through the container-release mechanics: the API container is replaced
from the new image on each deploy (the DB container is not), which introduces a
~second of downtime, and how that's solved both at small scale (blue-green on one
box) and at larger scale (replicas + rolling deploy behind a load balancer).

## Key conclusions

- **API release:** `docker compose up` stops the old API container and starts a
  fresh one from the new image (pulled from ghcr). Standard.
- **DB is different:** the Postgres container is **not** rebuilt per release — its
  image is stable; only the schema changes (via migrations), and data persists on
  the named volume. Don't recreate the DB container to ship app code.
- **Brief downtime:** recreating the API container leaves a ~1–2 s gap.
- **Small-scale fix:** start the new container **before** stopping the old
  (blue-green / rolling) with a **healthcheck**; Caddy switches to it once healthy.
  For Orion's current scale the ~2 s gap is also acceptable if kept simple.
- **Large-scale fix:** run **multiple API replicas behind a load balancer**; the
  deploy rolls them one at a time so others keep serving → zero downtime.
- **Statelessness is the prerequisite:** rolling replicas require a **stateless**
  API — no in-memory session/state; keep state in Postgres (or Redis).
- **Load balancer:** no extra container needed at this scale — **Caddy already is
  one** and load-balances across replicas natively.

## Open questions

- Adopt blue-green now, or accept the brief gap and keep Compose dead-simple?
- When (if ever) Orion needs multi-replica + rolling deploys vs single-instance.
- Whether a separate state store (Redis) is ever warranted, or Postgres suffices.

## Ideas to realize

- **Healthcheck + start-new-before-stop-old (blue-green) API swap** on the single
  box, with Caddy switching on healthy — eliminates the recreate gap.
- **Design the Dart API stateless from the start** (no in-memory session state;
  state in Postgres) so multi-replica rolling deploys are possible later without a
  rewrite.
- **Caddy as the load balancer** across multiple API replicas when scale demands
  it (no separate LB container at current scale).
- **Keep the DB container out of the app-release cycle** — ship schema changes via
  migrations against a persistent volume, never by recreating Postgres.
