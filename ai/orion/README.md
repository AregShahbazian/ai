# Orion — Workflow Root (Overview)

Root index for Orion's planning docs. Start here. Orion is the real mapping app
(GPS tracking + offline maps); `~/git/track` was the buggy POC (inspiration only).

## Canonical docs
- **MVP definition** → [`mvp.md`](mvp.md) — the first-release scope.
- **Feature backlog** → [`backlog.md`](backlog.md) — unsorted bag of feature ideas (`/feature`).
- **Flutter cheatsheet** → [`cheatsheet.md`](cheatsheet.md) — setup / daily-dev / build commands.
- **Bug fixes** → [`bugfix/`](bugfix/) — `.fix.md` investigation notes.
- **Deps / reference** → [`deps/`](deps/)

## Phases

Each release is delivered in phases. A **phase dir** (`phase-N/`) contains one or
more **task dirs**, and **each task** holds its own workflow docs
(`prd.md` → `design.md` → `tasks.md` → `review.md`).

### Phase 1 — Map Shell (single full-screen map, Philippines focus)
- **Map Shell** → [`phase-1/map-shell/prd.md`](phase-1/map-shell/prd.md) (`id: phase-1-map`) — ✅ **implemented & verified on device (2026-06-04)**; branch `phase-1-map`. (Launcher name/icon to confirm on a release install.)

### Phase 2 — My Location (+ map polish)
User location, plus all the location/map-polish tasks already scoped below.
- **Safe-area HUD** → [`phase-2/safe-area-hud/prd.md`](phase-2/safe-area-hud/prd.md) (`id: phase-2-safe-area`) — ✅ **implemented & verified on device (2026-06-06)**; branch `feature/p2-safe-areas`. PRD only (design/tasks/review pending). Native compass/attribution inset into the safe area + a single `SafeArea` overlay layer for future Flutter HUD.
- **My Location** → [`phase-2/my-location/prd.md`](phase-2/my-location/prd.md) (`id: phase-2-my-location`) — ✅ **implemented & verified on device (2026-06-06)**; branch `feature/p2-my-location`. MapLibre blue dot, foreground permission via `permission_handler`; auto on native, tap-to-locate button on web. Full PRD→design→tasks→review.
- **Follow Me** → [`phase-2/follow-me/prd.md`](phase-2/follow-me/prd.md) (`id: phase-2-follow-me`) — ✅ **implemented & verified on device (2026-06-06)**; branch `feature/p2-follow-me`. Location FAB (ported from track) cycles Off → Follow → Follow+Heading via stock MapLibre tracking modes; manual pan auto-exits; reset button keeps follow. Full PRD→design→tasks→review.
- **Heading Arrow** → [`phase-2/heading-arrow/prd.md`](phase-2/heading-arrow/prd.md) (`id: phase-2-heading-arrow`) — planned (must-have). Directional cone on the dot via `MyLocationRenderMode.compass`.
- **Accuracy Circle** → [`phase-2/accuracy-circle/prd.md`](phase-2/accuracy-circle/prd.md) (`id: phase-2-accuracy-circle`) — planned (nice to have). Translucent halo sized to reported GPS accuracy.
- **Reset-orientation button** → [`phase-2/reset-orientation/prd.md`](phase-2/reset-orientation/prd.md) (`id: phase-2-reset-orientation`) — ✅ **implemented & verified on device (2026-06-06)**; branch `feature/p2-reset-orientation`. One Flutter `CompassButton` (replaces native compass) appears on rotate **or** tilt, resets both. Full PRD→design→tasks→review.

### Phase 3 — Interaction Controller (app-global command bus + interaction log)
- **Interaction Controller** → [`phase-3/interaction-controller/prd.md`](phase-3/interaction-controller/prd.md) (`id: phase-3-interaction-controller`) — planned. One app-global channel for every meaningful interaction: **dispatch** interactions programmatically (as if the user did them) and **observe + locally log** the last N. Realizes the Command-bus + interceptor pattern with a closed, hierarchical interaction taxonomy (`domain.subject.action`). Substrate for diagnostics (attach recent interactions to bug reports) and scripted/automated testing. PRD only.

### Phase 4 — Navigation (app shell)
A new full screen, reached via a HUD button — the home for what comes later
(settings, tracks, routes). This phase only stands up the screen + navigation
plumbing; the sections it hosts arrive in later phases. Models its
screen-navigation interactions in the Phase 3 taxonomy from the start. No PRDs yet.

### Phase 5 — Import / export tracks
Import existing **Gaia GPS exports** (and re-export them). Imported tracks get
their own page and are **listed**: list items show a **summary**, the item-detail
page shows **full stats**. **No map rendering of tracks yet.** `~/git/track` had
import/export but its correctness was unverified — mine for reference, re-verify.
No PRDs yet.

### Phase 6 — Render tracks on map
Draw imported tracks on the map. Must be **efficient and scalable to much more
data** than a single track: use the efficient drawing callback/API `track` used to
keep the map smooth with multiple large tracks, and avoid unnecessary
re-renders/repaints. Confirm our impl is at least as efficient. No PRDs yet.

### Phase 7 — Track recording
Record tracks live: new HUD button(s) to start/stop, store tracks **locally**.
**No account/backend yet.** More details to follow. No PRDs yet.

> Note: "Phase 4 — Navigation" is **app-screen navigation**, not GPS routing/A→B
> routing, which remains out of scope (see [`mvp.md`](mvp.md)).

## Discussions

Chronological. The **Ideas to realize** column flags discussions whose
`## Ideas to realize` section contains work that still needs implementing — those
are the links to follow when picking up new work.

| Date | Topic | Doc | Ideas to realize |
|------|-------|-----|------------------|
| 2026-06-03 | Decentralization / storage priority (P2P = post-MVP) | [`discussions/2026-06-03-decentralization-priority.md`](discussions/2026-06-03-decentralization-priority.md) | yes |
| 2026-06-03 | MVP v0.1 scope (**superseded** by `mvp.md`) | [`discussions/2026-06-03-mvp-v01-scope.md`](discussions/2026-06-03-mvp-v01-scope.md) | historical |
| 2026-06-04 | MVP expansion, app identity, phases, Phase 1 | [`discussions/2026-06-04-mvp-expansion-and-phase1.md`](discussions/2026-06-04-mvp-expansion-and-phase1.md) | yes |
| 2026-06-04 | Dev loop (web-first) & map plugin (`maplibre_gl` v0.26.1) | [`discussions/2026-06-04-dev-loop-and-map-plugin.md`](discussions/2026-06-04-dev-loop-and-map-plugin.md) | yes |
| 2026-06-04 | Devbox & driving Orion dev from the phone | [`discussions/2026-06-04-devbox-and-phone-access.md`](discussions/2026-06-04-devbox-and-phone-access.md) | yes |
| 2026-06-04 | Runtime-state inspection in dev flow (brainstorm) | [`discussions/2026-06-04-runtime-state-inspection.md`](discussions/2026-06-04-runtime-state-inspection.md) | yes (deferred) |

## Backlog — ideas to realize (with source)

Pulled from discussion `## Ideas to realize` sections. Implement → then check the
box and reference the source discussion in the commit/PRD.

- [x] **Phase 1: Map Shell** — Flutter + `maplibre_gl` v0.26.1, OpenFreeMap `liberty`, Philippines bbox, all gestures, offline indicator → ✅ done, verified on device 2026-06-04 → *2026-06-04 mvp-expansion / dev-loop*
- [ ] **Track recording** — start/stop/pause, reliable background/screen-off (MVP acceptance gate) → *2026-06-04 mvp-expansion*
- [ ] **Track viewing** — stats, polyline, saved-tracks list (toggle/rename/delete) → *2026-06-04 mvp-expansion*
- [ ] **Export** — GPX & KML → *2026-06-04 mvp-expansion*
- [ ] **Offline map storage** — rectangle-select region download, downloaded vs downloading, seamless offline use (test on phone) → *2026-06-04 mvp-expansion*
- [ ] **App logo / branding** — integrate when provided → *2026-06-04 mvp-expansion*
- [ ] **Dev workflow** — Flutter web as primary debug target; phone for location/recording/offline → *2026-06-04 dev-loop*
- [ ] **Runtime-state inspection** — pick mechanism once app runs (DevTools / Playwright+`window` / VM Service / mobile endpoint) → *2026-06-04 runtime-state-inspection*
- [ ] **iOS groundwork** — keep platform code isolated; no Apple builds yet → *2026-06-04 dev-loop*
- [ ] **Plugin re-evaluation (future)** — revisit newer `maplibre` plugin → *2026-06-04 dev-loop*
- [ ] **Self-host PH tiles (post-MVP1)** — before real-scale launch, host OpenFreeMap weekly full-planet MBTiles for the offline feature instead of scraping the public server → *mvp.md Q4*
- [ ] **orion-dev-box** (separate repo/agent) — Linux devbox hosting Claude Code on demand + build/serve APK at a private URL for phone testing (local-first → VPS, Tailscale) → *2026-06-04 devbox-and-phone-access*
- [ ] **APK distribution to testers** — evaluate Firebase App Distribution / Play internal testing vs plain URL → *2026-06-04 devbox-and-phone-access*
- [ ] **P2P / decentralized sharing (post-MVP)** — local-first + central sync first → *2026-06-03 decentralization*

## Key decisions (quick reference)
- App: name **Orion**, `applicationId com.mby4m.orion` (track was unpublished).
- Stack: Flutter + **`maplibre_gl` v0.26.1** + SQLite (Drift TBD); **web-first** dev, phone for native.
- Decentralization: **post-MVP**; local-first + central sync.
- iOS: deferred, kept clean.
- Export: **GPX first** (KML/others later). Offline UX mirrors `track`.
- Tiles: OpenFreeMap public server for **MVP1**; **self-host PH tiles post-MVP1**.
- Background recording target: **wide range of common PH Android phones** (incl. aggressive OEMs).

(Durable decisions also live in memory — see `MEMORY.md` pointers prefixed `orion:`.)
