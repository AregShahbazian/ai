---
name: save-workflow
description: Regenerate the ~/ai/<repo>/README.md root overview from the workflow docs on disk — refresh the phases table, discussions index, and "ideas to realize" backlog, and fix cross-links. Also checks the code repo's architecture docs (CLAUDE.md + docs/architecture.md) and updates them if the app's architecture grew/changed enough. Triggered when the user types /save-workflow (or asks to "save the workflow" / "update the workflow readme").
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
---

# Save Workflow

Regenerate the **root overview** (`~/ai/<repo-name>/README.md`) so it reflects the
current state of the workflow docs on disk, and keep cross-references correct and
**concise** (a link + a few words — never paste doc contents into the index).

## Procedure

1. **Locate the repo.** `repo = basename "$(git rev-parse --show-toplevel)"`.
   Work in `~/ai/<repo>/`. If it doesn't exist, tell the user and stop.

2. **Scan the docs on disk** (don't trust the old README — rebuild from reality):
   - **MVP / canonical docs** — `mvp.md` and any other top-level specs.
   - **Phases → tasks.** Each `phase-*/` dir contains one or more **task dirs**,
     and **each task dir** holds its own `prd.md` (+ optional `design.md` /
     `tasks.md` / `review.md`). So scan two levels: for each `phase-*/`, list its
     task subdirs; for each task, read which docs exist, the task title (PRD `#`
     heading) and PRD `id:`, and derive a status (e.g. "PRD done; design pending",
     "in review"). A phase's status is the roll-up of its tasks. (Do NOT expect a
     `prd.md` directly inside a phase dir — PRDs live in task dirs.)
   - **Discussions** — `discussions/*.md`. For each, read the date (filename),
     the title (`#` heading), and whether it has a non-empty `## Ideas to realize`
     section. Note "superseded"/"historical" if the doc says so.

3. **Rebuild `README.md`** with these sections (keep it tight):
   - One-line project description (preserve the existing one if present).
   - **Canonical docs** — links to `mvp.md`, `deps/`, etc.
   - **Phases** — list each phase, and **nested under it its tasks**, each task
     linking its `prd.md` (and design/tasks/review when present) with a status.
     Render the overview in this shape:

     ```
     Phase <N> — <phase title>
         <task title> → phase-<N>/<task>/prd.md   (<status>)
     ```

     (Use a nested list or a table grouped by phase — but tasks must appear under
     their phase, never as bare phase-level PRDs.)
   - **Discussions** table — date, short topic, link, and an "Ideas to realize"
     flag (yes / historical / deferred).
   - **Backlog — ideas to realize** — a checklist aggregated from every
     discussion's `## Ideas to realize` section. Each item = a short label + a
     `→ source` pointer to the discussion (date or slug). Preserve existing
     checkbox states (`[x]`) where the item still matches; don't un-check
     completed work.
   - **Key decisions** — a few one-line pointers (app identity, stack, major
     strategy calls). Pull from `mvp.md` / decision discussions; keep to one line
     each.

4. **Fix cross-links concisely.** Ensure top-level docs (`mvp.md`, phase PRDs)
   carry a single short "Part of Orion — see [README.md](README.md)" line near the
   top. Add it if missing; do NOT make it verbose or duplicate it.

5. **Check the architecture docs in the code repo.** Two files describe the app's
   architecture: the `## Architecture` section in the repo's `CLAUDE.md`
   (always-loaded summary) and `docs/architecture.md` (full map). Compare both
   against the current `lib/` reality (skim the directory layout, controllers,
   feature folders, key packages in `pubspec.yaml`). If the architecture has
   **changed or grown enough to matter** — a new top-level subsystem, a new
   feature folder, a changed state/persistence/map approach, a new
   platform-conditional boundary, or a core convention — update the docs:
   - Keep `CLAUDE.md`'s section **lean** (the 6-ish essentials + the pointer to
     `docs/architecture.md`); only add a bullet when a genuinely new pillar appears.
   - Put the detail in `docs/architecture.md`.
   - If nothing material changed, leave both untouched (idempotent — don't churn
     wording). These files live in the **code repo**, so stage them there:
     `git add CLAUDE.md docs/architecture.md`. Never commit or push.

6. **Stage** the workflow changes in the `~` repo: `git -C ~ add ai/<repo>/`. Do
   NOT commit or push (those are explicit, separate actions).

7. **Report** an **under-100-word** overview of *what* was updated and *why* —
   which phases/discussions/backlog items were added, updated, or marked done
   (and any architecture-doc update + its reason). Keep it to the changes that
   matter; no filler.

## Principles

- **Rebuild from disk, don't hand-edit blindly** — the README is a generated index.
- **Concise references only** — links and a few words; never inline doc bodies.
- **Idempotent** — running it twice with no doc changes should produce no diff.
- **Preserve human edits** — keep the project one-liner, existing checkbox states,
  and any manual notes that don't conflict with on-disk reality.
