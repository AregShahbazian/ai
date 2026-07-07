# MCP server after the 5.4.x merge — how it works, install, SC gap

Post-merge orientation discussion (2026-07-06). Recapped what 5.4.x and the
Superchart repo shipped since June 30, walked through how the new MCP server
works, installed it into Claude Code against the running dev desktop app, and
live-tested the tools — which surfaced that all chart tools are TV-only and
one selector was lost in the merge (fixed + committed during the session).

## Key conclusions

- **MCP architecture**: Electron main runs a StreamableHTTP MCP server on
  `http://127.0.0.1:6850/mcp` (bearer token, 30-min idle sessions, desktop
  only — web gets stubs). Tools proxy over IPC to the renderer; reads come
  from Redux/coinray cache, writes drive real UI flows (position open via
  Import Trade Setup modal, bot wizards) behind an in-app confirm bus.
  Enabled via Settings → MCP; works fine in `yarn start` dev mode.
- **Installed for Claude Code** with `claude mcp add --transport http altrady ...`
  (token in `~/.claude.json` local scope, not the repo). Verified live:
  session context, tabs, alerts, indicators, drawings all read correctly.
- **Chart tools are TV-only**: `src/mcp/chart-bridge/widget-registry.js` is
  populated only by the TV context-provider; helpers assume `tvWidget`.
  Under SC every tab reports `chartId: null, rendered: false`. Non-chart
  tools work under either provider.
- **Merge regression found & fixed**: `MarketTabsSelectors.selectSelectedChartTab`
  was dropped by the merge, crashing `resolve_active_chart`. Re-added
  (commit `b979496b75`).
- **Notifications mystery**: not price alerts (zero delivered) — TA Scanner
  strategy 319676 subscription fires them.
- PRD draft for the SC port written:
  `~/ai/crypto_base_scanner_desktop/mcp-sc-chart-bridge/prd-draft.md` —
  user then locked decisions in it: full indicator parity in v1,
  `setChartReadyToDraw` fix in scope, TV-parity multi-chart granularity
  (one chartId per grid widget, no per-pane support).

## Open questions

- SC indicator/panel API surface (must support full parity per locked decision).
- Drawing id round-tripping between SC overlay ids and the canonical schema.
- `ready: false` seen on a mounted TV chart — readyToDraw timing or real issue?

## Ideas to realize

- **Port MCP chart tools to SuperChart** — provider-agnostic chart handle over
  `ChartRegistry`, SC drawing adapter, SC screenshot dispatch; PRD draft ready
  for a follow-up agent (`mcp-sc-chart-bridge/prd-draft.md`).
- **Wire `setChartReadyToDraw` from SC** — unsticks Smart Trading intro-modal
  Start buttons; in scope of the port per locked decision.
- **Optional: install altrady-mcp Phase 2 skills plugin** in Claude Code
  (`/plugin marketplace add altrady/altrady-mcp`) — skipped for now because it
  auto-updates third-party skills; revisit deliberately.
- **Use the MCP server for agent-driven app testing** — this session proved
  Claude can inspect live app state (tabs, drawings, alerts) over MCP; useful
  as a verification harness for future chart work.
