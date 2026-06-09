---
name: implement
description: Implement an Orion frontend feature end-to-end from an existing PRD — strict gap-check, then PRD→design+tasks→implementation in one go, stopping only when your input is genuinely required. Triggered when the user types /implement <phase/task-slug>. Frontend only; refuses anything needing backend/server/container/devops. Enforces the word caps, the two-repo commit split, and the "leave code uncommitted for the user to test" handoff.
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
---

# Implement Mode — Orion frontend feature, one prompt

Drive a single Orion **frontend** feature from an **already-written PRD** all the
way to working (uncommitted) code, in one pass. The PRD exists before you're
invoked. The ideal run is: read PRD → strict gap-check → commit PRD → design+tasks
→ commit them → implement → `flutter analyze` → ≤50w report. **Stop only when the
user's input is genuinely required.** Stay in this mode across turns until the
report is delivered or the user exits.

This skill is the at-a-glance, enforced version of the loops already written down —
it does **not** re-document them. Lean on:

- `~/ai/workflow.md` — PRD/design/tasks/review phase definitions, the `[id]`
  commit-linking rule, "stage new docs at creation" (`git -C ~ add`), code style,
  the `Nw-` word-cap shorthand.
- `~/ai/orion/workflow.md` — the **Default feature loop** for Orion, the
  `flutter analyze`-before-done gate, the per-task path layout, the
  How-to-apply / What-to-test handoff.
- `~/git/orion/CLAUDE.md` + `~/git/orion/docs/architecture.md` — **read before any
  non-trivial `lib/` work.** The `InteractionController` spine, the no-state-
  framework / `ChangeNotifier` + command-bus model, the compile-time platform
  split (`_io.dart` / `_web.dart`), offline-first, persistence (Drift/SQLite +
  SharedPreferences).

## Scope — frontend only

You handle the Flutter/Dart app (`lib/`, widgets, state, DB, GPX, map, settings).
You do **not** handle backend, server, API, database server, containers, or
DevOps/CI. If the feature genuinely requires any of those, **refuse** (see below) —
a separate agent owns that.

## Input

Invoked as `/implement <phase/task-slug>` — e.g. `/implement phase-7/route-planner`.

Resolve the slug to the task dir, in order:
1. `~/ai/orion/mvp/<slug>/` (the canonical layout, e.g.
   `~/ai/orion/mvp/phase-7/route-planner/`).
2. If not found, glob `~/ai/orion/mvp/**/<task>/prd.md` / `~/ai/orion/**/<task>/prd.md`.
3. If still missing or **ambiguous**, stop with a ≤50w line stating what you looked
   for and asking which task. Do not guess.

The PRD is `<taskdir>/prd.md`. Its frontmatter `id` is the link used in commits.

## The loop

### 0 — Load context
Read `prd.md` and its `id`. Skim `~/ai/orion/README.md` + `~/ai/orion/mvp.md` for
where this feature sits. Read the repo arch docs (above) and the **relevant** `lib/`
code the feature touches. Don't read the whole tree — scope to what the PRD implies.

### 1 — Strict gap-check (the only place you decide to stop)
Read the PRD as a serious production spec and look **only** for things that would
actually block a correct implementation:

- Something material **left out or unclear**.
- A **contradiction** within the PRD.
- A **scope/architecture conflict** (e.g. fights the `InteractionController` spine,
  offline-first, or the platform-split model).
- A **backend/server/container/devops dependency**.

Be strict the other way too: **do not overthink, invent features, or pad with
unlikely edge cases** that don't hinder a serious production app. A clean-enough PRD
gets **no stop** — treat the invocation as the green light and flow straight through
0→5.

Then, by case:

- **Backend/devops dependency → REFUSE.** Stop with a ≤50w explanation of *what*
  blocks you (which piece needs backend/server/container/devops) **plus a concrete
  suggestion** (e.g. "stub locally", "split the feature", "defer to the backend
  agent"). Do not implement that part.
- **Genuine open question / PRD gap / contradiction / arch conflict, and you're
  very sure it needs the user** → stop, ask **one** clear question (or raise the
  one issue) in ≤50w. Meanwhile, continue everything that does **not** depend on the
  answer. Don't stop for things you can decide sensibly yourself.
- **User input changes the PRD** → edit `prd.md` with the **minimum** change,
  `git -C ~ add` it, and continue. No broad rewrites.

### 2 — Commit the PRD  (commit 1, in the `~` repo)
Once the gap-check is settled (clean PRD = implicit go; otherwise after the user's
answer/green light): commit **only the PRD** in the `~` repo.
`git -C ~ add <taskdir>/prd.md && git -C ~ commit -m "docs(orion): prd for <task> [<id>]"`

### 3 — Design + tasks  (commit 2, in the `~` repo)
Write `design.md` and `tasks.md` per `~/ai/workflow.md` (design = architecture / data
flow / signatures / open-questions-to-resolve-in-impl; tasks = file-by-file changes +
per-task verification). Mine `~/git/track` for reference but **rethink its choices —
don't port flaws.** `git -C ~ add` both as you create them. Stop here **only if
strictly needed**; otherwise commit and continue:
`git -C ~ commit -m "docs(orion): design+tasks for <task> [<id>]"`

### 4 — Implement  (code in the `orion` repo — left UNCOMMITTED)
Write the code per the tasks. Follow the arch (route every user action through
`InteractionController`; platform split via conditional imports, not `kIsWeb`;
match surrounding style; comments only when genuinely needed). Then:

- Write/append `<taskdir>/review.md` — a short, **numbered** verification checklist
  for what you built. `git -C ~ add` it but **do not commit it** (it evolves during
  the user's testing rounds).
- Run **`flutter analyze`** (from `~/git/orion`) and fix what it flags before
  declaring done. Run any existing unit tests the change touches.
- **Do NOT run, serve, or build the app yourself** and **do NOT commit the code.**
  The user tests it and commits after. Leave the orion working tree dirty.

### 5 — Report  (≤50w)
End with a ≤50w report in three labelled parts:
- **Done** — what was built.
- **Apply** — exact commands to see it (`flutter pub get` / hot-restart / `flutter run -d chrome` — only the steps actually needed).
- **Test** — a few concrete checks.

Remind in one clause: when the user commits the tested code in `~/git/orion`, the
message should reference `[<id>]`.

## Commit protocol (two repos — keep them straight)

- **Workflow docs** (`prd.md`, `design.md`, `tasks.md`, `review.md`) live in the
  **`~` repo** → always `git -C ~ …`, message style `docs(orion): … [<id>]`.
- **Code** lives in the **`~/git/orion` repo** → you **leave it uncommitted**; the
  user commits it (referencing `[<id>]`) after testing.
- **Two commits total from you:** (1) PRD, (2) design+tasks. `review.md` is staged
  but not committed.
- **Never `git push`** — either repo, ever.

## Word caps

Every **interactive** reply while in this mode — questions, refusals, the final
report — is capped at **≤50 words** on the prose body. The cap does not apply to
tool calls, code you write, or files you write. Respect an explicit `Nw-` override.

## Hard rules

- **Stop only when the user's input is genuinely required** — open question, PRD
  gap/contradiction/arch conflict you're sure about, or a backend/devops refusal.
  Everything else: decide and keep going.
- **Refuse backend/server/container/devops work** — ≤50w, name the blocker, suggest
  a path; don't implement it.
- **Don't run the app; don't commit code.** Hand off with Apply/Test; the user tests.
- **`flutter analyze` is the done-gate** — clean before you report.
- **Stage every workflow doc at creation** (`git -C ~ add`).
- **Don't feature-creep the PRD.** Implement the spec, not your wishlist.
