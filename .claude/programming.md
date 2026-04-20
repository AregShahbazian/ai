# Personal AI Workflow

My personal workflow docs (PRDs, design, tasks, phase notes, bug investigations,
reference docs about dependency repos) live centrally at `~/ai/`, not in repos.
This keeps my workflow out of shared codebases.

## Layout

```
~/ai/
├── workflow.md               # general workflow preferences (shared across repos)
└── <repo-name>/              # keyed by bare repo name (basename of git root)
    ├── workflow.md           # repo-specific overrides (optional)
    ├── local.config          # repo-specific paths/env
    ├── deps/                 # my reference docs about related repos
    ├── <feature-slug>/       # per-feature PRDs, design, tasks, phases
    └── bugs/ or bugfix/      # bug investigation notes
```

## When to auto-follow my workflow

If the current git repo's basename matches an existing `~/ai/<repo-name>/`
folder, treat that as an implicit "follow my personal workflow" — read
`~/ai/workflow.md` (if present) and survey `~/ai/<repo-name>/` at the start
of substantive work in that repo. The slash command `/myflow` does the same
thing explicitly.

## Committing the workflow repo

`~/` is itself a git repo that tracks my personal workflow state (`~/ai/`,
`~/.claude/` selected files, etc.). When I say **"commit my workflow"**,
that means: commit the repo at `~/` — stage the relevant changes, create
a commit with a concise message, and present a ≤100-word summary of what
was changed.

## Rules

- **Never create or modify files in a repo's own `ai/` folder.** Personal
  workflow artifacts always go in `~/ai/<repo-name>/`.
- **Paths referenced in a repo's own CLAUDE.md (e.g. `ai/workflow.md`,
  `ai/deps/`, `ai/local.config`) now resolve to `~/ai/<repo-name>/...`.**
  Translate when reading those instructions.
- **When a feature ships and I ask to "produce documentation,"** selectively
  distill `~/ai/<repo-name>/<feature-slug>/` into the repo's own docs — not
  everything goes upstream.

## Repo-specific hard rules

**crypto_base_scanner_desktop** — never read Superchart, coinrayjs, or
crypto_base_scanner source directly (including `node_modules/superchart`,
`$SUPERCHART_DIR`, `$COINRAYJS_DIR`, `$CRYPTO_BASE_SCANNER_DIR`) before
first reading the matching doc in `~/ai/crypto_base_scanner_desktop/deps/`
(`SUPERCHART_API.md`, `SUPERCHART_USAGE.md`, `COINRAYJS_API.md`,
`CRYPTO_BASE_SCANNER_API.md`). For cross-repo source exploration use the
`sc-source-explorer` sub-agent. Full staleness-check procedure in
`~/ai/crypto_base_scanner_desktop/workflow.md`.
