---
name: project-orion-mapping-app
description: orion is the real mapping app; ~/git/track was the POC
metadata: 
  node_type: memory
  type: project
  originSessionId: 7bd505c8-36dd-4658-9ab4-79cc8862d6fb
---

`~/git/orion` is the real/production mapping app. `~/git/track` was a proof-of-concept (Flutter + Supabase) that preceded it.

As of 2026-06-03 `~/git/orion` is essentially empty (only `.claude/`) and is not yet its own git repo — `git` commands there resolve up to the `~/` workflow repo. No `~/ai/orion/` workflow folder exists yet.

**Why:** Avoid confusing the two repos, and don't mistake the `~/` workflow repo's git history for orion's.
**How to apply:** Treat orion as the canonical app going forward; mine track only for reference/POC learnings.
