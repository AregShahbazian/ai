# Phase 12 — DevOps: backend stack

The locked backend/infra stack for Orion once it needs a real server (accounts,
sync, CRUD APIs, shared data). **Purely additive** — the existing GitHub Actions
deploy workflow and Caddy static serving are untouched; the API and DB are new
services on the same VPS.

## Locked stack

| Layer | Pick | Why |
|---|---|---|
| Edge / TLS | **Caddy** (keep) | Public HTTPS server: holds the cert, terminates TLS on 443, auto Let's Encrypt issuance+renewal, HTTP/2 & HTTP/3. Reverse-proxies `/api/*` → the app; serves the static Flutter web build directly. The only process facing the internet. |
| App / API | **Dart `shelf`** | Shares models/serialization with the Flutter app — one language across the stack. Binds `localhost:8080` (plain HTTP, private, never exposed). |
| DB | **PostgreSQL + PostGIS** | Real relational DB with spatial extension: indexed track geometries, bbox / nearby / distance queries, GeoJSON in/out. |
| Runtime | **systemd** unit | Manages the Dart server process; no Docker (matches the root-on-VPS `claude-vps` philosophy). |
| Migrations | **dbmate** | Plain-SQL versioned schema; simplest with PostGIS `CREATE EXTENSION`. |

## Why the edge is split from the API

Caddy could be merged into the app (app binds 443, does its own TLS), but they're
kept separate because:

1. **TLS is solved — don't reimplement it.** Caddy does ACME issuance/renewal,
   OCSP, HTTP/2+3, modern ciphers for free.
2. **One cert, many backends.** The edge serves the static web build *and*
   `/api/*` *and* anything added later, under one domain + one cert.
3. **Restart isolation.** Redeploying/crashing the Dart app doesn't drop TLS for
   the whole site — Caddy stays up and briefly 502s `/api` during a restart.
4. **Smaller attack surface.** The app binds `localhost:8080`, unreachable from
   the internet; only Caddy faces the world. Rate-limiting, auth, compression,
   logging live at the edge in one place.
5. **Cheap.** The proxy is one config block; the hop is localhost, sub-ms.

Standard shape: a thin, battle-tested front door + dumb internal app processes.

## Caddyfile (edge → app)

```
orion.example.com {
  handle /api/* { reverse_proxy localhost:8080 }
  handle { root * /root/orion/site/web; file_server }
}
```

## Relationship to existing deploy

- GitHub Actions (`build-and-deploy.yml`) already rsync/scp's the static web +
  APK builds over plain SSH to `/root/orion/site/{web,apk}/` — **no special
  service, just `ssh`/`rsync`/`scp`** authenticated by `secrets.VPS_SSH_KEY`
  (public half in the VPS user's `~/.ssh/authorized_keys`).
- This phase adds the **API process** + **DB** behind Caddy; the deploy workflow
  and deploy root are reused as-is unless we revisit the `/root/orion/site/` path.

## Open / future (not part of the locked stack yet)

- API deploy mechanism (separate workflow / systemd restart hook on push).
- Auth/accounts model.
- Backup strategy for Postgres.
- Whether previews (`feature/<name>`) get their own API/DB slot or share one.

## Build scaffolding (when we start)

1. `backend/` Dart `shelf` skeleton — health route + a PostGIS-backed
   `/api/tracks` example.
2. systemd unit for the Dart server + the Caddyfile block above.
3. dbmate migration enabling PostGIS + a `tracks` table with a `geometry` column.

No PRDs yet.
