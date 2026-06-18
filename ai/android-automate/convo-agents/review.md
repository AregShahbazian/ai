---
id: convo-agents
title: Per-conversation reply agents — review / verification
status: implemented (dry-run), pending on-device verification
branch: feature/convo-agents
---

## Round 1: initial implementation (2026-06-18)

Implemented in worktree `~/git/android-automate-convo-agents` on
`feature/convo-agents`. Left uncommitted for the user to test.

### Files
- `src/common.py` — shared u2 helpers (nav, dump, parse, inbox rows).
- `src/convo_agents.py` — orchestrator + `ConvoAgent` + settings/memory/LLM.
- `scripts/convo_agents.sh` — executable wrapper.
- `config/global.example.json`, `config/convos/example.json.sample`.
- `requirements.txt` (`uiautomator2`, `anthropic`), `.gitignore` (restored
  `screenshots/`; added `__pycache__/`, `data/`, secret config).

### Verification

1. ✅ `py_compile` clean for both modules.
2. ✅ `import common` clean.
3. ✅ `./scripts/convo_agents.sh -h` prints usage + all defaults.
4. ✅ Settings merge unit test: per-convo overrides win, `rules`+`extra_rules`
   merge, `None` convo falls back to global; `slug()` stable.
5. ✅ `read_convo_messages` classifies sender by x-alignment; header + EditText
   excluded; sorted top→bottom. `new_messages_since` handles first-contact,
   marker-present, and marker-scrolled-away.
6. ✅ Queue (`enqueue`/`load_outbox`/`save_outbox`): re-composing replaces the
   convo's *pending* entry without clobbering `approved`/`sent` ones.
7. ⬜ **On-device (needs phone + `ANTHROPIC_API_KEY`):** `--probe` writes a
   non-empty XML and the printed messages match the screen.
8. ⬜ **On-device compose:** one tracked convo → composes a reply, prints
   `[queued—pending]`, appends to `data/outbox.json`, writes
   `data/memory/<id>.json`, device untouched.
9. ⬜ **On-device flush (opt-in):** set an entry's `status` to `approved`, run
   `--flush`; reply is typed and the send affordance hit; entry → `sent`, memory
   `last_seen → me`. If the send-button heuristic misses, capture its
   resource-id via `--probe` and set `send_button_id` in global config.
10. ⬜ Turn detection: convo whose last bubble is ours is skipped with no API call.

### Known limitations / open questions
- Convo identity = `slug(name)`; collisions possible for duplicate names, and
  accented characters get flattened. Fold in age/location if it bites.
- Message-bubble reading is alignment-heuristic (no confirmed resource IDs).
  `--probe` exists to capture real IDs and tune if the heuristic misreads.
- Send happens only via `--flush` against hand-approved `outbox.json` entries
  (queue-for-review model). Send-button detection is heuristic; `send_button_id`
  override provided.
- Existing `tantan_inbox.py` / `tantan_unmatch_all.py` not yet migrated to
  `common.py` (left to avoid regressions) — follow-up.
