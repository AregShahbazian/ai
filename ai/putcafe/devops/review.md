# DevOps — Review

PRD: [`prd.md`](prd.md) (`pc-devops`)

## Round 1: initial implementation (2026-06-12)

Implemented per [`design.md`](design.md)/[`tasks.md`](tasks.md) and provisioned
the live VPS via the committed scripts (agent ran: `ops.sh status`, `setup.sh`
×2, `deploy.sh staging`, `ops.sh health`). `shellcheck` not installed locally —
`bash -n` used for all scripts instead.

### Verification

1. ✅ Scripts pass `bash -n`; `ci.yml` parses as YAML (agent-verified)
2. ✅ Vite relative base: `dist/index.html` references `./assets/…` (agent-verified)
3. ✅ `setup.sh` provisioned the site: import line added to Orion's Caddyfile
   (validated, backup/revert path in place), edge reloaded, `putcafe_ci` key
   generated and saved to `.secrets/` (agent-verified)
4. ✅ Idempotent re-run: key auth, "import line already present", no changes
   (agent-verified)
5. ✅ `deploy.sh staging` → `https://putcafe.46-250-232-224.sslip.io/web/staging/`
   returns HTTP/2 200 with a real cert (agent-verified)
6. ✅ Orion regression: `https://46-250-232-224.sslip.io/web/` still 200 after
   reload (agent-verified)
7. Open the staging URL in a browser — chart app loads and works over HTTPS
8. After adding the GitHub remote: `./scripts/dev/local/edge/setup-github.sh`
   succeeds (secret + vars + gated `production` environment)
9. Push to `main` → CI deploys to `/web/staging/` automatically
10. Push a `v*` tag → run pauses on the `production` gate; approving deploys
    `/web/` (then `ops.sh health` shows 200 on both paths)

### Notes

- `/web/` (prod) is 404 until the first gated tag deploy (or
  `deploy.sh prod`) — expected.
- **Caveat fixed (same round):** Orion's phase-12 Caddyfile template now has a
  generic `import /root/*/site.caddy` (edited in `~/git/orion-p12-devops-edge`,
  uncommitted there — fold into phase-12). Putcafe's file was renamed
  `putcafe.caddy` → `site.caddy`; its setup migrates the legacy line, skips
  appending when the glob import is present, and was re-run live (verified,
  staging 200). Orion redeploys no longer drop putcafe.
- `putcafe.{$ORION_HOST}` tracks Orion's host: if Orion moves to a real
  domain, putcafe's host changes too — revisit then.
- `ops.sh start/stop/restart` act on the shared `orion-web` service (warned in
  the scripts); `reload` is the default advice.
