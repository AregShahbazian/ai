# Generalize Devbox — Design

Design + implementation choices for `devbox-generalize` (see `prd.md`). Built on the
existing `devbox-core` codebase.

**Status:** D1–D5 implemented (T1–T5, on branch `generalize-devbox`). D6 (writable home
repo) is next; D7 (multi-project) is designed, not yet implemented.

## Overview

Split the repo into a **generic core** (container, SSH, tmux/Claude, serve, lifecycle)
and **pluggable projects** under `projects/<name>/`. The active project is chosen in
`devbox.conf`; its toolchain is installed at image-build time and its build is dispatched
at runtime. The personal **home repo** is cloned **writable** into the container where
Claude runs (`dev`). The repo + all artifacts are renamed `orion-dev-box → devbox`.

## Decisions

### D1 — Rename `orion-dev-box` → `devbox`  ✅
- Host dir `/root/orion-devbox` → `/root/devbox` (`$BASE`); image + container → `devbox`;
  `/opt/orion-dev-box` → `/opt/devbox`. `DEVBOX_REPO_URL` keeps its name.
- `vps-clean.sh` keeps removing the **old** names (container/image `orion-devbox`,
  `/root/orion-devbox`, `/root/orion-dev-box`) as legacy so a box mid-migration cleans up.
- GitHub repo rename + local dir move are manual.

### D2 — One base image + per-project toolchain layer  ✅
- `Dockerfile` installs only the **generic base** (git, tmux, curl, openssh, unzip,
  ca-certs, Claude, scripts/PATH) — **no JDK/Flutter/Android**.
- `ARG PROJECT` (default `orion`) → Dockerfile runs `projects/$PROJECT/provision.sh` as a
  later layer; `compose` passes `PROJECT` as a build arg (from `.env`).

### D3 — Generic `build` dispatches to the project  ✅
- `scripts/build` loads the active project and runs `projects/$PROJECT/build.sh`, which
  writes artifacts into `$SERVE_DIR`. `serve` unchanged. `build-apk` was **removed
  outright** (no shim) — clean break since the box isn't in daily use yet. Served APK is
  now generic **`app.apk`**.

### D4 — Project contract: `projects/<name>/`  ✅
```
projects/<name>/
  provision.sh   # install the toolchain (image build; root → /opt, else $HOME)
  build.sh       # produce artifacts into $SERVE_DIR (runtime, as dev)
  project.env    # contract/metadata (sourced by `build`)
```
- `build.sh` uses `$PROJECT_DIR` (the project's clone), `$PROJECT_REPO_URL`,
  `$PROJECT_BRANCH`, `$SERVE_DIR`; owns clone-sync + build + publish.
- **Orion** = `projects/orion/`: `provision.sh` (JDK21+Flutter+Android, moved out of the
  base), `build.sh` (APK+web → `$SERVE_DIR/app.apk` + `web/`), `project.env`.

### D5 — Config (extends `devbox.conf`)  ✅
```
DEVBOX_REPO_URL   = git@github.com:<you>/devbox.git   # the devbox fork (unchanged role)
PROJECT           = orion                              # which projects/<name> to build
PROJECT_REPO_URL  = https://github.com/<you>/app.git  # was ORION_REPO_URL
PROJECT_BRANCH    = main                              # was ORION_BRANCH
HOME_REPO_URL     = git@github.com:<you>/home.git     # was AI_REPO_URL; "home repo", SSH (pushable)
```
- `vps-setup.sh` writes `$SRC/.env` with `PROJECT`, `PROJECT_REPO_URL`, `PROJECT_BRANCH`,
  `HOME_REPO_URL`. `compose` reads `.env` for the `PROJECT` build arg + container env.
- Core defaults are **empty** for the repo URLs (config/.env supplies them); only the
  `PROJECT` selector defaults to `orion`. `common.sh` derives `PROJECT_DIR=$DEVBOX_HOME/src/$PROJECT`,
  `HOME_DIR=$DEVBOX_HOME/src/home`.

### D6 — Writable HOME repo in the container (NEXT — the key call)
Claude runs as `dev`, so the home repo must live there, writable, with my **home-level**
`CLAUDE.md` + `.claude/*.md` + `ai/` in effect. Obstacle: my `CLAUDE.md` imports use
**absolute** `/home/areg/...` paths, and `/home/dev/.claude` is a mounted volume (Claude
login state).

**Chosen approach (confirm in review):**
1. `50-repos.sh` clones `HOME_REPO_URL` (SSH/deploy-key → pushable) into `$HOME_DIR`
   (`$DEVBOX_HOME/src/home`, persisted on `devbox-data`).
2. Entrypoint symlinks the home entry points into it:
   - `~/CLAUDE.md → $HOME_DIR/CLAUDE.md`
   - `~/ai → $HOME_DIR/ai`
   - `~/.claude/<file>.md → $HOME_DIR/.claude/<file>.md` per tracked md (the `~/.claude`
     login volume is untouched; only personal md files are linked).
3. Symlink `/home/areg → /home/dev` (entrypoint) so the absolute imports resolve. Editing
   through any link writes into `$HOME_DIR`, so `git commit`/`push` work.

**Why not** clone the repo *as* the home dir: the `~/.claude` volume shadows the repo's
`.claude/*.md`, and `reset --hard` over a live home risks clobbering devbox dotfiles.
**Alternative:** make the container user `areg` (home `/home/areg`) — no symlink, but
renames the SSH user everywhere; deferred.

### D7 — Multiple projects on one VPS (designed, not implemented)
Per the PRD: one VPS hosts several deployments, one per project, without collision.
- Naming derives from the project: `$BASE=/root/devbox-<project>`, container/image
  `devbox-<project>`. `PROJECT` (from `devbox.conf`) drives all three.
- Ports are per-deployment: derive from a base + offset, or an explicit
  `SSH_PORT`/`SERVE_PORT` per `devbox.conf`. No two projects share `2222`/`8080`.
- Lifecycle scripts already pin paths via `$BASE`; make `$BASE`/container/ports a function
  of `PROJECT` (in `deploy.conf`/`devbox.conf`), so `upload/setup/up/down/clean/status`
  each target one deployment. `clean` is already project-scoped.
- Open: where the per-project port mapping lives (computed vs explicit), and whether
  `local/` scripts take a `--project` arg or read it from `devbox.conf`.

## Target repo structure (current)
```
devbox/
├── Dockerfile                 # base + ARG PROJECT → projects/$PROJECT/provision.sh
├── docker-compose.yml         # PROJECT build arg + env from .env
├── provision/                 # GENERIC: 10-system (base only), 30-claude, 40-tailscale,
│                              #   50-repos (project + home clone), bootstrap, host-setup
├── scripts/                   # GENERIC: lib/common.sh, claude-start/stop, serve/serve-stop,
│                              #   build (dispatch)
├── projects/
│   ├── orion/                 # provision.sh, build.sh, project.env   (shipped)
│   └── example-react/         # stub proving pluggability             (T7, todo)
├── local/  vps/               # lifecycle scripts
├── docker/entrypoint.sh       # + home-repo symlinks, /home/areg link (T6)
├── devbox.conf.example  config.example
```

## Rename map (old → new)
| Old | New |
|-----|-----|
| `orion-devbox` / `orion-dev-box` (repo/image/container/dir) | `devbox` |
| `/root/orion-devbox` | `/root/devbox` |
| `ORION_REPO_URL` / `ORION_BRANCH` / `ORION_DIR` | `PROJECT_REPO_URL` / `PROJECT_BRANCH` / `PROJECT_DIR` |
| `AI_REPO_URL` / `AI_DIR` | `HOME_REPO_URL` / `HOME_DIR` |
| `scripts/build-apk` | `scripts/build` (+ `projects/orion/build.sh`) |
| served `orion.apk` | `app.apk` |

## Compatibility / migration
- Old VPS has `/root/orion-devbox` + container `orion-devbox`. Migrate: `vps-clean.sh
  --all` on the old box (force-removes old names), then fresh `upload → setup → up` from
  the renamed repo → `/root/devbox`, container `devbox`.
- Orion output (APK + web, served paths, phone URLs) behavior-identical (artifact renamed
  `orion.apk → app.apk`).

## Open questions
- D6 symlink set: which `~/.claude/*.md` to link (enumerate vs glob tracked).
- D7 port scheme: computed offset vs explicit per-project ports.
- `example-react` (T7): minimal real `npm run build` vs no-op stub. Leaning real-minimal.
