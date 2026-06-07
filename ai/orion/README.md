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
- **Heading Arrow** → [`phase-2/heading-arrow/prd.md`](phase-2/heading-arrow/prd.md) (`id: phase-2-heading-arrow`) — ✅ **implemented & verified**; branch `feature/p2-heading-accuracy`. Stock `MyLocationRenderMode.compass` (gated on `enabled`); heading cone on native, plain dot on web. Full PRD→design→tasks→review.
- **Accuracy Circle** → [`phase-2/accuracy-circle/prd.md`](phase-2/accuracy-circle/prd.md) (`id: phase-2-accuracy-circle`) — ✅ **implemented & verified**; branch `feature/p2-heading-accuracy`. No code — MapLibre draws the metric ring by default (native) + web `showAccuracyCircle`; visible at street zoom. Full PRD→design→tasks→review.
- **Reset-orientation button** → [`phase-2/reset-orientation/prd.md`](phase-2/reset-orientation/prd.md) (`id: phase-2-reset-orientation`) — ✅ **implemented & verified on device (2026-06-06)**; branch `feature/p2-reset-orientation`. One Flutter `CompassButton` (replaces native compass) appears on rotate **or** tilt, resets both. Full PRD→design→tasks→review.
- **Dev Logging** → [`phase-2/dev-logging/prd.md`](phase-2/dev-logging/prd.md) (`id: phase-2-dev-logging`) — ✅ **implemented & verified**; branch `feature/p2-dev-logging`. One structured `devLog(scope, data)` path tagged `orion.<scope>` — collapsable in the web console, DevTools Logging tab on Android — so debugging is the same motion everywhere and nothing is lost to flat text. `avoid_print` enforced. Full PRD→design→tasks→review.

### Phase 3 — Interaction Controller (app-global command bus + interaction log)
- **Interaction Controller** → [`phase-3/interaction-controller/prd.md`](phase-3/interaction-controller/prd.md) (`id: phase-3-interaction-controller`) — ✅ **implemented (done for now)**; branch `feature/p3-interaction-controller` (pushed). One app-global channel for every meaningful interaction: **dispatch** programmatically (as if the user did them) and **observe + locally log** the last N. Hand-rolled command bus + ring-buffer interceptor (decided against `flutter_bloc` — Orion is plain `ChangeNotifier`), closed hierarchical taxonomy (`domain.subject.action`). HUD/map interactions retrofitted to dispatch through it; web-only dev console bridge (`orion.dispatch(...)`). **Map camera gestures** (`map.{zoom,scroll,rotate,tilt}.changed`) captured on settle via a record-only `observe()` half (MapLibre runs them natively — nothing to execute) and re-dispatchable to drive the camera. In-memory only — persistence/export deferred. Full PRD→design→tasks→review.

### Phase 4 — HUD (shared HUD controls)
One consistent style for every map-HUD control, so new buttons (the Phase 5
settings cog, future recording controls) reuse one base instead of reinventing it.
- **Shared HudButton** → [`phase-4/hud-button/prd.md`](phase-4/hud-button/prd.md) (`id: phase-4-hud-button`) — ✅ **implemented**; branch `feature/p4-hud-button`. One reusable HUD-button base (compass's 44 dp circle + shadow as the fixed style; per-button bg/fg color); migrated `CompassButton` + `LocationFab` onto it so all HUD controls match. Also landed: **edge-to-edge transparent system bars** (map fills behind the nav bar; SafeArea keeps the HUD clear) and the **location FAB pinned bottom-right, lifted clear of the OpenFreeMap attribution** (forced to the compact "ⓘ" on web so it never collides). Full PRD→design→tasks→review.

### Phase 5 — Navigation (app shell)
Stand up the app shell: leave the live map for a full-screen page (first one:
**Settings**, empty) and come back, with the map kept alive the whole time.
- **Navigation** → [`phase-5/navigation/prd.md`](phase-5/navigation/prd.md) (`id: phase-5-navigation`) — 📝 **planned (PRD→design→tasks)**. `go_router` `ShellRoute` with the map persistent in the shell builder (never re-mounted); pages render over it. HUD **cog** button → `/settings` (empty placeholder). Nav modelled in the Phase 3 taxonomy both ways (`hud.settings.tap`, `nav.screen.open/close`); `push` for opening, back = `nav.screen.close` (a pop) so Android back is intuitive and modals close on back. **No custom navigation plumbing** — off-the-shelf go_router. See design's build-vs-buy verdict.

### Phase 6 — Import / export tracks
Import existing **Gaia GPS exports** (and re-export them). Imported tracks get
their own page and are **listed**: list items show a **summary**, the item-detail
page shows **full stats**. **No map rendering of tracks yet.** `~/git/track` had
import/export but its correctness was unverified — mine for reference, re-verify.
No PRDs yet.

### Phase 7 — Render tracks on map
Draw imported tracks on the map. Must be **efficient and scalable to much more
data** than a single track: use the efficient drawing callback/API `track` used to
keep the map smooth with multiple large tracks, and avoid unnecessary
re-renders/repaints. Confirm our impl is at least as efficient. No PRDs yet.

### Phase 8 — Track recording
Record tracks live: new HUD button(s) to start/stop, store tracks **locally**.
**No account/backend yet.** More details to follow. No PRDs yet.

### Phase 9 — Language support (i18n)
Localize **as much of the app as possible** — **at least 2 languages** to start
(**English** + **Tagalog/Filipino**, matching the PH focus; `~/git/track` already
had `app_en.arb` / `app_tl.arb` to mine). Set up `flutter_localizations` + `intl`
with ARB message files, **externalize every user-facing string** (the lone
`_kLocationDeniedMessage` const today folds in here), follow the device locale with
an optional in-app override, and keep it easy to add more languages later. Built so
any new feature ships its strings localized from the start. No PRDs yet.

> Note: "Phase 5 — Navigation" is **app-screen navigation**, not GPS routing/A→B
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
| 2026-06-06 | Dev-mode log monitoring (web + Android), one structured path | [`discussions/2026-06-06-dev-log-monitoring.md`](discussions/2026-06-06-dev-log-monitoring.md) | yes (partly done) |

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
- [x] **Structured dev logger `devLog`** — one tagged path, collapsable web / DevTools Logging on Android → ✅ done 2026-06-06 (`feature/p2-dev-logging`) → *2026-06-06 dev-log-monitoring*
- [ ] **Log funnel enforcement** — `avoid_print: error` (done); later discourage direct `dart:developer` outside `core/log` → *2026-06-06 dev-log-monitoring*
- [ ] **Log levels / severity + timestamps** — extend `devLog` without breaking the `(scope, data)` call site → *2026-06-06 dev-log-monitoring*
- [ ] **Android fold-tree log inspection** — in-app overlay or route native logs to the browser console (VM service) for web-like expand/collapse → *2026-06-06 dev-log-monitoring*
- [ ] **Bug-report capture** — attach the last N records to bug reports; overlaps Phase 3 interaction log → *2026-06-06 dev-log-monitoring*
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
- **Interactions:** every new user action wires through the `InteractionController` **both ways** — captured (`dispatch`/`observe`) and programmatically dispatchable; reachable remotely via `window.orion` (web) and `ext.orion.*` VM service extensions (native, `scripts/mobile/orion.sh`). No inline-handler bypass. See `phase-3/interaction-controller/design.md`.
- **Persistent state, transient screens:** expensive, long-lived state (the map + controller, and later track/route/waypoint data) is owned by a persistent root shell, created **once**; navigation never unmounts/re-creates it. The map stays alive across navigation (no remount/reload/re-fit); data pages **never fetch on mount** — they observe a long-lived controller that fetched once, so navigating to/from them is instant and re-fetch only happens the first time. Tearing the map down for a specific page is an explicit, per-destination opt-out, never the default. (`track`'s laggy nav came from violating this.) See `phase-5/navigation/prd.md`.

(Durable decisions also live in memory — see `MEMORY.md` pointers prefixed `orion:`.)
