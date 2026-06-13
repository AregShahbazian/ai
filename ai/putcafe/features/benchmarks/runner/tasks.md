# Benchmark runner — tasks

Design: [design.md](design.md). Branch `feature/benchmarks-runner`, worktree
`~/git/worktrees/putcafe/benchmarks-runner`. Commit tag `[pc-benchmark-runner]`.

## T1 — bench package

- `backend/bench/Dockerfile` — python:3.12-slim, install requirements, copy
  `bench/` + `specs/`, default CMD `python -m bench.run`.
- `backend/bench/requirements.txt` — polars (export); stdlib urllib for HTTP.
- `backend/bench/bench/{__init__,config,spec,candles,randoms,metrics,store,runner,status,manifest,leaderboard,export,run}.py`
  per design table.
- `backend/bench/specs/{algo-compare,pivot-map}.json`.

Verify: `python -m bench.run --spec algo-compare --dry-run` lists/counts sessions
(no calls); unit checks for `config_hash` stability, grid expansion + cap,
`roll_random_range` (seeded determinism), `metrics` (drawdown/return on a hand
snapshot).

## T2 — compose wiring

- `backend/compose.yml`: `bench` service (build ./bench, `profiles: ["bench"]`,
  `restart: "no"`, `candledata:/data`, `depends_on: [bot]`,
  `BOT_URL=http://bot:8102`).

Verify: `docker compose config` validates; normal `up -d` does NOT start bench;
`--profile bench up -d bench` does.

## T3 — results store + leaderboard + export

- `store.py` schema/upsert/resume/leaderboard query; `leaderboard.py` ranked
  JSON+md; `export.py` parquet (with provenance columns).

Verify: seed a tiny shard + a few result rows; leaderboard ranks by metric;
export writes parquet with `config_hash`/`corpus_manifest_ref` columns.

## T4 — ops scripts

- `scripts/dev/remote/bench/bench.sh` — multiplexer per design.
- `scripts/dev/local/bench/{start,stop,resume,status,monitor,leaderboard,export}.sh`
  + `_run.sh` + `.gitignore` (`out/`).

Verify: `bash -n` clean; full start→monitor→stop→status→resume cycle against the
VPS once the corpus has data.

## T5 — docs + deploy

- Append bench ops to repo README (scripts + spec format).
- review.md checklist.
- Push `feature/benchmarks-runner`; deploy API via CI `workflow_dispatch`
  (`deploy_api=true`) so `backend/bench/` lands on the VPS (profile, so the
  stack `up` won't start it — the ops `start.sh` does).

Verify: CI api job green; `bench/` present at `/root/putcafe/api/bench`;
`status.sh` → "(no run yet)"; a small `start.sh algo-compare` produces result
rows + leaderboard against whatever corpus exists.
