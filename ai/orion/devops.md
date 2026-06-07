# Orion — DevOps (Concept Epic)

> An **ongoing concept epic**, not a phase. Phases (`phase-N/`) deliver the
> [MVP](mvp.md) and are finite; DevOps is continuous infrastructure/delivery work
> that outlives any single release. Detailed docs live in [`devops/`](devops/).

**Status:** active concept epic
**Scope owner doc:** this file (the epic); [`devops/`](devops/) holds the stack,
sources, and design detail.

## What this epic is

Everything about how Orion is built, shipped, hosted, and operated: the VPS, the
edge/HTTPS server, the backend API + database, containerization, environments
(prod/staging), CI/CD pipelines, releases, and the operational runbooks. It grows
as the app does, rather than being "done."

## Relationship to the MVP

The MVP is local-only (no account/backend). The **only** DevOps piece the MVP
needs is the **edge**: Caddy serving the Flutter web build over HTTPS (plus the
existing GitHub Actions static deploy). Everything else in this epic — API, DB,
containers, staging, gated prod releases — is **post-MVP** and tracked here, not in
a phase. See [`phase-12/prd.md`](phase-12/prd.md) for the MVP-scoped slice.

## Locked direction (summary)

The backend, when it lands, is a **Docker Compose** stack on the VPS: **Caddy**
edge (HTTPS + reverse-proxy) → **Dart `shelf`** API → **PostgreSQL + PostGIS**,
images built on GitHub runners and pushed to **ghcr.io**, schema via **dbmate**.
Two long-lived backend environments (**prod** + **staging**); per-feature staging
URLs are frontend-only. Prod ships via **tag-to-release with a manual gate**
(GitHub Actions Environments). Full detail + rationale:

- **Stack** → [`devops/stack.md`](devops/stack.md)
- **Sources / discussions** → [`devops/sources.md`](devops/sources.md)

## Ongoing workstreams (high level)

- **Edge / hosting** — Caddy, TLS, DNS, the VPS itself.
- **Backend** — Dart `shelf` API + Postgres/PostGIS.
- **Containerization** — Dockerfile, Compose, volumes, ghcr images.
- **Environments** — prod + staging, isolation, resource limits.
- **CI/CD** — build/test pipelines, staging auto-deploy, gated prod tag releases.
- **Ops** — backups (`pg_dump`), restore/runbooks, move-to-new-VPS procedure,
  monitoring, rollback.

See [`devops/sources.md`](devops/sources.md) for the captured ideas-to-realize
backing each of these.
