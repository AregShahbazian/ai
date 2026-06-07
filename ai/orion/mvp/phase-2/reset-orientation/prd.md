---
id: phase-2-reset-orientation
---

# Orion — Phase 2: Reset-orientation button (PRD)

> Part of Orion — see [`README.md`](../../README.md) (root overview).

**Date:** 2026-06-06
**Phase:** 2 (map polish)
**Status:** implemented & verified on device (2026-06-06); branch `feature/p2-reset-orientation`

## Problem

The native MapLibre compass auto-appears when the map is **rotated** (bearing ≠ 0)
and resets bearing on tap — that works. But a **two-finger pan tilts** the map
(pitch ≠ 0), and the native compass ignores pitch: it stays hidden, leaving the
user with a tilted map and no way to restore the flat, north-up view. Most map
apps surface a single "reset orientation" affordance for exactly this.

## Requirements

1. A single on-screen button restores the default orientation: **bearing = 0 and
   tilt = 0**, animated.
2. The button **appears whenever the map is oriented away from default** — i.e.
   rotated (bearing ≠ 0) **or** tilted (tilt ≠ 0) — and **disappears** when both
   return to ~0 ("re-focused").
3. Reuse one button and one appearance rule for both cases — not a separate
   rotate-reset and tilt-reset control.
4. The button doubles as a **north indicator**: a compass needle that rotates to
   the current bearing (so it reads as a compass, like the native one it replaces).
5. Lives in the safe-area HUD (top-right, where the native compass sat), inheriting
   the existing safe-area insets — no per-widget inset math.
6. No new permissions, no settings UI.

## Non-requirements

- A separate "reset tilt" button below the compass (track's two-button layout).
  Explicitly rejected — one button covers both.
- Keeping the native MapLibre compass. It is disabled and replaced by this Flutter
  control (this is the "real HUD control" that `safe-area-hud` deferred to).
- Persisting orientation, gesture config changes, or any location features.
