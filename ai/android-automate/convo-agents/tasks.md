---
id: convo-agents
title: Per-conversation reply agents — tasks
status: draft
branch: feature/convo-agents
---

## Task 1 — `src/common.py` (shared u2 helpers)

Extract the helpers the new script needs (existing scripts untouched):
`PACKAGE`, resource-id constants, `parse_nodes`, `by_id`, `node_center`,
`first_text`, `poll_until`, `dump_when_ready`, `ensure_messages_screen`,
inbox-row reader.

**Verify:** `python3 -c "import sys; sys.path.insert(0,'src'); import common"` imports clean.

## Task 2 — settings + memory layer (in `convo_agents.py`)

- `load_global()`, `load_convo(convo_id)`, `effective_settings()` (merge, `rules`+`extra_rules`).
- `slug(name)` → convo_id.
- `load_memory(convo_id)` / `save_memory(...)`.
- `config/global.example.json`, `config/convos/.gitkeep`, `.gitignore`.

**Verify:** unit-call the merge with a fake global+convo, assert per-convo wins and rules merge.

## Task 3 — convo screen reading + turn detection

- `read_convo_messages(d)` → `[{"sender": "me"|"match", "text": ...}]` via
  alignment heuristic from one dump.
- `last_sender()` / `new_messages_since(memory, msgs)`.
- `--probe` mode: dump one convo's hierarchy to `logs/convo_probe_<ts>.xml`.

**Verify:** `--probe` on the device writes a non-empty XML; printed messages list
matches what's on screen (manual eyeball during test run).

## Task 4 — the agent turn (Anthropic call)

- `build_system_prompt`, `render_new_messages`, `DECISION_SCHEMA`.
- `ConvoAgent.run(new_msgs)` → decision dict; updates summary/facts.
- Lazy-import `anthropic`; clear error if SDK missing or key unset.

**Verify:** with a stub conversation and a real key, returns valid JSON with
`should_reply`/`reply`/`summary`/`facts`.

## Task 5 — orchestrator + sending gate

- `ensure_messages_screen` → resolve tracked set (config files / `--convo` / `--all`).
- For each: open convo (`dump_when_ready` on header), read, turn-detect, run agent,
  dry-run print or (with `send`+`--send`) type+send, update memory, back to list.
- Empty convo → opener path when `open_empty`.
- `argparse` with `-h`: `--convo`, `--all`, `--send`, `--probe`, `--skip`.
- Tee log to `logs/` like `tantan_inbox.py`.

**Verify:** dry-run over one tracked convo prints a composed reply and writes memory,
device is not mutated.

## Task 6 — `scripts/convo_agents.sh` + requirements

- Wrapper forwarding args; `chmod +x`; `#!/usr/bin/env bash`.
- `requirements.txt`: `uiautomator2`, `anthropic`.

**Verify:** `./scripts/convo_agents.sh -h` prints usage with all defaults.

## Task 7 — review doc + handoff

Write `review.md` checklist; report config + test-run instructions to the user.
