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
