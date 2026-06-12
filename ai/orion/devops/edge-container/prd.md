---
id: orion-edge-container
---

# Orion — Containerized Edge (Caddy in Docker)

The shared VPS edge (Caddy, currently the `orion-web` systemd service) moves
into a Docker container so it appears in the VPS ops UI
(putcafe `pc-docker-ui`, Dozzle at `https://ops.<host>/`) like every other
service — visible status, live logs, restart from the browser. Driven by the
putcafe docker-ui work; Orion owns the edge, so the change lands here.

## Requirements

1. **Same edge behavior, new runtime.** All current hosts keep working
   unchanged: Orion site (`<host>`), putcafe (`putcafe.<host>`), ops UI
   (`ops.<host>`). Same Caddyfile, same sibling-site glob import, same
   automatic HTTPS.
2. **Visible in the ops UI, separately.** The Caddy container shows up in
   Dozzle as its own group (not lumped into an app's stack), with logs and
   status.
3. **Keep existing certs.** Migrate Let's Encrypt state so the switch doesn't
   re-issue certs (re-issue acceptable as fallback, never as the plan).
4. **Idempotent provisioning, scripted.** `scripts/dev/local/edge/setup.sh`
   keeps being the one entry point; re-runs are safe; a fresh box still
   provisions end-to-end (now Docker-based instead of apt Caddy + systemd).
5. **Minimal downtime** during migration (seconds), no Orion or putcafe
   deploy-pipeline changes (CI never touches the edge).
6. **Sibling contract preserved:** putcafe's scripts may validate/reload the
   edge; whatever replaces `systemctl reload orion-web` must be available to
   them.

## Non-requirements

- No new edge features (no domains, no auth, no new routes).
- No containerization of anything else of Orion's.
- No CI changes beyond what keeps deploys green.
