---
id: devbox-generalize
---

# Generalize Devbox — PRD

Turn the Orion-specific devbox into a **project- and language-agnostic devbox**, with
Orion as the first pluggable project, and make my personal workflow fully usable on the
box by cloning my workflow repo there **writable**.

Builds on `devbox-core`. This PRD covers requirements only — no design choices.

## Background / why

The current devbox bakes Orion (Flutter + Android) into the core: the Dockerfile installs
the Flutter/Android toolchain, and `build-apk`/serve assume a Flutter app. To reuse the
same box for another project (e.g. a React app) I must be able to plug a project in
without rewriting the core. Separately, when I drive Claude on the box I want my **full
personal workflow** available — the `~` workflow repo (CLAUDE.md, `.claude/`, `ai/`) —
and writable, so Claude can read *and commit* workflow docs exactly like on my laptop.

## Goals

1. **Project-agnostic core.** The devbox core provides everything generic — container,
   hardened SSH, persistent tmux/Claude session, static serve, the lifecycle scripts —
   with nothing tied to any one project or language.
2. **Pluggable projects.** Each project contributes its own toolchain and build/serve
   logic under a project-named path; which project a box runs is config-driven.
3. **Orion as the first project.** Everything Orion/Flutter/Android-specific is moved out
   of the core into the Orion project, with no behavior regression for the Orion deploy.
4. **Writable workflow repo on the box.** My `~` workflow repo is present in the
   environment where Claude runs, as a normal writable git clone, so the full personal
   workflow applies and I can commit/push workflow changes from the box.
5. **Rename to `devbox`.** The project is named/branded as a generic `devbox`, not
   `orion-dev-box`.

## Requirements

### Naming / rename
- The repo, image, container, on-host directory, and all script/doc references use a
  generic `devbox` name instead of `orion`/`orion-dev-box`.
- No Orion-specific identifier remains in any generic (core) file name or path.
- The GitHub repo rename itself is performed manually by me; everything in-repo must be
  updated to match.

### Project-agnostic core
- The generic core contains no project- or language-specific logic, toolchain, branch,
  or build command.
- Core capabilities remain exactly as in `devbox-core`: SSH-in as a non-root user,
  `claude-start`/`claude-stop`, `serve`/`serve-stop`, and the full VPS lifecycle
  (`upload → setup → up/down → clean`, status, key update, connect).

### Pluggable projects
- Projects live under a per-project path in the repo (e.g. one folder per project).
- Each project declares: the toolchain it needs, how to **build**, and what to **serve**.
- Exactly one project is active per box, selected via config (no code edits to switch).
- Adding a new project (e.g. a React app) requires only adding a new project folder +
  config — no changes to the generic core.
- Orion is delivered as the first project: its toolchain (JDK/Flutter/Android) and its
  build (APK + web) live entirely under the Orion project path.

### Multiple projects on one VPS
- A single VPS must be able to host **several independent devbox deployments at once**,
  one per project — each its own on-host dir, its own container, and its own ports.
- Per-deployment naming is derived from the project (e.g. on-host dir `devbox-<project>`,
  container `devbox-<project>`) so deployments never collide.
- SSH/serve ports are per-deployment (no two projects share `2222`/`8080`); the lifecycle
  scripts target a single deployment without disturbing the others.
- `clean` stays project-scoped: tearing down one project's deployment leaves the other
  projects' dirs, containers, and volumes intact (already a `devbox-core` principle).

### Build & serve contract
- A single generic `build` command produces the active project's output and publishes it
  to the served directory; a single generic `serve` hosts that output (unchanged phone
  flow: download/install or open in browser).
- The build output location and what gets served are defined by the active project, not
  hardcoded in the core.

### Workflow repo (writable) where Claude runs
- Claude runs **inside the container as the non-root `dev` user** (not on the VPS host).
  The workflow repo must therefore be available in the container, not on the host.
- The workflow repo is cloned as a **writable** git clone (SSH/deploy-key auth) so I can
  `git commit`/`git push` workflow changes from the box.
- It is placed so that my personal workflow resolves automatically for Claude — i.e. the
  home-level `CLAUDE.md`, `.claude/` imports, and `ai/` docs are in effect in the
  container, matching the laptop experience.
- Survives container restarts (persisted), like the other devbox state.

### Config-driven identity
- Project selection, the project's repo/branch, and the workflow repo URL are all set via
  config (extending `devbox.conf`); no GitHub owner or repo is hardcoded in tracked files.
- The existing config pattern (gitignored `devbox.conf` from a committed example) is kept.

### Compatibility
- After generalization, an Orion deployment produces the same APK + web output and the
  same phone-reachable URLs as before.
- The lifecycle scripts, secrets handling, and Tailscale/SSH model are unchanged in
  behavior (only paths/names updated for the rename).

## Non-requirements (out of scope)
- Actually shipping a second project (React, etc.) — only the structure must support it;
  a stub/example is enough.
- Auto-detecting a project's type or toolchain.
- Combining more than one project's toolchain into a *single* image/container (each
  project still gets its own image/container — see "Multiple projects on one VPS").
- Automating the GitHub repo rename, or migrating existing clones/branches on the VPS.
- Any change to the phone-side clients or to phone↔container connectivity (still untested,
  parked until the VPS scripts are settled).
- iOS builds; public/unauthenticated hosting; multi-user/concurrent sessions (unchanged
  from `devbox-core`).

## Open questions (to resolve in design, not here)
- Exact placement of the writable workflow repo in the container so home-level
  `CLAUDE.md`/`.claude/` apply (clone-as-home vs subdir + links).
- Single base image with a per-project toolchain layer vs per-project images.
- Whether project selection lives in `devbox.conf` only, or also needs a per-project
  `project.env`.
