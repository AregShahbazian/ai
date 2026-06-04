---
name: project-orion-mapping-app
description: orion is the real mapping app; ~/git/track was the POC
metadata: 
  node_type: memory
  type: project
  originSessionId: 7bd505c8-36dd-4658-9ab4-79cc8862d6fb
---

`~/git/orion` is the real/production mapping app. `~/git/track` was a proof-of-concept (Flutter + Supabase) that preceded it (buggy; inspiration only, not a foundation).

As of 2026-06-04 `~/git/orion` is its own git repo (remote `github.com:AregShahbazian/orion.git`, single `Initial commit`, has `CLAUDE.md`). The workflow folder `~/ai/orion/` exists (`mvp.md`, `discussions/`, `deps/`).

**App identity (locked):** public name = **Orion** (final). Android `applicationId`/namespace = **`com.mby4m.orion`**, reused from the `track` POC, which was never published (id is free). Permanent once published to Play.

**Why:** Avoid confusing the two repos, and don't mistake the `~/` workflow repo's git history for orion's.
**How to apply:** Treat orion as the canonical app; mine `track` only for reference/intent. Build on the most stable/proven stack & dep versions; propose better approaches where track's were buggy. See [[project-orion-mvp-v01]], [[project-orion-decentralization-deprioritized]].
