# Phase 12 — DevOps: backend stack

The locked backend/infra stack for Orion once it needs a real server (accounts,
sync, CRUD APIs, shared data). Delivered as a **Docker Compose stack on the VPS**.
The existing GitHub Actions static deploy and Caddy serving stay intact; this phase
adds the API + DB and moves the runtime to containers.

**Direction decided in**
[`../discussions/2026-06-08-docker-deploy-strategy.md`](../discussions/2026-06-08-docker-deploy-strategy.md)
(see also [`sources.md`](sources.md)): **adopt Docker at Phase 12**, driven by two
hard requirements — **reproducible deploys across machines** and an upcoming
**staging DB**. Single-box systemd would work, but containers give cross-machine
reproducibility and clean prod/staging isolation.

## Locked stack

| Layer | Pick | Why |
|---|---|---|
| Edge / TLS | **Caddy** (own container) | Public HTTPS server: holds the cert, terminates TLS on 443, auto Let's Encrypt issuance+renewal, HTTP/2 & HTTP/3. Reverse-proxies `/api/*` → the API container over the internal Docker network; serves the static Flutter web build. The only thing facing the internet. |
| App / API | **Dart `shelf`** (container) | Shares models/serialization with the Flutter app — one language across the stack. Listens on `:8080` inside the Compose network, never exposed directly. |
| DB | **PostgreSQL + PostGIS** (container) | Real relational DB with spatial extension: indexed track geometries, bbox / nearby / distance queries, GeoJSON in/out. **Data on a host-backed named volume** (see below). |
| Orchestration | **Docker Compose** | One `docker-compose.yml` defines Caddy + API + Postgres, their network, volumes, and per-env config. Run/upgrade the whole stack with `docker compose up -d`. |
| Image registry | **ghcr.io** (GitHub Container Registry) | GitHub hosts the image bytes under our namespace; built on GitHub runners, pulled by the VPS. |
| Migrations | **dbmate** | Plain-SQL versioned schema; simplest with PostGIS `CREATE EXTENSION`. |

## Container layout

~3–4 containers (plus optional staging): **Caddy** (edge) · **Dart API** ·
**Postgres/PostGIS**. Static web files are a volume/host mount served by Caddy —
**not** a container. Staging (when added) is the **same image, separate
containers** differing only by config/env (ports, DB connection) → up to ~5
containers if staging runs on the same box.

## Postgres data — must persist

Containers are ephemeral: recreating one (image update, restart) wipes its internal
filesystem. Postgres data **must** live on a host-backed **named volume**, outside
the container lifecycle:

```yaml
volumes:
  - pgdata:/var/lib/postgresql/data
```

Forget this and a redeploy deletes the DB. Add scheduled `pg_dump` backups
(cron / systemd timer) written off-volume, for both prod and staging.

## Why the edge is split from the API

Caddy could be merged into the app (app binds 443, does its own TLS), but they're
kept as separate containers because:

1. **TLS is solved — don't reimplement it.** Caddy does ACME issuance/renewal,
   OCSP, HTTP/2+3, modern ciphers for free.
2. **One cert, many backends.** The edge serves the static web build *and*
   `/api/*` *and* anything added later, under one domain + one cert.
3. **Restart isolation.** Redeploying/crashing the API container doesn't drop TLS
   for the whole site — Caddy stays up and briefly 502s `/api` during a restart.
4. **Smaller attack surface.** The API has no published port; only Caddy faces the
   world. Rate-limiting, auth, compression, logging live at the edge in one place.
5. **Cheap.** The proxy is one config block; the hop is the internal Docker
   network.

Standard shape: a thin, battle-tested front door + dumb internal app containers.

## Caddyfile (edge → API container)

`api` is the API service name on the Compose network (Docker DNS resolves it):

```
orion.example.com {
  handle /api/* { reverse_proxy api:8080 }
  handle { root * /srv/web; file_server }
}
```

## Deploy flow

1. GitHub workflow **builds the API image on its runners** (multi-stage: Dart SDK
   build stage → minimal runtime image, ~20–80 MB compiled-exe; Flutter/build
   tools never reach the runtime image).
2. Workflow **pushes the image to ghcr.io**. The registry is passive — it does not
   notify the VPS.
3. The VPS gets the new image by `docker compose pull && up -d`, triggered either
   by the workflow's final SSH step (matches today's deploy style) **or** by a
   VPS-side pull (poll/webhook). A VPS-pull approach removes the per-VPS GitHub
   SSH-key dependency when changing boxes.
4. The static web build still ships as files (rsync to a Caddy-served volume/mount,
   reusing the existing `build-and-deploy.yml` path) — no special service, just
   `ssh`/`rsync`/`scp` authenticated by `secrets.VPS_SSH_KEY`.

## Switching VPS (runbook)

1. `pg_dump` backup of the DB.
2. Install Docker on the new box.
3. Copy `docker-compose.yml` + restore the volume/dump.
4. `docker compose up -d` (pulls images from ghcr).
5. Repoint DNS to the new IP.

Data is carried by steps **1 + 3** only; the rest just rebuilds the environment.

## Open / future

- Deploy trigger: SSH-trigger vs VPS-pull (poll/webhook).
- Auth/accounts model.
- Staging on the same VPS or a second box; `feature/**` → staging, `main` → prod?
- Registry visibility (private vs public) on ghcr.io.
- Whether the Flutter web build gets containerized too, or stays host static files.

## Build scaffolding (when we start)

1. **Multi-stage Dockerfile** for the Dart `shelf` API (SDK build → minimal
   runtime image).
2. **`docker-compose.yml`**: Caddy + API + Postgres/PostGIS on an internal
   network, with the `pgdata` named volume and the Caddyfile block above.
3. **`backend/`** Dart `shelf` skeleton — health route + a PostGIS-backed
   `/api/tracks` example.
4. **dbmate migration** enabling PostGIS + a `tracks` table with a `geometry`
   column.
5. **GitHub workflow** to build + push the API image to ghcr and trigger the VPS
   pull.
6. **Scheduled `pg_dump` backups** for prod + staging.

No PRDs yet.
