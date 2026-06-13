---
name: wrap-up
description: Wrap up the current line of work so it is testable both locally and on the remote — verify the build, commit relevant changes with the Claude co-author trailer, push the current feature branch (this skill explicitly authorizes the push), and report what the remote preview can and cannot test. Triggered when the user types /wrap-up.
---

# /wrap-up

Wrap up the current line of work so it can be tested **locally** (front + backend)
and on the **remote** (whatever the push builds). Run the steps in order. If a
build/verify step fails, stop and report — never push broken code.

This skill is the one place push is pre-authorized. Still: **only push the current
feature branch**, never the default branch, and never merge to main, unless the
user explicitly says so in the same request.

## 1. Scope the work
- Current repo + branch: `git rev-parse --abbrev-ref HEAD`.
- If on the default branch (`main`/`master`), do NOT commit feature work there —
  create/switch to `feature/<slug>` first (ask for a slug if it isn't obvious).
- `git status` — identify the relevant uncommitted changes. If something looks
  unrelated (left by another agent/branch), flag it and exclude it; don't sweep
  it into the commit.

## 2. Verify LOCAL testability (before committing)
- Run the build / typecheck (e.g. `yarn build`); run the quick e2e if it's fast.
- Confirm there is a **one-command local run** that brings up the backend(s) +
  frontend together (e.g. `scripts/dev/local/run-stack.sh`). If it's missing,
  create it — never leave the user raw `docker`/`yarn dev` commands to paste.
- If anything fails, fix it or report; do not proceed to push.

## 3. Commit the relevant changes
- Stage and commit with a concise message. End every commit message with the
  Claude co-author trailer (per the environment's commit rule), e.g.:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- Also commit any companion repos that hold this work (e.g. the `~/` workflow
  repo) so nothing dangles — but do not push the personal `~/` repo.
- Leave every working tree clean: nothing unstaged, uncommitted, or
  untracked-and-not-ignored.

## 4. Push the feature branch
- `git push -u origin <branch>` for the code repo's current branch.
- A push typically triggers CI: a **frontend preview slot** for the branch.
- Do not push `main`; do not merge; do not deploy the api unless explicitly asked.

## 5. Report REMOTE testability honestly
- Surface CI status and the preview URL the push produces (e.g. `/web/<slug>/`).
- State clearly what the remote preview CAN and CANNOT test. In particular, if
  the repo deploys the **backend/api only from `main`**, a branch preview's
  frontend still talks to the **main** backend — so new backend code is **not**
  on the remote until merged to main. Say this plainly.
- If the change needs backend-on-remote to be exercised, offer the path (merge to
  main → staging deploy, or a manual api deploy) but do not take it without an OK.

## 6. Final summary (concise)
- Branch + commits pushed.
- The single local test command.
- Remote preview URL + exactly what it can/can't test (the api-from-main caveat).
- Confirmation that all working trees are clean.
