---
description: Follow my personal AI workflow for the current repo
---

Determine the current repo name — it's the basename of the git repo root
(run `git rev-parse --show-toplevel` and take the basename), or the last
path segment of the current working directory if not in a git repo.

Then, in order:

1. If `~/ai/workflow.md` exists, read it for my general workflow preferences.
2. If `~/ai/<repo-name>/` exists, list its contents and read what's relevant:
   - `workflow.md` — repo-specific workflow overrides (if present)
   - `local.config` — repo-specific paths, env hints (if present)
   - `deps/` — my reference docs about related repos
3. For a specific feature I'm working on, read the matching subfolder at
   `~/ai/<repo-name>/<feature-slug>/`.

Do not create or modify files in the repo's own `ai/` folder (if one exists).
All personal workflow artifacts live in `~/ai/<repo-name>/`.

If `~/ai/<repo-name>/` does not exist, tell me and ask whether to create it.
