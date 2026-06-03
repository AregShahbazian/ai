# Discussion — Decentralization & storage priority for Orion

**Date:** 2026-06-03
**Mode:** discussion (answers-only)
**Outcome:** Decentralized P2P sharing is **NOT a priority** for Orion. Build local-first + central sync; treat P2P as a post-MVP experiment.

## Architecture sketch discussed

Tiered local-first model:
1. **Offline-first** — local store is the working source of truth; full function with no connectivity.
2. **Distributed / P2P network** — opportunistic sync between peers when reachable.
3. **Central servers** — durability guarantee + relay/discovery/bootstrap. Optional infra, not the source of truth.

Sharing model: **private-by-default, opt-in sharing.**
- Base map tiles = third-party (OpenFreeMap / OSM), a shared commons.
- User-generated **tracks & routes** = shared explicitly by the user.
- Sharing transport (P2P vs server vs both) = **TBD**.

## Landscape (web-verified)

- Centralized download-for-offline trail apps: **Gaia GPS** (the competitor), Organic Maps, OsmAnd, HiiKER, Trailforks, Hiking Project.
- **Mapeo** (Digital Democracy) = the real P2P mapping system: osm-p2p, USB/Wi-Fi sync, crypto-verified logs, **no central server** — but niche (indigenous territory mapping), and deliberately has no central tier.
- The exact blend Orion wants (consumer trail app, offline-first, P2P mesh, *with* central durability/relay + opt-in sharing) does **not** exist as a product. Mapeo is the nearest architecture; Gaia the nearest product.

## Why the combo doesn't exist

1. **Business model / moat** — incumbents centralize because the cloud is the monetization lever + data-network-effect moat. *Correction:* monetization **can** coexist with decentralized storage (Obsidian Sync/Publish, Tailscale, Ditto) — it's *harder to defend*, not impossible.
2. **Users don't feel the pain** — most have connectivity; "download region for offline" is good enough → no market pull.
3. **Hard tech, thin payoff** — P2P sync (CRDT, peer discovery, NAT traversal, bandwidth, incentives) is expensive; if central servers exist anyway, the mesh adds complexity for marginal benefit.
4. **Tiles are third-party** — the bulky data is OSM; only lightweight tracks/routes truly need syncing.

## Cost reasoning (the core conclusion)

- **Map tiles need no durability guarantee** — they're third-party and *reproducible*; if your copy vanishes, re-fetch from source. That's a *serving/bandwidth* cost, not a durability cost.
- Serving static tiles is exactly what **CDNs** already do cheaply (edge cache, ~99% hit rate). P2P tile-offload competes against an already-cheap solution while adding complexity.
- **Relaying through your servers does NOT save bandwidth** — relayed bytes still pass through you (and cost you). Savings come only from *direct* peer transfers; relay/TURN is the costly fallback for mobile NAT.
- P2P frictions for a trail app: mobile peers won't seed (data caps/battery); locality problem — remote areas (the core use case) have no nearby peers to serve.
- **Gaia is expensive not because tile-serving is costly** but due to *licensed premium imagery* (USGS, NatGeo Trails Illustrated, satellite), value-based subscription pricing, and Outside+ bundling. (Reasoned, not from their actual financials.)

## Relevant knowledge: local-first / CRDTs

Local-first = on-device source of truth, works offline, merges across devices without a central authority. Enabling tech: **CRDTs** (conflict-free merge of concurrent offline edits). Libraries: **Automerge**, **Yjs**, **Ditto**, **Earthstar**. Directly relevant — Orion's "two devices edit/record offline then sync" problem is the local-first problem. The POC sidestepped it via a Supabase mirror; Orion's sharing model won't be able to.

## Decisions

- Decentralized P2P sharing = **post-MVP**, not MVP scope.
- Core = **local-first + central CRDT-style sync**; central servers for durability of user content + relay/discovery.
- `~/git/track` (POC) = **reference/fallback implementation** — consult its working MapLibre + tile-download + Supabase sync when building Orion; free to redesign.

## Open questions

1. Sharing transport: P2P / server / both — **TBD**.
2. Central-server choice (keep Supabase vs. alternative) — **decide later**.
3. Is true no-infrastructure offline (Mapeo-style field use) an actual target, or is "download-then-roam" enough?

## Sources

- Mapeo docs — https://docs.mapeo.app/overview/about-mapeo
- Mapeo P2P sync — https://docs.mapeo.app/overview/about-mapeo/peer-to-peer-and-mapeo-sync
- OSM without servers (Digital Democracy) — https://wp.digital-democracy.org/openstreetmap-without-servers-part-2-a-peer-to-peer-osm-database/
- Organic Maps — https://organicmaps.app/
- HiiKER — https://hiiker.app/free-offline-maps-with-hiiker
- Best hiking apps 2026 (The Trek) — https://thetrek.co/best-hiking-navigation-apps-of-2026/
