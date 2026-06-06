---
name: feature
description: Capture one or more feature ideas into a single per-repo backlog file (a "bag of features") at ~/ai/<repo>/backlog.md. Triggered when the user types /feature followed by one or more feature ideas. Append-only quick capture — does NOT design, plan, or implement anything.
allowed-tools: [Read, Write, Edit, Glob, Bash]
---

# Feature — quick capture

The user is dumping **one or more feature ideas** they just thought of. Your only
job is to **record them** in a single, growing backlog file — a bag of features —
so they aren't lost. This is **capture, not planning**: do NOT design, scope,
estimate, write PRDs, or start implementing. Just file the ideas cleanly and stop.

## Where it goes

`repo = basename "$(git rev-parse --show-toplevel)"`. The backlog lives at
**`~/ai/<repo>/backlog.md`**.

- If `~/ai/<repo>/` exists, use it.
- If it doesn't exist, create the `~/ai/<repo>/` dir and the backlog file.
- If not inside a git repo at all, tell the user and ask where to put it (don't guess).

## Procedure

1. **Split the input into discrete features.** The user may give one idea or
   several in one message (comma/newline/"and"-separated, a bulleted list, etc.).
   Separate them into individual items. Keep the user's own wording — lightly
   normalize into a short imperative title; preserve any detail they gave as a
   one-line note under the title. Do **not** invent detail they didn't provide.

2. **Read the existing backlog** (if present) to avoid duplicates. If a new idea
   is essentially already there, skip it (or merge a new detail into the existing
   entry) rather than adding a near-duplicate — mention what you skipped.

3. **Append** each new feature to the **## Backlog** list as an unchecked item.
   Create the file with the skeleton below if it doesn't exist. Append to the end
   of the list; never reorder or rewrite existing entries.

   Entry shape (one line, optional indented note + capture date):

   ```
   - [ ] <short imperative title>  <!-- 2026-06-06 -->
         <optional one-line detail, only if the user gave any>
   ```

   Use today's date from the environment context for the `<!-- ... -->` stamp.

4. **Report** in **one or two lines**: how many features were added, their titles,
   and any skipped as duplicates. No elaboration, no "shall I plan this?" prompts.

## File skeleton (only when creating it)

```markdown
# <Repo> — feature backlog

A bag of feature ideas captured via `/feature`. Unsorted, unplanned — a holding
pen so nothing gets lost. Promote items into real phases/PRDs when they're picked
up; check them off (`[x]`) or remove them once shipped.

## Backlog
```

## Rules

- **Append-only capture.** Never delete, reorder, or rewrite existing entries
  (except merging a genuine duplicate). Never tick items off here.
- **Don't plan or build.** This skill only files ideas. If the user wants to act
  on one, that's a separate, explicit request.
- **Stay terse.** No preamble, no follow-up questions unless the location is
  genuinely ambiguous (no repo / no `~/ai/<repo>/`).
- **Stage, don't commit.** After writing, `git -C ~ add ai/<repo>/backlog.md` so
  it's ready, but do NOT commit or push (those are explicit, separate actions).
