# Leverage — Design

PRD: [`prd.md`](prd.md) (`pc-leverage`).

## Scope recap

Leverage applies only to the pivot backtest sim (`pivot_strategy.py` →
`/api/bot/simulate`). Positions-backend (spot DCA) untouched. Branch base
includes `sl-tp-fix` (SL is a fixed % from entry; `slCapPct` is the SL %, no
opposite-pivot distance anymore).

## Margin model

- `quoteAmount` is reinterpreted as the **isolated margin** per position.
- `notional = quoteAmount × leverage`; `qty = notional / entry`. At ×1 nothing
  changes (notional == quoteAmount, today's behavior).
- Fees/slippage stay on the notional (`notional × TAKER_FEE`), so fee drag
  scales with leverage — already true since fees use `notional`.

## Liquidation

- Liq distance as a fraction of entry: `liq_pct = 1/leverage − 2·TAKER_FEE`
  (fee adjustment only when `feesEnabled`; at ×125, `0.008 − 0.002 = 0.006` —
  still positive, so ×1–×125 is always valid).
  - long: `liqPrice = entry × (1 − liq_pct)`; short: `entry × (1 + liq_pct)`.
  - At ×1 liq_pct ≈ 1 → liq ≈ 0 / 2×entry — effectively unreachable, no
    special-casing.
- **Effective stop** = whichever of SL / liq is closer to entry on the adverse
  side: long `max(slPrice, liqPrice)`, short `min(slPrice, liqPrice)`; reason
  `"sl"` or `"liq"` by which one wins. The reverse level still preempts only
  when it's closer to entry than the effective stop (existing `rev > slPrice`
  check, now against the effective stop).
- A liq close realizes **exactly −margin** (isolated: loss can never exceed
  the allocated margin, even on a gap past liq — `pnl = max(pnl, −margin)`
  clamp inside `close_pos`, applied on every close so gap-through-SL beyond
  liq is also capped).

## Bankruptcy guard

- `open_pos` refuses when `equity < margin` (equity is flat-equity at that
  point — entries only happen from flat, reverse closes first). The sim sets
  `bust = True` the first time an entry is refused; armed stops effectively
  stay dead for the rest of the range (flat equity can't recover). Reverse
  whose re-open is refused degrades to a plain close.

## Bot-backend changes

### `app/pivot_strategy.py`

- `simulate` reads `leverage = int(params.leverage)`; `margin = quoteAmount`,
  `notional = margin * leverage`.
- `open_pos`: bankruptcy check; compute `liqPrice`; store `liqPrice` on `pos`.
- Position handling: replace `pos["slPrice"]` comparisons with the effective
  stop (`_stop(pos)` helper returning `(price, reason)`).
- `close_pos`: clamp `pnl = max(pnl, -margin)`; new reason `"liq"`.
- Trades gain `liqPrice`, `notional`, `margin`. Result gains `leverage`,
  `bust`.

### `app/main.py`

- `StrategyParams.leverage: int = Field(default=1, ge=1, le=125)`.

## Frontend changes

- **`api/backend.ts`** — `PivotParams.leverage: number`; `PivotTrade`:
  `exitReason` adds `"liq"`, new `liqPrice`, `notional`, `margin`;
  `PivotSimResult`: `leverage`, `bust`.
- **`components/BacktestPanel.tsx`** — `PanelConfig.leverage`. Picker: a
  discrete slider over `LEVERAGE_STEPS = [1,2,3,5,10,20,25,50,75,100,125]`
  (range input over indices, label shows `×N`), under Position size, shown
  only for the pivot algo, live-tunable (`disabled={pivotsLocked}` like
  ratio/SL). Pivot results add a `Leverage ×N` row and a *bust* note when the
  cursor-clipped equity can no longer fund the margin
  (`pEquity < config.positionSize`).
- **`App.tsx`** — `DEFAULT_CONFIG.leverage = 1`; thread `leverage` into
  `setPivotParams` effect + `startSession` pivotParams. Preset load becomes
  `setConfig({ ...DEFAULT_CONFIG, ...p.config })` so pre-leverage presets get
  ×1 (presets store the whole `PanelConfig`, so new saves carry it for free).
- **`backtest/engine.ts`** — default fallback params gain `leverage: 1`
  (PivotParams type change covers the rest; no logic change).
- **`chart/ChartView.tsx`** — `pivotMarkers`: `"liq"` exit renders as an
  orange (`#ff9800`) circle labelled `LIQ`; bracket price lines add a dashed
  orange `Liq` line for the cursor-open trade when its liq is meaningful
  (leverage > 1, i.e. `sim.leverage > 1`).

## Numbers sanity

×10, margin 100 ⇒ notional 1000, qty = 1000/entry. A 1% adverse move ⇒
−10 USDT (−10% on margin). liq_pct = 0.10 − 0.002 = 9.8% adverse ⇒ −98 −
~2 fees = −100 = −margin. SL 4% < 9.8% ⇒ SL normally fires first; SL 12% ⇒
liq at 9.8% wins, reason `liq`.

## Open questions (resolve while implementing)

- None blocking; bust surfacing in the panel is intentionally minimal (a note,
  no dedicated state in the sim payload beyond `bust`).
