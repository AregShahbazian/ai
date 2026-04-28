# Development Workflow

## File Structure

Docs live in `ai/<feature>/<task>/<subtask>/`. Each subtask folder contains its workflow docs as files:

```
ai/<feature>/<task>/<subtask>/
  prd.md          # git-tracked
  design.md       # gitignored
  tasks.md        # gitignored
  review.md       # gitignored
```

Only PRD files are committed. Design, tasks, and review docs are process artifacts — the decisions they capture are embodied in the resulting code and git history.

**Stage new PRDs immediately.** When a new `prd.md` is created, run `git -C ~ add <path>` right away so it shows as a staged change rather than an untracked file. Same applies to any other git-tracked file (e.g. updates to `workflow.md`). Do NOT stage gitignored files (`design.md`, `tasks.md`, `review.md`).

If a subtask has a related but separate piece of work (e.g., a storybook prototype), prefix the doc type:

```
ai/superchart-integration/phase-3/bases/
  prd.md                  # integration PRD
  design.md               # integration design
  tasks.md                # integration tasks
  review.md               # integration review
  storybook-prd.md        # storybook PRD
  storybook-design.md     # storybook design
  storybook-tasks.md      # storybook tasks
  storybook-review.md     # storybook review
```

## Phases

### 1. PRD

Requirements only. No design choices, no implementation details.

- What the feature should do
- Visual/behavioral requirements
- Storybook controls and defaults
- Non-requirements (explicit scope boundaries)

Every PRD must have a unique ID in its frontmatter:

```yaml
---
id: sc-bases
---
```

IDs are short, lowercase, hyphenated. Use a `<feature>-<scope>` pattern (e.g. `sc-bases`, `sc-drawings`, `portfolio-rebalance`). The ID is stable — it never changes even if the file is moved or renamed.

**Prompt scope:** Only generate the PRD doc.

### Linking PRDs to code

Commits that implement a PRD must include its ID in the commit message:

```
Phase 3: add bases overlay [sc-bases]
```

To find all code changes for a PRD:

```bash
git log --grep="sc-bases"
```

### 2. Design + Tasks

Design and implementation choices based on the PRD, followed by concrete tasks.

#### Design

- Architecture decisions
- API usage, data flow
- Function signatures, key styles/properties
- Open questions to resolve during implementation

#### Tasks

- File-by-file changes
- Verification steps per task

**Prompt scope:** Generate both design and tasks docs in one prompt (unless told otherwise).

### 3. Implement

Apply the code changes from the design + tasks (or from review fixes).

**Prompt scope:** Write code, then:
- **Update `review.md`** — create or append a verification checklist for what was implemented. Testing steps go in the review doc, not in the chat.
- **Apply steps** — mention in chat what's needed to see the changes (HMR, restart webpack, rebuild lib, yarn install, etc.). Only include steps that are actually needed.

### 4. Review

Iterative review rounds after implementation. Each round can:

- Identify bugs or missing requirements
- Edit PRD where requirements were incorrect or missing

**Prompt scope:** Only write the review doc (and PRD if requirements change). Do NOT edit design/tasks docs or implement code fixes unless the prompt explicitly says to. If the fix involves design or task decisions, include them in the review round section itself.

#### Review round format

Each round is appended to the review doc:

```
## Round N: <short description> (<date>)

### Bug X: <title>
**Root cause:** ...
**Fix:** ...
**Files:** ...
**Design notes:** (optional — design/task decisions that come with this fix)

### Verification
1. checklist item
2. ✅ checklist item (done)
```

Verification items must be **numbered** so they can be referenced by number. Prefix with ✅ when verified.

Previous round checklist items are marked done/skipped as appropriate.

#### Trading Terminal context test cases

Review verification must include test cases that combine the chart feature being tested
with common Trading Terminal actions. These actions often have logic coupled with the
chart and can expose bugs that feature-only testing misses:

- **Changing TradingTab** — switch to a different tab while the feature is active
- **Changing coinraySymbol** — switch market within the same tab
- **Changing resolution** — switch timeframe within the same tab
- **Changing exchangeApiKeyId** — switch exchange API key for the current tab

Each review should include at least one test case per action above, verifying the
feature behaves correctly before, during, and after the action.

## Debugging Procedure

When told to debug an issue, follow this procedure:

1. **User reports** — symptoms and reproduction steps
2. **Analyze** — read relevant docs and code, form a hypothesis for the root cause
3. **Suggest a fix** — describe the proposed fix, don't apply yet
4. **Add console.logs** — place logs in relevant code to confirm the hypothesis and
   gain extra knowledge in case the first hypothesis is wrong
5. **User reproduces** — user runs the reproduction steps and shares the log output
6. **If hypothesis confirmed** — wait for user's confirmation before applying the fix
7. **If hypothesis not confirmed** — use newly gained knowledge from the logs to form
   a new hypothesis, suggest a new fix, add new logs, repeat from step 5

If you can't form a hypothesis, add logs to the relevant code paths to gather more
information. Use the log output to build a hypothesis from there.

Never apply a fix before the hypothesis is confirmed with logs. Never remove logs
before the user confirms the fix works.

## Bugfix Tracking

When told to, create a `.fix.md` file documenting the bug and its resolution.

### Location

- SuperChart bugs: `ai/superchart-integration/bugfix/`
- Other bugs: `ai/bugfix/`

### Filename

`YYYY-MM-DD-short-name.fix.md` — date is when the fix was made.

### Format

```markdown
# <Short bug title>

**Date:** YYYY-MM-DD
**Branch:** <branch name>
**Status:** fixed | workaround | investigating

## Symptoms
What was observed — user-visible behavior, console output, etc.

## Diagnosis
How the root cause was found — what was investigated, what logs/tools were used, what the logs revealed.

## Cause
Root cause of the bug.

## Solutions Tried
What was attempted, including failed approaches (if any).

## Final Solution
What actually fixed it.

## Edited Files
- path/to/file1.js
- path/to/file2.js
```

### Rules

- Only create when explicitly told to — not automatically after every fix.
- When working on a bugfix, DO remind the user of the above procedure and suggest tracking the bugfix.

## Local Config (`ai/local.config`)

Dev-specific paths to sibling repos are stored in `ai/local.config`. This file is gitignored — copy `ai/local.config.example` and fill in your paths.

```
SUPERCHART_DIR=/path/to/Superchart
COINRAYJS_DIR=/path/to/coinrayjs
```

Claude reads this file to resolve `$SUPERCHART_DIR` and `$COINRAYJS_DIR` at runtime. All `ai/` docs use these variables — **never hardcode absolute paths in `ai/` docs**.
