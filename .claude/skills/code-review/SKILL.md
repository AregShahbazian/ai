---
name: code-review
description: Review code quality of the current unpushed commits on the repo (or a specified range/working tree) — scalability without overengineering, fragile logic, inconsistencies, over-long units, extraction opportunities, comment quality. Read-only; suggests fixes grouped by severity, never applies them. Triggered when the user types /code-review.
allowed-tools: [Read, Glob, Grep, Bash]
---

# Code Review

Review the **changed code** for quality and report a **tight, prioritized list of
fixes/refactors — never apply them**. The bar: this project must stay **scalable
and expandable** for any future agent or person — minimum bugs, no spaghetti,
descriptive-but-concise comments.

This is a **read-only review**. Suggest; do not edit, run, or commit anything.

## Scope (what to review)

`repo root = git rev-parse --show-toplevel`. Pick the diff to review:

1. **No args (default)** — the **unpushed commits** plus any uncommitted work:
   - If the branch has an upstream: `git diff @{u}...HEAD` **and** `git diff` /
     `git diff --staged` for working-tree changes.
   - If no upstream: diff against the base branch — `git diff main...HEAD` (or
     `master`) — plus working-tree changes. Say which base you used.
2. **`working tree` / `staged`** — review only `git diff` (and `--staged`).
3. **A ref / range / SHA(s)** (e.g. `HEAD~3..HEAD`, a branch, a commit) — review
   `git diff <range>` exactly as given.

Get the file list with `git diff --name-only <range>`, read the **full changed
files** (not just the hunks) so structure/length is judged in context, and skim
neighbouring code to judge **consistency** with existing patterns. Focus on
changed/added code; flag pre-existing issues only if the change makes them worse.

## What to check (Dart/Flutter lens)

- **Scalability vs overengineering** — will this extend cleanly, or is it rigid?
  Equally: is it *over*-abstracted for what it does? Flag both. Prefer the simplest
  thing that won't need a rewrite to grow.
- **Fragile logic / bugs** — async gaps (`await` then `context`/`mounted`), state
  desync, races, unhandled null/empty/error paths, `setState` after dispose,
  listeners/streams/controllers not disposed, off-by-one, silent catches.
- **Consistency** — naming, file/dir layout, state patterns, and idioms match the
  surrounding code. New one-off patterns that diverge are a smell.
- **Size / extraction** — methods, classes, and files that are too long or do too
  much. Rough flags: method >~40 lines or many responsibilities; widget `build`
  doing non-trivial logic; file >~300 lines; deeply nested widget trees that want
  extracting into named widgets.
- **Flutter idioms** — `const` where possible, avoid rebuilding heavy subtrees,
  `ValueListenable`/keys used correctly, no business logic in `build`.
- **Comments** — descriptive **and** concise. Flag missing *why* on non-obvious
  logic, redundant *what* comments, and stale/contradictory comments.

## Output (keep it tight — well under ~100 lines)

One-line verdict, then findings grouped by severity, **highest first**. **Label every
finding** with a severity-prefixed id (`C1`, `C2`, `H1`, `M1`, `L1`, …) so the user
can refer to them ("apply C1 and M2"). Each finding is **one line**:
`**<id>** \`path:line\` — problem → suggested fix`. Omit empty severities. Be
selective: the most valuable findings, not an exhaustive dump (cap ~5 per group).

```
## Code Review — <range reviewed> (<n> files)

**Verdict:** <one line — is it scalable / clean, or are there real concerns?>

### 🔴 Critical — bugs / will break or not scale
- **C1** `lib/...:NN` — <problem> → <fix>
- **C2** ...

### 🟠 High — fragile logic, risky patterns, real inconsistency
- **H1** ...

### 🟡 Medium — structure: extract / shorten / dedupe
- **M1** ...

### 🟢 Low — naming, comments, polish
- **L1** ...
```

Number within each severity (C1, C2…; H1, H2…). Close with a one-line pointer to the
ids worth doing first, and invite the user to pick ids to apply.

If nothing material: say so plainly in the verdict and list only minor polish (or
"no changes suggested"). Don't invent issues to fill groups.

## Rules
- **Read-only.** Suggest fixes; never edit/apply. (The user applies what they pick.)
- **Concise & prioritized.** One line per finding, grouped by severity. No essays,
  no re-explaining the code back to them.
- **Cite `path:line`** so findings are actionable.
- **Honest calibration.** Don't inflate severity; "clean" is a valid result.
- Never run/build the app.
