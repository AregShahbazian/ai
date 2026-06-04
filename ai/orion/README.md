# Orion — Workflow Root (Overview)

Root index for Orion's planning docs. Start here. Orion is the real mapping app
(GPS tracking + offline maps); `~/git/track` was the buggy POC (inspiration only).

## Canonical docs
- **MVP definition** → [`mvp.md`](mvp.md) — the first-release scope.
- **Deps / reference** → [`deps/`](deps/)

## Phases

Each release is delivered in phases. A **phase dir** (`phase-N/`) contains one or
more **task dirs**, and **each task** holds its own workflow docs
(`prd.md` → `design.md` → `tasks.md` → `review.md`).

### Phase 1 — Map Shell (single full-screen map, Philippines focus)
- **Map Shell** → [`phase-1/map-shell/prd.md`](phase-1/map-shell/prd.md) (`id: phase-1-map`) — PRD done; design/tasks pending

### Phase 2+ — TBD
- Recording → viewing → export → offline; sequencing not yet defined.

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
| 2026-06-04 | Runtime-state inspection in dev flow (brainstorm) | [`discussions/2026-06-04-runtime-state-inspection.md`](discussions/2026-06-04-runtime-state-inspection.md) | yes (deferred) |

## Backlog — ideas to realize (with source)

Pulled from discussion `## Ideas to realize` sections. Implement → then check the
box and reference the source discussion in the commit/PRD.

- [ ] **Phase 1: Map Shell** — Flutter + `maplibre_gl` v0.26.1, OpenFreeMap `liberty`, Philippines bbox, all gestures, offline indicator, web-first → *2026-06-04 mvp-expansion / dev-loop*
- [ ] **Track recording** — start/stop/pause, reliable background/screen-off (MVP acceptance gate) → *2026-06-04 mvp-expansion*
- [ ] **Track viewing** — stats, polyline, saved-tracks list (toggle/rename/delete) → *2026-06-04 mvp-expansion*
- [ ] **Export** — GPX & KML → *2026-06-04 mvp-expansion*
- [ ] **Offline map storage** — rectangle-select region download, downloaded vs downloading, seamless offline use (test on phone) → *2026-06-04 mvp-expansion*
- [ ] **App logo / branding** — integrate when provided → *2026-06-04 mvp-expansion*
- [ ] **Dev workflow** — Flutter web as primary debug target; phone for location/recording/offline → *2026-06-04 dev-loop*
- [ ] **Runtime-state inspection** — pick mechanism once app runs (DevTools / Playwright+`window` / VM Service / mobile endpoint) → *2026-06-04 runtime-state-inspection*
- [ ] **iOS groundwork** — keep platform code isolated; no Apple builds yet → *2026-06-04 dev-loop*
- [ ] **Plugin re-evaluation (future)** — revisit newer `maplibre` plugin → *2026-06-04 dev-loop*
- [ ] **P2P / decentralized sharing (post-MVP)** — local-first + central sync first → *2026-06-03 decentralization*

## Key decisions (quick reference)
- App: name **Orion**, `applicationId com.mby4m.orion` (track was unpublished).
- Stack: Flutter + **`maplibre_gl` v0.26.1** + SQLite (Drift TBD); **web-first** dev, phone for native.
- Decentralization: **post-MVP**; local-first + central sync.
- iOS: deferred, kept clean.

(Durable decisions also live in memory — see `MEMORY.md` pointers prefixed `orion:`.)
