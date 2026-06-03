---
name: project-orion-decentralization-deprioritized
description: Orion decision — P2P/decentralized sharing is post-MVP; build local-first + central sync
metadata: 
  node_type: memory
  type: project
  originSessionId: 7bd505c8-36dd-4658-9ab4-79cc8862d6fb
---

For the Orion mapping app, decentralized P2P sharing is **not a priority** (decided 2026-06-03). The core is **local-first + central CRDT-style sync**; central servers provide durability for user-generated content plus relay/discovery. P2P mesh is a post-MVP experiment.

Key reasoning: base map tiles are third-party (OSM/OpenFreeMap) and reproducible, so they need no durability guarantee — serving them is a CDN-cheap bandwidth cost, not a storage cost. P2P tile-offload competes with already-cheap CDNs and has mobile-seeding/locality frictions; relaying through your own servers doesn't save bandwidth. Closest existing systems: Mapeo (niche P2P) and Gaia GPS (centralized competitor). Local-first/CRDT tech (Automerge, Yjs, Ditto, Earthstar) is relevant for syncing user tracks/routes.

Full discussion: `~/ai/orion/discussions/2026-06-03-decentralization-priority.md`. See also [[project-orion-mapping-app]].
