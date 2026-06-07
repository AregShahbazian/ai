# Phase 12 — DevOps: sources & background

Pointers to the discussions and reasoning behind the Phase 12 backend stack.
See [`stack.md`](stack.md) for the locked stack itself.

## Discussions

- [`../discussions/2026-06-08-docker-deploy-strategy.md`](../discussions/2026-06-08-docker-deploy-strategy.md)
  — when/whether Docker is needed for the VPS backend, and how a containerized
  deploy works end-to-end (image vs container, Dockerfile/manifest ownership,
  build-on-GitHub-runners, ghcr.io registry, Compose, Postgres volume gotcha,
  staging vs prod, switching VPS). **Decision: adopt Docker at Phase 12**, driven
  by reproducible cross-machine deploys + an upcoming staging DB. Its
  "Ideas to realize" section is the concrete build backlog for this phase.
- [`../discussions/2026-06-08-staging-topology.md`](../discussions/2026-06-08-staging-topology.md)
  — same-day follow-on on **staging topology**: staging gets its own API + Postgres
  containers (separate volume), one Caddy routes prod vs staging by hostname
  (~5 containers same-box), start same-box and split to a second box later if it
  risks prod.
