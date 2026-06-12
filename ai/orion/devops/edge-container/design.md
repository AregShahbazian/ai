# Containerized Edge — Design

PRD: [`prd.md`](prd.md) (`orion-edge-container`). Work on
`feature/p12-devops-edge` (worktree `~/git/orion-p12-devops-edge`), then merge
to `main`. Sibling change in putcafe `pc-docker-ui` (its scripts talk to the
new edge).

## Shape

```
/root/orion/edge/             compose project "edge" → container edge-caddy-1
  compose.yml                 caddy:2.11, network_mode: host
  data/                       /data in-container (certs; migrated from /caddy)
  config/                     /config in-container
```

- **`network_mode: host`** — the Caddyfile reverse-proxies to `127.0.0.1:81xx`
  and binds 80/443(+udp)/2019 exactly like the systemd unit did; host
  networking keeps all of that byte-identical. No port mapping, no Caddyfile
  edits.
- **Same config paths inside the container**: `/root/orion` and
  `/root/putcafe` bind-mounted read-only at identical paths, so
  `/root/orion/Caddyfile`, the `import /root/*/site.caddy` glob, and the
  `file_server` roots all resolve unchanged. New sibling app = one more mount
  line (documented in compose.yml).
- **`ORION_HOST`** via `env_file: /root/orion/orion-web.env` (same file as
  before).
- **Cert migration:** the systemd Caddy's storage is empirically `/caddy` on
  the box (root service, odd XDG resolution). One-time copy
  `/caddy` → `/root/orion/edge/data/caddy` (the image sets
  `XDG_DATA_HOME=/data`) when the target doesn't exist yet. `/caddy` is left
  in place as rollback.
- **Project name `edge`** (explicit `name:` in compose.yml) → groups
  separately in Dozzle. Healthcheck: admin API `127.0.0.1:2019/config/`.

## Provisioning (rewrite of remote `setup.sh`)

Same skeleton, swapped middle: host derivation, layout, env file, ufw, CI key
all stay. Replaces "apt-install Caddy + install/enable orion-web unit" with:

1. Ensure Docker (get.docker.com convenience script + compose plugin — same
   approach as putcafe's `setup-api.sh`).
2. Validate the merged Caddyfile via
   `docker run --rm` (caddy:2.11, ro mounts, ORION_HOST env) — works with the
   edge down, used by putcafe's setup too.
3. Migrate certs (one-time copy, see above).
4. **Cutover:** if `orion-web.service` is active → pull image first, then
   `systemctl disable --now orion-web` and `docker compose up -d`
   (seconds of downtime, once). Unit file left on the box, disabled, as
   rollback. `orion-web.service` deleted from the repo.
5. Steady state: `compose up -d` + `caddy reload` exec'd in the container
   (cheap, no dropped connections) to apply config changes.

**Reload contract for siblings** (putcafe setup.sh):
`docker compose -f /root/orion/edge/compose.yml exec -T caddy caddy reload
--config /root/orion/Caddyfile --adapter caddyfile --force`.

`ops.sh` (both layers): status/start/stop/restart/logs move from
systemctl/journalctl to compose; `health` curls unchanged.

## Risks

- Brief 80/443 gap at cutover (systemd stop → compose up): accepted, seconds.
- apt `caddy` package stays installed but disabled (binary unused; remove
  later if desired).
- Rollback: `docker compose down` + `systemctl enable --now orion-web`
  (unit + `/caddy` storage untouched on the box).
