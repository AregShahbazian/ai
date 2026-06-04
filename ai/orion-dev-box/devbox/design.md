# Devbox — Design

Design for PRD `devbox-core`. Build-then-serve-static model; one provisioning path
that runs the same locally and on a future Ubuntu VPS, differing only by config.

## Deployment model: Docker container (host runs only Docker + Tailscale)

The whole devbox runs as **one container** (image `orion-devbox`), so the host stays
clean — no Flutter/Android/Claude on the host PATH. The host needs only **Docker**
and **Tailscale**.

```
host (laptop now / cheap CPU VPS later): docker + tailscale only
└─ container "orion-devbox"  (Dockerfile = the verified provision/*.sh steps)
   ├─ flutter + android-sdk + jdk   (baked in image, /opt)
   ├─ claude + tmux + our scripts   (on PATH for login shells)
   ├─ sshd (hardened, user `dev`)   → published host :2222
   └─ serve (static)                → published host :8080
volumes (persist across rebuild): devbox-data (clone+build+serve),
   devbox-claude (login), devbox-sshkeys (stable host keys)
phone → (Tailscale/LAN) → host :2222 ssh / :8080 web → container
```

- **Repo cloning** uses a GitHub **deploy key** mounted from `secrets/deploy_key`
  (the Orion repo is private). The entrypoint installs it for `dev` and rewrites
  `https://github.com/` → `git@github.com:` so the existing URLs auth via the key.
- **Phone SSH key** is provided in `secrets/authorized_keys`; the entrypoint installs
  it into `dev`'s `~/.ssh` (mounted to a neutral path to dodge uid-mapping).
- **`provision/host-setup.sh`** bootstraps the host: installs Docker + Tailscale,
  adds a swapfile on low-RAM boxes (Gradle is memory-bursty), prints next steps.
- The original `provision/10..50-*.sh` are reused **as the image build steps**, so a
  container build and a bare-metal install provision identically.

The tmux / build / serve sections below describe what happens **inside** the
container; they are unchanged by containerisation.

## Architecture

```
        Tailnet (private, encrypted)
  ┌──────────────┐                 ┌──────────────────────────────────────┐
  │   Zenfone    │                 │            Devbox (100.x)             │
  │              │   ssh :22       │  ┌────────────────────────────────┐   │
  │ Termius  ────┼─────────────────┼─▶│ tmux "work" — tabs you control:│   │
  │              │                 │  │  win0 claude  win1 claude(dirB)│   │
  │              │                 │  │  win2 dev server  win3 shell   │   │
  │              │                 │  └────────────────────────────────┘   │
  │              │   http :PORT    │  ┌────────────────────────────────┐   │
  │ Chrome   ────┼─────────────────┼─▶│ static server → SERVE_DIR/     │   │
  │              │                 │  │   orion.apk   (download+install)│   │
  └──────────────┘                 │  │   web/        (browser preview) │   │
                                    │  └────────────────────────────────┘   │
                                    │   $DEVBOX_HOME/src/orion (own clone)  │
                                    └──────────────────────────────────────┘
```

Three independent surfaces, no coupling between them:
1. **tmux workspace** — one persistent session you attach to; inside it you open
   tabs (tmux windows) and manage them like laptop terminal tabs.
2. **build** — produces artifacts into `SERVE_DIR`.
3. **static server** — serves `SERVE_DIR` (SSH and HTTP are separate; build can run
   while you're attached).

## Workspace model (tab behaviour)

Mirrors using terminal tabs on the laptop, not an opinionated launcher:

- **One persistent tmux session** `work`. `claude-start` creates it if absent
  (window 0 = `claude` in `$ORION_DIR`) and attaches; if it already exists it just
  attaches. Reconnect-safe: the phone always lands back in the same live tabs.
- **Tabs = tmux windows.** You add them yourself like at your desk: `Ctrl-b c` for a
  new tab, `cd` anywhere, then run `claude`, a dev server, or manual commands.
  Switch with `Ctrl-b <n>` / `Ctrl-b n`/`p`, or tap Termius' window bar.
- **Parallel Claude agents** = a tab per agent, each `cd`'d to its own folder. To
  avoid two agents fighting over one working tree, point them at separate clones or
  `git worktree` dirs — same discipline as on the laptop. The box doesn't enforce
  this; it's yours to arrange.
- **`claude-stop`** kills the whole `work` session (all tabs). It does not touch the
  build output or the static server.

### Phone input (compose-and-paste)
Long prompts are composed in a phone editor (Jota) — voice via the Gboard mic —
then copied and pasted into the Termius terminal (Claude's prompt). Live typing in
the TUI is not the expected input path. **Gotcha to handle at implement time:** big
pastes into a tmux/TUI input can submit early unless bracketed paste is on — set
`set -g set-clipboard on` + bracketed paste in the shipped `.tmux.conf`.

## Repo layout (to build)

```
provision/
  bootstrap.sh        # orchestrator: runs the steps below in order, idempotent
  10-system.sh        # apt deps, git, tmux, curl, unzip, jdk
  20-flutter.sh       # Flutter SDK + android-sdk/build-tools, accept licenses
  30-claude.sh        # install Claude Code
  40-tailscale.sh     # install tailscale (does NOT auth — see secrets)
  50-repos.sh         # clone orion + ~/ai if absent
scripts/
  claude-start        # create-or-attach tmux session running claude in orion
  claude-stop         # kill the tmux session
  build-apk           # pull orion, flutter build apk + web, publish to SERVE_DIR
  serve               # start/ensure the static server over SERVE_DIR
  lib/common.sh       # load config, log helpers, guard checks
config.example        # committed template; real `config` is gitignored
```

## Config (`config`, gitignored; `config.example` committed)

Single sourced shell file, the only thing that differs local vs VPS:

```sh
DEVBOX_HOME="$HOME/devbox"         # the devbox owns this tree; NEVER ~/git
ORION_REPO_URL="https://github.com/AregShahbazian/orion.git"
AI_REPO_URL="https://github.com/AregShahbazian/ai.git"
ORION_DIR="$DEVBOX_HOME/src/orion" # service-owned clone, NOT your working copy
AI_DIR="$DEVBOX_HOME/src/ai"       # service-owned clone of the workflow repo
SERVE_DIR="$DEVBOX_HOME/serve"     # APK + web/ published here
SERVE_PORT=8080                    # static server port (reached over tailnet)
TMUX_SESSION="work"                # persistent tmux workspace name
ORION_BRANCH="main"                # branch build-apk pulls
```

**Hard rule — isolation:** the devbox NEVER reads or writes the user's `~/git`
working copies. It clones the repos itself into `$DEVBOX_HOME/src/` and operates
only there. `$DEVBOX_HOME` is disposable: deleting it loses nothing but cached
clones + build output. This also makes local and VPS identical — neither relies on
a pre-existing `~/git`.

Scripts `source` it via `lib/common.sh`; missing keys fall back to these defaults so
a fresh box works before a `config` is written.

## Script contracts

- **claude-start** — `tmux has-session -t $TMUX_SESSION` → attach; else
  `tmux new-session -d -s … -c $ORION_DIR 'claude'` then attach. Ships a `.tmux.conf`
  (mouse on, bracketed paste, readable window bar). Reconnect-safe: re-running from
  the phone always lands in the same live tabs; you add more tabs yourself.
- **claude-stop** — `tmux kill-session -t $TMUX_SESSION` (no-op + clear message if
  none). Kills all tabs in the session; does not touch builds or the server.
- **build-apk** — `git -C $ORION_DIR pull --ff-only origin $ORION_BRANCH` →
  `flutter build apk --release` → `flutter build web --release` → copy
  `build/app/outputs/flutter-apk/app-release.apk` to `$SERVE_DIR/orion.apk` and
  `build/web/` to `$SERVE_DIR/web/`. Prints the tailnet URLs on success.
- **serve** — ensure one static server bound to `$SERVE_PORT` over `$SERVE_DIR`
  (Python `http.server` to start; revisit if directory listing/headers matter).
  Idempotent: if already up, report the URL instead of starting a second.

## Data flow (build → phone)

1. `build-apk` pulls latest, builds release APK + web, copies into `SERVE_DIR`.
2. `serve` exposes `SERVE_DIR` at `http://<tailnet>:$SERVE_PORT`.
3. Phone (Chrome): `…/orion.apk` → download → install; `…/web/` → preview.
   Map renders on the phone's GPU (box never renders it).

## Secrets (outside repo, per CLAUDE.md)

- **Tailscale** — `40-tailscale.sh` installs only; auth is manual (`tailscale up`,
  interactive or `--authkey` from an env not in the repo). Provisioning prints the
  command to run; never stores the key.
- **Android release keystore** — referenced by path from outside the repo. The user
  is creating the keystore separately (via the Orion agent); until that lands,
  `build-apk` uses debug-signed release for testing and logs that it is
  unsigned-for-store. Wire `key.properties` (pointing outside the repo) when ready.
- **Anthropic credentials** — Claude Code's own login on the box; not handled here.

## Local-vs-VPS portability

Nothing in `provision/`/`scripts/` hardcodes a host. The laptop→VPS move is:
run `bootstrap.sh`, write `config`, `tailscale up`. The phone's saved host changes
from the laptop's `100.x` to the VPS's `100.x` — nothing else.

## Open questions (resolve during implementation)

- **Static server choice** — `python -m http.server` is fine for one user; if we
  want correct APK MIME type / no dir-listing, switch to a tiny `caddy`/`busybox
  httpd` config. Decide when `serve` is built.
- **APK signing** — debug-signed for the test phase is acceptable (sideload). Need a
  real keystore + `key.properties` before any shareable build. Confirm scope.
- **Auto-start on boot (VPS)** — should `serve` (and maybe a default Claude session)
  come up via systemd on the always-on VPS, or stay manual? Out of MVP unless wanted.
- **Build triggering from phone** — MVP runs `build-apk` by hand in the SSH session.
  A one-tap trigger (URL/endpoint) is a later idea, not in this design.
- **flutter pub get** — assume `build-apk` runs it implicitly via `flutter build`;
  confirm no separate step needed after a pull that changes `pubspec.lock`.
