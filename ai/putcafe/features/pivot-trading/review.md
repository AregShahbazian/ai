# Pivot trading — Review

## Round 0: implementation verification (2026-06-12)

Implemented on branch `feature/pivot-trading` (worktree
`~/git/worktrees/putcafe/pivot-trading`), uncommitted, tag `[pc-pivot-trading]`.

Files: `backend/bot/app/pivot_strategy.py` (new), `backend/bot/app/main.py`,
`frontend/src/api/backend.ts`, `frontend/src/backtest/engine.ts`,
`frontend/src/App.tsx`, `frontend/src/components/BacktestPanel.tsx`,
`frontend/src/chart/ChartView.tsx`.

### Architecture

The `pivot` algo is **simulated bot-side, stateless** (`POST /api/bot/simulate`,
mirroring `/analyze`) — it never touches the spot/buy-only positions-backend
(which can't model shorts/resting orders/brackets; that's the deferred
`pc-futures-orders`). The frontend calls it once over the session range, stores
the result, and **replay reveals the pre-computed trades by advancing the
cursor** — no per-candle backend calls.

### Verification

1. ✅ Strategy simulator standalone (claude-verified): over the exported BTCUSDT
   1h May-30 file (116 candles) — reverses chain **price-continuously** (each
   reverse-exit price equals the next entry price), no overlapping positions
   (single-position invariant), brackets obey the ratio (long@74061: SL −0.893%,
   TP +1.785% = 2×), SL caps at the configured % (short@73283: SL exactly 4.0%,
   TP 8.0%), and re-arm creates flat gaps after SL/TP exits.
2. ✅ `/api/bot/simulate` over real HTTP across params (claude-verified):
   `lb3/r2/cap4/fees` → 6 trades −3.75; `lb2/r3/cap5/nofees` → 7 trades +3.88
   (2W/4L); `lb1/r1/cap2/fees` → 7 trades. `chain_ok` invariant held in all.
   Param defaults apply (`params:{}` → 200); `slCapPct=0` → 422.
3. ✅ `tsc -b` clean; `vite build` clean (claude-verified).
4. Replay (pivot): pick a range, algo **Pivot breakout**, Start → entries appear
   as ▲L / ▼S, exits as circles (TP/SL/R), bracket price lines (Entry/SL/TP)
   track the open position; playback pauses on each trade (auto-resume off).
5. Step back: trades/markers/bracket lines confirmed at/before the cursor show;
   stepping back hides later ones and redraws the earlier open position's
   bracket. (Render-only rewind — the sim isn't re-run.)
6. Live control: mid-replay change **TP/SL ratio** or **SL cap %** → the sim
   re-runs and markers/lines/results update without restarting; changing pivot
   **lookback** / **alternation** likewise re-runs.
7. Headless (pivot): finished view shows all entries/exits over the fitted range,
   final results (realized PnL, ROI, win rate, trades), no playback controls.
8. Results panel (pivot): running stats are **clipped to the cursor** (realized
   PnL / equity / ROI / W-L / open position + unrealized) so replay doesn't spoil
   the final outcome.
9. Close + reverse: a long breaking the current low pivot closes and opens a
   short same candle (mirror for short) — verified via the chained entry/exit
   prices in #1/#2.
10. Switching algo back to **DCA** restores the buy-amount/frequency fields and
    the spot results; pivot fields hide. Algo locked once a session is active.
11. Stop session → back to live chart: bracket price lines and trade markers
    clear; live pivots return.

## Notes / deferred

- Pivot sims are **not persisted** to the positions-backend → no Sessions-list
  entry, no reload (acceptable while simulated-only; persisted futures sessions
  wait on `pc-futures-orders`).
- Sim runs over the **session range only**, so the first/last `lookback` candles
  can't seed pivots — early-range breakouts wait for structure to form.
- Pivot **lookback** input only appears when "Show pivots" is on; the strategy
  uses it regardless. Minor UX wrinkle (default is on).
- Intra-candle fills use the **OHLC color heuristic** (green O→L→H→C, red
  O→H→L→C); a reverse's fresh position is evaluated from the next candle.
- "Smart" TP/SL via pivot recency/time-distance and an equity-curve subchart are
  future refinements (see the discussion's *Ideas to realize*).
