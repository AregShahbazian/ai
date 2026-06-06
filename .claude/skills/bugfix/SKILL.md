---
name: bugfix
description: Enter "bugfix mode" — diagnose a bug from the user's description using logs, then suggest (not apply) a fix only once the root cause is confirmed. Triggered when the user types /bugfix. Operationalizes the Debugging Procedure in ~/ai/workflow.md, plus a hard rule that Claude never runs the dev server itself — it tells the user how to start it and waits for log output.
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
---

# Bugfix Mode

The user is reporting a bug and wants it **diagnosed via logs**, then a fix
**suggested only once the root cause is confirmed**. This skill follows the
**Debugging Procedure** and **Bugfix Tracking** sections in `~/ai/workflow.md` —
read those if you haven't; this skill is the at-a-glance, enforced version. Stay
in bugfix mode across turns until the bug is fixed or the user exits.

## The loop (from ~/ai/workflow.md → Debugging Procedure)

1. **User reports** — symptoms + reproduction steps. Ask for missing repro detail
   if needed.
2. **Analyze** — read the relevant code/docs, form a hypothesis for the root cause.
3. **Suggest where to look, don't fix yet** — describe the proposed fix in words,
   but do NOT apply it.
4. **Add logs** — place targeted log statements in the relevant code paths to
   confirm (or refute) the hypothesis, and to gather context in case it's wrong.
   Editing code to add logs is allowed; changing behavior to "fix" is not yet.
5. **Hand off to the user to reproduce** — see the dev-server rule below. Tell them
   how to run it and exactly what to do; then wait.
6. **User shares log output** — read it.
   - **Hypothesis confirmed** → describe the fix and **wait for the user's
     go-ahead before applying it**.
   - **Not confirmed** → use what the logs revealed to form a new hypothesis, add
     new logs, repeat from step 5.
7. If you can't form a hypothesis at all, skip straight to adding logs on the
   relevant paths to gather information, then build a hypothesis from the output.

**Never apply a fix before the hypothesis is confirmed with logs. Never remove the
logs before the user confirms the fix works.**

## Dev-server rule (the user's hard preference)

- **Do NOT start, run, build, or serve the app yourself.** No `flutter run`, no
  dev server, no `claude`-side execution of the app.
- Instead, **give the user the instructions** to run it — and only if it isn't
  already running. Keep it to the exact steps needed, e.g. for Orion (Flutter):
  `flutter run -d chrome` (or hot-restart `R` if already up). Adapt to the repo.
- After adding logs, tell the user: what to run (or to hot-restart if already
  running), what to do to reproduce, and to **paste the log output back here**.
- Then stop and wait for their log output. You may read code/docs while waiting,
  but take no app-running action.

## Suggesting the fix

- Only once the logs **clearly** confirm the root cause, present the fix:
  root cause (one or two lines, grounded in the log evidence) → the proposed
  change → which files. Then wait for the user's go-ahead before editing.
- Keep it tight — evidence and the change, not a narrative.

## Bugfix tracking (per ~/ai/workflow.md)

- After a confirmed fix, **remind** the user this can be tracked, and offer to
  write a `.fix.md` to `~/ai/orion/bugfix/` (or `~/ai/<repo>/bugfix/`) using the
  format in `~/ai/workflow.md` → Bugfix Tracking. Only create it when the user
  says so. Stage it with `git -C ~ add` once written.

## Rules

- **Diagnosis first, fix second.** No behavior-changing edits until the cause is
  confirmed by logs and the user gives the go-ahead.
- **You never run the app** — the user does; you provide the steps and read the logs.
- **Logs stay** until the user confirms the fix works, then clean them up.
- Stay in bugfix mode until the user says it's done (e.g. "fixed", "exit bugfix").
