---
id: phase-5-settings
title: Settings page — persisted on-device toggles
status: implemented & verified on device (2026-06-07)
branch: feature/followme-longpress-zoom
---

## Goal

Turn the empty Phase 5 Settings placeholder into a real settings page with
working, **on-device-persisted** toggles (no backend). Establish the settings
store the rest of the app reads from, and ship the first two toggles.

## Requirements

- A `SettingsController` holds app settings, **persisted on-device** via
  `shared_preferences` (no account/backend). Loaded once before the first frame
  so values are in effect from startup.
- Settings render on the Settings page as **`SwitchListTile`** rows (label +
  subtitle + platform toggle) — the standard control for a boolean.
- **Toggle 1 — Long-press to zoom** (default **on**). Gates the follow-FAB
  long-press (`phase-2-followme-zoom`). When **off**, the FAB has no long-press
  at all — it behaves exactly as before that feature. **Native-only**: hidden on
  web (the feature doesn't exist there — web already center+zooms on a tap).
- **Toggle 2 — Log interaction events** (default **off**). Echoes every
  interaction to the dev log. This is the persisted owner of what used to be
  `InteractionController.logEvents` — the flag moves out of the bus into the
  settings store. Shown on all platforms.
- Each toggle is a user action → routes through the **InteractionController**
  both ways (ids `settings.longPressZoom.set` / `settings.logEvents.set`,
  payload `{enabled}`), so it's recorded and re-dispatchable from the dev
  bridges. (Interaction-controller convention.)
- The existing dev-console `logEvents` toggles (`orion.logEvents(...)` on web,
  `orion.sh logEvents on=…` native) now go **through the persisted setting**, so
  toggling from the console persists and reflects in the in-app switch (and
  vice-versa).

## Non-requirements

- No backend/account sync — on-device only.
- No settings beyond these two yet (the page is the vehicle; more toggles land as
  features need them).
- The default-follow-**zoom level** stays a constant — making *that* adjustable
  is a separate backlog item, not this one.
- No grouping/sections/search on the page yet — a flat list is enough for two.
