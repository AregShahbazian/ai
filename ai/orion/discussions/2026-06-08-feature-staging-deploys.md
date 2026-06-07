# Per-feature staging deploys: frontend vs backend

**Date:** 2026-06-08
**Context:** Same-day follow-on to the Phase 12 Docker/staging discussions
([`2026-06-08-docker-deploy-strategy.md`](2026-06-08-docker-deploy-strategy.md),
[`2026-06-08-staging-topology.md`](2026-06-08-staging-topology.md),
[`2026-06-08-api-deploy-downtime-scaling.md`](2026-06-08-api-deploy-downtime-scaling.md)).
Question: should `feature/**` branches each get their own staging URL (like
Altrady's `?version=superchart-integration`, parsed from `feature/superchart-integration`),
and would that need a container per feature?

## Summary

We split the question by layer. Per-feature staging URLs make sense for the
**frontend** (cheap, already in place) but not the **backend** (a container per
feature gets expensive and fights over shared DB/migrations). Conclusion: keep
per-feature deploys frontend-only; the backend has just two long-lived
environments, prod and staging, and backend changes are tested serially on
staging before promotion.

## Key conclusions

- **Frontend per-feature URLs: yes, no extra containers.** A `?version=<branch>`
  param just selects which static build to load — exactly Orion's existing web
  previews (`feature/<name>` → `/web/<name>/`, served by one Caddy). Free.
- **Backend per-feature: no.** A pure-frontend feature reuses the shared staging
  API+DB. Only a feature that changes the API would need its own API container
  (and possibly its own DB for migrations) — per-feature backend containers get
  expensive fast, so we don't do it.
- **Backend = two environments only:** **prod** and **staging** containers. All
  feature-branch frontends test against the single shared staging API.
- **Backend workflow:** push/merge backend changes to the **staging** line, test
  the single staging API+DB, then promote to prod. One staging slot, tested
  **serially**.
- **Conflict case:** two backend-touching features at once fight over the single
  staging API (last deploy wins). For a solo dev, **serialize** (one backend
  feature on staging at a time); heavier options (on-demand per-feature API,
  merge-first integration branch) exist but aren't needed at this scale.

## Open questions

- Should staging always track `main` (backend merged before frontend feature
  testing), or a dedicated staging branch?
- A lightweight convention for "claiming" the staging API while testing a backend
  feature.
- If parallel backend work ever becomes common, revisit on-demand per-feature API
  containers.

## Ideas to realize

- **Frontend-only per-feature staging URLs** via Caddy + a `?version=<branch>`
  selector (parsed from `feature/<name>`), reusing the existing
  `/web/<name>/` preview mechanism. No backend containers per feature.
- **Exactly two backend environments** (prod + staging) as the standing
  architecture; all feature frontends point at the shared staging API.
- **Serial backend testing convention:** backend changes go to staging, get tested
  against the single staging API+DB, then promoted to prod — one feature's backend
  on staging at a time.
- **(Future, only if needed)** on-demand per-feature API container spun up only
  when a branch touches `backend/`, torn down after — for parallel backend work.
