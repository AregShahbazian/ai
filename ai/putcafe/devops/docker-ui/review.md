# Docker UI — Review

PRD: [`prd.md`](prd.md) (`pc-docker-ui`). Live at
**https://ops.46-250-232-224.sslip.io/** — creds in
`scripts/dev/local/edge/.secrets/ops-ui.env` (both checkouts).

## Round 1: initial implementation + live provisioning (2026-06-12)

Implemented per [`tasks.md`](tasks.md) in worktree
`~/git/worktrees/putcafe/docker-ui`; provisioned live from the laptop script.
Screenshots: [dashboard](ops-ui-dashboard.png), [live logs](ops-ui-logs.png).

### Bug 1: `dozzle generate` choked on generated password
**Root cause:** local creds bootstrap used `openssl rand -base64 | tr '+/' '-_'`;
a password starting with `-` was parsed as a CLI flag by `dozzle generate`.
**Fix:** `openssl rand -hex 16` locally (never starts with `-`, shell-safe) +
`--password=`/`--name=` equals-form in the remote script.
**Files:** `scripts/dev/{local,remote}/edge/setup-ops-ui.sh`

### Bug 2: health check expected 200, Dozzle answers 307
**Root cause:** with auth enabled, `/` redirects (307) to `/login`.
**Fix:** follow redirects (`curl -L`), expect 200 after; applied to the setup
wait-loop and both `ops.sh` health additions.
**Files:** `scripts/dev/local/edge/setup-ops-ui.sh`,
`scripts/dev/{local,remote}/edge/ops.sh`

### Verification
1. ✅ `bash -n` + shellcheck clean on all four touched scripts; compose file
   parses (`docker compose config -q`) (agent-verified)
2. ✅ first `setup-ops-ui.sh` run provisions end-to-end: edge reload,
   users.yml generated, `ops-ui-dozzle-1` up (healthy) (agent-verified)
3. ✅ second run is a true no-op: "users.yml up to date", container kept
   running, **no dozzle restart** (agent-verified)
4. ✅ `https://ops.<host>/` serves over valid HTTPS, redirects to login;
   `ops.sh health` (laptop): `/web/` 200, `/web/staging/` 200, ops UI 200
   (agent-verified)
5. ✅ login with `.secrets/ops-ui.env` creds works (Playwright); dashboard
   shows all 4 containers — `api` stack grouped (bot/positions/db) +
   `ops-ui-dozzle-1` — with status, created, live CPU/MEM, host totals
   (4 CPUs / 7.76 GB) (agent-verified)
6. ✅ per-container live logs render (api-bot-1 uvicorn log) (agent-verified)
7. ✅ no interference: `api-*` uptimes continuous across provisioning;
   `/api/positions/health` + `/api/bot/health` return ok; Orion
   `https://<host>/web/` still 200 (agent-verified)
8. wrong password rejected at login (not yet tested)
9. container actions (start/stop/restart from the UI, enabled via
   `DOZZLE_ENABLE_ACTIONS`) — try restarting `api-bot-1` from the UI
10. user check from own browser: open https://ops.46-250-232-224.sslip.io/,
    log in, browse containers/logs
