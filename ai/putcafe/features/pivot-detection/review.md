# Pivot detection — Review

## Round 0: implementation verification (2026-06-12)

Implemented on branch `feature/pivot-detection` (worktree
`~/git/putcafe-pivots`), uncommitted, tag for commits: `[pc-pivots]`.

Files: `backend/bot/app/pivots.py` (new), `backend/bot/app/main.py`,
`frontend/src/api/backend.ts`, `frontend/src/util/pivotOptions.ts` (new),
`frontend/src/backtest/engine.ts`, `frontend/src/App.tsx`,
`frontend/src/components/BacktestPanel.tsx`, `frontend/src/chart/ChartView.tsx`,
`frontend/src/app.css`, `frontend/vite.config.ts`.

### Verification

1. ✅ Detector vs manual selection (claude-verified): on the exported
   BTCUSDT 1h file, `lookback=3` raw matches **8/8** saved candles;
   alternation on → strictly alternating, **7/8** (the 09-06 04:00 high
   collapses into the adjacent higher 08-06 22:00 high — expected: those two
   picks were consecutive highs).
2. ✅ Bot API smoke via TestClient (claude-verified): seed with/without
   options, pivots in seed response, `PUT /options` recompute + disable,
   409 on unknown session, stateless `/analyze`, `lookback=0` rejected (422).
3. ✅ `tsc -b && vite build` clean (claude-verified).
4. ✅ Dev proxy (claude-verified): `VITE_LOCAL_BOT=1 yarn dev` + local uvicorn
   → `/api/bot/health` answered by local bot, `/api/positions/health` proxied
   to the deployed API (200), `VITE_API_BASE` blanked in served code.
5. Replay session: pivot triangles appear in pre-start history immediately;
   new pivots appear only `lookback` candles after their extreme as playback
   advances (orange ▼ above highs, blue ▲ below lows).
6. Step back: pivots confirmed later than the cursor disappear; step forward
   brings them back.
7. Live control: with a replay paused/playing, toggle alternation / change
   lookback / toggle Show pivots in the panel — markers update without
   restarting the session.
8. Headless run: finished view shows pivots over the whole range + pre-history.
9. Sessions list: loading a finished session shows pivots (stateless analyze);
   works after a bot restart too.
10. Pivot options survive a page reload (localStorage); trade markers (green
    ▲ + "B …") still render and remain distinguishable from pivot lows.
11. Changing market/timeframe mid-session still exits cleanly (no pivot
    leftovers on the live chart).

## Round 1: pivot colors + painted candles (2026-06-12)

User-requested visual experiment: markers black (high) / white (low) instead of
orange/blue (`8ed09d4`), and the pivot **candles themselves** painted in those
colors via per-bar overrides, not just the arrows (`46ed948`). Repaint honors
`confirmedAt`: a newly confirmed pivot (or a live option change) forces setData
over the incremental update. Deployed to the preview slot only.

### Verification

12. ✅ `tsc -b && vite build` clean; preview CI run green (claude-verified).
13. Replay: a pivot candle behind the cursor flips to black/white exactly when
    the confirming candle renders; step back reverts it.
14. Live alternation/lookback change repaints affected candles immediately.
15. Black high-candles are visible enough against the dark background (else
    pick a new pair).

## Round 2: live-chart pivots, indicator-style (2026-06-12)

Pivots on the plain live chart, no session needed — like an indicator. The
existing persisted pivot options (Show pivots / lookback / alternation in the
Backtest panel) now also drive the live chart: ChartView keeps live candles in
state, calls the bot's stateless `POST /analyze` whenever the candle set or the
options change (including older history loaded by scrolling left), and renders
markers + painted pivot candles. No `confirmedAt` clipping in live mode — all
detected pivots show (the trailing `lookback` candles can't have pivots yet by
construction). Bot unreachable → chart stays usable, pivots just don't render.

Files: `frontend/src/chart/ChartView.tsx` (live candles → state, analyze +
render effects, live pivot markers), `frontend/src/App.tsx` (pass options).
Committed as `e782eb6`, merged to main (`f146fe5`), staging deployed; the
`~/git/putcafe-pivots` worktree and local branch are removed.

### Verification

16. ✅ `tsc -b && vite build` clean (claude-verified).
17. Live chart with Show pivots on: markers + painted candles appear over the
    initial 1000 candles, no session running.
18. Scroll left into history: as older candles load, pivots appear on them too
    (recomputed over the full drawn set).
19. Toggle Show pivots / change lookback / alternation in the panel: live chart
    updates without reload; disabling clears markers and repaints candles plain.
20. Start a replay session: live pivots hand off to session pivots (confirmedAt
    clipping); stop it: live pivots come back after the refetch.
