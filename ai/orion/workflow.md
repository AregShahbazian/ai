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
