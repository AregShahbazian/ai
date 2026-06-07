# Phase 12 staging topology — containers & box layout

**Date:** 2026-06-08
**Context:** Same-day follow-on to
[`2026-06-08-docker-deploy-strategy.md`](2026-06-08-docker-deploy-strategy.md)
(which decided: adopt Docker/Compose for the Phase 12 backend). This session
clarifies how **staging** fits the containerized stack.

## Summary

We confirmed staging is not a config flag on prod — it needs its own running
containers, including its own database, and reasoned through whether staging
should sit on the same VPS as prod or on a separate box.

## Key conclusions

- **Staging needs its own pair of containers:** a separate API container **and** a
  separate Postgres container (own volume). **Prod and staging never share a
  database.**
- **Same-box count = 5 containers:** Caddy + prod API + prod Postgres + staging API
  + staging Postgres. **One Caddy serves both**, routing by hostname
  (`orion…` vs `staging.orion…`).
- **Same image, different containers:** staging uses the same image as prod,
  differing only by config/env (ports, hostname, DB connection).
- **Same box vs separate box for staging:**
  - *Same box* — cheaper, simpler, one Caddy/DNS; but staging load / bugs /
    migrations can disturb prod (shared resources).
  - *Separate box* — true isolation, safe to break staging, and it **doubles as a
    rehearsal of the "switch VPS" runbook** (install Docker → copy Compose →
    restore data → repoint DNS), proving that runbook actually works. Costs a
    second VPS.
- **Recommendation: start same-box**, split staging onto its own box later if it
  ever risks prod.

## Open questions

- Where exactly the split-to-second-box threshold is (when does staging "risk
  prod"?).
- Per-container resource limits values (CPU/mem) for a shared box.
- Auto-deploy policy tie-in: `feature/**` → staging, `main` → prod?

## Ideas to realize

- **Staging = its own API + Postgres containers** (separate volume), same image as
  prod, differing only by config/env; one Caddy routes prod vs staging by hostname.
- **Start staging same-box** (5 containers total); plan to split it to a second box
  if it begins to risk prod.
- **Per-container resource limits (CPU/mem)** to protect prod when staging shares
  the box.
- **Use a separate staging box as a live rehearsal** of the "switch VPS" runbook
  (validates the move-to-new-VPS procedure end-to-end).
