# Mega-prompt — one-go: design → tasks → implement → tests

Template for running the full post-PRD loop in a single prompt, on any model
(Opus / Sonnet / Fable). Invoked as:

> Run the megaprompt for `~/ai/<repo>/<feature>/<task>/prd.md`

`$PRD` below refers to that path; `$DIR` is its containing folder. When
invoked, this template **overrides phase-gating** for the repo — the whole
loop runs in one prompt. All other rules from `~/ai/workflow.md` and
`~/ai/<repo>/workflow.md` still apply.

## Inputs — load before starting

1. `$PRD` — the approved PRD (must have a frontmatter `id`).
2. `~/ai/<repo>/workflow.md` — repo-specific rules (deps docs, dev server,
   local.config, etc.). Follow its reference-doc rules strictly (e.g. never
   read Superchart/coinrayjs source directly; use `deps/` docs and the
   designated sub-agents).
3. Any `context.md` the repo workflow points to for the feature area.

If the PRD is ambiguous on a point that changes the design, ask **one**
clear question and continue everything that doesn't depend on the answer.
Never park the whole run on a single open point.

## Phase 1 — Design (`$DIR/design.md`)

Architecture decisions, API usage, data flow, function signatures, key
styles/properties, open questions — per the Design phase spec in
`~/ai/workflow.md`.

**Gate:** before moving on, re-read `$PRD` and check the design against
every requirement and every non-requirement. Fix gaps now; list each
requirement → design-section mapping briefly at the bottom of `design.md`
(one line per requirement). Anything unmapped is a design bug — resolve it
before Phase 2.

## Phase 2 — Tasks (`$DIR/tasks.md`)

File-by-file changes with verification steps per task, per the Tasks phase
spec. Order tasks so each leaves the app in a working state.

## Phase 3 — Implement

Work through `tasks.md` in order. For each task:

- Follow repo code style (comments, i18n, typography, etc. from the repo's
  CLAUDE.md).
- Never run build commands unless the repo workflow says otherwise.
- Commit nothing; push nothing. Stage new git-tracked source files.

## Phase 4 — Self-review (mandatory, before reporting done)

1. Re-read the full diff (`git diff` + staged files) against `$PRD`
   requirement by requirement, and against `design.md` decision by decision.
2. Check the standard coupling points the repo workflow calls out (for
   crypto_base_scanner_desktop: TradingTab change, coinraySymbol change,
   resolution change, exchangeApiKeyId change — reason through each even
   when it can't be executed).
3. Check cleanup paths: unmount, dependency arrays, symbol-change cleanup,
   listeners/subscriptions.
4. Fix what the self-review finds, then re-run the self-review on the fixes.
5. Optionally delegate an adversarial re-check to a subagent (one per risky
   area). Findings verified only by a subagent are marked `(agent-verified)`.

## Phase 5 — Review doc (`$DIR/review.md`)

Create `review.md` with a **Round 0: implementation** section containing the
full numbered verification checklist for everything implemented (including
the Trading Terminal context test cases where applicable). Unverified items
stay unchecked — do not pre-tick items only reasoned about; mark
self-review-confirmed items `(agent-verified)` at most.

## Doc hygiene

- Stage every new/edited doc immediately: `git -C ~ add <path>`.
- Never hardcode absolute sibling-repo paths in docs — use the
  `$SUPERCHART_DIR`-style variables from `local.config`.

## Output contract — end of run, in chat

Finish with exactly these two sections, short and concrete (per-task
grouping if tasks differ materially):

1. **How to apply changes** — only the steps actually needed (with a
   running dev server, usually "HMR picks it up" or "hard-reload because
   <reason>").
2. **What to test** — the handful of highest-signal manual checks, numbered,
   referencing the checklist numbers in `review.md`.

No essays. The durable record is `review.md`; chat output is the
at-a-glance version.
