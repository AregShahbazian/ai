---
id: convo-agents
title: Per-conversation reply agents with persistent memory
status: draft
branch: feature/convo-agents
---

## Goal

Let the user dock their phone, leave it untouched, and have an automation
session work through Tantan conversations and reply on their behalf. Each
conversation the user *cares about* gets a **dedicated agent** that holds
durable memory of that thread, reads new messages, interprets them, and replies
when it is the user's turn — shaped by the user's global and per-conversation
preferences.

## Concepts

- **Orchestrator** — the single top-level process. Scans the inbox, decides
  which conversations are in scope, and **synchronously** delegates each one to
  its convo agent, one at a time (no concurrency).
- **Convo agent** — a per-conversation worker, keyed by a stable conversation
  identity. Owns that conversation's memory and applies the merged settings.
- **Convo memory** — durable per-conversation state so the agent never needs to
  re-scrape the full chat history every run.
- **Settings** — user preferences that steer replies, at two scopes: **global**
  (all convos) and **per-convo** (overrides for one thread).

## Requirements

### Orchestration

- The orchestrator runs over the existing Tantan inbox scan and produces the
  list of in-scope conversations.
- Processing is **sequential** — one conversation handled start-to-finish before
  the next. No parallel agents, no shared-device contention.
- Only conversations the user has opted into ("cares about") are delegated.
  There must be a way to mark a conversation as tracked vs. ignored.
- The orchestrator must reach a known-good inbox state before delegating, and
  return to it between conversations (consistent with existing scripts' rule of
  verifying the screen before acting).

### Convo identity

- Each conversation maps to a **stable identifier** that survives across runs
  (so memory and settings reattach to the right thread on every session).
- Identity must tolerate inbox reordering and list scrolling.

### Convo memory

- Each tracked conversation has its own persistent memory store.
- Memory records at least: a pointer to the **last message already processed**
  (so only new messages are read each run), a **running summary** of the thread,
  and any **facts/persona notes** the agent should carry forward.
- On each run the agent reads only messages newer than the stored pointer, then
  updates the pointer and summary. Full-history re-scrape happens only on first
  contact or when memory is missing/invalid.

### Reading & interpreting

- The agent reads the new messages in a tracked conversation and interprets
  them well enough to decide: is it the user's turn to reply, and what is being
  asked / discussed.
- The agent must correctly distinguish **who sent the last message** (user vs.
  match) to determine whose turn it is.

### Replying

- The agent replies **only when it is the user's turn** (i.e. the match sent the
  last message and a reply is warranted). Otherwise it leaves the thread
  untouched.
- Replies are generated under the merged settings (see below) — tone, language,
  intent, length, and any do/don't rules.
- **Empty conversation (first contact)** — a match with no messages yet. There
  is no memory and nothing to interpret. The agent may generate an **opener**
  under the merged settings if (and only if) opening is enabled for that convo,
  then seed memory. Default is to not open unsolicited.
- Writing a reply is a device-mutating action and is gated by the project's
  "never edit a connected device without asking" rule — the PRD assumes an
  explicit opt-in / dry-run vs. send distinction (exact gating defined in
  design).

### Settings (global + per-convo)

- **Global settings** apply to every convo agent (e.g. default tone, language,
  hard rules, signature style).
- **Per-convo settings** override or extend global ones for a single
  conversation (e.g. this match speaks Spanish; keep replies short; a specific
  goal for this thread).
- Effective settings for an agent = global merged with that convo's overrides,
  with per-convo winning on conflict.

### How settings are configured

Two layered paths, decided in the discussion of 2026-06-18:

1. **Plain config files are the source of truth.** A global settings file plus
   one per-conversation file keyed by convo identity. Durable, versionable,
   survive across sessions. This is what the agents read.
2. **Verbal-to-orchestrator is a convenience front-end, not a separate
   channel.** The user can tell the main agent "for this convo keep it short and
   in Spanish" and the agent *writes that into the per-convo config file*. Speech
   edits the files; it never holds settings only in memory.

Pure-verbal-only is explicitly rejected: nothing would persist between sessions
and settings couldn't reattach to the right thread. Config files are the
backbone; verbal editing is sugar on top.

## Non-requirements (this iteration)

- No concurrent / async processing of multiple conversations.
- No support for apps other than Tantan.
- No automatic decision about *whom* to talk to — scope is limited to
  conversations the user explicitly tracks.
- No learning/auto-tuning of settings from outcomes; settings are user-authored.
- No cloud component — runs locally against the docked phone, like the existing
  scripts.

## Open questions (resolve in design)

- Exact convo identity key (match name is not guaranteed unique/stable).
- The reply send/approve gating model (full auto, queue-for-review, or dry-run).
