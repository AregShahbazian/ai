# Phase 12 — Design (edge: staging + HTTPS + edge scripts)

`id: phase-12-edge` — implements [`prd.md`](prd.md).

## Topology (unchanged shape, one new host + one new env slot)

One Caddy on the VPS serves a single static tree `/root/orion/site/` over **HTTPS**
on a free wildcard-DNS host. Nothing else runs (no containers/API/DB). Environments
are **path slots** under that one tree — prod at the root, everything else nested:

```
https://46-250-232-224.sslip.io/
        ├── web/                 prod      (from a version tag, gated)
        ├── web/staging/         staging   (from main, auto)
        ├── web/<slot>/          preview   (from feature/**, dev/**)
        ├── apk/ , apk/staging/ , apk/<slot>/   (same mapping)
        └── index.html           landing page (gen-landing-index.sh)
```

`staging` is **just a reserved preview slot** named `staging`; it reuses the exact
nested-path mechanism previews already use, so serving + both index generators are
untouched.

## Deploy flow (the only behavioural change is in `ci.yml`)

| Event | `github.ref_type` | Job(s) | Target | Gate |
|-------|-------------------|--------|--------|------|
| push `main` | branch | `web`,`apk` | `/web/staging/`,`/apk/staging/` | none (auto) |
| push `feature/**`,`dev/**` | branch | `web`,`apk` | `/web/<slot>/`,`/apk/<slot>/` | none (auto) |
| push tag `v*` | tag | `web-prod`,`apk-prod` | `/web/`,`/apk/` | **`environment: production`** |

- Branch and tag events are mutually exclusive, so jobs are split by
  `if: github.ref_type == 'branch'` (staging/preview) vs `== 'tag'` (prod). The
  prod jobs carry `environment: production`, GitHub's native required-reviewer gate.
- **Slot unification:** `main` is no longer special on branch builds — it maps to
  slot `staging` and is deployed exactly like a preview leaf (`--delete` for web,
  `keep=3` for apk). Only the **prod** (tag) jobs write the root and must **not**
  use `--delete` (it would wipe sibling slots).
- The `production` environment (with the solo dev as required reviewer) is created
  by `setup-github.sh` via the `gh` API, so the very first tag is already gated —
  without it GitHub would auto-create an *unprotected* environment and skip the gate.
- Tag scheme: `v*` (e.g. `v1.2.0`). Report-only tests (`unit`,`web-e2e`) also run on
  tags — the release candidate gets tested before the gate.

## HTTPS without a domain

- Host = `<dashed-ipv4>.sslip.io` (wildcard DNS → the VPS IP, Let's-Encrypt-eligible
  via HTTP-01). The IP is **never committed**: the `Caddyfile` uses Caddy's env
  placeholder `{$ORION_HOST}`, and setup derives the value from the VPS IP and writes
  it to a gitignored on-box env file the systemd unit reads (`EnvironmentFile`).
- Caddy auto-provisions + renews the cert; needs ports **80 + 443** (HTTP-01 + TLS).
  The unit already grants `CAP_NET_BIND_SERVICE`; setup opens 80/443 (drops 8080).
- Swapping in a real domain later = set `ORION_HOST` to the domain (one value), no
  file change.

## File & service layout (post-migration)

The `deploy/` + `deploy/vps/` trees are **removed**; edge tooling moves under
`scripts/dev/{local,remote}/edge/`, mirroring the existing `scripts/dev/` home.

```
scripts/dev/local/edge/        # run FROM the laptop (thin SSH wrappers)
  setup.sh            transfer assets + run remote setup over one SSH conn
  setup-github.sh     wire deploy key+facts into GitHub; create gated `production` env
  ops.sh              status|start|stop|restart|reload|logs|health  (SSH→remote ops.sh)
  deploy.conf.example committed sample (first-run password); deploy.conf gitignored
  .gitignore          ignores deploy.conf + .secrets/
  .secrets/           gitignored: orion_ci (CI/ops key), vps.env (HOST/USER/PORT)
scripts/dev/remote/edge/       # run ON the VPS (as root)
  setup.sh            idempotent provisioner (Caddy, layout, unit, ports, CI key, host env)
  ops.sh              status|start|stop|restart|reload|logs|health  (systemctl/journalctl/curl)
  Caddyfile           {$ORION_HOST} static host (HTTPS)
  orion-web.service   systemd unit (+ EnvironmentFile for ORION_HOST)
  gen-apk-index.sh    moved verbatim
  gen-landing-index.sh moved verbatim
  README.md           folded hosting docs
```

`ci.yml` `scp` paths for the two `gen-*.sh` change from `deploy/` to
`scripts/dev/remote/edge/`; nothing else references `deploy/`.

## Edge ops — one dispatcher per layer (mirrors `scripts/mobile/orion.sh`)

`ops.sh <cmd>` rather than seven tiny scripts (house style: a single dotted/sub-command
dispatcher). Commands: `status start stop restart reload logs health`.
- **remote** `ops.sh` runs the real command on the box: `systemctl <verb> orion-web`,
  `journalctl -u orion-web -f`, `caddy reload` via `systemctl reload`, and `health`
  = `curl -sI` localhost over HTTPS.
- **local** `ops.sh` is a thin SSH wrapper: it reads `.secrets/vps.env` + key
  `.secrets/orion_ci`, then `ssh … 'bash /root/orion/ops.sh <cmd>'`. Exception:
  `health` curls the **public** `https://$ORION_HOST/web/` end-to-end (host derived
  from `VPS_HOST`), the more meaningful external check.

## Config & secrets

- **Key-first auth:** `local/edge/setup.sh` uses the CI key
  (`.secrets/orion_ci`) when present (re-runs against a live box, no password); only a
  brand-new box falls back to `sshpass` + `deploy.conf` password. Makes setup truly
  re-runnable.
- Secrets stay gitignored (`deploy.conf`, `.secrets/`), each with a committed
  `.example`. The same `orion_ci` key serves both CI deploys and laptop ops.

## Idempotency (PRD §6 — check-then-act, every step)

`remote/edge/setup.sh` generalises today's `remote-setup.sh`: install Caddy only if
absent; write/refresh `/root/orion/{Caddyfile,orion-web.service,gen-*.sh,ops.sh}`;
write the `ORION_HOST` env file (derive from IP if not passed); `systemctl enable`
+ reload-or-restart; open 80/443 only if a firewall is active; generate the CI key +
authorize it only if missing. Safe to re-run against a live system; never destructive.

## Open questions — resolved in-impl (no user input needed)

- **sslip.io host** → derived from the VPS IP at setup time (`46-250-232-224.sslip.io`).
- **Caddy switch downtime** → user pre-authorised ("can go offline until the new one
  is online"); plain restart, no blue-green.
- **Required reviewer id** → the authenticated solo dev (`gh api user --jq .id`).
- **Landing index label** → left byte-identical per PRD "index pages untouched"
  (root row still reads `main`; cosmetic, noted in review).

## Verify (done-gate)

`shellcheck` every script; `caddy validate` the new Caddyfile (locally, with
`ORION_HOST` set); a YAML parse of `ci.yml`. Read-only SSH to the live box to
confirm the current service state. **No VPS state changes and no real deploy** —
hand off Apply/Test for the user to run.
