---
id: phase-2-my-location
title: My Location — blue dot
status: implemented (verify pending)
branch: feature/p2-my-location
---

## Goal

Show the user's current GPS position as a blue dot on the map so they can
orient themselves at a glance.

## Requirements

- Request foreground location permission on first use; gracefully handle denial
  (dot simply absent, no crash, no nagging).
- Blue dot renders at the device's current position and updates in real time as
  the user moves.
- Works on Android, iOS, and web. Web falls back to browser geolocation
  (Wi-Fi / cell triangulation, typically 10–50 m accuracy) — acceptable.
- Foreground only. No background location, no always-on permission.

## Out of scope

Follow-me camera, accuracy circle, heading arrow — separate tasks.
