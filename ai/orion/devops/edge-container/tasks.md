# Containerized Edge — Tasks

Design: [`design.md`](design.md). Orion code in
`~/git/orion-p12-devops-edge`; putcafe side in
`~/git/worktrees/putcafe/docker-ui` (tracked in putcafe `pc-docker-ui` docs).

## T1 — Commit the pending glob-import Caddyfile change (orion)

The worktree's uncommitted `import /root/*/site.caddy` edit is live on the VPS
already; commit it as its own change before new work.

## T2 — Edge compose stack (orion)

`scripts/dev/remote/edge/compose.yml` (new): project `edge`, caddy:2.11,
host networking, ro mounts of `/root/orion` + `/root/putcafe`, env_file,
data/config volumes, admin healthcheck. **Verify:** `docker compose config -q`.

## T3 — Rewrite remote `setup.sh`, `ops.sh`; update local `setup.sh` (orion)

Per design: docker bootstrap, docker-run validate, cert migration, cutover,
compose steady-state; ops.sh → compose; local setup.sh uploads compose.yml to
`/root/orion/edge/` and drops the unit upload; delete `orion-web.service` from
the repo. **Verify:** `bash -n` + shellcheck.

## T4 — Migrate the VPS (orion)

Run `./scripts/dev/local/edge/setup.sh`. **Verify:** `edge-caddy-1` up
(healthy); orion `/web/` + `/apk/` 200; putcafe `/web/`, `/web/staging/`,
api healths, ops UI all still served; certs reused (no new issuance in caddy
logs); `systemctl is-enabled orion-web` = disabled. Re-run setup → no-op,
no restart.

## T5 — Putcafe scripts follow the new edge (putcafe)

`remote/edge/setup.sh`: preconditions (compose file instead of unit),
docker-run validate, compose-exec reload. `remote/edge/ops.sh` +
`local/edge/ops.sh`: compose-based status/start/stop/restart/reload/logs.
`site.caddy` comment touch-up. **Verify:** `bash -n` + shellcheck; re-run
`setup-ops-ui.sh` end-to-end green.

## T6 — UI + regression verification

Dozzle shows `edge` group with `edge-caddy-1` separate from `api`/`ops-ui`;
caddy logs visible live. Full health sweep (orion + putcafe + ops).

## T7 — Merge + push + CI

Orion: merge `feature/p12-devops-edge` → `main`, push. Putcafe: merge
`feature/docker-ui` → `main`, push. Home repo: commit docs, push. Watch both
CI runs green (orion deploys web staging; putcafe path-filtered).
