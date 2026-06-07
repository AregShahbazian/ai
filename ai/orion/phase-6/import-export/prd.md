---
id: phase-6-import-export
title: Import / Export Tracks
status: draft
---

# Phase 6 — Import / Export Tracks

## Goal
Import existing **Gaia GPS exports** and re-export them. No map rendering of
tracks yet (that's Phase 7).

## Scope
- Import a Gaia GPS export file into Orion.
- **Each `<trk>` becomes exactly one entry** in our data structure. A single file
  with 15 tracks → **15 entries**. No folders or grouping for now (deferred —
  see backlog).
- **Reached via a new "Tracks" HUD icon** on the map, placed **above the settings
  cog, below the follow-me FAB** (reuses the Phase 4 `HudButton`). The settings
  icon + page stay as-is. Opens the Tracks page (pushes over the live map, per the
  Phase 5 navigation pattern).
- Imported tracks get their **own page**, shown as a **flat list** of entries.
  - List item: a **summary** — for now: track **name**, **start date**,
    **distance**, **duration** (+ a small **color** swatch). (Refine later.)
  - **Tapping the item body** opens the **item-detail page** (**full stats**).
  - **Ellipsis (⋮) at the right** of each item opens a per-item dropdown menu via
    Flutter's built-in **`PopupMenuButton`** (`Icons.more_vert`) — identical on web
    and mobile (Flutter-rendered, not native), the menu pops anchored to the ⋮
    button. For now it contains **only "Export"** — this is how you export a single
    track. Batch select / export is **deferred**.
- **Import is triggered from an import icon in the page header** (`AppBar`
  `actions`, same row as the page title) → opens the system file picker.
- **File picker via `file_picker`** — works on **web and mobile**.
  - `allowedExtensions: ['gpx']` to nudge toward GPX (web sets `<input accept>`;
    Android's picker may ignore it and show all files — so still
    **validate after pick**: check extension + that it parses as GPX, friendly
    error otherwise).
  - **`allowMultiple: true`** — user can pick several `.gpx` files at once; import
    each (every `<trk>` in every file → its own entry).
- **Non-blocking import.** Picking file(s) does **not** freeze the app — parsing
  and storing run asynchronously (off the UI) while the user keeps using the app.
- **Progress badge on the import icon** — a Material `Badge` showing the number of
  **tracks still being processed** (not files). Track count is only known after a
  file is parsed, so the badge fills in as files are parsed and counts down as
  each track is stored; it disappears at zero.
- **Reactive list** — as each track finishes processing it is **added to the list**
  immediately (a long-lived controller, `ChangeNotifier`/stream — list observes,
  no manual refresh). **Always appended, no "already present" check** (the
  no-dedup decision below — simplest for now; re-imports duplicate, accepted).
- Re-export an imported track.

## Out of scope
- Rendering tracks on the map (Phase 7).
- Live track recording (Phase 8).

## Data format (from real samples)

Both source apps export **GPX 1.1** (`xmlns="http://www.topografix.com/GPX/1/1"`).
Two real-world shapes of the *same* trip, both must import cleanly:

- **Gaia GPS** (`creator="GaiaGPS"`): **one file, many `<trk>`** — the Mindanao
  sample holds 15 tracks / 37,775 points in a single 3.6 MB file. Compact
  single-line XML. Whole-second `<time>` (`...:50Z`). Track color in a
  `gpx_style` `<extensions>` block.
- **MyTracks** (`creator="...My Tracks..."`): **one file per `<trk>`** (15 files
  for the same trip). Pretty-printed, has a top-level `<metadata>`, `<name>`/
  `<desc>` wrapped in `CDATA`, sub-second `<time>` (`...:50.154Z`), color in
  `topografix:color`.

### Internal model & storage
- **One canonical track model** for both formats. Parse Gaia and MyTracks GPX into
  the same normalized type; flatten format differences (time precision, color
  source, CDATA) at import. Nothing format-specific persists downstream.
- **Persisted with Drift** (SQLite) — works on **both web (WASM SQLite) and
  mobile** from one API. Web and Android are **both production targets**, so
  persistence (and import perf) must be solid on each. (MVP listed Drift as TBD;
  this confirms it.) Plain `sqflite` is mobile-only, so not enough on its own.

### Structure to parse
- A file may contain **N `<trk>`** → import must handle multi-track files, not
  assume one.
- `<trk>` → `<name>` (may be CDATA), optional `<desc>`, optional `<extensions>`,
  one or more `<trkseg>`.
- `<trkpt lat=".." lon="..">` with child `<ele>` (float metres) and `<time>`
  (ISO-8601 UTC, with **or without** fractional seconds).
- Samples have **no `<wpt>` / `<rte>`** — out of scope for now; tolerate/skip if
  present.
- **Preserve track color & `<desc>` on import.** Color lives in `<extensions>`:
  Gaia uses a `gpx_style` `<line><color>` block, MyTracks uses
  `<topografix:color>` — read both into one internal color field. `<desc>` may be
  CDATA-wrapped. Round-trip them back out on re-export.

### Identity / dedup
- **No dedup for this run.** Every `<trk>` imports as a new entry, even if a
  same-named entry already exists (re-importing the same file duplicates — fine
  for now).
- **Entry name = the track's `<name>` verbatim** (exact string from the GPX, no
  normalization/cleanup). E.g. `Mindanao 2022-12-27 09:22`.

### Stats (item-detail page)
Derive from `<trkpt>` data: distance (from lat/lon), duration (first→last
`<time>`), point count, elevation gain/loss & min/max (from `<ele>`), avg/max
speed. Aligns with the MVP track-stats list (distance, duration, avg/max speed,
elevation gain/loss).

### Re-export
- Export a single entry as **GPX 1.1** (one `<trk>`).
- Preserve track `<name>`, `<desc>`, color, and point `lat`/`lon`/`<ele>`/`<time>`.
- (Multi-track / folder-level export deferred with folders.)

## Performance
- **Not a real concern at this scale.** The biggest sample is 3.6 MB / 37,775
  points across 15 tracks. Gaia GPS and the `track/` POC both handled multiple
  such files with no trouble — and that was while *rendering* them (Phase 7); we
  only parse + store here.
- **Store full resolution** — no point dropping/simplification at import. (Any
  thinning belongs to Phase 7 rendering, not storage.)
- **Proven approach from `track/`:** parse GPX with `package:xml`
  (`XmlDocument.parse`), insert points via a **batched SQLite transaction**
  (`db.batch()` → `commit(noResult: true)`) so 37k inserts are one commit, not
  37k. `track/` even parsed synchronously without jank.
- **Optional hardening only if a file ever stutters:** move parse to a background
  isolate (`compute`) and/or show import progress. Not needed for the known data.
- **Compute stats once at import**, store them on the entry, so the list/detail
  pages never recompute.

## Open questions
- _(none open)_

## Notes
- `~/git/track` had import/export, but its correctness was **unverified** —
  mine for reference, then re-verify.
- Sample data: `~/Downloads/temp/mindanao.gpx` (Gaia, one file) and
  `~/Downloads/temp/2022-12-mindanao/` (MyTracks, per-track files) — same trip.
