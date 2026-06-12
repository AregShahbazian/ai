# DevOps — Design

PRD: [`prd.md`](prd.md) (`pc-devops`). Model: Orion phase-12 edge
(`~/ai/orion/mvp/phase-12/`, worktree `~/git/orion-p12-devops-edge`).

## Topology

The VPS already runs Orion's edge: one Caddy as `orion-web.service`, config
`/root/orion/Caddyfile`, host `{$ORION_HOST}` (= `46-250-232-224.sslip.io`)
from `/root/orion/orion-web.env`. Putcafe **requires that edge** (setup fails
loudly if absent) and adds one site to it:

```
/root/putcafe/
  putcafe.caddy        # site block: putcafe.{$ORION_HOST}
  setup.sh  ops.sh     # copied by laptop setup
  site/web/            # prod  → https://putcafe.<host>/web/
  site/web/staging/    # main  → /web/staging/
  site/web/<slot>/     # feature/**, dev/** previews
```

Integration = **one line appended idempotently** to `/root/orion/Caddyfile`:
`import /root/putcafe/putcafe.caddy` (validated with `caddy validate` + backup
restore on failure, then `systemctl reload orion-web` — no dropped
connections). Orion is otherwise untouched. Known caveat: if Orion re-deploys
its Caddyfile the import line vanishes — re-running putcafe setup restores it;
noted for upstreaming into Orion's edge later. Since the site file uses
`putcafe.{$ORION_HOST}`, a future real Orion domain changes putcafe's host too
(acceptable; revisit with real domains). `/` redirects to `/web/`.

## Frontend builds & slots

`vite.config.ts` gets `base: "./"` (relative assets) so one build serves at
any slot depth — no per-slot base flag. SPA has no router, so no fallback
rewrite needed.

## CI (`.github/workflows/ci.yml`)

Mirror of Orion's mapping, web-only, yarn:

| Event | Job | Target | Gate |
|---|---|---|---|
| push `main` | `web` | `/web/staging/` (rsync `--delete`) | none |
| push `feature/**`,`dev/**` | `web` | `/web/<slot>/` (`feature/` stripped) | none |
| tag `v*` | `web-prod` | `/web/` (**no** `--delete` — preserves slots) | `environment: production` |

Build = `yarn --frozen-lockfile && yarn build` in `frontend/`. Auth via secret
`VPS_SSH_KEY` (key `putcafe_ci`, separate from Orion's) + vars
`VPS_HOST/VPS_USER/VPS_PORT`.

## Scripts (mirror Orion's two layers; shared conn helper)

```
scripts/dev/local/edge/     # laptop
  _conn.sh                  # sourced: key-first auth (.secrets/), sshpass+deploy.conf fallback
  setup.sh                  # upload assets → run remote setup → first-run: save key+vps.env
  ops.sh                    # status|start|stop|restart|reload|logs|health (health curls public URL)
  deploy.sh [slot|prod]     # manual deploy: yarn build + rsync (staging default)
  setup-github.sh           # secret VPS_SSH_KEY, vars, gated `production` env (gh api)
  deploy.conf.example       # committed; deploy.conf + .secrets/ gitignored
scripts/dev/remote/edge/    # VPS (as root)
  setup.sh                  # idempotent provisioner (see below)
  ops.sh                    # systemctl/journalctl/curl on the box
  putcafe.caddy
```

Improvement over Orion: `ops.sh` also works **before** first setup via the
`_conn.sh` fallback — used to inspect the live box read-only without ad-hoc SSH.
`start/stop/restart` act on the **shared** `orion-web` service (affects Orion);
scripts warn, `reload` is the default advice.

## Remote setup.sh (idempotent, check-then-act)

1. Require `caddy` + `/root/orion/Caddyfile` (else: "provision Orion edge
   first").
2. `mkdir -p /root/putcafe/site/web`.
3. Ensure the `import` line; validate merged config (env from
   `orion-web.env`); on failure restore backup and abort.
4. Reload-or-restart `orion-web`.
5. Generate `/root/.ssh/putcafe_ci` + authorize, only if missing.
6. Report `https://putcafe.$ORION_HOST/web/`.

## Secrets

`deploy.conf` (root password, first run only) copied from
`~/git/claude-vps/deploy.conf`; `.secrets/{putcafe_ci,vps.env}` written by
setup. All gitignored with committed examples. Agent rule honored: every VPS
action runs through these committed scripts.

## Verify (done-gate)

`shellcheck` all scripts; `bash -n` too. Then live: `ops.sh status` (inspect),
`setup.sh`, `deploy.sh staging`, `ops.sh health` (expect 200 on
`/web/staging/`), and an Orion regression check (`https://<host>/web/` still
200). GitHub wiring (`setup-github.sh`) needs the repo remote — currently not
configured; left as a handoff step.
