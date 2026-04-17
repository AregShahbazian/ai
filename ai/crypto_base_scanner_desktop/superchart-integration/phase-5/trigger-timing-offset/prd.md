---
id: sc-replay-trigger-timing
---

# Phase 5: Replay Trigger Timing Offset — Research

Research task. The deliverable is a written report — no code changes, no staging,
no commits.

Both the TV and SC replay implementations share a one-candle timing offset that
affects smart trading. On a 1h chart, an alert or order time-trigger set for
`08:00` only fires when the replay's current time reaches `09:00` — one candle
late. If the user plays up to `08:00` without it firing and then switches to the
`1m` resolution and steps one candle forward to `08:01`, the trigger also fires
there.

A related symptom: because of the same offset, a trade placed on the very first
candle of a session cannot be undone by stepping back — the timestamp the
frontend sends to the backend is not recognised as a revert target for that first
trade.

Desired behaviour: a time-trigger set for `08:00` should fire when the replay's
current time is `08:00`, for both alerts (frontend) and order time-triggers
(backend), on every resolution.

The report determines whether this can be fixed purely on the frontend or whether
the backend must change too, and documents the exact changes required on each
side.

---

## Scope

### In scope

- Investigation of the frontend replay engine, alerts, and order time-trigger
  code paths in this repo (SC replay under
  `ai/superchart-integration/phase-5/` implementation + legacy TV replay for
  cross-reference).
- Investigation of the backend (`crypto_base_scanner`) code paths that consume
  replay timestamps from the frontend.
- Documentation of findings in `research.md` inside this PRD's folder.

### Out of scope

- Any code changes — this PRD produces a report only.
- Implementation plan beyond naming the concrete frontend/backend edits needed.
  (A follow-up PRD will turn the recommendations into a design + tasks cycle.)
- New features unrelated to the timing offset.

---

## Requirements

The deliverable is a single file `research.md` living next to this PRD. It must
cover all of the following, in this order.

### 1. Origin of the one-candle offset

Identify precisely where the offset is introduced:

- Which variable holds the "current replay time" value used for trigger
  evaluation.
- Which controller/file/line advances it, and by how much per tick.
- Whether the offset lives in the replay engine itself, the candle-feed layer,
  or in the sites that consume the timestamp.
- Reference file paths with `file:line` so the reader can jump directly to the
  source.

### 2. Why the current behaviour exists

Look for intentional design justification for the one-candle lag:

- Search prior commits (TV and SC replay) and PRD/design docs for any mention
  of "current time", "last candle", "close time", "seen at", or similar.
- Quote the relevant note/commit if one exists.
- If no justification is found, state that explicitly and hypothesise why it
  was written that way (e.g. "close-time of the current candle" semantics vs
  "open-time of the next candle").

### 3. Frontend → backend timestamp flow

Enumerate every frontend site that sends a replay-time timestamp to the
backend. For each site:

- The file and function that builds the request.
- The exact field name and format (seconds vs milliseconds, open vs close).
- The backend endpoint it hits.
- What the backend does with the value — which column is written, which
  comparison is performed, which service method consumes it.
- Whether the offset is already compensated anywhere along the path.

Required sites to cover (add others if found):

- Order time-trigger placement (smart trading order with a time condition).
- `last_candle_seen_at` / equivalent progress marker.
- `checkResetToPossible` probe.
- `PUT /backtests/:id/reset` (step-back / reset-to).
- Any trade placement call that records a replay timestamp.

### 4. Required changes

Specify the exact edits needed to make `08:00` fire at `08:00`:

- **Frontend changes** — file, function, and the change in semantics (e.g.
  "send `currentTime` instead of `currentTime + resolutionMs`"). List every
  call site that must be updated consistently.
- **Backend changes** — if any — with the same level of detail: controllers,
  services, comparison operators (`<` vs `<=`), column semantics.
- **Ripple effects** on each of:
  - Alert evaluation (frontend).
  - Order time-trigger evaluation (backend).
  - Position triggers (SL/TP/trailing) that rely on the same timestamp.
  - `last_candle_seen_at` semantics and anything that reads it.
  - `checkResetToPossible` and `PUT /backtests/:id/reset` — confirm step-back
    still lands on the correct candle after the fix.
  - The "first-trade cannot be undone via step-back" symptom — verify the fix
    resolves it, or call out a separate fix if not.

### 5. Frontend-only feasibility

Answer explicitly:

- Is a frontend-only fix feasible? Yes / No / Partial.
- If yes, what are its limits — which cases still misfire, which backend
  behaviours the frontend would be papering over.
- If no or partial, which specific backend comparison or column semantics
  force a coordinated change.
- Recommend the preferred path (frontend-only vs coordinated) with a one-line
  justification.

### 6. Risks and open questions

A short section capturing:

- Any code path the researcher could not fully trace and why.
- Any assumptions that need to be validated with a reproducer before the
  follow-up implementation PRD is written.
- Migration/compatibility concerns for in-flight replay sessions or persisted
  backtests if the semantics of a stored timestamp column change.

---

## Non-Requirements

- The report does **not** need to produce a design doc, task list, or code
  patch. Those belong to a follow-up PRD.
- The report does **not** need to cover non-replay (live) trading paths except
  where they share code with replay and the shared code is affected by the
  fix.
- No UI mockups, i18n keys, or storybook entries — this is a research task.
- No build or test runs — investigation is read-only (`Read`, `Grep`, `Glob`,
  and backend repo reads under `$CRYPTO_BASE_SCANNER_DIR`).
