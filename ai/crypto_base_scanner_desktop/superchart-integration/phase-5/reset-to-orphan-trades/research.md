---
id: sc-replay-reset-orphans
---

# Reset-To Orphan Trades — Research

## 1. Symptom confirmation

Reproduced in SC smart replay against current `feature/superchart-integration`
(and also confirmed on the legacy TV implementation — same bug, same root
cause).

- **Endpoint hit:** `PATCH /backtests/:id/reset`, body `{ reset_to: <seconds> }`
  (unix seconds, candle-aligned).
- **Client-observable response fields:** `backtest.backtest_orders`,
  `backtest.backtest_trades`, `backtest.backtest_positions` — all exposed raw
  on the Backtest entity (`app/api/api_v3/entities/backtest.rb:28-33`).
- **Which fields retain orphans:** *all three*. The trades stay, the orders
  stay, the position row stays — because the backend never touches them when
  the position's `open_time` is earlier than `reset_to`.

Scenario that triggers it: a smart sell-ladder with N entry orders that fill
on non-adjacent candles C₁ < C₂ < … < Cₙ, forming **one** open position with
`open_time = C₁`. Stepping back to any candle in `(C₁, Cₙ]` leaves the
position and all its child trades/orders intact.

## 2. Frontend reset-to flow (FE is clean)

Static read of the FE chain confirms the FE is doing the right thing:

- `replay-controller.js` → `handleStepBack` → `_revertAndSeek(time, …)`
- `smart-replay-controller.js:812` → `resetTo(time, {force})` → `_flushPendingReset`
- `_flushPendingReset` → `_resetBacktest(target)` → `PATCH /backtests/:id/reset`
  with `reset_to = target / 1000` (seconds), then rebuilds Redux trading info
  via `loadBacktestTradingInfo`.

The timestamp sent is the **cursor time in seconds**, candle-aligned, no
offset — matches what the backend expects. The reset re-fires on every
step-back because `loadBacktestTradingInfo` brings back a Backtest response
that still contains the orphans, so the next step-back again computes
`_hasChangesSince(target) === true` (the orphan trades have `time >= target`
so they count as "changes") and flushes another reset. This re-fire loop is
a *consequence* of the backend bug, not an FE bug — each reset is a
legitimate request to roll back to the new cursor, it's just that the
backend refuses to roll anything back.

## 3. Backend reset endpoint — the whole thing

**Controller action** (Grape V3):
`app/api/api_v3/backtests.rb:397-404`

The entire destructive path is inline, three lines:

```ruby
# backtests.rb:399
backtest.backtest_positions.where("open_time >= ?", params[:reset_to]).destroy_all
# backtests.rb:400
backtest.update(last_candle_seen_at: Util.normalize_time(params[:reset_to]))
# backtests.rb:401
backtest.update_stats
```

- **Comparator:** `>=` on `backtest_positions.open_time`. One column, one
  operator, one table.
- **Cascade:** trades and orders are only removed via
  `dependent: :delete_all` declared on `BacktestPosition`
  (`app/models/backtest_position.rb:13-14`). They are never queried
  directly by the reset endpoint.
- **`open_time` definition:**
  `app/models/concerns/position_calculations.rb:258` →
  `self.open_time = trades.first&.time || self.created_at.to_i`
  (i.e. first fill's time).

## 4. Root cause

A multi-fill entry ladder produces one `backtest_positions` row with
`open_time = C₁`. Stepping back to a cursor in `(C₁, Cₙ]` evaluates
`open_time >= reset_to` as **false**, so the position is kept, and because
no query ever touches `backtest_trades` or `backtest_orders` directly, all
its child rows survive too — including the ones with `time > reset_to`.
Only when the cursor crosses C₁ does the position itself finally qualify
for destruction and the cascade wipes the children.

This explains every observed symptom:

1. Orphans survive because the parent position anchor is `open_time = C₁`.
2. Reset re-fires on every step-back because the FE sees "post-cursor
   trades still present" and loops forever against an unresponsive backend.
3. Stop+resume preserves the orphans because they really are in the
   database — the response entity just reads raw DB rows.
4. TV / SC share the bug because both call the same endpoint and the bug
   lives in the endpoint, not the client.

## 5. Required changes

Two plausible fix shapes; pick one.

### Option A — backend position-rebuild (clean fix)

Rewrite the reset action as a `Backtest#reset_to(timestamp)` method,
~30-60 lines, with a test suite for the permutations. Must:

1. Delete `backtest_trades` with `time >= reset_to` (scoped to the
   backtest).
2. Delete `backtest_orders` created/filled after `reset_to` — pick the
   column carefully (`created_at` vs `filled_at`); partially-filled orders
   must have their fill state reset too.
3. For each surviving position that lost some trades, call
   `position.recalculate!`
   (`app/models/concerns/position_calculations.rb:10`) — re-derives
   `open_time`, `open_quantity`, `open_price`, `close_time`, `status`,
   stats from the remaining trades.
4. For positions that become trade-less, destroy them (or cancel, if
   created before `reset_to`).
5. For positions whose close trade was deleted (closed position stepping
   back past its close), flip `status` back to `open` via
   `recalculate(force_open: true)`.
6. Destroy positions where `open_time >= reset_to` after recalc (matches
   current behaviour for the simple case).
7. Leave the existing `update(last_candle_seen_at: …)` and
   `update_stats` calls in place.

**Risk:** non-trivial. The naive "widen the WHERE clause to also delete
positions with a late trade" approach is *wrong* — it would destroy the
parent and lose the earlier fills. The position-rebuild path has several
edge cases (closed→open reopen, partial fills, order status restoration)
that need explicit tests.

**Migration:** existing backtests already containing orphans will not be
cleaned retroactively; they'd need a one-off backfill script, or the user
deletes and re-runs the affected backtests.

### Option B — frontend block (pragmatic short-term)

Extend `checkResetToPossible` in `smart-replay-controller.js:762` to
include a new irreversible case: **open positions with more than one
entry fill, when the target cursor falls strictly between the first and
last fill times.** Same UX as the existing
`positionsPartiallyClosed` guard — warn and refuse the step.

Sketch (logic only):

```js
if (isOpen) {
  const entryTrades = entryOrders.reduce(
    (acc, {externalId}) => acc.concat(
      this._backtest.trades.filter(({externalOrderId}) => externalOrderId === externalId)
    ), []
  )
  if (entryTrades.length > 1) {
    const firstFill = Math.min(...entryTrades.map(t => t.time * 1000))
    const lastFill  = Math.max(...entryTrades.map(t => t.time * 1000))
    if (time > firstFill && time <= lastFill) irreversiblePositions.push(position)
  }
}
```

Needs a new i18n key along the lines of
`replay.positionsPartiallyOpened` so the warning is distinct from the
partially-closed case (optional — could reuse the existing key if
consistency is preferred).

**Limits:**
- Stats-on-resume of already-corrupted backtests stay wrong (same limit
  as Option A without migration).
- User loses the ability to step back through ladder fills — a usability
  regression, but matches the already-blocked partial-close case and
  aligns with the invariant "any reset that would need a recalc is
  forbidden".
- Does not help TV (unless the same guard is back-ported).

### Ripple effects (either option)

- `loadBacktestTradingInfo` — no change; it already re-hydrates from the
  response.
- Chart overlays (trades, positions, orders) — no change; they render
  whatever the trading info holds.
- `last_candle_seen_at` — Option A leaves it correct (still updated);
  Option B doesn't reach the backend so no change.
- Backtest stats — Option A: recomputed via `update_stats` after the
  trade cleanup, correct. Option B: no change (step is refused).
- Resume-from-widget — Option A cleans future fills; Option B has no
  effect on already-orphaned backtests.

## 6. Frontend-only feasibility

**Partial.** Option B blocks *new* orphan creation for users running the
fixed FE build. It does not retroactively clean already-corrupt backtests
and it does not help TV users. It also does not actually fix the backend
bug — any other client (TV, future mobile) will continue to produce
orphans.

**Recommended path:** **Option B (FE block) first, as a follow-up PRD in
this phase.** Reasons:

- The backend fix is not a 5-line edit — it needs a position-rebuild
  routine with test coverage for closed→reopen, partial fills, and
  trade-less positions. That's a real change with real regression risk
  on backtest PnL correctness, not "obvious and safe".
- The FE block reuses the exact pattern already in production for
  partially-closed positions (`checkResetToPossible`). Low risk, ~20
  lines, one new i18n key.
- Backend fix can land later as Option A without conflicting with the
  FE block (the FE guard just becomes dead code once BE handles it and
  can be removed in the same PR that ships the backend fix).

If the backend fix is taken on directly: it is not a one-liner, budget
a day including tests and think carefully about the closed-position
reopen case — that's where regressions will hide.

## 7. Risks and open questions

- **Option A — closed position reopen:** `recalculate(force_open: true)`
  exists on the concern, but its behaviour when a TP/SL close trade is
  deleted has not been verified end-to-end. Needs a runtime test.
- **Option A — order restoration:** filled entry orders have
  `status = "filled"`. Reverting them to `"open"` requires the backend
  to actually re-run them on forward replay; confirm the backtest engine
  re-subscribes to filled-status orders on resume.
- **Trigger-timing-offset cross-check:** the TTO fix (now merged on this
  branch) does not resolve this bug — the cursor alignment is correct,
  the backend still refuses to roll back. Independent issues.
- **Migration:** already-corrupt backtests exist in production DBs. A
  one-time cleanup script is optional for Option A (users can re-run
  backtests); for Option B it's a no-op (the FE just refuses to walk
  them into orphan territory further).
