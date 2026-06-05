# Generalize Devbox — Tasks

Implementation tasks for `devbox-generalize` (see `design.md`). Branch:
`generalize-devbox` (code repo), merge to `main` later. Commits carry `[devbox-generalize]`.

**Status:** T1–T5 ✅ done (commits `b7ca48a`, `859dd11`). T6 next. T7/T8/multi/T9 pending.

---

## T1 — Rename `orion-dev-box` → `devbox`  ✅
Mechanical rename across scripts/Dockerfile/compose/dotfiles/config/docs; `vps-clean.sh`
keeps old names (`orion-devbox`, `/root/orion-devbox`, `/root/orion-dev-box`) as legacy
removals. Verified: `bash -n` clean, `docker compose config` parses, no stray old names.

## T2 — Slim base image + `ARG PROJECT` toolchain layer  ✅
`10-system.sh` drops JDK; `Dockerfile` generic base + `ARG PROJECT=orion` →
`projects/$PROJECT/provision.sh`; `compose` passes `PROJECT` build arg. Generic
`/etc/profile.d/devbox.sh` (scripts PATH); project writes `devbox-project.sh`.

## T3 — `projects/orion/` (toolchain + build extracted)  ✅
`provision.sh` (JDK21+Flutter+Android; root→/opt else $HOME; chowns dev; writes
profile.d), `build.sh` (APK + web → `$SERVE_DIR/app.apk` + `web/`), `project.env`.
Removed `provision/20-flutter.sh`.

## T4 — Generic `build` dispatch  ✅
`scripts/build` → `projects/$PROJECT/build.sh` (sources `project.env`). `scripts/build-apk`
**removed** (no shim — clean break). Served artifact renamed `app.apk`.

## T5 — Config: project + home keys  ✅
`ORION_*→PROJECT_*`, `AI_*→HOME_*` ("home repo"), add `PROJECT` selector. `common.sh`
defaults (empty repo URLs, `PROJECT=orion`, `PROJECT_DIR=$DEVBOX_HOME/src/$PROJECT`,
`HOME_DIR=$DEVBOX_HOME/src/home`). `vps-setup.sh` writes `.env` (PROJECT, PROJECT_REPO_URL,
PROJECT_BRANCH, HOME_REPO_URL); `compose`/`entrypoint` consume it.

---

## T6 — Writable HOME repo in the container (NEXT)
**Files:**
- `provision/50-repos.sh`: already clones `PROJECT_REPO_URL`→`$PROJECT_DIR` and
  `HOME_REPO_URL`→`$HOME_DIR` best-effort. Ensure the home clone uses SSH (deploy key →
  pushable) and is idempotent (fetch/reset if present).
- `docker/entrypoint.sh`: after `50-repos`, if `$HOME_DIR/.git` exists, create symlinks
  into the dev home:
  - `~/CLAUDE.md → $HOME_DIR/CLAUDE.md`
  - `~/ai → $HOME_DIR/ai`
  - `~/.claude/<f>.md → $HOME_DIR/.claude/<f>.md` for each tracked md (don't disturb the
    `~/.claude` login volume).
  - `/home/areg → /home/dev` so absolute `@/home/areg/...` imports resolve.
- Guard everything (skip cleanly if `HOME_REPO_URL` empty / clone absent).

**Verify (in container):** `cat ~/CLAUDE.md` shows the home file; `ls -l ~/ai` resolves;
`readlink /home/areg` = `/home/dev`; edit a file via the link → `git -C $HOME_DIR status`
shows it; `git -C $HOME_DIR push` works; Claude honors the personal CLAUDE.md (imports
resolve, no `/home/areg` errors).

---

## T7 — Prove pluggability: `projects/example-react/`
- `provision.sh` (install Node), `build.sh` (`npm ci && npm run build` → `$SERVE_DIR/web/`),
  `project.env`. Document `PROJECT=example-react` in `devbox.conf.example`.
- **Verify:** image built with `PROJECT=example-react` has Node not Flutter; `build` runs
  the react build against a sample repo and serves it. (May be gated/manual — log if skipped.)

---

## Multi-project on one VPS (D7 — design + impl)
- Make `$BASE=/root/devbox-<PROJECT>`, container/image `devbox-<PROJECT>`, and per-project
  SSH/serve ports a function of `PROJECT` (set in `devbox.conf`/`deploy.conf`).
- Thread `PROJECT` through `local/` + `vps/` scripts so each lifecycle command targets one
  deployment; `clean` stays project-scoped (already is).
- **Verify:** two projects deployed on one VPS run concurrently — distinct dirs,
  containers, ports — and cleaning one leaves the other intact.

---

## T8 — Docs sweep  (largely done in T1–T5 pass)
`RUNBOOK`/`CHEATSHEET`/`CLAUDE`/skill already on `devbox` + new keys + `projects/<name>`
model. Remaining: document the `projects/<name>` "how to add a project" flow, the writable
home repo (T6), and multi-project once implemented.

## T9 — Parity check (end-to-end, gated on a box)
Fresh `upload → setup → up` with `PROJECT=orion` → same APK (now `app.apk`) + web, same
URLs; `vps-status.sh` UP; home repo present + pushable; Claude honors personal workflow.
Record in `review.md`.
