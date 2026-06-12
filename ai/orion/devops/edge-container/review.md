# Containerized Edge — Review

PRD: [`prd.md`](prd.md) (`orion-edge-container`).

## Round 1: implementation + live migration (2026-06-12)

Implemented per [`tasks.md`](tasks.md); VPS migrated live. The edge now runs
as `edge-caddy-1` (compose project `edge`, caddy:2.11, host networking) and
shows in the ops UI under a dedicated **edge** custom group
(`dev.dozzle.group` label — Dozzle doesn't group single-container compose
projects on its own; discovered in verification, fixed in the same round).
Screenshots in putcafe's docs: `~/ai/putcafe/devops/docker-ui/`
(`ops-ui-groups.png`, `ops-ui-edge-logs.png`).

### Verification
1. ✅ `bash -n` + shellcheck clean (orion edge scripts) (agent-verified)
2. ✅ migration ran end-to-end: certs copied `/caddy` →
   `/root/orion/edge/data/caddy`, legacy `orion-web` disabled (unit file kept
   as rollback), `edge-caddy-1` up (healthy) (agent-verified)
3. ✅ certs REUSED — zero "obtaining certificate" lines in the container log
   after cutover (agent-verified)
4. ✅ all hosts 200 through the container: orion `/web/` + `/apk/`, putcafe
   `/web/` + `/web/staging/` + both api healths, ops UI login page
   (agent-verified)
5. ✅ re-run of `setup.sh` is idempotent: no second migration/cutover;
   container only recreated when compose.yml actually changed
   (agent-verified)
6. ✅ putcafe's setup/ops scripts work against the new edge (validate via
   `docker run caddy:2.11`, reload via `compose exec`) (agent-verified)
7. ✅ `edge` shows as its own sidebar group in Dozzle, with live caddy logs
   (agent-verified)
8. ✅ app containers untouched by the whole migration (`api-*` uptimes
   continuous) (agent-verified)
9. orion CI deploy still green after merge to main (checked in T7)
10. user check: open the ops UI, see `edge` group, tail caddy logs
