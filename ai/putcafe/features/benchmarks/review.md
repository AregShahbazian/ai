# Candle store & scraper — review

## Round 1: implementation verification (2026-06-13)

Implemented on `feature/benchmarks` (worktree
`~/git/worktrees/putcafe/benchmarks`), tag `[pc-candle-store]`.

### Bugs found & fixed during implementation

**Bug 1: SQLite cross-thread error under `asyncio.to_thread`**
**Root cause:** `to_thread` hops pool threads; sqlite3 connections default to
same-thread enforcement. Surfaced in the first live bitvavo run.
**Fix:** `check_same_thread=False` in `store.open_shard` — safe because each
shard has exactly one worker task, so access is serialized.
**Files:** `backend/scrape/scraper/store.py`

**Bug 2: manifest recorded config-default resolutions, not the run's**
**Fix:** `Status` carries the run's actual resolutions; manifest reads them.
**Files:** `scraper/status.py`, `scraper/manifest.py`, `scraper/run.py`

### Verification

Local (agent-verified, live exchange data):

1. ✅ `bash -n` all 8 scripts, `py_compile` all python, `docker compose config` (agent-verified)
2. ✅ store: upsert idempotent, watermark, coverage — unit-style sqlite test (agent-verified)
3. ✅ `--dry-run` vs live kraken+bitvavo: majors-only, volume-ranked, capped 20 (kraken exactly 20, bitvavo 9) (agent-verified)
4. ✅ real scrape bitvavo 1d: 6,465 candles, full 2y span, later-listed pairs start at listing date (gap handling), manifest JSON+md written (agent-verified)
5. ✅ resume: immediate re-run adds 0 rows, finishes in seconds (agent-verified)
6. ✅ second run after fixes: zero errors in manifest (agent-verified)
7. ✅ export: `scraper.export bitvavo BTC/EUR 1d 2025-01-01 2025-02-01` → parquet, 31 candles (agent-verified)
8. ✅ SIGTERM mid-1m-scrape: clean exit, manifest `state: stopped`, 143k candles flushed (agent-verified)
9. ✅ endpoint SQL shape against a seeded shard (query-level; FastAPI route not run locally — no venv with fastapi) (agent-verified)

Remaining — needs the VPS / user:

10. deploy backend to VPS (CI: push branch + workflow_dispatch with `deploy_api`, or merge to main)
11. `status.sh` before any run → "(no run yet)", container absent, du works
12. `start.sh` → container up; `monitor.sh` shows per-exchange progress
13. `stop.sh` mid-run → manifest `stopped`; `resume`/`start.sh` continues from watermarks
14. full corpus run completes; disk within ~10–15 GB (`status.sh` du)
15. `curl https://putcafe.../api/bot/candles?exchange=binance&market=BTC/USDT&resolution=1h&start=...&end=...` returns candles; bogus market → 404 "not in store"
16. `export.sh binance BTC/USDT 1h 2025-01-01 2025-02-01` lands parquet in `scripts/dev/local/scrape/exports/`
