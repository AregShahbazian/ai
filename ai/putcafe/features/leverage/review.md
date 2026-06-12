# Leverage — Review

PRD: [`prd.md`](prd.md) · Design: [`design.md`](design.md) · Tasks: [`tasks.md`](tasks.md)
Branch `feature/leverage` (worktree `~/git/worktrees/putcafe/leverage`), left
uncommitted for user testing. Tag: `[pc-leverage]`.

## Round 1: implementation (2026-06-13)

### What was built

- **Bot sim** (`backend/bot/app/pivot_strategy.py`): `quoteAmount` = isolated
  margin; `notional = margin × leverage`; liq price
  `entry × (1 ∓ (1/leverage − 2·fee))` set at entry; effective stop =
  closer-to-entry of SL/liq (reason `sl`/`liq`); `pnl ≥ −margin` clamp on every
  close (covers gaps past liq); bankruptcy guard in `open_pos` (+ `bust` flag);
  trades carry `liqPrice`/`notional`/`margin`; result carries `leverage`/`bust`.
- **Bot API** (`main.py`): `StrategyParams.leverage` int, 1–125, default 1.
- **Frontend**: `PivotParams.leverage` end-to-end (App effect, session config,
  engine fallback); panel slider over steps ×1…×125 with live notional readout,
  live-tunable mid-replay; "Position size" relabelled "Margin per position";
  results gain `Leverage ×N`, liq count, bust note (cursor-honest:
  `pEquity < margin`); chart gains `LIQ` exit circles (`#e040fb`) and a `Liq`
  bracket line at leverage > 1; preset load merges over `DEFAULT_CONFIG` so old
  presets get ×1.

### Automated checks (agent-run, deterministic script)

Script: `/tmp/leverage_check.py` over synthetic candles, run against the
worktree bot package.

1. ✅ ×1 parity & scaling: same TP trade, ×10 pnl = 10× the ×1 pnl; ×1 liq
   price ≈ 0 (unreachable). (agent-verified)
2. ✅ SL beyond liq → exit reason `liq` at the computed liq price, pnl exactly
   −margin. (agent-verified)
3. ✅ SL inside liq → normal `sl` exit, loss = SL% × notional. (agent-verified)
4. ✅ Gap past liq (open far below) → pnl clamped at −margin. (agent-verified)
5. ✅ Bust: after a liq leaves equity < margin, the next breakout is refused,
   `bust=true`, no further trades. (agent-verified)
6. ✅ Fees on: liq price fee-adjusted (`1/lev − 0.002`), pnl still −margin.
   (agent-verified)
7. ✅ `tsc -b && vite build` clean; `python -m compileall` clean. (agent-verified)

### Manual verification (user)

8. Pivot backtest at ×1 over a known range reproduces pre-feature numbers
   (same trades, same equity).
9. Leverage slider: shows ×N + notional; dragging mid-replay re-runs the sim
   (trade list/markers update); locked during a running headless batch.
10. High leverage (e.g. ×50, SL% > liq%): chart shows the purple `Liq` line on
    the open position and `LIQ` exit circles; results count liqs separately.
11. Bust note appears once equity (at the cursor) can't fund the margin; no
    entries render after it.
12. Presets: a pre-existing preset loads as ×1; saving with ×25 and reloading
    restores ×25 (after market/interval switches too).
13. Headless and replay over the same range + leverage give identical final
    equity.

### Known pre-existing bug found (NOT fixed here — separate decision)

**TP exits fill at the candle open, not the TP price.** In `close_pos` the
gap clamp `raw = min(level, open) if open < level` applies to *all* long
closes; for a TP (level above entry) the exit candle almost always opens below
the TP, so the fill becomes the open — TP profits are systematically
understated (a synthetic clean TP trade realizes pnl 0). Mirror issue for
shorts. Present on `main` since `pc-pivot-trading` (pre-dates this branch).
Repro: green candle entry 110, TP 118.8, next candle O110→H120 → exit fills at
110. Suggested fix (one line per side): clamp toward the open only for
stop-side closes (`sl`/`liq`/`reverse`), or for TP use `max(level, open)`
(long) / `min(level, open)` (short). **Fixed in Round 2 below.**

## Round 2: TP fill semantics (2026-06-13)

### Bug 1: TP exits filled at the exit candle's open

**Root cause:** `close_pos`'s gap clamp treated every close as a stop-market
(adverse gap → open). A TP is a resting limit: it fills at its price or
*better*. With the exit candle almost always opening between entry and TP,
every TP "win" realized at the open — shorts whose exit candle opened above
entry booked losses on TP hits (user repro: short 63,556, TP 63,530.58,
filled at open 63,558.65 → −0.004).
**Fix:** in `close_pos`, branch on reason: `tp` → `max(level, open)` long /
`min(level, open)` short, **no slippage** (limit, not taker market); stops
(`sl`/`liq`/`reverse`) keep adverse-gap clamp + slippage. Maker-vs-taker fee
stays deferred to `pc-futures-orders` (TP still pays taker fee for now).
**Files:** `backend/bot/app/pivot_strategy.py` (`close_pos`, docstring).

### Verification

1. ✅ Long TP, exit candle opens below TP → fills exactly at TP, pnl = qty×ΔTP.
   (agent-verified)
2. ✅ Short TP, exit candle opens above entry (user's repro shape) → fills at
   TP, pnl > 0. (agent-verified)
3. ✅ Favorable gap through TP → fills at the (better) open. (agent-verified)
4. ✅ Fees on: TP exit price == tpPrice exactly (no slippage); SL exit still
   slips below the stop. (agent-verified)
5. ✅ Rounds-1 checks 1–7 still pass after the fix. (agent-verified)
6. User: re-run the repro range — the short @ 63,556 TP trade should now book
   ≈ +0.04 (2× the 0.02 SL loss), and overall W/L + equity improve.
