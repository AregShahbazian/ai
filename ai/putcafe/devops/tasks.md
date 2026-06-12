# DevOps — Tasks

PRD: [`prd.md`](prd.md) · Design: [`design.md`](design.md)

1. **Vite relative base** — `frontend/vite.config.ts`: `base: "./"`.
   Verify: `yarn build`, dist/index.html uses `./assets/…`.
2. **Remote layer** — `scripts/dev/remote/edge/{putcafe.caddy,setup.sh,ops.sh}`.
   Verify: shellcheck clean.
3. **Local layer** — `scripts/dev/local/edge/{_conn.sh,setup.sh,ops.sh,deploy.sh,setup-github.sh,deploy.conf.example,.gitignore}`;
   create gitignored `deploy.conf` from `~/git/claude-vps/deploy.conf`.
   Verify: shellcheck clean; `ops.sh status` reaches the box (password fallback).
4. **CI** — `.github/workflows/ci.yml` (web branch job + gated web-prod tag job).
   Verify: YAML parses; paths match remote layout.
5. **Provision + first deploy** — `./scripts/dev/local/edge/setup.sh`, then
   `./scripts/dev/local/edge/deploy.sh staging`.
   Verify: `ops.sh health` → 200 on `https://putcafe.<host>/web/staging/`;
   Orion `https://<host>/web/` still 200.
6. **Review doc** — `review.md` with numbered checklist + handoff (GitHub
   remote + `setup-github.sh` + first push).
