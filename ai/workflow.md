# Development Workflow

## When running as Fable 5 (Claude Fable 5 / Mythos-class only)

These rules apply only when the model is Fable 5; older models keep the
behavior defined elsewhere in this file.

### Hard stops — never cross autonomously

Run long arcs freely between these points, but always stop and wait for me at:

1. **Debugging:** never apply a fix before the hypothesis is confirmed with logs
   (see Debugging Procedure). Suggest + add logs, then wait.
2. **`git push`:** never, in any repo, unless explicitly told.
3. **Connected devices:** never write to an attached device (adb push/install/rm,
   settings) without asking first.
4. **Review rounds:** write the review doc only — no code fixes, no design/tasks
   edits, unless the prompt explicitly says to.

### Delegate gathering to Sonnet sub-agents

If you need to read code, logs, or do online research, create a **Sonnet**
sub-agent to gather, process, and summarize the data before handing off to
you. You, the Fable, do the reasoning/analysis only, on the processed,
summarized data.

### Execution mode per repo

- **crypto_base_scanner_desktop:** phase-gated — one workflow phase per prompt
  (PRD only, then design+tasks, then implement), as defined below.
- **orion:** one-go — full PRD→design→tasks→implement→review loop per
  `~/ai/orion/workflow.md`.
- Other repos: default to phase-gated unless their workflow.md says otherwise.

### On-the-fly docs — the default forward mode

For any non-trivial feature/change, generate the workflow docs **on the fly**
and run the whole loop in one go: `prd.md` → `design.md` → `tasks.md` →
implement → `review.md`, in the proper per-task dir under `~/ai/<repo>/…`.
Don't wait for separate per-phase prompts. Document everything done this way;
prompt me only on genuine blockers. When no existing dir fits, propose a
location/organization for the new docs (briefly, in the same turn) and proceed
with it.

### Blockers

If you must ask, ask one clear question and continue everything that doesn't
depend on the answer. Don't park the whole task on a single open point.

### Review verification via subagents

In review rounds, you may delegate verification to subagents — e.g. an
adversarial re-check per numbered bug/checklist item — and fold the verdicts
back into the review doc. Checklist items verified only by a subagent (not by
me) get ✅ plus a `(agent-verified)` note, so my manual verification stays
distinguishable.

## File Structure

Docs live in `ai/<feature>/<task>/<subtask>/`. Each subtask folder contains its workflow docs as files:

```
ai/<feature>/<task>/<subtask>/
  prd.md
  design.md
  tasks.md
  review.md
```

All workflow docs are git-tracked.

**Stage new docs immediately.** When a new doc is created (`prd.md`, `design.md`, `tasks.md`, `review.md`, or any other workflow file), run `git -C ~ add <path>` right away so it shows as a staged change rather than an untracked file.

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
- **Update `review.md`** — create or append the full verification checklist for what was implemented (the durable record lives in the review doc).
- **After each task, present two short sections in chat:**
  - **What to test** — a few concrete things to check that this task works.
  - **How to apply changes** — the exact commands/steps to see it (e.g. `flutter pub get`, hot restart, `flutter run -d chrome`, rebuild). Only steps actually needed.
  Keep both short — instructions/descriptions, not essays. The full checklist still goes in `review.md`; these are the at-a-glance per-task version.

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

## Code Style

### Comments

Default to no comments. When a comment is genuinely needed:

- Keep it under 3 lines unless a longer explanation is absolutely necessary (subtle invariant, hidden constraint, non-obvious workaround).
- Be terse — short and concise, no narration.
- Don't restate what the code does. Don't explain the obvious.
- Don't reference the current task / fix / PR (those belong in the commit message).

If removing the comment wouldn't confuse a future reader, don't write it.

## Local Config (`ai/local.config`)

Dev-specific paths to sibling repos are stored in `ai/local.config`. This file is gitignored — copy `ai/local.config.example` and fill in your paths.

```
SUPERCHART_DIR=/path/to/Superchart
COINRAYJS_DIR=/path/to/coinrayjs
```

Claude reads this file to resolve `$SUPERCHART_DIR` and `$COINRAYJS_DIR` at runtime. All `ai/` docs use these variables — **never hardcode absolute paths in `ai/` docs**.

## Shorthand

When I append `Nw-` to a message (e.g. `100w-`, `50w-`, `200w-`), it means "reply in N words or less." Treat it as a hard cap on the answer body — not on tool calls or code blocks I explicitly asked for.
