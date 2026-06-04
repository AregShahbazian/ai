# Discussion — Devbox & driving Orion dev from the phone

**Date:** 2026-06-04
**Mode:** discussion (answers-only)
**Outcome:** Plan a Linux "devbox" to host Claude Code + build/serve the APK so Orion can be worked on from the phone. Set up locally first, move to a VPS later. On-device hot-reload dropped; install-and-test via URL is enough.

## Summary / conclusions

- **Goal:** drive Claude *and* test the app from the phone, without the laptop, with the box reachable even when the laptop is packed → needs an **always-on devbox**, not the laptop.
- **The consumer Claude app (installed on the Zenfone) is a chatbox** — not the agentic Claude Code used here. It's unsuitable for real repo coding. The right way to get *this* experience on the phone is a **VPS running Claude Code (CLI) in `tmux`, reached via an SSH client** (Termius, or Termux as a terminal). Coding happens on the box, shown in a phone terminal.
- **claude.ai/code** (Claude app / browser) can drive cloud coding + web preview, but: can't reach your physical phone (no ADB), no emulator, and doesn't carry our `~/ai` + `~/.claude` layout — so it doesn't fit our workflow or on-device install.
- **No app backend needed** — Orion MVP1 is local-only. The "server" is purely **dev infrastructure**.
- **On-device hot-reload / ADB-over-wifi: dropped for now.** **Decision: install-and-test via a URL** — devbox builds the APK and hosts it at a (private) URL the phone downloads + installs. Simpler, and the same path used to give testers builds (later: Firebase App Distribution / Play internal testing).
- **Tailscale** = private VPN mesh linking devices; used to keep the devbox/preview **private** (phone fetches over the tailnet), not for ADB.
- **Server type:** a **VPS** (clean Ubuntu, root) — not a literal "dedicated" machine. ~≥8 GB RAM / 2–4 vCPU / ~40 GB for Flutter+Gradle. Hetzner cheapest. Can host any language/runtime.
- **Local-first:** set up & test the devbox locally before renting; scripts stay host-agnostic.
- Created repo **`~/git/orion-dev-box`** (with `CLAUDE.md`) to hold provisioning + control; **another agent will build it.**

## Open questions
1. Which VPS provider/plan when the time comes (Hetzner vs DO/Vultr).
2. APK distribution: plain hosted URL vs Firebase App Distribution / Play internal testing for the tester group.

## Ideas to realize
- **orion-dev-box** (separate repo, separate agent): a Linux devbox that —
  - hosts **Claude Code on demand** (`tmux` session, SSH from phone via Termius/Termux), with start/stop control;
  - has `build-apk` script: pull both repos → `flutter build apk` → publish;
  - **serves the APK (+ web preview) at a private URL** for phone download/install;
  - provisions host-agnostically (local now, Ubuntu VPS later); **Tailscale** for private access;
  - keeps secrets (keystore, Anthropic creds, Tailscale keys) outside the repo.
- **APK distribution to testers:** evaluate Firebase App Distribution / Play internal testing track (versioning + notifications) vs a plain URL.

## Related
- `~/git/orion-dev-box/CLAUDE.md` — the devbox repo
- `~/ai/orion/discussions/2026-06-04-dev-loop-and-map-plugin.md` — web-first dev loop, maplibre_gl
- See also [[project-orion-dev-stack]]
