# Benchmark UI — review

## Round 1: implementation + live verification (2026-06-13)

On `feature/benchmarks-runner`, tag `[pc-benchmark-runner]`.

### Bugs found & fixed during bring-up

**Bug A — run crashed on first DB write.** One shared `results.db` connection +
concurrent workers raced sqlite's transaction state ("cannot commit - no
transaction is active"), and `gather` propagated it, killing the run (0 rows).
Fix: serialize upserts with an `asyncio.Lock`; single bad session is
record-and-continue, not fatal; `busy_timeout`. Stress-verified 150 sessions @
concurrency 16, 0 errors. Then the real run completed: 2340 sessions, 0 gaps, 0
errors.

**Bug B — bot 500 reading results.db.** Two-part: (1) WAL reader needs to write
the `-shm` sidecar, impossible on the bot's ro `/data` mount; (2) even in DELETE
mode, plain `mode=ro` fails `SQLITE_CANTOPEN` on read-only media. Fix: runner
writes DELETE journal mode (no sidecars) + bot opens with `immutable=1`. Endpoint
then returns 200 with the full dataset.

**Bug C — web deploy cancelled.** CI `cancel-in-progress` concurrency killed the
push-triggered `web` job when the `api` dispatch landed on the same ref. Fix:
re-ran the web job once nothing competed. (Operational, no code change.)

### Verification (agent-verified)

1. ✅ run completes: donchian, 2340 sessions, 0 gaps, 0 errors
2. ✅ leaderboard.sh produces ranked per-market md (htx ETH/USDT +1.33% top)
3. ✅ bot endpoints live: `/algos` 200 (2340 sessions, median −0.43%, best
   +11.27%, worst −27.16%, busts 0); `/markets`, `/sessions` shaped right
4. ✅ frontend build (tsc + vite) clean; deployed to `/web/benchmarks-runner/`
5. ✅ UI rendered live (Playwright): algo leaderboard, return-distribution
   histogram (+42.18% green), clickable per-market bars — the donchian run
   properly visualized

### Round 2 — cross-algo compare (2026-06-13)
- All 7 algos benchmarked (16,380 sessions, 0 gaps/errors). Added compare view:
  box-plots (identical windows) + per-market winner heatmap. Verified live
  (Playwright). Surfaced the dca no-op visually (flat 0 line, wins markets by
  default) — a config issue, not a real edge.

### Remaining (user / future)
- Frontend candle-endpoint reads likely need the same `immutable=1` (pre-existing
  in candle-store; out of scope here).
