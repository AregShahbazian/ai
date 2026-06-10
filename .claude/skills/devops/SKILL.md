---
name: devops
description: Implement an Orion DevOps/infra task end-to-end from an existing PRD — strict gap-check, then PRD→design+tasks→implementation in one go, stopping only when your input is genuinely required. Triggered when the user types /devops <phase/task-slug> (or a devops/<task-slug>). DevOps only (edge/Caddy, CI/CD, VPS, Docker, later the backend); refuses pure Flutter feature work (defers to /implement). May SSH into the VPS to provision/verify. Enforces idempotent provisioning, the word caps, the two-repo commit split, and the "leave code uncommitted for the user to test" handoff.
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
---

# DevOps Mode — Orion infra/delivery task, one prompt

Drive a single Orion **DevOps/infra** task from an **already-written PRD** all the
way to working (uncommitted) code/config, in one pass. The PRD exists before you're
invoked. The ideal run is: read PRD → strict gap-check → commit PRD → design+tasks
→ commit them → implement → lint/verify → ≤50w report. **Stop only when the user's
input is genuinely required.** Stay in this mode across turns until the report is
delivered or the user exits.

This is the devops counterpart of `/implement` (frontend) — same workflow, same
loop, same commit protocol; only the **scope** and the **done-gate** differ. It
does **not** re-document the shared loops. Lean on:

- `~/ai/workflow.md` — PRD/design/tasks/review phase definitions, the `[id]`
  commit-linking rule, "stage new docs at creation" (`git -C ~ add`), the `Nw-`
  word-cap shorthand.
- `~/ai/orion/workflow.md` — the Default feature loop, the per-task path layout, the
  How-to-apply / What-to-test handoff.
- **DevOps context — read before any non-trivial infra work:**
  - `~/ai/orion/devops.md` — the DevOps **concept epic** (what's in it, what's not).
  - `~/ai/orion/devops/stack.md` — the locked backend stack (Caddy → Dart `shelf`
    → Postgres/PostGIS, Compose, ghcr, dbmate) for when the backend lands.
  - `~/ai/orion/devops/sources.md` + the `~/ai/orion/discussions/2026-06-08-*.md`
    set — the deploy/staging/release decisions (Docker adoption, staging topology,
    API downtime/scaling, per-feature staging, tag-to-release gate).
  - `~/git/orion/.github/workflows/ci.yml` and the edge tooling under
    `scripts/dev/{local,remote}/edge/` (pre-migration: `deploy/` + `deploy/vps/`).

## Scope — devops/infra only

You handle delivery and infrastructure: the **Caddy edge**, **CI/CD** (`ci.yml`,
GitHub Actions, environments/gates), **VPS provisioning** + edge ops scripts,
**Docker/Compose** (epic), the registry, migrations, and — when it lands — the
**Dart backend** (`backend/`, API, Postgres/PostGIS). You do **not** handle Flutter
app features (`lib/`, widgets, state, map, GPX, settings). If the task is really a
frontend feature, **refuse** and defer to `/implement` (see below).

## Input

Invoked as `/devops <phase/task-slug>` — e.g. `/devops phase-12/edge` — or a
`/devops <epic-task-slug>` under the epic.

Resolve the slug to the task dir, in order:
1. `~/ai/orion/mvp/<slug>/` (e.g. `~/ai/orion/mvp/phase-12/`) — note Phase 12's PRD
   is at `~/ai/orion/mvp/phase-12/prd.md` (the phase dir is the task dir).
2. `~/ai/orion/devops/<task>/` for epic tasks.
3. If not found, glob `~/ai/orion/**/<task>/prd.md` and `~/ai/orion/mvp/**/prd.md`.
4. If still missing or **ambiguous**, stop with a ≤50w line stating what you looked
   for and asking which task. Do not guess.

The PRD is `<taskdir>/prd.md`. Its frontmatter `id` is the link used in commits.

## The loop

### 0 — Load context
Read `prd.md` and its `id`. Skim `~/ai/orion/README.md` + `~/ai/orion/devops.md` for
where the task sits. Read the relevant DevOps docs/discussions (above) and the
**relevant** existing config the task touches (`ci.yml`, edge scripts, Caddyfile,
service unit). Don't read the whole tree — scope to what the PRD implies.

### 1 — Strict gap-check (the only place you decide to stop)
Read the PRD as a serious production spec and look **only** for things that would
actually block a correct implementation:

- Something material **left out or unclear** (e.g. unstated domain/hostname, env
  mapping, secret, or VPS access you can't infer).
- A **contradiction** within the PRD.
- A **conflict** with the locked stack/decisions (fights the Caddy-edge model, the
  prod/staging/tag-gate flow, the "Docker only when the backend lands" line, the
  idempotent-provisioning rule, or the URL/index-structure-untouched constraint).
- A **frontend dependency** that really belongs to `/implement`.

Be strict the other way too: **do not overthink, invent infra, or pad with unlikely
ops edge cases** that don't hinder a serious production app. A clean-enough PRD gets
**no stop** — treat the invocation as the green light and flow straight through 0→5.

Then, by case:

- **Frontend (Flutter `lib/`) dependency → REFUSE.** Stop with a ≤50w explanation of
  *what* belongs to the app, plus "defer to `/implement`". Don't implement it.
- **Genuine open question / PRD gap / contradiction / decision conflict, and you're
  very sure it needs the user** → stop, ask **one** clear question in ≤50w. Meanwhile
  continue everything that does **not** depend on the answer. Don't stop for things
  you can decide sensibly yourself. (Common one: the exact domain/sslip.io hostname
  for HTTPS — ask only if the PRD leaves it open and it blocks you.)
- **User input changes the PRD** → edit `prd.md` with the **minimum** change,
  `git -C ~ add` it, and continue. No broad rewrites.

### 2 — Commit the PRD  (commit 1, in the `~` repo)
Once the gap-check is settled (clean PRD = implicit go): commit **only the PRD**.
`git -C ~ add <taskdir>/prd.md && git -C ~ commit -m "docs(orion): prd for <task> [<id>]"`

### 3 — Design + tasks  (commit 2, in the `~` repo)
Write `design.md` and `tasks.md` per `~/ai/workflow.md` (design = topology / deploy
flow / file & service layout / config & secrets / open-questions-to-resolve-in-impl;
tasks = file-by-file changes + per-task verification). `git -C ~ add` both as you
create them. Stop here **only if strictly needed**; otherwise:
`git -C ~ commit -m "docs(orion): design+tasks for <task> [<id>]"`

### 4 — Implement  (code/config in the `orion` repo — left UNCOMMITTED)
Write the scripts/config/workflows per the tasks. Hold to the infra rules:

- **Idempotent provisioning** — any setup/provision script must **check-then-act**
  per step so it's safe to run anytime against a live system; never destructive.
- **Edge scripts split** — laptop wrappers in `scripts/dev/local/edge/` (thin SSH
  wrappers; creds via the gitignored key, never a password), on-box scripts in
  `scripts/dev/remote/edge/`. Keep them mirrored.
- **Secrets stay gitignored** — the SSH key (`…/edge/.secrets/orion_ci`) and any
  `deploy.conf`/`vps.env`; never commit a secret, always provide a `.example`.
- **Keep CI honest** — match `ci.yml`'s existing structure; don't break the
  URL/index layout the PRD says to leave untouched.
- Match surrounding shell/YAML style; `set -euo pipefail`; comments only when
  genuinely needed.

Then verify (the done-gate, below). Write/append `<taskdir>/review.md` — a short,
**numbered** verification checklist for what you built. `git -C ~ add` it but **do
not commit it** (it evolves during the user's testing rounds). **Do not commit the
code.** Leave the orion working tree dirty for the user.

### Done-gate — lint + verify (replaces frontend's `flutter analyze`)
- **`shellcheck`** every script you wrote/changed (and `caddy validate` / a YAML
  parse where applicable); fix what they flag before declaring done.
- **Verify against the real VPS when the task is about live infra** — you MAY SSH in
  using the gitignored key (`ssh -i <…/edge/.secrets/orion_ci> -p $VPS_PORT
  $VPS_USER@$VPS_HOST`, facts from `vps.env`). **Read-only checks are free**
  (`systemctl status`, `journalctl`, `curl -sI`, `ls`, `caddy version`). **Any state
  change on the VPS** (restart/stop, install, file writes, deploys, firewall) needs
  the user's **explicit OK first** — propose the exact command and wait. Prefer
  verifying through the idempotent setup/ops scripts rather than ad-hoc commands.
- **Don't trigger a real deploy or push** to land the change — hand off; the user
  tests and commits.

### 5 — Report  (≤50w)
End with a ≤50w report in three labelled parts:
- **Done** — what was built/changed.
- **Apply** — exact commands to put it in effect (run the setup/ops script, push the
  branch to fire CI, etc. — only the steps actually needed).
- **Test** — a few concrete checks (curl the HTTPS URL, `systemctl status`, watch the
  CI run, confirm the right env got the build).

### 6 — Suggest verification/tests  (separate ≤50w, after the user has tested)
Once built and the user has tested, **before any push**, add a **separate ≤50w**
message suggesting durable verification worth adding — a smoke/health-check script,
a CI assertion, or (when the backend lands) unit/integration tests per
`~/ai/orion/dev/testing/prd.md`. Keep it a **suggestion** — short, useful only.
**Don't run real deploys or destructive checks yourself unless explicitly asked.**

Then wait: the **user approves** → you implement → the **user runs/verifies** and
**green-lights the commit**. When the user commits the tested code in `~/git/orion`,
the message references `[<id>]`. Never push.

## Commit protocol (two repos — keep them straight)

- **Workflow docs** (`prd.md`, `design.md`, `tasks.md`, `review.md`) live in the
  **`~` repo** → always `git -C ~ …`, message style `docs(orion): … [<id>]`.
- **Code/config** (scripts, `ci.yml`, Caddyfile, units, Dockerfiles, `backend/`)
  lives in **`~/git/orion`** → you **leave it uncommitted**; the user commits it
  (referencing `[<id>]`) after testing.
- **Two commits total from you:** (1) PRD, (2) design+tasks. `review.md` staged, not
  committed.
- **Never `git push`** — either repo, ever.

## Word caps

Every **interactive** reply while in this mode — questions, refusals, the final
report — is capped at **≤50 words** on the prose body. The cap does not apply to
tool calls, code you write, or files you write. Respect an explicit `Nw-` override.

## Hard rules

- **Stop only when the user's input is genuinely required** — open question, PRD
  gap/contradiction/decision conflict you're sure about, or a frontend refusal.
  Everything else: decide and keep going.
- **Refuse frontend (Flutter `lib/`) feature work** — ≤50w, name the blocker, defer
  to `/implement`; don't implement it.
- **VPS writes need explicit OK** — read-only SSH inspection is free; any state
  change (restart/install/deploy/file-write/firewall) is proposed and waits for the
  user. Read the target before overwriting; surface surprises instead of clobbering.
- **Provisioning is idempotent + non-destructive** — check-then-act every step.
- **Secrets stay gitignored**, always with a committed `.example`. Never print a
  private key into a committed file or the chat.
- **Don't fire real deploys; don't commit code.** Hand off with Apply/Test; the user
  tests and commits.
- **Lint is the done-gate** — `shellcheck` (+ `caddy validate`/YAML check) clean
  before you report.
- **Stage every workflow doc at creation** (`git -C ~ add`).
- **Don't feature-creep the PRD.** Implement the spec, not your wishlist.
