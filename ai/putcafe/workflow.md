# Putcafe — Repo Workflow Overrides

Inherits the shared workflow at `~/ai/workflow.md`.

- **Package manager: yarn** — use `yarn` for installs/scripts in this repo,
  never npm/pnpm. Lockfile is `yarn.lock`.
- **Deploys go ONLY through GitHub CI (commit → push → CI).** Never deploy via
  `scripts/dev/local/edge/deploy.sh` / `deploy-api.sh` — they exist for
  emergencies only (CI down). Staging must always equal a pushed commit.
  Push only after asking; "deploy" therefore means: commit, ask, push, watch CI.
- **Every feature gets its own branch, merged to `main`.** Branch `feature/<slug>`
  (or `dev/<slug>`) at task start — never commit feature work directly to `main`.
  Pushing the branch deploys a preview slot (`/web/<slug>/`); merge to `main`
  (ask first, as with any push) deploys staging. Backend (`api`) deploys only
  from `main`.
