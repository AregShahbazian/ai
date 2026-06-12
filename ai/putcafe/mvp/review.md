# MVP — Review

PRD: [`prd.md`](prd.md) (`pc-mvp`)

## Round 1: initial implementation (2026-06-12)

Implemented per [`design.md`](design.md)/[`tasks.md`](tasks.md). Backends + DB
deployed to the VPS (Docker provisioned by `setup-api.sh`, stack via
`deploy-api.sh`); frontend deployed to staging. Replay UI mined from
Superchart's storybook reference + Altrady's smart-replay controller.

### Verification

1. ✅ Frontend `yarn build` clean (strict tsc); backend `py_compile` + `bash -n`
   + YAML parse clean (agent-verified)
2. ✅ API live through Caddy: `/api/positions/health` + `/api/bot/health` 200
   (agent-verified)
3. ✅ Protocol smoke test against the live API: create → seed → step (buy) →
   order → step +1h (no buy) → step +25h (buy) → order → finish. DCA timing,
   fee (0.1 %) + slippage (0.05 %) math, avg entry, and persisted trades all
   correct (agent-verified)
4. ✅ Orion regression after Caddy reload: 200 (agent-verified)
5. Staging app loads; "Backtest" header button toggles the panel
6. Range selection: "Select Start/End Candle" arms picking (orange), chart
   click sets it, Esc cancels; shaded range + labeled lines appear; right-click
   menu offers "Set backtest start/end here" and "Start replay here"
7. **Replay session**: Start → first candle shown, strip appears (status,
   ⏮⏮ ⏮ ▶/⏸ ⏭ ⏹, speed 1–100×, auto-resume, candle time). Play steps candles;
   each DCA buy drops a green marker and (auto-resume **off**) pauses playback;
   auto-resume **on** keeps playing. Shift+↓/→/←/R/Q shortcuts work
8. **Headless session**: controls hidden, progress bar in panel, on completion
   the viewport jumps to the backtest range with all trade markers + final
   results (balance, position, avg entry, unrealized PnL, fees, equity, ROI)
9. Example flow from the PRD: DCA 10 USDT weekly, 20-week range, 1000 USDT —
   ~20 trades, sane PnL
10. Sessions persist: reload the app → panel "Sessions" lists past sessions;
    clicking one loads its candles + trades + results onto the chart
11. Stop ("⏹"/"Stop session") returns to the live chart; "Back to live chart"
    after finish does the same
12. Fees toggle off → trades fill at exact close, feesPaid stays 0
13. **Context cases** (Trading-Terminal style): switching market or timeframe
    during an active replay exits the session (mirrors Altrady) and the live
    chart works; starting a new session right after works
14. Replay stepBack rewinds the view only (markers past the cursor hide);
    stepping forward again does not duplicate orders

## Round 2: replay context + viewport fixes (2026-06-12)

### Bug 1: replay showed one lone candle, no perceptible movement
**Root cause:** session render sliced only the backtest-range candles
(`upTo=1` at start ⇒ one bar); the 500 pre-start candles fetched for the bot
seed were never rendered, and the viewport wasn't positioned at the cursor.
**Fix:** `preCandles` added to the engine snapshot and rendered as chart
context; on replay entry the viewport parks at the cursor (~120 context bars +
right-edge whitespace) so playback visibly appends.
**Files:** `frontend/src/backtest/engine.ts`, `chart/ChartView.tsx`, `App.tsx`

### Bug 2: finished session viewport had no padding
**Fix:** fit uses a logical range padded by ~7 % of the backtest range
(min 8 candles) on both sides; loaded sessions also fetch pre-start context.
**Files:** same.

### Verification
1. Start a replay: chart keeps showing history before the start line, cursor
   at the right with whitespace; ▶ visibly appends candles and follows
2. Headless finish / loading a past session: viewport shows the whole range
   with visible padding before start and after end
3. stepBack doesn't yank the viewport; restart re-parks it

## Round 3: bodyless-request 400 + React select warning (2026-06-12)

### Bug 1: `finish`/`delete` failed with 400 (sessions stuck "active")
**Root cause:** the API client set `Content-Type: application/json` on every
request; Fastify rejects bodyless JSON POSTs (`FST_ERR_CTP_EMPTY_JSON_BODY`).
The engine's `.catch` swallowed it, so finishes/deletes silently never landed.
(The `GET …/finish 404` in the console was the URL opened in the address bar.)
**Fix:** header only sent when a body exists. Verified live via Playwright:
bodyless POST/DELETE now hit the handlers.
**Files:** `frontend/src/api/backend.ts`

### Bug 2: React warning — `value` without `onChange` on the algo select
**Fix:** `defaultValue` (single option). **Files:** `components/BacktestPanel.tsx`

### Verification
1. ✅ Bodyless POST/DELETE return handler responses, not 400 (agent-verified)
2. Finishing a replay/headless session marks it `finished` in the Sessions list
3. No React warnings in the console on load + full session cycle

## Round 4: headless batch endpoint (2026-06-12)

Headless was N candles × 2 public HTTPS round-trips. Replaced with a single
server-side run.

### Change
- **bot** `POST /sessions/:id/run {candles[]}` — loops in Python, tracks
  `lastTradeTime` locally (no per-candle positions GET), hits positions only on
  fills (in-cluster). Returns `{steps, trades}`.
- **engine** `runHeadless()` → one `bot.run` call, then refetch final session.
- **panel** headless progress is now indeterminate (one call, no granular %).

### Verification
1. ✅ Live batch: 60 candles → 3 trades in one 0.26 s call; trade times exactly
   `frequencySec` apart; balance/fees/avg-entry correct (agent-verified)
2. Headless session in the UI completes near-instantly; results + markers +
   padded viewport render as before
3. Replay (per-candle `step`) unaffected

### Notes

- Per-step calls to both backends are by design (PRD §6); discussed
  alternative — frontend-held position with save-at-finish — would need the
  position snapshot in each bot step (stateless bot). Cheap to switch later.
- Positions-backend naming ("session backend") — candidate rename, backlog.
- One shared API stack serves all frontend slots; restart of the bot container
  loses seeds — frontend re-seeds on 409 (verified in code path, not live).
- `restart` deletes the old session and creates a fresh one (trades are
  server-side; render-only rewind can't undo them).
