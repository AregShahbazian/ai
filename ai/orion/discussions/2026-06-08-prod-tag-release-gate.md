# Prod releases: tag-to-release with a manual gate

**Date:** 2026-06-08
**Context:** Same-day follow-on to the Phase 12 deploy discussions
([`2026-06-08-docker-deploy-strategy.md`](2026-06-08-docker-deploy-strategy.md),
[`2026-06-08-staging-topology.md`](2026-06-08-staging-topology.md),
[`2026-06-08-api-deploy-downtime-scaling.md`](2026-06-08-api-deploy-downtime-scaling.md),
[`2026-06-08-feature-staging-deploys.md`](2026-06-08-feature-staging-deploys.md)).
How should pushes to prod be triggered? Reference: Altrady auto-deploys `main` to
staging and cuts prod releases via a **tag**, with a human doing the prod deploy.

## Summary

Confirmed the "tag-to-release with a manual gate" pattern as standard practice and
decided **Orion should adopt it**: `main` auto-deploys to the staging environment;
a version tag marks a release candidate whose build/test is automated up to a
**manual approval gate**, after which the prod deploy is automated. The gate lives
in GitHub's native **Environments** feature (required reviewers), approved in the
repo UI.

## Key conclusions

- **Common practice:** yes — `main` auto-deploys to staging; a version tag (e.g.
  `v1.2.0`) marks a release and triggers a **gated** prod deploy.
- **Automated before the gate:** tag push → build → image → push to registry →
  run tests.
- **The gate:** a human approves.
- **Automated after the gate:** pull image on prod → run migrations → swap the
  container → healthcheck.
- **Where the gate lives:** GitHub itself — **Actions "Environments"** with
  **required reviewers**; the approval happens in the repo's UI. No external CD
  tool needed.
- **Decision:** Orion should do this too.

## Open questions

- Tag scheme / versioning convention (`vMAJOR.MINOR.PATCH`?).
- Who the required reviewer(s) are (solo dev today → self-approval).
- Rollback procedure if the post-gate prod deploy fails its healthcheck.

## Ideas to realize

- **`main` → staging auto-deploy:** every push to `main` deploys to the staging
  environment automatically.
- **Tag-triggered prod release:** pushing a version tag runs build → image → push
  → tests automatically (up to the gate).
- **Manual approval gate via GitHub Actions "Environments"** with required
  reviewers, approved in the repo UI.
- **Automated post-approval prod deploy:** pull image → run migrations → swap
  container → healthcheck.
- **Define a tag/versioning convention** and a **rollback path** for a failed
  prod healthcheck.
