# Putcafe — Repo Workflow Overrides

Inherits the shared workflow at `~/ai/workflow.md`.

- **Package manager: yarn** — use `yarn` for installs/scripts in this repo,
  never npm/pnpm. Lockfile is `yarn.lock`.
- **Deploys go ONLY through GitHub CI (commit → push → CI).** Never deploy via
  `scripts/dev/local/edge/deploy.sh` / `deploy-api.sh` — they exist for
  emergencies only (CI down). Staging must always equal a pushed commit.
  Push only after asking; "deploy" therefore means: commit, ask, push, watch CI.
