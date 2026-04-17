# Bug: `PATCH /backtests/:id/reset` leaves orphan trades and orders on multi-fill positions

## Summary

The smart-replay rewind endpoint (`PATCH /backtests/:backtest_id/reset` in
`app/api/api_v3/backtests.rb:397`) only deletes `BacktestPosition` rows whose
`open_time >= reset_to`. Trades and orders are *only* removed via the cascade
`dependent: :delete_all` declared on the position
(`app/models/backtest_position.rb:13-14`).

For positions whose **first** fill is before `reset_to` but which have **later**
fills (or the close trade) after `reset_to`, the position survives the deletion
and so do all of its child trades and orders — including the ones with
`time > reset_to`. The frontend chart then renders these "orphan" trades sitting
visually in the future of the replay cursor. Stepping back further keeps
re-firing reset (every step looks like a divergence to the client) and nothing
is cleaned up until the cursor finally crosses the position's first fill,
at which point the whole position is destroyed and the orphans disappear with
it.

This affects both client implementations (the legacy TradingView replay and
the new SuperChart replay), confirming the bug is in the backend, not the
client.

## Reproducer (manual)

1. Start a smart-replay session in the desktop app, on any market.
2. Place a smart entry that produces multiple fills on **non-adjacent** candles.
   Two equivalent setups, both reproduce:
   - **Limit ladder**: a sell ladder of 3+ entry orders staggered above the
     current price; let price rise through the ladder so they fill on
     candles `C₁ < C₂ < C₃` with empty candles in between.
   - **Scattered market entries**: place 3 separate `MARKET` entries on the
     same position over time, on candles `C₁ < C₂ < C₃`.
3. Do **not** close the position. No TP/SL fills.
4. Step the replay cursor back to candle `C₃` (the last fill).
   - **Observed:** `PATCH /backtests/:id/reset` is sent with
     `reset_to = C₃_time`. Backend returns 200. Response still contains the
     trade for `C₃` and the corresponding `BacktestOrder` (status `closed`,
     `closed_at` past `reset_to`). Chart shows the trade hanging in the
     future of the cursor.
5. Step back again to an empty candle between `C₂` and `C₃`.
   - **Observed:** Reset re-fires. Same orphans returned.
6. Step back to `C₂`.
   - **Observed:** Reset called. Trades for `C₂` and `C₃` still in the
     response.
7. Step back past `C₁` (before the position's `open_time`).
   - **Observed:** The position now matches `open_time >= reset_to`, gets
     destroyed, cascade wipes its trades and orders. Chart is finally clean.

Same reproduction also happens when the position has been **closed** by an
exit order on `Cₙ` and the user steps back to a candle in
`(open_time, close_time)` — the close trade and any partial-reduce trades
along the way stay on the chart.

## Current backend code (the entire destructive path)

`app/api/api_v3/backtests.rb:397-404`:

```ruby
patch '/backtests/:backtest_id/reset' do
  backtest = current_account.backtests.find(params[:backtest_id])
  backtest.backtest_positions.where("open_time >= ?", params[:reset_to]).destroy_all
  backtest.update(last_candle_seen_at: Util.normalize_time(params[:reset_to]))
  backtest.update_stats

  present backtest, with: Entities::Backtest, type: :full
end
```

Three lines. The single comparator `open_time >= ?` is the entire decision.

Relevant supporting code:

- `BacktestPosition` cascade declarations:
  `app/models/backtest_position.rb:13-14`
  ```ruby
  has_many :backtest_trades, dependent: :delete_all
  has_many :orders, -> { includes(:market) }, class_name: "BacktestOrder", dependent: :delete_all
  ```
- `open_time` is derived from the **first** trade:
  `app/models/concerns/position_calculations.rb:258`
  ```ruby
  self.open_time = trades.first&.time || self.created_at.to_i
  ```
- `close_time` is set when the position is closed and there are trades:
  `app/models/concerns/position_calculations.rb:269`
  ```ruby
  self.close_time = trades.any? && closed? ? trades.last.time : nil
  ```
- Position rebuild routine already exists (this is what the fix should call):
  `app/models/concerns/position_calculations.rb:10-14, 68-86`
  ```ruby
  def recalculate!(force_open = false)
    clear_memoizations
    recalculate(force_open)
    save
  end
  ```
- Backtest entity exposes the orphans directly (so the bug is real DB state,
  not a serializer artifact): `app/api/api_v3/entities/backtest.rb:28-33`.

## Root cause

`open_time` anchors the position's eligibility for deletion. When a position
has trades at `t₁ < t₂ < … < tₙ` and the user resets to a `reset_to` in
`(t₁, tₙ]`:

- The position has `open_time = t₁ < reset_to`, so the position survives.
- The trades and orders are never queried directly by the endpoint, so
  trades with `time > reset_to` and orders with `closed_at > reset_to`
  also survive.
- Position-level state (`open_quantity`, `open_price`, `close_quantity`,
  `close_price`, `status`, `num_trades`, `stats`, `close_time`) is never
  recomputed, so even if the trades *had* been trimmed, the position would
  still report the wrong totals.

`update_stats` recomputes backtest-level aggregates from the surviving
positions, which is fine — but a position that hasn't been recalculated
contributes wrong values, so the backtest stats are also wrong after every
mid-lifetime reset.

## Expected behaviour

After `PATCH /backtests/:id/reset` with `reset_to = T`:

1. **No `BacktestTrade` for the backtest exists with `time >= T`.**
   This invariant is the test the fix must satisfy. (Pick the inclusivity
   that matches existing client expectations — current code uses `>=`, see
   "Inclusivity" below.)
2. **No `BacktestOrder` for the backtest is in a "this happened after T"
   state.** Concretely:
   - Orders with `closed_at >= T` and status `closed` (i.e. they filled
     after `T`) must either be re-opened (status `open`, `closed_at` and
     `last_trade_time` cleared) if the order was placed before `T`, or
     destroyed if the order was created after `T`.
   - Orders with status `canceled` and `closed_at >= T` (cancelled after
     `T`) need similar treatment — re-opened or destroyed depending on
     creation time.
3. **Every surviving position has its computed state consistent with its
   surviving trades.** I.e. for every surviving position, `recalculate!`
   would be a no-op. Concretely: `open_time`, `open_quantity`, `open_price`,
   `close_quantity`, `close_price`, `num_trades`, `sum_quote_fee`,
   `sum_base_fee`, `status`, `close_time`, `stats` must all reflect only
   the trades with `time < T`.
4. **A position that was `closed` at `close_time >= T` is reopened** (status
   `open`, `close_time` cleared) since its close trade is now in the future.
5. **A position whose every trade got deleted (open_time >= T)** is destroyed
   (matches the current behaviour).
6. **A position whose trades all got deleted but whose row was created
   before T** (e.g. the position was set up but no fills happened until
   after `T` — rare but possible) should be destroyed too. There is no
   meaningful "pending position with no trades" state to revert to, and
   the smart engine will recreate the position on forward replay if the
   smart settings still say so.
7. **`backtest.last_candle_seen_at`** is updated to `Util.normalize_time(T)`
   (already done; keep).
8. **`backtest.update_stats`** runs after the cleanup so the aggregates
   reflect the trimmed state (already done; keep — but the per-position
   recalc above must happen *before* it).

### Inclusivity (`>=` vs `>`) of `reset_to`

Current code uses `open_time >= reset_to` for position deletion (positions
opened *at or after* `reset_to` are gone). The frontend sends `reset_to` as a
candle-aligned unix-seconds timestamp matching the cursor. A trade whose
`time == reset_to` happens *at the cursor* and the chart treats it as
already-played. So:

- Match the same convention for trades: **delete trades with `time >= reset_to`**
  (a trade exactly at the cursor is removed, since the cursor lands at the
  start of that candle's close moment from the client's POV).
- Same for orders: an order whose `closed_at >= reset_to` is treated as
  "filled in the cursor's future" and must be reverted/destroyed.

If existing clients rely on the opposite inclusivity for some edge case,
flag it explicitly in the PR — but this is the convention that makes the
client's `_hasChangesSince(target)` ≡ "any trade.time >= target or
position.open_time >= target" map cleanly to a backend that has cleaned up
all such records.

## Test scenarios

These are the scenarios a fix MUST be tested against. Each one should be a
spec in `spec/requests/api_v3/backtests_spec.rb` (or wherever the existing
backtest endpoint specs live — currently the reset endpoint appears to have
no tests at all). The setup is always: a `Backtest`, with positions whose
trades are inserted at fixed `time` values; then `PATCH .../reset` is
called and the resulting `Backtest` state is asserted.

### S1 — Single-fill open position, reset before fill
- Position opened at `t=100`, single trade at `time=100`.
- `reset_to = 90`.
- **Expect:** position destroyed, trade destroyed, order destroyed,
  `last_candle_seen_at = 90`.
- (This case works today; keep it green.)

### S2 — Single-fill open position, reset after fill
- Position with one trade at `time=100`.
- `reset_to = 110`.
- **Expect:** position survives unchanged. Trade and order survive.
- (This case works today.)

### S3 — Multi-fill ladder open position, reset between fills
- Position with trades at `time=100, 200, 300` (limit ladder, 3 buys),
  status `open`, `open_time=100`.
- `reset_to = 250`.
- **Expect:** position survives, trades at `time=100, 200` survive, trade
  at `time=300` is destroyed. Order that produced the `t=300` trade is
  reverted to `status=open` (or destroyed if its `created_at` was also
  after 250 — see S6). Position recalculated:
  `num_trades=2`, `open_quantity = sum of first two amounts`,
  `open_price = weighted avg of first two`,
  `sum_quote_fee = first two fees`. `close_time = nil`. `status = open`.
- **This is the original bug.**

### S4 — Multi-fill ladder open position, reset before all fills
- Same as S3 but `reset_to = 50`.
- **Expect:** position destroyed (`open_time=100 >= 50`), all trades and
  orders destroyed.

### S5 — Multi-fill ladder open position, reset to exactly the second fill's time
- Same as S3 with `reset_to = 200`.
- **Expect:** trades at `time=200` and `time=300` destroyed (inclusive of
  cursor). Position survives with only the `t=100` trade. Orders for the
  destroyed trades reverted to `open` (or destroyed if created after 200).

### S6 — Order created after reset, never filled
- Position has trade at `time=100` (entry filled). A second entry order
  was *created* at `t=200` (e.g. a rebalance), still status `open`.
- `reset_to = 150`.
- **Expect:** the order created at `t=200` is destroyed (its
  `created_at >= reset_to`). The trade at `t=100` and its order survive.
  Position recalculated.
- Use whichever timestamp the model has — `BacktestOrder` has `created_at`
  and `closed_at`; pick `created_at` for "the order existed before T?".

### S7 — Closed position, reset between open and close
- Position with entry trade at `time=100` and exit trade at `time=300`,
  `status=closed`, `open_time=100`, `close_time=300`.
- `reset_to = 200`.
- **Expect:** exit trade destroyed. Position survives, status reverted
  to `open`, `close_time = nil`, `close_quantity = 0`, `close_cost = 0`,
  `close_price = 0`, recalculated against just the entry trade. The exit
  order that produced the `t=300` trade is reverted to `open` (or
  destroyed if it was a TP/SL created at the same moment as the close —
  in that case, destroy and let the smart engine recreate it on forward
  replay).
- This is the **closed-position reopen** path. Use
  `recalculate!(force_open: true)` per
  `position_calculations.rb:10` to force `status = "open"`.

### S8 — Closed position, reset to exactly close_time
- Same as S7 but `reset_to = 300`.
- **Expect:** the exit trade at `time=300` is destroyed (inclusive). Same
  outcome as S7.

### S9 — Closed position, reset just after close
- Same as S7 but `reset_to = 310`.
- **Expect:** position and all trades survive unchanged.

### S10 — Multi-fill closed position (entries + partial exits)
- Position with entries at `time=100, 200`, partial-reduce exit at
  `time=400`, full close at `time=500`. `open_time=100`, `close_time=500`.
- `reset_to = 350`.
- **Expect:** trades at `time=400` and `time=500` destroyed. Position
  recalculated against entries only; status reverted to `open`,
  `close_time = nil`, `close_quantity = 0`. Orders for the destroyed
  trades reverted to `open` or destroyed per their `created_at`.

### S11 — Multiple positions, partial reset
- Backtest has three positions: P1 (open_time=100, trade at 100), P2
  (open_time=200, trades at 200, 400), P3 (open_time=500, trade at 500).
- `reset_to = 300`.
- **Expect:**
  - P1 survives unchanged.
  - P2 survives, trade at `t=400` destroyed, position recalculated to
    1 trade.
  - P3 destroyed entirely.
- Stats reflect P1 + trimmed P2.

### S12 — Empty candle reset (no trades land in the trimmed window)
- Backtest has positions with last trade at `time=200`. `reset_to = 250`.
- **Expect:** nothing changes. Idempotent. The endpoint should be cheap
  and not touch any rows.
- This is important because the client currently re-fires reset on every
  step-back even on empty candles (a consequence of the bug), and after
  the fix it may continue to fire reset some of the time. The endpoint
  must handle "no-op resets" without errors.

### S13 — Idempotency
- Run any of the above scenarios twice with the same `reset_to`. The
  second call must produce the same state and the same response.

### S14 — Backtest stats correctness after reset
- Set up S3 with explicit, computable trade amounts/prices/fees so the
  expected `realized_profit_*`, `sum_quote_fee`, `num_trades`, and
  position-count aggregates are all hand-computable. Assert
  `backtest.update_stats` reflects only the surviving trades, not the
  pre-reset values.

### S15 — Cancelled position untouched
- Position with `status=canceled` (entry never filled, position cancelled
  before any trade). `reset_to = anything`.
- **Expect:** untouched. `recalculate` already skips `canceled` positions
  (`position_calculations.rb:69`: `return if canceled? && !force_open`),
  but the new code path must not call `force_open: true` on a cancelled
  position by accident.

### S16 — Position with order created before `reset_to` but filled after
- Position with entry order created at `t=100`, filled at `t=300` (one
  trade at `t=300`). `reset_to = 200`.
- **Expect:** trade destroyed. The order is reverted to `status=open`
  (it was placed before T, so it should be live again on forward replay).
  Position has zero trades after the cleanup → destroy the position
  (S6-style: trade-less positions are destroyed; the smart engine will
  recreate it on forward replay if the smart settings still call for it).

## Fix shape (sketch — not prescriptive)

A working sketch lives at the controller level, but ideally moved into a
`Backtest#reset_to(timestamp)` method on the model so it can be unit-tested
directly. Approximate shape:

```ruby
class Backtest < ApplicationRecord
  def reset_to(timestamp)
    transaction do
      # 1. Trim trades that landed at/after the cursor.
      affected_position_ids = backtest_trades.where("time >= ?", timestamp).pluck(:backtest_position_id).uniq
      backtest_trades.where("time >= ?", timestamp).delete_all

      # 2. Handle orders that filled or were created at/after the cursor.
      late_orders = backtest_orders.where("closed_at >= ? OR created_at >= ?", timestamp, timestamp)
      late_orders.find_each do |order|
        if order.created_at.to_i >= timestamp
          order.destroy
        else
          # Placed before T, filled/cancelled after T → revive it.
          order.update!(status: BacktestOrder::OrderStates::OPEN, closed_at: nil, last_trade_time: nil, filled: 0)
        end
      end

      # 3. For every position that lost trades, recalculate or destroy.
      affected_position_ids.each do |position_id|
        position = backtest_positions.find_by(id: position_id)
        next unless position

        if position.backtest_trades.reload.none?
          position.destroy
        else
          # force_open: true so a previously-closed position whose close
          # trade was just deleted reverts to status=open.
          position.recalculate!(true)
        end
      end

      # 4. Destroy positions whose own open_time is at/after the cursor
      # AND have no surviving trades (covers S4 and similar). The
      # cascade then deletes any remaining unaffected children.
      backtest_positions.where("open_time >= ?", timestamp).destroy_all

      # 5. Existing housekeeping.
      update(last_candle_seen_at: Util.normalize_time(timestamp))
      update_stats
    end
  end
end
```

Then the controller becomes:

```ruby
patch '/backtests/:backtest_id/reset' do
  backtest = current_account.backtests.find(params[:backtest_id])
  backtest.reset_to(params[:reset_to])
  present backtest, with: Entities::Backtest, type: :full
end
```

Notes on the sketch:

- **Wrap in `transaction`.** All-or-nothing for the rewind. Today's
  three-statement endpoint isn't transactional either, but a multi-step
  cleanup definitely needs to be.
- **`backtest_orders` association** — `Backtest has_many :backtest_orders`
  per `app/models/backtest.rb:8-9`. Use it directly so polymorphic
  ownership doesn't matter.
- **Order `created_at` vs `placed_at` vs the smart engine's notion of
  "placed".** Smart entries are created in DB when the position is set
  up, not when they fire on a price hit. If `BacktestOrder.created_at`
  reflects DB-creation time and that's earlier than the trade time, the
  "placed before T?" check is still correct. If smart orders are inserted
  at the moment of fill instead, the check needs a different column —
  verify against `BacktestOrder` insert path before settling on
  `created_at`.
- **`recalculate!(force_open: true)`** is the right call for positions
  whose close trade was just deleted (S7). For positions that were never
  closed, `force_open` is harmless (status stays `open`). For positions
  that became trade-less, destroy them outright instead.
- **`update_stats`** should remain at the end so the aggregates reflect
  the post-trim state. Verify it doesn't memoize anything that survives
  the call.
- **Performance.** The destructive path uses `delete_all` for trades
  and per-record `find_each`/`destroy` for orders (because they need
  conditional logic). For a single replay step this is cheap (a handful
  of orders at most). If a backtest has tens of thousands of orders and
  the user does a deep rewind, consider batching — but realistic backtest
  shapes shouldn't need that.

## Out of scope / non-goals

- Do not change the request/response shape of the endpoint. Same path,
  same params (`reset_to: Integer`), same `Entities::Backtest, type: :full`
  response.
- Do not introduce a new "pending revert" state on positions or orders —
  the rewind is synchronous and atomic.
- Do not migrate already-corrupted backtest rows. Existing backtests in
  production may contain orphan trades from before this fix; users can
  delete and re-run those backtests, or live with them. (If a one-time
  cleanup script is wanted, that's a separate task.)
- Do not change `open_time` semantics on `BacktestPosition` /
  `position_calculations.rb`. The bug is in the deletion query, not the
  column definition.

## Independent client-side mitigation (FYI)

The desktop client is independently planning a frontend block that refuses
the step-back when it would land in `(first_fill_time, last_fill_time]` of
an open position with multiple fills (mirroring the existing
`partially-closed positions` guard). That guard is purely a usability
backstop; it does not fix the backend bug and it does not help legacy TV
users. The backend fix is the canonical fix and will allow the FE guard
to be removed.

## File references

- `app/api/api_v3/backtests.rb:397-404` — endpoint to fix
- `app/models/backtest_position.rb:13-14` — cascade declarations
- `app/models/backtest.rb:8-10, 100-173` — backtest associations and
  `update_stats`
- `app/models/concerns/position_calculations.rb:10-14, 68-86, 258, 269` —
  `recalculate!`, `open_time`/`close_time` derivation
- `app/models/backtest_order.rb` — order states
  (`OrderStates::OPEN/CLOSED/CANCELED/PENDING/COOLING_DOWN`),
  `closed_at`, `last_trade_time`
- `app/models/backtest_trade.rb` — `time` column (unix seconds),
  `backtest_position_id` FK
- `app/api/api_v3/entities/backtest.rb:28-33` — response entity
  exposing raw `backtest_orders` / `backtest_trades`
