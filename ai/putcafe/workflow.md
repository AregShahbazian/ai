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
- **End every change with a deploy-status overview.** Dev loop = frontend on
  localhost (`yarn dev`, hot-reload) + backend on the VPS. After any change, close
  the reply with a short, clear summary of what changed and what it needs:
  - **Frontend** — auto hot-reloads, nothing to do.
  - **Backend** — needs a VPS deploy (ask/run per the rule below) before it's live.
- **Never hand me raw docker / direct tool commands to paste.** Any operational
  command (docker, compose, build/rebuild, restart, db, etc.) goes into a script
  under `scripts/dev/local/` — give it a clear name and keep it idempotent. Then
  ask permission to either (a) run the script myself, or (b) have you run it.
  Never end a task with "now run `docker …`" in prose.
