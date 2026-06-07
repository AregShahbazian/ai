# Phase 12 — DevOps (MVP slice)

> Phases deliver the [MVP](../mvp.md). DevOps as a whole is an **ongoing concept
> epic**, not a phase — see [`../devops.md`](../devops.md) and [`../devops/`](../devops/).
> This phase captures only the sliver of DevOps the MVP actually needs.

## Scope (MVP)

**Only the edge is needed for the MVP.** The MVP is local-only (no
account/backend), so the sole infrastructure requirement is:

- **Caddy edge** serving the Flutter web build over **HTTPS**, plus the existing
  GitHub Actions static deploy (web + APK) already in `build-and-deploy.yml`.

That's it. No API, no database, no containers for the MVP.

## Out of scope (→ DevOps concept epic)

Backend API, PostgreSQL/PostGIS, Docker/Compose, prod + staging environments,
ghcr images, gated tag releases, backups/runbooks — all of this is post-MVP and
lives in the ongoing DevOps epic: [`../devops.md`](../devops.md) /
[`../devops/`](../devops/).
