---
id: pc-devops
---

# Putcafe — DevOps (build/release pipeline + VPS)

Build, release, and hosting for putcafe, modeled on Orion's phase-12 edge work
— reference the planning at `~/ai/orion/mvp/phase-12/` and the working tree at
`~/git/orion-p12-devops-edge` (unfinished; **its PRD is the authoritative
reference**, not its code). Serves [`../bare/prd.md`](../bare/prd.md)
first (static frontend), then [`../mvp/prd.md`](../mvp/prd.md) (backends
+ DB).

## Requirements

### 1. Shared VPS, zero interference with Orion

- Same VPS Orion runs on. Orion's services, paths, units, and deploys must be
  completely unaffected: separate directories, services/containers, and ports;
  the only shared component is the edge server, which gains a putcafe site.
- HTTPS via the existing wildcard-DNS scheme: **`putcafe.46-250-232-224.sslip.io`**
  (Let's Encrypt auto-provisioned, as Orion does). A real domain can swap in
  later with a one-line edge change.

### 2. What runs on the VPS

- **Frontend** — static web build served over HTTPS.
- **Backends** (when the mvp lands) — bot-backend and positions-backend as
  **containers** (Docker/Compose; unlike Orion's static-only MVP, putcafe has
  real services + a DB, which is what Docker is for).
- **DB** — persisted on the VPS (volume), surviving container restarts and
  redeploys.

### 3. CI/CD — GitHub Actions, Orion's deploy mapping

- **push to `main` → staging** (auto).
- **version tag → prod** (gated by a manual-approval GitHub Environment;
  solo-dev self-approval).
- **`feature/**` / `dev/**` → per-branch preview slots** (auto, frontend only).
- One pipeline for the monorepo: builds frontend (and later backend images),
  publishes to the matching slot on the VPS.

### 4. Scripts — laptop-driven, no manual VPS login

Mirror Orion's two-layer layout:

- **`scripts/dev/local/`** — run from the laptop (`./scripts/dev/...`); thin
  SSH wrappers around the remote scripts. SSH auth by **key**; any creds live
  in a **gitignored** config file (source material in `~/git/claude-vps`,
  non-staged).
- **`scripts/dev/remote/`** — the matching on-box scripts.
- Operations: **setup** (provision), **status**, **start/stop/restart**,
  **logs**, **health check** (curl the public endpoints).

### 5. Setup script — idempotent, safe anytime

One setup script provisions a fresh VPS slot for putcafe **and** is safe to
re-run against the live box: every step checks before acting (install only if
absent, write only if changed, never touch Orion's config beyond adding the
putcafe edge site).

### 6. Agent operating rule

Any command the agent runs on the VPS must be executed **via a committed script
file** (then run over SSH) — never ad-hoc one-liners — so every action is
reproducible by the user.

### 7. Handoff

When implemented, the apply-steps (VPS setup, first deploy, how to verify) must
be described clearly and runnable end-to-end from the laptop.

## Non-requirements

- No real domain, no backups/runbooks, no blue-green deploys, no monitoring
  stack, no Android distribution, no multi-VPS. Revisit post-MVP.
