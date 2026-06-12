---
id: pc-docker-ui
---

# Putcafe — VPS Docker Web Interface

A single URL I can open in the browser to see what's running on the VPS:
which apps, which containers, doing what. Sub-task of
[`../prd.md`](../prd.md) (pc-devops); same VPS, same edge.

## Requirements

### 1. One URL

- One HTTPS address (existing wildcard-DNS scheme, e.g.
  `ops.46-250-232-224.sslip.io`) opens the interface. No SSH, no tunnels,
  no port numbers to remember.
- Protected by a login (single user — just me). Nothing visible without it.

### 2. What it shows

- **All Docker containers on the VPS** — not just putcafe's. Per container:
  name, image, up/down status, uptime/restarts, published ports, live CPU/RAM.
- **Which app owns what** — containers grouped or labeled per app/compose
  project (putcafe api vs. anything else that lands on the VPS later).
- **Logs** — live and recent logs per container, viewable in the browser.
- **Non-container services where feasible** — at minimum whether Caddy is up;
  host-level CPU/RAM/disk is a nice-to-have.

### 3. Operations from the browser (minimal)

- Restart/stop/start a container from the UI is wanted but secondary;
  a read-only view is an acceptable v1.

### 4. Provisioning

- Fits the existing edge-script layout (`scripts/dev/local/edge` +
  `scripts/dev/remote/edge`): laptop-driven, idempotent, re-runnable.
- Zero interference with Orion's services and putcafe's running containers:
  setup must not restart or reconfigure them.
- Survives reboots and keeps itself running like the other services.

## Non-requirements

- No multi-user access, roles, or audit log.
- No metrics history, dashboards, or alerting — live view only.
- No image building/deploying from the UI — deploys stay in GitHub CI.
- No real domain; sslip.io is fine.
