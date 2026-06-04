---
name: discussion
description: Enter "discussion mode" — answers only, no actions. Triggered when the user types /discussion. In this mode Claude answers questions concisely and never edits, writes, runs, or commits anything unless explicitly told to. File reads are allowed. Mode stays active until the user ends it.
---

# Discussion Mode

When this skill is invoked, enter **discussion mode** and stay in it for every
subsequent response until the user explicitly ends it (e.g. "end discussion",
"exit discussion", "stop discussion", "we're done discussing").

## Rules while in discussion mode

1. **Answers only — no actions.** Do NOT edit, write, create, delete, run,
   build, commit, push, or otherwise change anything. Only do so if the user
   explicitly asks in that message. Reading is fine: file reads, searches,
   and look-ups are allowed to inform answers.

2. **Be concise.** Aim for **under 50 words**. Go up to **100 words** only if
   genuinely necessary. No preamble, no filler, no restating the question.

3. **Header on every response.** Begin every response with this exact header
   line so it's obvious the mode is active:

   > 💬 **DISCUSSION MODE** · answers only — say "end discussion" to exit

   (Terminal markdown doesn't render reliable ANSI color, so the bold blockquote
   is the visual marker. Always keep it as the first line.)

4. **Suggest follow-ups — only when genuinely useful.** Do NOT append questions
   to every response. When they'd actually help move the discussion forward, add
   a few, separated by a `---` divider under a **Follow-ups:** label, and
   **numbered (1, 2, 3, …)** so the user can refer to them. Otherwise omit the
   section entirely. These don't count toward the word limit.

5. **Strict until ended.** Apply these rules to EVERY response, not just the
   first. When the user ends discussion mode, confirm in one line that it's off
   and resume normal behavior (drop the header, word cap, and follow-ups).

6. **Discussions are an idea backlog.** Many discussions contain ideas about
   **features, workflows, and methods that will be realized at some point** —
   not just decisions for "now." Treat the discussion as a source of future,
   implementable work. When summarizing, extract these explicitly so they aren't
   lost or buried in prose (see the **Ideas to realize** section below).

7. **Auto-save a summary on exit.** When the user ends the discussion, ALWAYS
   write a summary before confirming exit:
   - **Location:** if the current repo has a `~/ai/<repo-name>/` workflow folder,
     save the full summary to `~/ai/<repo-name>/discussions/YYYY-MM-DD-<slug>.md`
     (the appropriate home for project discussions). Otherwise fall back to the
     auto-memory dir (`~/.claude/projects/-home-areg/memory/discussion-<slug>.md`,
     `type: reference`).
   - **Content:** a one-paragraph summary, key conclusions, open questions, and a
     dedicated **## Ideas to realize** section — a bullet list of every feature /
     workflow / method idea raised that is intended for future implementation,
     each phrased as a concise, actionable item. This is the most important part
     to get right; it's what the discussion-explorer agent later mines.
   - **Memory pointer:** for significant decisions, also add/update a `type:
     project` memory file and a one-line pointer in `MEMORY.md`, linking the doc
     path. Link related memories with `[[name]]`.
   - If the discussion was trivial (no substantive content), say so and skip the
     file instead of writing an empty summary.

## Comparing with past discussions

Before or during a discussion, to see how the current topic relates to previous
ones WITHOUT loading every old doc into context, delegate to the
**`discussion-explorer`** sub-agent (it reads `~/ai/<repo>/discussions/` and
returns a concise comparison: related prior discussions, prior decisions/ideas
that bear on the current topic, contradictions, and already-captured ideas to
avoid re-deciding). Use it when the user references "what we discussed before",
asks whether something was already decided, or when a new idea may overlap past
ones.

## Response shape

```
> 💬 **DISCUSSION MODE** · answers only — say "end discussion" to exit

<concise answer, <50 words ideally>

---
**Follow-ups:**
1. <question 1>
2. <question 2>
```
