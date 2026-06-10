# Phase 12 — Tasks (edge: staging + HTTPS + edge scripts)

`id: phase-12-edge` — see [`design.md`](design.md). Code lands **uncommitted** in
the `orion` worktree `/home/areg/git/orion-p12-devops-edge` (branch
`feature/p12-devops-edge`); the user tests + commits.

Work order: create the new tree (T1–T6) → rewire CI (T7) → delete the old tree (T8)
→ docs (T9) → verify (T10).

## T1 — `scripts/dev/remote/edge/` static assets (moved + updated)
- `gen-apk-index.sh`, `gen-landing-index.sh` — **move verbatim** from `deploy/`.
- `orion-web.service` — moved; add `EnvironmentFile=-/root/orion/orion-web.env` so
  Caddy gets `ORION_HOST`. Keep `CAP_NET_BIND_SERVICE`.
- `Caddyfile` — site address becomes `{$ORION_HOST}` (was `:8080`); same `root`,
  `file_server`, APK MIME block. Drop the 8080/domain comment, add a short HTTPS note.
- **Verify:** `ORION_HOST=test.example caddy validate --adapter caddyfile --config
  scripts/dev/remote/edge/Caddyfile` (or `caddy adapt`) parses clean.

## T2 — `scripts/dev/remote/edge/setup.sh` (idempotent provisioner)
Generalise `deploy/vps/remote-setup.sh`:
- Caddy install only if absent (unchanged).
- Lay out `/root/orion/site/{web,apk}`; copy bundled assets to `/root/orion/`
  (`Caddyfile`, `orion-web.service`, `gen-*.sh`, `ops.sh`); `chmod +x` scripts.
- Resolve `ORION_HOST`: use `$ORION_HOST` if set, else derive `<dashed-ip>.sslip.io`
  from the first global IPv4 (`hostname -I`/`ip route get`). Write
  `/root/orion/orion-web.env` (`ORION_HOST=…`) only if changed.
- Install unit, `daemon-reload`, `enable`, then `reload`-or-`restart` orion-web.
- Firewall: if a firewall is active, open **80,443** (was 8080).
- CI key: generate `/root/.ssh/orion_ci` + authorize only if missing (unchanged).
- Seed empty apk index if absent (unchanged). Report host + status.
- **Verify:** `shellcheck`; dry read-through (no run on the box yet).

## T3 — `scripts/dev/remote/edge/ops.sh` (on-box dispatcher)
`ops.sh <status|start|stop|restart|reload|logs|health>`:
- start/stop/restart/reload/status → `systemctl <verb> orion-web` (reload = no-drop
  Caddy reload via the unit's `ExecReload`).
- logs → `journalctl -u orion-web -f`.
- health → `curl -fsS -o /dev/null -w '%{http_code}\n'` against
  `https://localhost/web/` (with `--resolve`/`-k` as needed for the local check),
  plus `/apk/`. Unknown cmd → usage, exit 2.
- **Verify:** `shellcheck`.

## T4 — `scripts/dev/local/edge/ops.sh` (laptop SSH wrapper)
- Read `.secrets/vps.env` (HOST/USER/PORT) + key `.secrets/orion_ci`.
- Most cmds: `ssh -i <key> -p $PORT $USER@$HOST 'bash /root/orion/ops.sh <cmd>'`
  (logs streams fine over SSH).
- `health`: derive `ORION_HOST` from `VPS_HOST`, `curl -sI https://$ORION_HOST/web/`
  end-to-end from the laptop.
- Usage/exit-2 on unknown cmd. **Verify:** `shellcheck`.

## T5 — `scripts/dev/local/edge/setup.sh` (laptop orchestrator)
Generalise `deploy/vps/01-provision-vps.sh`:
- **Key-first:** if `.secrets/orion_ci` + `.secrets/vps.env` exist, connect with the
  key (no password, re-runnable). Else first-run path: require `sshpass` +
  `deploy.conf` (IP/user/password), same shared-ControlMaster connection as today.
- Pass `ORION_HOST` (derived from the target IP) to the remote setup.
- Upload assets from `scripts/dev/remote/edge/` (`Caddyfile`, `orion-web.service`,
  `gen-apk-index.sh`, `gen-landing-index.sh`, `setup.sh`, `ops.sh`) to `/root/orion/`.
- Run `ORION_HOST=… bash /root/orion/setup.sh`.
- First-run only: fetch `/root/.ssh/orion_ci` → `.secrets/orion_ci`; write
  `.secrets/vps.env`. Skip if already present.
- **Verify:** `shellcheck`.

## T6 — `scripts/dev/local/edge/setup-github.sh` (GitHub wiring + gate)
Generalise `deploy/vps/02-setup-github.sh`:
- Same `gh secret set VPS_SSH_KEY` + `gh variable set VPS_HOST/USER/PORT` from
  `.secrets/`.
- **New:** create/ensure the gated **`production`** environment — resolve the solo
  dev id (`gh api user --jq .id`) and
  `gh api -X PUT repos/$REPO/environments/production -f
  'reviewers[][type]=User' -F 'reviewers[][id]=<id>'` (idempotent PUT). Log that the
  prod tag deploy now requires approval.
- Add `.gitignore` (`deploy.conf`, `.secrets/`) and `deploy.conf.example`
  (moved from `deploy/vps/`, wording kept). **Verify:** `shellcheck`.

## T7 — `ci.yml` — staging + gated prod (the only behavioural change)
- `on.push`: add `tags: ['v*']`.
- `web` job → `if: github.ref_type == 'branch'`; slot step: `main` → slot `staging`,
  else `${ref#feature/}`; **all** branch builds use `base=/web/$slot/`,
  `dir=…/web/$slot`, `--delete`.
- `apk` job → `if: github.ref_type == 'branch'`; `main` → `…/apk/staging keep=3`,
  else `…/apk/$slot keep=1`.
- New `web-prod` job: `if: github.ref_type == 'tag'`, `environment: production`,
  build `--base-href /web/`, deploy to `…/site/web` **without** `--delete`, regen
  landing index.
- New `apk-prod` job: `if: github.ref_type == 'tag'`, `environment: production`,
  deploy to `…/site/apk keep=3`, regen apk + landing index.
- Update the two `scp deploy/gen-*.sh` paths → `scripts/dev/remote/edge/gen-*.sh`.
  Update the header comment block (targets table; `see deploy/` → new path).
- **Verify:** YAML parses (`python -c 'import yaml,sys;yaml.safe_load(...)'`);
  re-read the slot logic for the no-`--delete`-on-root invariant.

## T8 — Remove the old tree
- `rm` `deploy/Caddyfile deploy/orion-web.service deploy/README.md
  deploy/gen-apk-index.sh deploy/gen-landing-index.sh` and all of `deploy/vps/`
  (incl. `.gitignore`, `deploy.conf.example`). Confirm nothing else references
  `deploy/` (`grep -rn 'deploy/' --include=*.yml --include=*.sh --include=*.md .`).

## T9 — Docs
- `scripts/dev/remote/edge/README.md` — folded from `deploy/README.md`: HTTPS host,
  the slot/env table, setup + ops usage, day-to-day push→live. Drop retired `:8080`
  and `<vps-ip>` framing; use `https://<host>/…`.
- `scripts/README.md` — add a `dev/local/edge` + `dev/remote/edge` section (setup,
  setup-github, ops subcommands).

## T10 — Verify (done-gate) + review.md
- `shellcheck` all new scripts; `caddy validate` Caddyfile; YAML-parse `ci.yml`.
- Read-only SSH to the live box (key) — `systemctl is-active orion-web`,
  `caddy version`, current listening ports — to confirm starting state. **No state
  changes, no deploy.**
- Write numbered `review.md` (staged, not committed). Report (Done/Apply/Test).
