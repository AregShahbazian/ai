# crypto_base_scanner_desktop — personal workflow

Repo-specific workflow. Read alongside `~/ai/workflow.md` (general preferences).

## External library references (`deps/`)

Pre-built API reference docs live in `~/ai/crypto_base_scanner_desktop/deps/`:

- **`SUPERCHART_API.md`** — Superchart + klinecharts constructor, methods, types, datafeed interface
- **`SUPERCHART_USAGE.md`** — Initialization, datafeed wiring, symbol/period change, cleanup, gotchas
- **`COINRAYJS_API.md`** — CoinrayCache singleton, fetchCandles, subscribeCandles, Market/Exchange shapes
- **`CRYPTO_BASE_SCANNER_API.md`** — Rails backend REST API (V3 endpoints, models, services)

### Rules

1. **Do NOT explore library source.** Read these docs instead of browsing `node_modules/superchart`, `$SUPERCHART_DIR`, `$COINRAYJS_DIR`, or `$CRYPTO_BASE_SCANNER_DIR`.
2. **Staleness check.** On first read per session, verify git hashes match:
   - Superchart: `git -C $SUPERCHART_DIR rev-parse HEAD` vs Superchart hash in `SUPERCHART_API.md`
   - coinray-chart: `git -C $SUPERCHART_DIR/packages/coinray-chart rev-parse HEAD` vs coinray-chart hash in `SUPERCHART_API.md`
   - CoinrayJS: `git -C $COINRAYJS_DIR rev-parse HEAD` vs hash in `COINRAYJS_API.md`
   - Backend: `git -C $CRYPTO_BASE_SCANNER_DIR rev-parse HEAD` vs hash in `CRYPTO_BASE_SCANNER_API.md`
   - `SUPERCHART_API.md` and `SUPERCHART_USAGE.md` track both Superchart and coinray-chart hashes — check once per repo.
   - If hashes differ, explore only the changed files (`git diff <old>..<new> --name-only`) and patch the docs.
   - A PreToolUse hook at `~/.claude/hooks/check-deps-staleness.sh` auto-warns on Read/Grep of these docs when hashes are stale.
3. **Superchart has its own `docs/` folder** at `$SUPERCHART_DIR/docs/` (`api-reference`, `data-loading`, `indicators`, `overlays`, `replay`, `scripts`, `storage`, `customization`, `index`). When updating `SUPERCHART_API.md` / `SUPERCHART_USAGE.md`, read those docs alongside the latest source — they are maintained by the SC author and are the primary source of truth. Fall back to source only where docs are incomplete or out of date.
4. **Resolve `$SUPERCHART_DIR` / `$COINRAYJS_DIR` / `$CRYPTO_BASE_SCANNER_DIR`** by reading `~/ai/crypto_base_scanner_desktop/local.config` at the start of a session.

## SuperChart integration

For any SuperChart integration work, read `~/ai/crypto_base_scanner_desktop/superchart-integration/context.md` before starting.

## Related personal agents

- `sc-source-explorer` (`~/.claude/agents/`) — investigates Superchart / coinray-chart source and returns concise summaries so the main thread never reads SC source directly.
- `tv-implementation-explorer` (`~/.claude/agents/`) — investigates the old TradingView integration on `release-5.2.x` from the backup checkout at `/home/areg/git/altrady/backup/crypto_base_scanner_desktop`.
