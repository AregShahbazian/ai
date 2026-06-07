# Orion — feature backlog

A bag of feature ideas captured via `/feature`. Unsorted, unplanned — a holding
pen so nothing gets lost. Promote items into real phases/PRDs when they're picked
up; check them off (`[x]`) or remove them once shipped.

## Backlog

- [ ] Volume buttons control map zoom in/out  <!-- 2026-06-06 -->
      Togglable via a setting. Already implemented in `track/` — reference that.
- [ ] Keep screen on while Orion is the focused app  <!-- 2026-06-06 -->
      Setting to prevent screen dimming/sleep on inactivity. Likely already implemented in `track/` — reference that.
- [ ] Show "reset orientation" button when map is panned/rotated  <!-- 2026-06-06 -->
      Appears below the compass button, disappears when re-focused. Implemented in `track/` but positioning logic may need rethinking for Orion.
- [ ] Export route/track (partially) as an animated GIF  <!-- 2026-06-06 -->
      GIF is a map render that moves as if navigating through part of the track/route. Map choice, custom tags, etc. Future feature.
- [ ] DevOps agent specialized for devops tasks  <!-- 2026-06-06 -->
- [ ] Bottom navbar on all non-map pages  <!-- 2026-06-07 -->
      Once on settings/tracks/etc., a bottom navbar makes moving between pages easier. Not shown on the map page.
- [ ] Long-press followme icon (OFF/FOLLOW modes) also zooms to default level  <!-- 2026-06-07 -->
      Mobile. Long-press in OFF or FOLLOW mode should let the default center-me action (scroll to user, rotate/pan) play out, then zoom to the app-load default zoom level — one fluent animation. In FOLLOW+HEADING mode, long-press is just a regular toggle to OFF (no zoom logic).
- [ ] Folder structures for organizing tracks/routes/etc.  <!-- 2026-06-07 -->
      Already in `track/` — reference that. Custom user-created folders, plus folders auto-created when importing multiple tracks/routes/others from one file. Some import cases (e.g. multiple files in one upload) may prompt the user to create a folder for them.
