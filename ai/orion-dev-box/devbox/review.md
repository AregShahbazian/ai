# Devbox — Review

Verification record for PRD `devbox-core`. One section per implemented task; full
PRD-goal acceptance is captured at the end of P1 and again after the VPS move.

---

## T1 — Repo skeleton + config ✅

**Implemented:** `config.example`, `scripts/lib/common.sh`, `README.md`.

- [x] `bash -n scripts/lib/common.sh` clean.
- [x] No `config` present → defaults resolve (`SERVE_PORT=8080`, `TMUX_SESSION=work`,
      `ORION_DIR=$HOME/git/orion`, `DEVBOX_ROOT` correct regardless of cwd).
- [x] `config` override applied (set `SERVE_PORT=9999` → loaded; unset keys stay default).
- [x] `need <cmd>` passes for present binaries, dies with a clear message for missing.
- [x] `config` (no extension) is gitignored; `config.example` is tracked.

---

## T2 — Workspace: claude-start / claude-stop ✅

**Implemented:** `scripts/claude-start`, `scripts/claude-stop`,
`provision/dotfiles/.tmux.conf`.

- [x] `bash -n` clean on both scripts.
- [x] `claude-start` creates session `$TMUX_SESSION` with window 1 in `$ORION_DIR`.
- [x] Shipped `.tmux.conf` applied via `tmux -f`: base-index 1, `mouse on`.
- [x] Second tab opens (`new-window`) and lists alongside the first — tab model works.
- [x] Re-running `claude-start` attaches, never spawns a duplicate session (idempotent).
- [x] `claude-stop` kills the session; second `claude-stop` → clean "nothing to stop".
- [x] `claude not found` path warns and opens a shell instead of failing.

**Deferred to T5 (need an interactive TTY / phone):**
- [ ] Real attach rendering + readable status bar in Termius.
- [ ] Long multi-line paste does not submit early (bracketed paste / `assume-paste-time`).
- [ ] Detach + reconnect lands back in the same live tabs.

---

## T3 — Serve ✅

**Implemented:** `scripts/serve` (python3 `http.server`, detached).

- [x] `bash -n` clean.
- [x] Creates `$SERVE_DIR` if absent; serves it on `$SERVE_PORT`, detached (SSH free).
- [x] `curl /orion.apk` and `/web/` return the published artifacts.
- [x] Second run detects the bound port → prints URLs, starts no duplicate
      (one listener confirmed via `ss`).
- [x] Start-failure path dies with a pointer to `$SERVE_DIR/.serve.log`.
- [x] URLs print the reachable host (LAN IP now; tailnet IP once Tailscale is up).

**Deferred to T5 (phone):**
- [ ] APK downloads + installs from the URL in mobile Chrome (MIME via python may be
      generic — acceptable for sideload; Caddy is the P3 fallback).
- [ ] Web build opens in mobile Chrome and the map renders on the phone GPU.

---

## T4 — Build: build-apk ✅ (orchestration) / ⏸ (real Flutter build gated)

**Implemented:** `scripts/build-apk` — sync service-owned clone → `flutter build apk
--release` + `build web --release` → publish to `$SERVE_DIR`.

- [x] `bash -n` clean.
- [x] **Clone path:** clones `$ORION_REPO_URL` → `$ORION_DIR` (under `$DEVBOX_HOME`,
      never `~/git`), builds, publishes `orion.apk` + `web/`. (verified with a fake
      flutter-project remote + stubbed `flutter`).
- [x] **Update path:** existing clone → `fetch`/`checkout`/`reset --hard` to upstream,
      rebuilds, republishes. Idempotent — one clone, artifacts refreshed to new HEAD.
- [x] Missing-artifact guard (`die` if APK/web not produced).
- [x] Signing note path runs (unzip check for CERT).

**Real build VERIFIED against `phase-1-map`** (DEVBOX_HOME=/tmp/devbox-real):
- [x] Clone of `origin/phase-1-map` → pub get `Got dependencies!`.
- [x] `flutter build apk --release` → `serve/orion.apk`, **70 MB, valid APK**.
- [x] `flutter build web --release` → `serve/web/` built.
- [x] APK is **debug-signed** (`CN=Android Debug`) — keystore not wired yet (T9);
      acceptable for sideload.

**Branch note (not a bug):** Orion's Flutter code lives on `phase-1-map`, while
`origin/main` is still an empty "Initial commit". `build-apk` defaults to
`ORION_BRANCH=main`, so set `ORION_BRANCH="phase-1-map"` in `config` until the code
lands on `main`. (My earlier "code not pushed" note was wrong — it was the branch.)

**Deferred:**
- [ ] Release signing via `~/certs/android/mby4m.jks` instead of debug key — see T9.

---

## T6 — Provisioning steps ✅ (logic) / ⏸ (full fresh install on VPS)

**Implemented:** `provision/bootstrap.sh` + `10-system.sh`, `20-flutter.sh`,
`30-claude.sh`, `40-tailscale.sh`, `50-repos.sh`; `ensure_line` helper in common.sh.

- [x] `bash -n` clean on all six scripts.
- [x] `bootstrap.sh` accepts a step subset; errors on unknown step.
- [x] **Idempotent no-op** verified on this box: `10/20/30` detect git/tmux/jdk/etc,
      flutter, and claude as present → no sudo, no apt, no network.
- [x] `~/.bashrc` checksum **unchanged** by the no-op run (no profile mutation when
      tools already present).
- [x] `50-repos`: clone-if-absent then skip-if-present, both verified with fake
      file:// remotes into a temp `$DEVBOX_HOME` (never `~/git`).
- [x] `ensure_line` idempotent (duplicate line ignored).
- [x] `40-tailscale` is install-only; prints manual `tailscale up` guidance, stores
      no key.

**Deferred to T8 (fresh Ubuntu VPS):**
- [ ] `10-system` actually apt-installs the missing set (needs a box without them).
- [ ] `20-flutter` full path: clone Flutter + Android cmdline-tools + licenses + SDK.
- [ ] `30-claude` native-installer download path.
- [ ] `40-tailscale` real install via the official script.

---

## T7 — Portability check ✅

- [x] Scan of `scripts/`/`provision/` for hardcoded hosts/paths: no `/home/areg`,
      no `~/git`, no hardcoded IPs. Remaining `localhost`/`127.0.0.1`/`8080` hits are
      legitimate (host-display fallback, local port check, documented default).
- [x] **Bug found + fixed:** `common.sh` applied defaults *before* sourcing `config`,
      so a `config` overriding only `DEVBOX_HOME` did NOT repoint the derived
      `ORION_DIR`/`AI_DIR`/`SERVE_DIR`. Reordered to source `config` first, then
      derive defaults from the (possibly overridden) `DEVBOX_HOME`.
- [x] Verified: single `DEVBOX_HOME` override repoints all paths; explicit per-key
      overrides still win; no-config defaults stay isolated from `~/git`.
