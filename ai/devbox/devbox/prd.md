---
id: devbox-core
---

# Devbox — PRD

A Linux box that lets me work on [Orion](../orion) from my phone, with no laptop.
Set up and tested locally first; later moved to a rented Ubuntu VPS unchanged.

## Goals

1. **Drive Claude Code from the phone.** Start an agentic Claude Code session on
   the box and reach it from an SSH client (Termius/Termux). The session must
   survive disconnects and reconnect to the same running state.
2. **Stop on demand.** Cleanly end the Claude session / free the box.
3. **Build & serve the app.** Pull the latest Orion code, build the Android APK
   (and Flutter web), and host the output at a private URL the phone can reach to
   download + install, or open for a quick web preview.

## Requirements

### Provisioning
- One host-agnostic provisioning path that installs everything needed: Flutter
  SDK, Android SDK/build-tools, Claude Code, a static web server, and private
  networking (Tailscale).
- Runs unchanged on the local machine now and on an Ubuntu VPS later — only config
  (paths, ports, repo URLs) differs.
- Clones both repos the box works with: Orion code and the `~/ai` workflow repo.

### Claude session
- A single command starts a persistent Claude Code session (tmux) for Orion.
- Reconnecting from the phone attaches to the existing session, not a new one.
- A single command stops the session cleanly.

### Build & serve
- A command pulls latest Orion, builds the APK, and publishes it to the served dir.
- Flutter web is built and served for quick checks.
- Artifacts are reachable from the phone at a private URL (over Tailscale).
- The phone flow is download-and-install / open-in-browser only.

### Access & secrets
- Phone access to both SSH and the served URL is private (not public internet).
- Release keystore, Anthropic credentials, and Tailscale auth keys live outside
  this repo and are never committed.

## Non-requirements (out of scope)
- ADB, on-device hot-reload, or any device-attached workflow.
- The box rendering the map itself (`maplibre_gl` has no desktop target).
- iOS builds.
- Public/unauthenticated hosting of artifacts.
- Multi-user or concurrent-session support.
- Auto-provisioning the VPS itself (provider setup is manual for now).
