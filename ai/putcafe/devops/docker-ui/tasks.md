# Docker UI — Tasks

Design: [`design.md`](design.md). All code in worktree
`~/git/worktrees/putcafe/docker-ui` (branch `feature/docker-ui`).

## T1 — Compose stack definition

`scripts/dev/remote/edge/ops-ui/compose.yml` (new): dozzle `amir20/dozzle:v8`,
socket + `./data:/data` mounts, `127.0.0.1:8103:8080`, simple auth + actions
env, built-in healthcheck, `restart: unless-stopped`.
**Verify:** `docker compose -f … config -q` parses.

## T2 — Caddy site block

`scripts/dev/remote/edge/site.caddy`: add `ops.{$ORION_HOST}` host →
`reverse_proxy 127.0.0.1:8103`; update header comment.
**Verify:** remote `setup.sh` validates the merged Caddyfile on the box (T5).

## T3 — Remote provisioner

`scripts/dev/remote/edge/setup-ops-ui.sh` (new): preconditions (docker,
compose.yml, creds.env), users.yml generate-on-change via
`docker run --rm amir20/dozzle:v8 generate`, `compose up -d`,
restart-on-creds-change, report URL. Idempotent, check-then-act.
**Verify:** `bash -n` + shellcheck; re-run is a no-op (T5).

## T4 — Laptop orchestrator + ops.sh awareness

`scripts/dev/local/edge/setup-ops-ui.sh` (new): per design (secrets bootstrap,
asset upload, remote setup.sh then setup-ops-ui.sh, summary).
`scripts/dev/remote/edge/ops.sh`: `status` shows ops-ui container, `health`
curls the ops URL. `scripts/dev/local/edge/ops.sh`: same addition to its
local `health` branch.
**Verify:** `bash -n` + shellcheck all touched scripts.

## T5 — Provision + live verification

Run `./scripts/dev/local/edge/setup-ops-ui.sh` twice (second run must be a
no-op, no dozzle restart). Then:
1. `docker ps` on VPS: `ops-ui-dozzle-1` up; `api-*` uptimes untouched.
2. `curl -sI https://ops.<host>/` → 200 (login page), valid cert.
3. Browser-level check: login with creds from `.secrets/ops-ui.env`, see all
   4 containers grouped (api stack + ops-ui), live logs + stats.
4. Regression: `https://putcafe.<host>/web/` and Orion `https://<host>/web/`
   still 200; `/api/positions/health` + `/api/bot/health` still healthy.

## T6 — Review doc

`review.md` with the full numbered verification checklist.
