---
id: sc-replay-reset-orphans
---

# Phase 5: Reset-To Orphan Trades — Research

Research task. The deliverable is a written report — no code changes, no staging,
no commits.

Both the TV and SC smart replay implementations exhibit the same bug when
stepping back through filled smart-trading orders. The reset endpoint is called
but the affected trades are not removed from the backend's response, leaving
them visually "hanging in the air" past the new replay time, and causing
follow-up resets on every subsequent step.

## Reproducer

1. Start a smart replay session on any market.
2. Place a sell ladder of 10 entry orders staggered above the current price.
3. Play forward. Price rises through the ladder; entry orders fill across
   several non-adjacent candles (some candles between fills are empty).
4. Once at least a few orders have filled, step back to the candle just before
   the most recent fill.
5. Observe:
   - The frontend calls `PATCH /backtests/:id/reset` with the new (earlier)
     replay time.
   - The backend response still contains the trade(s) that should have been
     rolled back. The chart shows the trades sitting at their original
     timestamps, which are now in the future relative to the replay cursor.
6. Step back further, candle by candle (including over candles where no order
   filled).
   - The reset endpoint is called on every step — even the empty candles —
     presumably because the controller keeps seeing the still-present
     orphaned trades and treats them as a divergence.
   - None of the orphaned trades disappear regardless of how far back you step.
7. Stop the session, then resume the same backtest from the widget. The
   orphans are still there.

The same reproducer applies to the legacy TV replay implementation, so the fix
almost certainly lives in the backend (`crypto_base_scanner`) — but the frontend
side needs to be ruled out (or co-fixed) before that can be claimed.

Desired behaviour: stepping back past the timestamp of a filled smart order
must remove that trade from the backtest's persisted state on the backend, so
the next response no longer includes it and the chart no longer shows it.

The report determines whether this is purely a backend bug, purely a frontend
bug, or a coordinated issue, and documents the exact changes required on each
side.

---

## Scope

### In scope

- Investigation of the frontend `resetTo` flow in both SC
  (`SmartReplayController.resetTo` /
  `super-chart/controllers/smart-replay-controller.js`) and the equivalent TV
  path under `tradingview/controllers/replay/`, including:
  - The `checkResetToPossible` probe.
  - The `_resetBacktest` / `PATCH /backtests/:id/reset` request builder.
  - The response-handling code that rebuilds local trading info after the
    reset.
  - The candle-step loop that decides when to call `resetTo` (to explain why
    reset is fired on empty candles after the first orphan appears).
- Investigation of the backend (`crypto_base_scanner`) controller, service,
  and persistence layer that handle `PATCH /backtests/:id/reset`, including:
  - Which records (`backtest_positions`, `backtest_trades`,
    `backtest_orders`, balances) are rolled back.
  - The exact comparison used to decide which records survive vs. are
    deleted (`<`, `<=`, time vs. candle index, open- vs. close-time).
  - Whether filled orders that closed *partially* before the reset point are
    handled differently from fully-filled ones.
- Documentation of findings in `research.md` inside this PRD's folder.

### Out of scope

- Any code changes — this PRD produces a report only.
- A design or task list for the fix. (A follow-up PRD will turn the
  recommendations into a design + tasks cycle.)
- Default-mode replay (which keeps trades in client-side state, not on the
  backend). It is only relevant if it shares helper code with the smart path
  and that helper is implicated.
- New features unrelated to step-back rollback.
- Investigation of the
  [trigger-timing-offset](../trigger-timing-offset/prd.md) one-candle lag,
  except where the lag plausibly *causes* the orphan symptom (e.g. the reset
  timestamp arrives at the backend with a one-candle skew that lands just
  past the trade row instead of just before it). Cross-reference the other
  PRD if so.

---

## Requirements

The deliverable is a single file `research.md` living next to this PRD. It must
cover all of the following, in this order.

### 1. Symptom confirmation

Confirm the reproducer against the current SC code path on `master` /
`feature/superchart-integration`. Note the exact:

- Backend endpoint hit (path, method, request body shape).
- Backtest record fields read from the response immediately after the reset
  call.
- Which of those fields still contain the orphan rows (positions vs. orders
  vs. trades — they may not all behave the same way).

If you cannot run the reproducer, state that explicitly and base the report on
a static read of the code only — but flag every conclusion that depends on
runtime evidence.

### 2. Frontend reset-to flow

Trace the call chain that runs when the user clicks step-back during a smart
session and a reset is needed. For each step:

- File and function (`file:line`).
- What state it reads, what it computes, what it dispatches.
- Which timestamp value is sent to the backend, in which unit (seconds vs
  milliseconds, open vs close, candle-aligned vs raw).
- Whether the timestamp is rounded, floored, or offset before being sent.

Cover at minimum:

- The step-back hotkey / button entry point (`handleStepBack` →
  `_revertAndSeek` in `replay-controller.js`).
- `SmartReplayController.resetTo` and its `checkResetToPossible` probe.
- `_resetBacktest` — the actual `PATCH /backtests/:id/reset` request
  builder.
- `loadBacktestTradingInfo` — the response-handling path that rebuilds the
  Redux trading info after the reset.
- The candle-step instrumentation that decides "we need another reset on
  this empty candle too" — explain why an empty candle still triggers a
  reset and whether this is correct given the current backend semantics.

### 3. Backend reset endpoint

Trace `PATCH /backtests/:id/reset` end-to-end in `crypto_base_scanner`:

- Controller action and the strong params it accepts.
- The service object / method that performs the rollback.
- Every database operation it issues (which tables, which `WHERE` clauses,
  which comparison operators).
- How it decides which `backtest_positions`, `backtest_orders`, and
  `backtest_trades` rows to delete vs. keep.
- How balances are recomputed after the rollback.
- The shape of the response — what the frontend gets back and which fields
  drive the orphaned-trade rendering on the chart.

Required `file:line` references for every comparison operator that touches
`reset_to`, `created_at`, `filled_at`, or any other timestamp-bearing column
on the backtest tables.

### 4. Hypothesis: why the orphans survive

Based on the trace, propose a concrete root cause hypothesis for *each* of the
observed symptoms:

1. The trade at the closest fill is not removed even though `resetTo` is
   called with a time strictly earlier than its fill timestamp.
2. Subsequent step-backs continue to call reset on every candle.
3. Stop + resume preserves the orphans (rules out an in-memory frontend
   cache as the sole cause).
4. The bug is identical between TV and SC — implying shared backend cause
   or identical-but-bugged client code.

For each symptom, identify the most likely failing comparison or missing
deletion, with the `file:line` reference.

### 5. Required changes

Specify the exact edits needed. Match the structure of the
trigger-timing-offset PRD's "Required changes" section:

- **Backend changes** — controllers, services, comparison operators (`<` vs
  `<=`), column semantics. Name every file and function.
- **Frontend changes** — if any — with the same level of detail. List every
  call site that must be updated consistently.
- **Ripple effects** on each of:
  - `loadBacktestTradingInfo` and the Redux trading-info rebuild path.
  - The chart overlays that render trades, positions, and orders during
    smart replay.
  - `last_candle_seen_at` / progress markers — confirm the reset still
    rewinds them correctly.
  - Backtest stats (PnL, win-rate, position count) — confirm they
    recompute correctly after orphans are removed.
  - Resume-from-widget — verify resuming a previously-orphaned backtest
    after the fix produces a clean state (or document that a one-time
    backfill / migration is required for already-corrupted backtests).

### 6. Frontend-only feasibility

Answer explicitly:

- Is a frontend-only fix feasible? Yes / No / Partial.
- If yes, what does it do — filter the orphans out of the response on the
  client side as a workaround, and what are its limits (stats stay wrong on
  the backend, resume still shows orphans for users on older app versions,
  etc.).
- If no or partial, which specific backend behaviour forces a coordinated
  change.
- Recommend the preferred path (frontend-only workaround vs coordinated
  fix vs backend-only fix) with a one-line justification.

### 7. Risks and open questions

A short section capturing:

- Any code path the researcher could not fully trace and why.
- Any assumptions that need to be validated with a runtime reproducer
  before the follow-up implementation PRD is written.
- Migration concerns for backtests that already contain orphan trades —
  do existing rows need a one-time cleanup script after the fix lands, or
  is a no-op acceptable?
- Whether the trigger-timing-offset PRD's expected fix would also resolve
  this bug as a side effect (cross-reference if so).

---

## Non-Requirements

- The report does **not** need to produce a design doc, task list, or code
  patch. Those belong to a follow-up PRD.
- The report does **not** need to cover default-mode replay's local
  step-back (which uses `ReplayTradingController.resetTo` against in-memory
  `trades[]`), unless the smart path shares the affected helper.
- No UI mockups, i18n keys, or storybook entries — this is a research task.
- No build or test runs — investigation is read-only (`Read`, `Grep`,
  `Glob`, and backend repo reads under `$CRYPTO_BASE_SCANNER_DIR`).
