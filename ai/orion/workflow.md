# Orion — Repo Workflow Overrides

Orion is the real mapping app. `~/git/track` was the POC (Flutter + Supabase) —
mine it for reference only.

Inherits the shared workflow at `~/ai/workflow.md`. Repo-specific overrides go here
as they emerge.

## Layout
- `~/ai/orion/README.md` — **root overview** (entry point): phases, discussions,
  ideas-to-realize backlog. Regenerate with `/save-workflow`.
- `~/ai/orion/mvp.md` — first-release MVP definition.
- `~/ai/orion/phase-<N>/<task>/` — **phases contain task dirs**; each task dir
  holds its own `prd.md` → `design.md` → `tasks.md` → `review.md`. No `prd.md`
  sits directly in a phase dir.
- `~/ai/orion/discussions/` — `YYYY-MM-DD-<slug>.md` discussion summaries.
- `~/ai/orion/deps/` — reference docs about related/sibling repos.
- `~/ai/orion/bugfix/` — `.fix.md` bug investigation notes.

`README.md` and `mvp.md` are the references into the phases/tasks; keep their
links concise (run `/save-workflow` to refresh them).

## Default feature loop (standard for Orion)

When asked to implement a feature, run the **whole loop in one go** and only stop
for genuine blockers:

1. **PRD** → **design** → **tasks** → **implementation** → a **short `review.md`**
   with a basic numbered test checklist. Use the per-task dir
   (`phase-N/<task>/`), one `id` in the PRD frontmatter, commits reference it.
2. Stage each new doc at creation (`git -C ~ add …`).
3. Mine `~/git/track` for reference, but rethink its choices — don't port flaws.
4. Run `flutter analyze` before declaring a task done.
5. **End with two short chat sections** (not essays):
   - **How to apply changes** — exact commands to see it (pub get / restart / run).
   - **What to test** — a few concrete checks.
6. Be concise. If you must ask, ask one clear question and continue everything
   that doesn't depend on the answer.