---
name: overview
description: Print a short status overview of the current repo's MVPs, phases, and tasks (one-liners), followed by a humanized git-status summary of both the code repo and its workflow docs in the ~/ repo (committed / staged / unstaged / unpushed). Triggered when the user types /overview.
allowed-tools: [Read, Glob, Grep, Bash]
---

# Overview

Give a **short** status snapshot. No edits, no regeneration — read-only reporting.
Be concise: one-liners for the work items, a short humanized paragraph for git.

## Gather

`repo = basename "$(git -C . rev-parse --show-toplevel)"`. Docs live in
`~/ai/<repo>/`; code lives in the repo root (e.g. `~/git/<repo>`).

1. **MVPs** — read `~/ai/<repo>/mvp.md` (and any `mvp*.md`). One line each:
   name + the gist + state (e.g. "spec'd, not built").
2. **Phases** — each `~/ai/<repo>/phase-*/`. One line each: `Phase N — <title>` +
   rolled-up status. **Also include coming/future phases** — any phase defined but
   not yet started (e.g. listed in `~/ai/<repo>/README.md` or `backlog.md`, or a
   `phase-*/` dir with no task docs yet). Mark these as "planned / not started"
   so the user can see what's next.
3. **Tasks** — each task dir inside a phase. One line each: task name + which docs
   exist (`prd/design/tasks/review`) + implementation state if known. **List every
   task of every phase**, including planned tasks of coming phases (even with no
   docs yet — show `(none)` / planned).
4. **Git — code repo** (`git -C <repo-root>`):
   - current branch; staged vs unstaged vs untracked (counts/kinds from
     `status --short`); ahead/behind upstream
     (`rev-list --left-right --count @{u}...HEAD`); if the branch has no upstream,
     say "not pushed yet".
5. **Git — workflow docs in the `~/` repo**, scoped to this repo's dirs
   (`git -C ~ status --short -- ai/<repo>` and any related
   `.claude/projects/*/memory` orion files): staged vs unstaged; and unpushed
   commits touching them (`git -C ~ log --oneline @{u}..HEAD -- ai/<repo>`).

## Output format (keep it tight)

Display the work items **hierarchically** — tasks nested under their phase, phases
nested under their MVP — since that's how they're actually organized. Show counts
in the section header.

```
## <Repo> — Overview

**Work** — <M> MVP / <P> phases / <T> tasks
- MVP<n>: <gist> — <state>
  - Phase <n> — <title>: <state>
    - <task>: <docs present> — <impl state>

**Git**
- **code** (`<repo-root>`): on `<branch>`, <humanized: what's committed, what's
  staged/unstaged/untracked, pushed or not>.
- **workflow** (`~/ai/<repo>` in ~ repo): <humanized: staged/unstaged/uncommitted,
  and whether commits are unpushed>.
```

If a phase isn't yet tied to a specific MVP, nest it under the MVP it serves (Phase
1 → MVP1 here). Keep indentation consistent so the containment is obvious.

## Rules
- **Show all phases and all tasks** — never trim to just the active ones. Coming
  phases and their planned tasks always appear too, in the same one-line format, so
  the overview doubles as a "what's next" roadmap. Order phases ascending so the
  future ones sit at the bottom.
- **Humanize git** — translate porcelain into plain English ("3 doc edits staged
  but not committed", "branch `phase-1-map` has 1 commit, not pushed yet"), not raw
  `git status` dumps.
- Keep the whole thing short — one-liners + a 2–4 line git summary. No file dumps.
