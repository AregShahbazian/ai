# Phase 12 — DevOps (MVP edge slice + staging)

> Phases deliver the [MVP](../mvp.md). DevOps as a whole is an **ongoing concept
> epic**, not a phase — see [`../devops.md`](../devops.md) and [`../devops/`](../devops/).
> This phase captures only the edge sliver the MVP actually needs — now including a
> **staging** environment for the frontend.

`id: phase-12-edge`

## Scope (MVP)

The MVP is local-only (no account/backend), so the only infrastructure is the
**edge**: one Caddy serving the Flutter web build + APKs over **HTTPS**, fed by the
existing GitHub Actions deploy. This phase adds **staging** alongside prod and
formalises which push deploys to which environment.

### 1. Caddy edge — hosts everything, one server

One Caddy on the VPS serves, for **web and APK**:

- **prod** — the released build.
- **staging** — the `main` build, for pre-release testing.
- **feature previews** — per-branch builds (`feature/**`, `dev/**`).

Static files only — no containers, no API, no DB. Staging is **not** a separate
box or service; it is just another path slot served by the same Caddy (same
mechanism as today's feature previews), so it costs nothing extra.

### 2. URL structure & index pages — untouched

The current layout stays exactly as-is — staging slots in as a reserved preview
slot, prod stays at the root:

| Environment | Trigger          | Web                | APK                |
|-------------|------------------|--------------------|--------------------|
| **prod**    | version **tag**  | `/web/`            | `/apk/`            |
| **staging** | push to `main`   | `/web/staging/`    | `/apk/staging/`    |
| **preview** | `feature/**`,`dev/**` | `/web/<slot>/` | `/apk/<slot>/`     |

`staging` is just a slot name, so the existing nested-path serving, the landing
index (`gen-landing-index.sh`), and the APK index (`gen-apk-index.sh`) keep working
unchanged — no new code paths, no new index pages.

### 3. Deploy mapping — which push → which env

Adopt the discussed flow (see
[`../discussions/2026-06-08-prod-tag-release-gate.md`](../discussions/2026-06-08-prod-tag-release-gate.md)):

- **`main` → staging** (auto): every push to `main` deploys to the staging slot.
- **version tag → prod** (gated): pushing a tag deploys to the prod root, behind a
  **manual approval gate** (GitHub Actions **Environments** + required reviewer,
  approved in the repo UI; solo-dev self-approval for now).
- **`feature/**`, `dev/**` → preview** (auto): unchanged.

This is the **only behavioural change to `ci.yml`**: `main` stops publishing to the
prod root and publishes to `/…/staging/`; a new tag-triggered, gated job publishes
to the prod root. Frontend per-feature staging stays as-is (backend per-feature is
explicitly out — see
[`../discussions/2026-06-08-feature-staging-deploys.md`](../discussions/2026-06-08-feature-staging-deploys.md)).

### 4. HTTPS — without owning a domain

Location permission (geolocation) needs a **secure context**, so the web endpoint
must be HTTPS even before there's a real domain. Use a free wildcard-DNS hostname
that resolves to the VPS IP and is eligible for a real Let's Encrypt cert:

- e.g. `46-250-232-224.sslip.io` (or `nip.io`) → resolves to the VPS IP.
- Caddy auto-provisions + renews the cert via the HTTP-01 challenge.
- Requires ports **80 + 443** open (the `orion-web.service` unit already grants
  `CAP_NET_BIND_SERVICE`).

A real domain can replace the sslip.io host later by swapping one Caddyfile line —
no other change. Bare-IP HTTPS is **not** possible (Let's Encrypt won't issue for
an IP), hence the sslip.io hostname.

### 5. Edge scripts — driven from the laptop, no manual VPS login

All routine edge operations are scripts, never hand-typed on the box:

- **`scripts/dev/local/edge/`** — run **from the laptop**; each wraps an SSH call to
  the VPS so day-to-day ops never require logging in manually. SSH auth uses a
  **key** (preferred); any creds live in a **gitignored** file inside the scripts
  folder (e.g. `deploy.conf` style, already gitignored).
- **`scripts/dev/remote/edge/`** — the matching scripts that run **on the VPS** (as
  root), for the rare case of operating on the box directly. The local scripts are
  thin SSH wrappers around these.

Operations to cover (both layers): **status**, **start**, **stop**, **restart**,
**reload** (apply a Caddyfile change with no dropped connections), **logs**
(`journalctl -u orion-web -f`), and a **health check** (`curl -sI` the web/apk
paths).

#### Migrate the existing scripts — and delete the old ones

The current edge tooling lives in `deploy/` and `deploy/vps/`. This phase **moves
it** into the new `scripts/dev/{local,remote}/edge/` layout and **removes the old
`deploy/vps/` scripts** (and the now-redundant `deploy/` copies) so there is one
home for edge ops:

| Old (delete after move)        | New home                                   | Layer  |
|--------------------------------|--------------------------------------------|--------|
| `deploy/vps/01-provision-vps.sh` | `scripts/dev/local/edge/` (setup)        | laptop |
| `deploy/vps/02-setup-github.sh`  | `scripts/dev/local/edge/` (gh wiring)    | laptop |
| `deploy/vps/remote-setup.sh`     | `scripts/dev/remote/edge/` (idempotent provision) | vps |
| `deploy/vps/deploy.conf(.example)` | `scripts/dev/local/edge/` (gitignored creds) | laptop |
| `deploy/Caddyfile`, `deploy/orion-web.service` | `scripts/dev/remote/edge/` (VPS assets) | vps |
| `deploy/gen-apk-index.sh`, `deploy/gen-landing-index.sh` | `scripts/dev/remote/edge/` | vps |
| `deploy/README.md`             | folded into the new dirs' docs             | —      |

`ci.yml` references (`deploy/gen-*.sh`, the deploy paths) are updated to the new
locations as part of the move. After migration the `deploy/` tree no longer exists —
nothing should point at it. The migrated setup script keeps the existing
**idempotent, safe-to-re-run** behaviour (§6).

### 6. Setup script — idempotent, safe to run anytime

One **setup** script provisions a brand-new VPS **and** is safe to re-run against a
live one — every step **checks first, then acts**, so it never harms a running
system (install Caddy only if absent, append the deploy key only if missing, write
the unit only if changed, etc.). Runnable both ways:

- from the **laptop** (`scripts/dev/local/edge`) — transfers files + runs the remote
  setup over one SSH connection;
- on the **VPS** (`scripts/dev/remote/edge`) — the idempotent on-box provisioner.

This generalises the existing `deploy/vps/remote-setup.sh` (already idempotent) into
the new local/remote `edge` layout (see the migration table in §5) — the old
`deploy/`/`deploy/vps/` scripts are deleted once moved.

## Out of scope (→ DevOps concept epic)

Backend API, PostgreSQL/PostGIS, Docker/Compose, ghcr images, per-feature **backend**
containers, blue-green API swaps, backups/runbooks — all post-MVP, in the ongoing
DevOps epic: [`../devops.md`](../devops.md) / [`../devops/`](../devops/). Docker is
deliberately **not** used here — for static-file serving it adds no value the edge
needs; the epic introduces it when the backend lands.
