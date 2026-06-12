# Console bridge — review

Implemented on `feature/console-bridge` (worktree
`~/git/worktrees/putcafe/console-bridge`). `tsc -b && vite build` clean.

## Verification

Live-driven via Playwright MCP against `yarn dev` + the VPS backend, then the
committed spec (`yarn e2e`) — **1 passed (4.6s)**.

- ✅ `pc.ready`, `pc.version`, `pc.help()` (29 entries) (agent-verified)
- ✅ Pivot headless `session.start` → finished, 481 candles, 19 trades;
  `verify()` → `{ok: true, kind: "sim"}` (agent-verified)
- ✅ Pivot replay: `playTo(firstEntry)` paused **exactly** on the entry candle
  (speed 20); `chart.markers()` showed the entry arrow, `chart.priceLines()` =
  Entry long/SL/TP, `renderedCandles().lastTime` == cursor, 4 pivot triangles,
  sane `visibleRange()` (agent-verified)
- ✅ DCA headless → backend session; `verify()` → `{ok: true, kind: "backend"}`
  incl. the 409 ran-out-of-balance edge (quoteBalance 0, feesPaid Σfee);
  `backend.sessions()` passthrough listed it (agent-verified)
- ✅ `stepForward`×2/`stepBack` (upTo 2→3→2), `setSpeed`, `setAutoResume`,
  `play`/`pause`, `waitFor.trade` event (dca fill payload),
  `waitFor.status` 1 ms timeout → structured `[timeout]` error,
  `session.stop` → idle (agent-verified)

## Issues found & fixed during implementation

1. **Stale-resolve on restart** — waiting for the target status could resolve
   on the pre-restart snapshot; fixed with a two-stage wait (must see the
   restart's own `loading` first).
2. **Chart getters one React commit behind the engine** — `playTo` resolved
   before ChartView re-rendered, so `markers()`/`priceLines()` returned the
   previous frame. Fixed: every `pc.chart.*` first awaits `settled()` — the
   drawn cursor matching the engine cursor (all session-derived chart refs
   update in the same commit).
3. **`reuseExistingServer` hijacked by a sibling worktree** — the spec on
   :5173 reused the `overview-widgets` dev server (no bridge code). Fixed:
   dedicated port 5183 + `--strictPort` in `playwright.config.ts`.

## Known limitations (accepted)

- `playTo` at speeds ≥100 can overshoot a few candles (engine batches steps
  per tick); documented in `help()` and the spec uses speed 20.
- Vite HMR of `bridge.ts` splits module state (engine keeps the old module's
  snapshot tap) — a page reload fixes it; dev-only artifact.
- Sim `verify()` reads `startingBalance` from current UI config; changing it
  mid-session without re-running the sim could report a false mismatch.
- `pc.events.since/clear` and the callable `pc()` dump are sync (everything
  else returns Promises, per PRD).
- The e2e spec is network-dependent (Binance + VPS backend) by design.

## Deploy status

- **Frontend only** — all changes hot-reload on `yarn dev`; nothing to deploy.
- **Backend** — untouched.
- Code left uncommitted on the branch for manual testing (new files staged).
