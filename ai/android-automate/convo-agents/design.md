---
id: convo-agents
title: Per-conversation reply agents — design
status: draft
branch: feature/convo-agents
---

## Overview

One Python entry-point (`convo_agents.py`) does everything synchronously:

```
orchestrator → for each tracked convo (one at a time):
    open convo → read new messages → ConvoAgent.run() → optional send → back
```

The "agent" is not a separate process — it's a `ConvoAgent` object that owns one
convo's memory + merged settings and makes one Anthropic API call per turn. This
matches the repo's existing single-script style and the "all sync" decision.

## Wireup — reuses the proven inbox patterns

Built directly on `tantan_inbox.py` / `tantan_unmatch_all.py`, which already
work on this device:

- `u2.connect()`, `ensure_messages_screen(d)` (back out, tap Messages tab, poll).
- Inbox list rows from one dump: `title_big` (name), `message_big` (preview /
  `Matched…` for empty), `time_big` (timestamp).
- `poll_until` / `dump_when_ready` for transitions (no `sleep`, no
  `exists(timeout>0)`), coordinate clicks from `node_center` — all per the
  performance rules in CLAUDE.md.
- These shared helpers move to **`src/common.py`** (this is the third consumer,
  which the CLAUDE.md rule says triggers extraction). The existing two scripts
  are left untouched in this iteration to avoid regressions; migrating them to
  `common.py` is a follow-up.

### Reading a conversation screen

Tantan's per-message resource IDs aren't known up front and reading the user's
real private convos to discover them needs their device + consent. So message
reading is **heuristic and ID-independent**, with optional ID overrides in
global settings:

- Dump the convo screen once. Candidate message nodes = nodes with non-empty
  `text` inside the scrollable list region, excluding the header (`title`), the
  input `EditText`, and known chrome.
- **Sender by horizontal alignment** (standard chat layout): bubble center-x
  `> screen_width/2` → outgoing (me); `< screen_width/2` → incoming (match).
  This needs no resource IDs and survives Tantan UI tweaks.
- A `tantan_convo_probe` mode dumps one convo's hierarchy to a file (read-only,
  no send) so the heuristic can be tuned / exact IDs captured later if needed.

### Turn detection (programmatic, before any API call)

Decided here: **heuristic, not the model.** The last bubble's sender is computed
from alignment. If the last message is outgoing (me) → not my turn → skip the
convo with no API call (saves tokens). If incoming (match) → my turn → call the
agent. Empty convo → opener path (settings-gated).

### Convo identity

`convo_id = slug(display_name)` (lowercase, non-alphanumerics → `-`). Matches the
name shown in the inbox list and on the convo header, so memory/settings
reattach across runs. Collision risk (two matches, same name) is accepted for
this iteration and listed as an open question; a future key could fold in
age/location already scraped by the inbox script.

## Memory

`data/memory/<convo_id>.json` (gitignored — runtime state):

```json
{
  "name": "Maria",
  "last_seen_text": "see you then!",
  "last_seen_sender": "match",
  "summary": "Matched 3 days ago. She's a nurse in Madrid, likes hiking...",
  "facts": ["nurse", "Madrid", "off on weekends"],
  "updated_at": "2026-06-18T15:00:00"
}
```

- **No full re-scrape:** only the on-screen messages are read each run. The
  agent is given the stored `summary` + `facts` as context plus the new messages
  (those after `last_seen_text`, matched in the visible list; if not found, the
  visible window is used and flagged). After the turn, `summary`/`facts` and the
  `last_seen_*` pointer are rewritten from the agent's structured output.
- First contact / missing memory → summary and facts start empty.

## Settings

Source of truth = JSON files. Effective settings = `{**global, **convo}` per key,
with list keys merged (`rules` + `extra_rules`).

`config/global.json` (git-tracked example committed as `global.example.json`):

```json
{
  "model": "claude-opus-4-8",
  "persona": "You are replying on behalf of Areg, a 30-something in Madrid.",
  "language": "English",
  "tone": "warm, curious, a little playful; never needy",
  "goal": "have a real conversation and, if it's going well, suggest meeting",
  "rules": ["never share contact info", "keep it under 2 sentences", "no emojis spam"],
  "max_reply_chars": 300,
  "open_empty": false,
  "send": false
}
```

`config/convos/<convo_id>.json` (user-authored; the orchestrator writes these
when the user gives verbal instructions):

```json
{
  "name": "Maria",
  "language": "Spanish",
  "tone": "playful",
  "extra_rules": ["she mentioned a trip — ask about it"],
  "send": true
}
```

- **Tracked set:** a convo is processed iff `config/convos/<id>.json` exists.
  `--convo "Name"` targets one; `--all` processes every visible convo using
  global settings only.

## Send gating — queue-for-review (decided 2026-06-18)

Composing **never touches the device**. The chosen gate is a two-step
review queue, not autonomous send:

1. A compose run writes each warranted reply to `data/outbox.json` as
   `{convo_id, name, reply, reason, status: "pending", queued_at}`. Re-composing
   the same convo replaces its *pending* entry; `approved`/`sent` entries are
   never clobbered.
2. The user reviews/edits `outbox.json` and sets `status: "approved"` on replies
   they want sent (editing the `reply` text is fine).
3. `--flush` opens each approved convo, types+sends the reply via `send_reply()`
   (input `EditText` + heuristic/`send_button_id` send button), marks it `sent`,
   and updates that convo's memory `last_seen → me`.

This satisfies the "never edit a connected device without asking" rule: the
device is only mutated during an explicit `--flush`, against entries the user
hand-approved.

## The agent turn (one Anthropic call)

`anthropic.Anthropic()` (reads `ANTHROPIC_API_KEY`), model from settings
(default `claude-opus-4-8`). Single structured call using `output_config.format`
(json_schema) — no tool loop needed:

```python
system = build_system_prompt(effective_settings, memory)   # persona, language, tone, goal, rules, summary, facts
user   = render_new_messages(new_msgs)                       # "match: ...\nme: ...", + turn instruction
resp = client.messages.create(
    model=settings["model"], max_tokens=1024,
    system=system, messages=[{"role": "user", "content": user}],
    output_config={"format": {"type": "json_schema", "schema": DECISION_SCHEMA}},
)
```

`DECISION_SCHEMA` →

```json
{
  "should_reply": "bool — false if no reply is warranted even though it's my turn",
  "reply": "string — the message to send (empty when should_reply is false)",
  "summary": "string — updated running summary to persist",
  "facts": ["string — updated salient facts"],
  "reason": "string — short why, for the log"
}
```

The model interprets the messages and decides `should_reply` + composes `reply`;
turn-ownership was already decided programmatically before the call, so the model
only sees a convo where it's our turn.

At compose time we always update `summary`/`facts` and the `last_seen` pointer to
the latest incoming message, and queue the reply (pending). `last_seen` only
flips to `me` at `--flush` time, when the reply is actually sent.

## Files

```
src/common.py            # shared u2 helpers (parse_nodes, poll_until, dump_when_ready, nav, IDs)
src/convo_agents.py      # orchestrator + ConvoAgent + settings/memory/LLM
scripts/convo_agents.sh  # chmod +x wrapper → python3 ../src/convo_agents.py "$@"
config/global.example.json
config/convos/.gitkeep
.gitignore               # data/, logs/, config/global.json, config/convos/*.json
requirements.txt         # uiautomator2, anthropic
```

## Open questions (carried to implementation)

- Exact convo identity key if name collisions appear (fold in age/location).
- Send/approve model beyond dry-run vs `--send` (e.g. queue-for-review file).
