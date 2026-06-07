# Docker deploy strategy for the Phase 12 backend

**Date:** 2026-06-08
**Context:** Follow-on to defining Phase 12 (DevOps backend stack). Explored
whether/when Orion's VPS backend needs Docker, and how a containerized deploy
would actually work end-to-end.

## Summary

We confirmed the Phase 12 stack (Caddy edge → Dart `shelf` API → Postgres/PostGIS,
under systemd, schema via dbmate) does **not** strictly need Docker for a single
box. But two of the user's real requirements — **reproducible deploys across
machines** and an upcoming **staging DB** — tip the decision toward adopting
Docker at Phase 12. We then walked the full containerized flow and terminology so
the user understands the moving parts before committing.

## Key conclusions

- **When Docker is worth it:** multiple isolated service versions, reproducible
  deploys across machines, conflicting dep versions, or per-env (staging/prod)
  isolation. The user has #2 and #4 → **adopt Docker at Phase 12.**
- **Container vs image:** image = static recipe/template; container = a running
  instance of an image.
- **Image is "baked" by the Dockerfile**, executed by `docker build`. The
  **Dockerfile lives in the repo** (user owns/writes it); the **image manifest**
  (JSON metadata: layers + config) is auto-generated at build and stored in the
  registry alongside the image.
- **Build happens on GitHub's runners**, not the VPS — all the heavy downloading/
  unpacking/compiling (Flutter, Dart SDK, deps) runs there. **Flutter and build
  tools never end up in the runtime image** (multi-stage: build stage with SDK →
  tiny runtime image with just the Dart server + runtime deps).
- **Registry:** GitHub Container Registry (ghcr.io) — GitHub hosts the image
  bytes; user owns the namespace and controls visibility. Docker Hub or a
  self-hosted registry are alternatives.
- **Deploy flow:** workflow builds image → pushes to ghcr → **registry is passive
  (no auto-notification)** → something must trigger the VPS to `docker compose
  pull && up -d`. Either the workflow's last step SSHes in to trigger it
  (matches today's rsync deploy), or the VPS polls / uses a webhook.
- **VPS-key implication:** if the VPS pulls itself (poll/webhook), GitHub never
  SSHes it, so **changing VPS doesn't require adding a new GitHub SSH key**. With
  the SSH-trigger style, you still add a key per VPS.
- **Restarting a container** does NOT reinstall packages — everything is baked in;
  start is seconds.
- **Image size estimate:** Dart API multi-stage ~50–200 MB; compiled-exe on a
  slim base ~20–80 MB.
- **Staging vs prod:** **same image, different containers** — config differs
  (env vars, ports, DB connection); staging → staging Postgres, prod → prod.
- **Edge in a container:** cleanest is Caddy as its own container in the same
  Compose stack, proxying to the API over Docker's internal network. Never bundle
  Caddy + app in one container. Static web files = a volume/host mount, not a
  container.
- **Docker Compose:** a tool + `docker-compose.yml` defining the multi-container
  stack (networks, volumes, config) run with `docker compose up`.
- **Container count:** ~3–4 (Caddy, Dart API, Postgres/PostGIS) — up to ~5 if
  staging API+DB run on the same box. Static web = files, not a container.
- **Postgres data gotcha (#1 Docker-Postgres mistake):** containers are
  ephemeral — recreating one wipes its internal filesystem. Postgres data **must**
  live on a host-backed **named volume** (`pgdata:/var/lib/postgresql/data`) so it
  survives restarts/redeploys. Add scheduled `pg_dump` backups on top.
- **Switching VPS, minimal steps:** (1) `pg_dump` backup, (2) install Docker on
  new box, (3) copy Compose + restore volume/dump, (4) `docker compose up`,
  (5) repoint DNS. **Data is carried by steps 1 + 3 only.**

## Open questions

- Compose vs `docker run` + systemd for prod/staging orchestration.
- Staging on the same VPS or a second box.
- Deploy trigger: keep SSH-trigger (consistent with current rsync) vs VPS
  poll/webhook (decouples from VPS SSH keys).
- Registry choice: ghcr.io (leading candidate) vs Docker Hub vs self-hosted.
- Whether the Flutter web build gets containerized or stays host static files
  served by Caddy.
- Auto-deploy policy: staging on `feature/**`, prod on `main`?

## Ideas to realize

- **Adopt Docker for the Phase 12 backend** (driven by reproducible-cross-machine
  deploys + staging DB needs). Update `mvp/phase-12/stack.md` to reflect a
  containerized deploy as the chosen direction.
- **Multi-stage Dockerfile** for the Dart `shelf` API: SDK build stage → minimal
  runtime image (target ~20–80 MB compiled-exe).
- **docker-compose.yml** defining the stack: Caddy (edge) + Dart API +
  Postgres/PostGIS, on an internal Docker network.
- **Named volume for Postgres** data (`pgdata:/var/lib/postgresql/data`) — never
  store DB data inside the container.
- **Scheduled `pg_dump` backups** (cron/systemd timer) for both prod and staging
  DBs, written off-volume.
- **Push images to ghcr.io** from the GitHub workflow (build on runners, push
  image — never ship source/build tools to the VPS).
- **CD trigger mechanism**: decide SSH-trigger vs VPS-pull (poll/webhook); a
  VPS-pull approach removes the per-VPS GitHub SSH key dependency.
- **Separate staging + prod containers from the same image**, differing only by
  config/env; consider `feature/**` → staging, `main` → prod auto-deploy.
- **"Move to a new VPS" runbook**: pg_dump → install Docker → copy Compose +
  restore data → `compose up` → repoint DNS.
- **Caddy as its own container** in the Compose stack (not bundled with the app);
  decide where static web files live (volume vs host mount).

> Follow-on (same-day, separate session): **staging topology** →
> [`2026-06-08-staging-topology.md`](2026-06-08-staging-topology.md).
