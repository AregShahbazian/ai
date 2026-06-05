# Devbox — Tasks

Implements PRD `devbox-core` per `design.md`. Order is bottom-up: config + shared
lib first, then the three surfaces (workspace, build, serve), then provisioning that
installs the prerequisites, then a local end-to-end pass. Commit messages carry
`[devbox-core]`.

Phasing: **P1 = make it work locally from the phone** (workspace + serve + build,
hand-run after a manual install). **P2 = one-command provisioning + portability**.
**P3 = VPS move + polish.**

---

## P1 — Local, hand-run

### T1. Repo skeleton + config
- **Files:** `config.example`, `scripts/lib/common.sh`, `README.md` (short).
- `config.example` — the keys from design (`ORION_DIR`, `AI_DIR`, `SERVE_DIR`,
  `SERVE_PORT`, `TMUX_SESSION`, `ORION_BRANCH`) with the documented defaults.
- `common.sh` — `source` real `config` if present (else defaults), `log()`/`die()`
  helpers, a `need <cmd>` guard that errors with a clear message if a binary is
  missing. Every script sources this first.
- Confirm `config` (no extension) is covered by `.gitignore` (it is: `config` line).
- **Verify:** `bash -n` on every script; sourcing common.sh with no `config` yields
  the defaults (`echo $SERVE_PORT` → 8080).

### T2. Workspace: `claude-start` / `claude-stop`
- **Files:** `scripts/claude-start`, `scripts/claude-stop`, `provision/dotfiles/.tmux.conf`.
- `claude-start`: `need tmux`; if `tmux has-session -t $TMUX_SESSION` → `tmux attach`;
  else `tmux new-session -d -s $TMUX_SESSION -c $ORION_DIR` then send `claude` to
  window 0 and `tmux attach`. Uses the shipped `.tmux.conf` (mouse on, bracketed
  paste, visible window/status bar so tabs are tappable in Termius).
- `claude-stop`: `tmux kill-session -t $TMUX_SESSION` or a clear "no session" message.
- **Verify (laptop terminal stands in for the phone):**
  - `claude-start` → lands in tmux, window 0 in `~/git/orion`, Claude running.
  - `Ctrl-b c`, `cd` elsewhere, run a command → second tab works; `Ctrl-b 0/1` switches.
  - Detach (`Ctrl-b d`), re-run `claude-start` → same tabs, same live state.
  - Paste a long multi-line block → does not submit early (bracketed paste OK).
  - `claude-stop` → session gone; second `claude-stop` → clean message, no error.

### T3. Serve: `serve`
- **Files:** `scripts/serve`.
- Ensure `$SERVE_DIR` exists; if a server is already bound to `$SERVE_PORT`, print the
  URL and exit (idempotent — no duplicate). Else start the static server over
  `$SERVE_DIR` on `$SERVE_PORT`. **Decision:** start with `python3 -m http.server`
  (zero install) for P1; revisit Caddy in P3 if APK MIME / dir-listing matter.
- Print both URLs: `http://<host>:$SERVE_PORT/orion.apk` and `…/web/`.
- **Verify:** drop a dummy file in `$SERVE_DIR`, run `serve`, `curl localhost:PORT/`
  lists it; re-running `serve` reports "already running", doesn't start a second.

### T4. Build: `build-apk`
- **Files:** `scripts/build-apk`.
- Steps: `need flutter git`; `git -C $ORION_DIR pull --ff-only origin $ORION_BRANCH`;
  `flutter -C $ORION_DIR build apk --release`; `flutter ... build web --release`;
  copy `build/app/outputs/flutter-apk/app-release.apk` → `$SERVE_DIR/orion.apk` and
  `build/web/` → `$SERVE_DIR/web/`. On success print the served URLs.
- Note in output whether the APK is debug-signed (no keystore yet) vs release-signed.
- Don't add a separate `flutter pub get` unless a build fails on deps — `flutter
  build` runs it; confirm during verify and only add if needed.
- **Verify:** run on the laptop; `$SERVE_DIR/orion.apk` exists and is non-trivial in
  size; `$SERVE_DIR/web/index.html` exists; re-run is idempotent (clean overwrite).

### T5. P1 end-to-end (manual install assumed)
- Manually ensure prerequisites exist on this laptop (flutter ✓ already, tmux, python3).
- Bring up Tailscale on the laptop and the Zenfone (manual `tailscale up`).
- From the **phone**: Termius SSH to the laptop's `100.x`; `claude-start`, drive
  Claude, open a 2nd tab; `build-apk`; `serve`; Chrome → download `orion.apk`, install;
  open `…/web/` and confirm the map renders on the phone.
- **Verify / acceptance (PRD goals):** phone drives Claude over SSH and survives a
  disconnect (goal 1); `claude-stop` ends it cleanly (goal 2); APK installs from the
  URL and web preview loads (goal 3). Record results in `review.md`.

---

## P2 — One-command provisioning

### T6. Provision steps (idempotent)
- **Files:** `provision/bootstrap.sh`, `provision/10-system.sh`, `20-flutter.sh`,
  `30-claude.sh`, `40-tailscale.sh`, `50-repos.sh`.
- Each step re-runnable: detect-then-install, never fail if already present.
  - `10-system.sh` — apt: git, tmux, curl, unzip, a JDK, python3.
  - `20-flutter.sh` — Flutter SDK + Android cmdline-tools/build-tools; accept licenses.
  - `30-claude.sh` — install Claude Code.
  - `40-tailscale.sh` — install only; print the `tailscale up` command, never store a key.
  - `50-repos.sh` — clone `orion` + `~/ai` if absent; otherwise leave alone.
  - `bootstrap.sh` — run 10→50 in order, source `common.sh`, summarise what changed.
- **Verify:** on a scratch container/VM, `bootstrap.sh` from clean → `flutter doctor`
  passes Android bits, `claude --version`, `tailscale version` all resolve; a second
  run reports "already installed" everywhere (idempotent).

### T7. Portability check
- Confirm nothing in `scripts/`/`provision/` hardcodes a host or absolute path outside
  `config`. `grep` for stray `/home/areg`, `localhost`, fixed IPs.
- **Verify:** with only `config` changed, every script still resolves paths correctly.

---

## P3 — VPS + polish

### T8. Move to VPS
- Provision a rented Ubuntu VPS, run `bootstrap.sh`, write `config`, `tailscale up`.
- Repoint the phone's Termius host + Chrome URL to the VPS `100.x`. Nothing else changes.
- **Verify:** full P1 acceptance again, now against the VPS.

### T9. Signing (gated on the keystore)
- Keystore exists at `~/certs/android/mby4m.jks` (created via the Orion agent, lives
  outside both repos — never commit it or its passwords).
- Still need from the user before wiring: key **alias**, and the **store/key
  passwords** (these go in a `key.properties` outside the repo, referenced by path).
- Add `key.properties` (outside repo), wire Orion's `android/app/build.gradle.kts`
  signing config to read it, make `build-apk` produce a release-signed APK; drop the
  "debug-signed" notice.
- **Verify:** `apksigner verify` on the published APK; phone install still works.

### T10. Optional polish (only if wanted)
- Caddy instead of `python http.server` (APK MIME, no dir-listing).
- systemd unit so `serve` (and maybe a default workspace) auto-start on the VPS.
- A phone-triggered `build-apk` (URL/endpoint) — explicitly a later idea.

---

## Cross-cutting verification
Each task: `bash -n` clean, sourcing `common.sh` works, re-running is idempotent, and
no secret/host value is committed. Full PRD-goal acceptance is recorded in `review.md`
at the end of P1 and again after the VPS move.
