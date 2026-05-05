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
2. **Staleness check.** On first read per session, verify git hashes match. All four repos track their default branch:
   - Superchart: `main` — `git -C $SUPERCHART_DIR rev-parse HEAD` vs Superchart hash in `SUPERCHART_API.md`
   - coinray-chart: `main` — `git -C $SUPERCHART_DIR/packages/coinray-chart rev-parse HEAD` vs coinray-chart hash in `SUPERCHART_API.md`
   - CoinrayJS: `master` — `git -C $COINRAYJS_DIR rev-parse HEAD` vs hash in `COINRAYJS_API.md`
   - Backend: `master` — `git -C $CRYPTO_BASE_SCANNER_DIR rev-parse HEAD` vs hash in `CRYPTO_BASE_SCANNER_API.md`
   - `SUPERCHART_API.md` and `SUPERCHART_USAGE.md` track both Superchart and coinray-chart hashes — check once per repo.
   - If hashes differ, explore only the changed files (`git diff <old>..<new> --name-only`) and patch the docs.
   - A PreToolUse hook at `~/.claude/hooks/check-deps-staleness.sh` auto-warns on Read/Grep of these docs when hashes are stale.
3. **Superchart has its own `docs/` folder** at `$SUPERCHART_DIR/docs/` (`api-reference`, `data-loading`, `indicators`, `overlays`, `replay`, `scripts`, `storage`, `customization`, `index`). When updating `SUPERCHART_API.md` / `SUPERCHART_USAGE.md`, read those docs alongside the latest source — they are maintained by the SC author and are the primary source of truth. Fall back to source only where docs are incomplete or out of date.
4. **Resolve `$SUPERCHART_DIR` / `$COINRAYJS_DIR` / `$CRYPTO_BASE_SCANNER_DIR`** by reading `~/ai/crypto_base_scanner_desktop/local.config` at the start of a session.

## Dev server

A dev server (`yarn start-web` or `yarn start`) is always running. Do not
include `yarn start-web` / `yarn start` / `yarn build` / `npx webpack` /
similar build commands in tasks, apply-steps, or verification steps. HMR
picks up most changes; tell me to hard-reload only when a change won't
hot-reload (constructor signatures, context shape, top-level module
state, etc.).

## SuperChart integration

For any SuperChart integration work, read `~/ai/crypto_base_scanner_desktop/superchart-integration/context.md` before starting.

## Browser console debugging via Playwright MCP

**This is a crucial debugging instrument.** The Playwright MCP server is configured globally (`~/.claude.json`) and gives Claude live browser access. Use it generously — whenever you need to inspect runtime state, verify behavior, or confirm a bug, reach for the browser instead of guessing from source.

Full reference — URLs, `storeGlobal` objects, DOM selectors, snippets:
**`~/ai/crypto_base_scanner_desktop/playwright-guide.md`**

### How to use

1. Navigate to the relevant page: `mcp__playwright__browser_navigate` with the app URL (`http://localhost:5001/#/...`)
2. Run JS: `mcp__playwright__browser_evaluate` with a `() => expression` function
3. Avoid returning circular objects — extract primitives (`.length`, specific fields, `JSON.stringify` with a replacer)

**Suggest this to the user proactively** when:
- Verifying that a controller/state update worked
- Checking how many items are in a list
- Reading live Redux state
- Measuring DOM layout (widths, heights, positions)
- Confirming a global is wired up correctly after a code change

## Related personal agents

- `sc-source-explorer` (`~/.claude/agents/`) — investigates Superchart / coinray-chart source and returns concise summaries so the main thread never reads SC source directly.
- `tv-implementation-explorer` (`~/.claude/agents/`) — investigates the old TradingView integration on `release-5.2.x` from the backup checkout at `/home/areg/git/altrady/backup/crypto_base_scanner_desktop`.
