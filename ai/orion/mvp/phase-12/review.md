# Phase 12 — Review checklist (edge: staging + HTTPS + edge scripts)

`id: phase-12-edge`. Code is **uncommitted** in worktree
`/home/areg/git/orion-p12-devops-edge` (branch `feature/p12-devops-edge`). Verify,
then commit in `~/git/orion` referencing `[phase-12-edge]`.

## What shipped
1. New edge tree `scripts/dev/{local,remote}/edge/`; old `deploy/` + `deploy/vps/`
   removed (no tracked file references `deploy/` anymore).
2. `ci.yml`: `main`→`/web/staging/`+`/apk/staging/` (auto); tag `v*`→`/web/`+`/apk/`
   (gated `environment: production`); `feature/**`,`dev/**`→preview (unchanged).
3. HTTPS via `{$ORION_HOST}` Caddyfile (sslip.io host derived from the VPS IP,
   `46-250-232-224.sslip.io`); IP never committed.
4. Idempotent `setup.sh` (local orchestrator + remote provisioner), `setup-github.sh`
   (incl. gated env creation), `ops.sh` (status/start/stop/restart/reload/logs/health).

## Verified now (read-only)
1. `shellcheck` clean on all 5 authored scripts (static v0.11.0).
2. `gen-apk-index.sh` / `gen-landing-index.sh` byte-identical to the originals
   (verbatim move). Their pre-existing SC2045/SC2012 lint is **intentionally left** —
   the `ls -t` mtime sort is load-bearing and PRD §2 says index pages stay untouched.
3. `ci.yml` parses; jobs = unit, web-e2e, web, web-prod, apk, apk-prod; triggers
   include `tags: ['v*']`.
4. Live box (read-only SSH): `orion-web` active+enabled, Caddy v2.11.4, currently
   `:8080`, prod root + all feature slots intact, no state changed.

## To confirm after applying (user)
1. Run `scripts/dev/local/edge/setup.sh` (key-first; uses existing `.secrets/`* ) →
   Caddy switches to HTTPS on 80/443, cert issues within seconds.
2. `scripts/dev/local/edge/ops.sh health` → `200` on `https://46-250-232-224.sslip.io/web/`.
3. `scripts/dev/local/edge/ops.sh status` → active.
4. `setup-github.sh` → `production` env exists with you as required reviewer.
5. Push `main` → build lands at `/web/staging/`, root prod untouched.
6. Push a `v*` tag → run pauses for approval; approve → root `/web/` refreshes.
7. Web geolocation/location permission prompt now works (secure context).

(*) `.secrets/` currently lives at `deploy/vps/.secrets/`; move it to
`scripts/dev/local/edge/.secrets/` (gitignored) — `orion_ci` + `vps.env` unchanged.

## Known / intentional
- Landing index root row still labelled `main` (now prod) — cosmetic, PRD says index
  generators untouched.
- Switch causes brief downtime (8080→443); user pre-authorised ("can go offline").
- Required-reviewer API may be restricted on some private-repo plans → falls back to
  a warning; set it in the repo UI if so.
