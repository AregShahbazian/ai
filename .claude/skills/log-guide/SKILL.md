---
name: log-guide
description: Enter "log-guide mode" — instrument a code flow the user names with numbered, tagged console logs, then guide the user through it one step at a time (user reloads the app, checks logs, says "next step"), so they understand the code/flow. Triggered when the user types /log-guide <flow description>. /log-guide clear removes all guide logs again. Claude never runs the app itself — the user drives, Claude guides.
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
---

# Log-Guide Mode

The user wants to **understand a code flow** (often one Claude built) by seeing
it run. `/log-guide <flow description>` means: add rich, tagged logs along that
flow's code path, then hand the user a **step-by-step walkthrough** — what to do
in the app at each step, and which log(s) with which data to look at at that
point. This is a teaching tool, not debugging (that's `/bugfix`).

`/log-guide clear` (or "clear the log guide") means: remove every guide log
again — see **Clearing** below.

## Adding the logs

1. **Trace the flow first.** Read the code path end-to-end and identify the
   handful of places that tell the story: entry point (user action / event),
   key transformations, decision branches, and the final effect (render, draw,
   dispatch, network send). Prefer 4–10 well-chosen logs over logging
   everything.
2. **Tag and number every log** in flow order so they're filterable and
   referenceable:
   ```js
   console.log("[LOG-GUIDE 3] script parsed → drawing commands", { count: commands.length, first: commands[0] }, result)
   ```
   - The tag is always `[LOG-GUIDE <n>]`, numbered in the order the flow runs.
     One shared sequence across all files. Add a short human label after the tag
     saying what just happened.
   - **Second argument: a small object with the relevant fields expanded** — the
     2–5 values that matter at that step, visible without clicking anything.
   - **Third argument (optional): the full object(s)**, expandable in devtools
     for when the user wants to dig.
   - If a logged object (or anything nested in it) may contain bignumbers or
     other non-plain values, pass it through `util.reparse(...)` so it prints
     as plain data (`import util from "~/util/util"` in this repo — match the
     file's existing import style).
3. **Logs must not change behavior.** No new side effects, no reordering, no
   extra function calls beyond building the log payload. If computing a payload
   is expensive or could throw, guard it.
4. Branches: if the flow forks (e.g. success vs. validation error), log both
   sides with the same number and a suffix — `[LOG-GUIDE 4a]` / `[LOG-GUIDE 4b]`
   — and say in the walkthrough which one the user should expect.

## The walkthrough (the actual deliverable)

After adding the logs, print a numbered checklist the user follows **in the
app**. The user performs the actions — never run, build, or serve the app
yourself; if it isn't running, tell them how to start it (in this repo the dev
webserver is normally already running — a reload is enough).

Format each step as:

> **Step 2 — Submit the script** (click *Save* in the editor)
> → look for `[LOG-GUIDE 3]` and `[LOG-GUIDE 4]`:
> `3` shows the parsed commands (`count` should match your script's draw calls);
> `4` fires once per command as it's converted to a chart primitive — check
> `type` and `coordinates` on each.

So each step names: the user action, the log number(s) that should appear, and
**what to look at in the data and why it matters for understanding the flow**.
Close the walkthrough with the devtools filter tip: type `LOG-GUIDE` in the
console filter box to see only these logs.

Then wait. Stay in log-guide mode across turns: answer questions about what
they're seeing, add/adjust logs on request, and extend the walkthrough deeper
into the flow if asked.

## Stepped iteration (the default rhythm)

Guide **one step at a time**, not the whole flow at once:

1. Add/adjust the logs for the current step only.
2. Stop and let the user reload the app (web) and check the console. Give them
   **under 30 words** of pointers: what to do, which `[LOG-GUIDE n]` to look at,
   which fields matter.
3. Wait. Answer questions about what they see.
4. When the user says **"next step"**, add/remove/change logs to guide through
   the next part of the flow, and repeat from 2.

Keep earlier logs in place unless they're noisy — remove or renumber only when
they'd drown out the current step.

## Clearing

On `/log-guide clear`:
- Find every guide log: `grep -rn "LOG-GUIDE" src/` (adapt root to the repo).
- Remove the log lines **and** any imports/variables added solely for them.
- Report which files were cleaned.

Also offer to clear when the user signals they're done ("got it", "makes
sense now") — but don't remove logs unprompted.

## Rules

- **Teaching, not fixing.** If you spot a bug while instrumenting, point it out
  but don't fix it in this mode — suggest switching to `/bugfix` or a normal edit.
- **You never run the app** — the user does; you provide the steps.
- **Every log is tagged `[LOG-GUIDE n]`** — never add untagged guide logs, so
  clearing stays a simple grep.
- Keep the walkthrough tight: one line of action, then what the logs show.
