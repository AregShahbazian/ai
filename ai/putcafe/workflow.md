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
- **Verify and debug through the console bridge (`window.pc`), not UI clicks.**
  The app exposes a scriptable bridge (README "Console bridge";
  `frontend/src/debug/bridge.ts`; feature docs in
  `~/ai/putcafe/features/console-bridge/`). Drive scenarios via `pc.*` in
  DevTools or Playwright `page.evaluate`: `pc.session.start` (awaitable),
  `pc.playTo`/`pc.waitFor.*` to position the replay, `pc.state.*` for app
  state, `pc.chart.*` for the *rendered* chart (render-settled), and
  `pc.verify()` for the frontend↔backend cross-check. `yarn e2e` runs the
  committed spec on its own dev server (:5183) — never point tests at :5173,
  it may be another worktree's server. Caveats: HMR edits to `bridge.ts`
  split module state (reload the page); `playTo` can overshoot at speeds ≥100.
  **When a feature adds state, actions, or chart visuals, extend the bridge
  and `pc.help()` in the same change** — the bridge staying complete is what
  keeps scripted verification possible.
