# Benchmark runner — review

## Round 1: implementation verification (2026-06-13)

Implemented on `feature/benchmarks-runner` (worktree
`~/git/worktrees/putcafe/benchmarks-runner`, off `feature/benchmarks`), tag
`[pc-benchmark-runner]`.

### Design notes / decisions during implementation

- **Spec → run via env, not a baked CMD.** The detached compose service can't
  take CLI args at `up` time, so `run.py` takes `--spec` defaulting to
  `$BENCH_SPEC` (set by `bench.sh start <spec>`) then `algo-compare`. Keeps the
  service name stable for `stop`/`logs`/`monitor`.
- **Candles read directly from the shard, engine called over HTTP.** Avoids a
  second HTTP hop for (potentially large) candle payloads while still reusing
  `/futures/run` byte-for-byte — no backtest re-implementation.
- **Sessions enumerated up front, deterministically.** Random windows are drawn
  at enumeration time from one seeded RNG over a stable iteration order, so the
  resolved absolute ranges reproduce across reruns and the cap/dry-run can count
  before any work.

### Verification

Local (agent-verified):

1. ✅ `py_compile` all modules; `bash -n` all 9 scripts (agent-verified)
2. ✅ `docker compose config` validates; `bench` absent from default services,
   present under `--profile bench` (profile-gated like `scrape`) (agent-verified)
3. ✅ `config_hash` order-independent + change-sensitive (agent-verified)
4. ✅ grid expansion: `pivot-map` → 3×3×2 = 18 configs, all scalar leaves;
   `is_map` true (agent-verified)
5. ✅ `roll_random_range` seeded-deterministic, in-bounds, candle-aligned
   (port of `pc-randoms`) (agent-verified)
6. ✅ candle reader: `list_exchanges/list_markets/bounds/slice` against a seeded
   bitvavo BTC/EUR 1h shard (1500 candles); missing shard → empty (agent-verified)
7. ✅ metrics on a hand snapshot: return_pct, win_rate, closed-trade count,
   peak-to-trough max_drawdown, bust (agent-verified)
8. ✅ full run (engine mocked): `algo-compare` → 20 result rows with absolute
   ranges + provenance; status.json + manifest JSON+md written (agent-verified)
9. ✅ resume: immediate re-run adds 0 rows (idempotent on the results PK) (agent-verified)
10. ✅ leaderboard build + md render (per-config + per-market) (agent-verified)
11. ✅ Parquet export carries `config_hash` + `corpus_manifest_ref` columns,
    20 rows (agent-verified)
12. ✅ `SESSION_CAP` guard refuses 180 > 5 sessions; `--force` overrides (agent-verified)

Remaining — needs the VPS / user:

13. deploy backend to VPS (CI: push branch + `workflow_dispatch` `deploy_api`)
14. `status.sh` before any run → "(no run yet)", `bench/` present at
    `/root/putcafe/api/bench`
15. `start.sh algo-compare` → container up; `monitor.sh` shows progress; result
    rows land against whatever corpus the scrape has produced
16. `leaderboard.sh algo-compare` → ranked report copied to `out/`
17. `export.sh algo-compare` → parquet copied to `out/`
18. `stop.sh` mid-run → manifest `stopped`; `resume`/`start.sh` continues
    (stored sessions skipped)
