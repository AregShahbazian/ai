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
- [`../discussions/2026-06-08-api-deploy-downtime-scaling.md`](../discussions/2026-06-08-api-deploy-downtime-scaling.md)
  — same-day follow-on on **API release mechanics**: API container is recreated
  from the new image per deploy (DB is not — schema via migrations on a persistent
  volume); the ~1–2 s recreate gap is closed by blue-green/healthcheck on one box,
  and at scale by stateless API + multiple replicas behind Caddy as load balancer.
- [`../discussions/2026-06-08-feature-staging-deploys.md`](../discussions/2026-06-08-feature-staging-deploys.md)
  — same-day follow-on on **per-feature staging deploys**: per-feature staging URLs
  are **frontend-only** (Caddy `?version=<branch>`, reusing the `/web/<name>/`
  preview mechanism — no extra containers); the backend has just **two
  environments** (prod + staging), and backend changes are tested **serially** on
  the shared staging API before promotion to prod.
- [`../discussions/2026-06-08-prod-tag-release-gate.md`](../discussions/2026-06-08-prod-tag-release-gate.md)
  — same-day follow-on, **decision** to adopt **tag-to-release with a manual gate**:
  `main` auto-deploys to staging; a version tag triggers automated build/image/
  push/tests up to a **manual approval gate** (GitHub Actions "Environments" +
  required reviewers, approved in the repo UI), after which prod deploy
  (pull → migrate → swap → healthcheck) is automated.
