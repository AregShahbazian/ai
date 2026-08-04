# Scripting Guide — learning tour plan

**Goal:** Areg will port the scripting feature to SuperChart. Before that, learn
what scripting is, how it works, and where it lives — via a guided interactive
tour. This doc is the plan; the tour starts only when Areg says so.

**Branch context:** `feature/coinray-script` is a **5.4 clone** — it does NOT
contain the superchart-integration changes. The chart here is TradingView.
Anything SC-related lives in other branches/repos, not in this working tree.

## Interaction format

- Stepped tour, one step at a time; Areg says **"next step"** to advance.
- Each step is mostly a **<20-word explanation** of what something is / how it
  works, plus **file/repo references** (`path:line`).
- **Example scripts:** each functionality is demonstrated with the simplest
  bare script that exercises it, followed through the code to the result
  (drawing, submitting, creating, …).
- Logs are the exception, not the rule: at 1–2 well-chosen points per
  implementation area, suggest a `/log-guide` and run it (stepped, <30-word
  pointers, Areg reloads the web app and checks the console).
- Claude never runs/builds the app; the dev webserver is already running.

## Tour outline (6 parts)

### 1. Functionalities of scripts
What a script can do, shown with bare example scripts:
- draw on chart (lines, shapes, indicators?)
- CRUD other data — orders, alerts, …?
- limitations (sandboxing, what it explicitly cannot do)

### 2. Functionality overlap with MCP
Which script capabilities the Altrady MCP server also exposes (chart tools are
TV-only today; SC-port PRD draft exists in `~/ai/…/mcp-sc-chart-bridge/`).
Output: a short capability-overlap table.

### 3. Implementation for TV (this branch)
- Which repo holds which part of the logic:
  `crypto_base_scanner_desktop` vs `@coinrayio/superchart-script`
  (= `packages/superchart-script` in the coinray_rest monorepo) vs coinrayjs.
- Where the modules link/use each other (editor → parse/compile → execute →
  TV chart primitives / API calls).
- 1–2 suggested log-guides max, e.g. "script edited & submitted → drawn on TV
  chart".

### 4. Implementation for SuperChart (if any exists)
- Why is the script lib called **superchart**-script? Which code in it is
  actually SC-specific?
- How much of it does this app use today; what is the unused rest meant for?
- Does any SC-side script execution already exist (SC repo / integration
  branch), or is the port greenfield?

### 5. Implementation overlap with MCP
Where scripting and the MCP server touch the same code paths (chart drawing
entry points, order APIs) — the seams the SC port can reuse.

### 6. Branch state
What `feature/coinray-script` adds vs its 5.4 base (diff survey): what's done,
partial, or missing. This frames the actual porting work.

## Prep (Claude, at tour start)

1. Read `~/ai/crypto_base_scanner_desktop/deps/` docs first (hard rule) —
   `COINRAYJS_API.md`, `SUPERCHART_API.md`, `SUPERCHART_USAGE.md`; use
   `sc-source-explorer` for any cross-repo source digging.
2. Diff the branch against its 5.4 base to scope part 6.
3. Locate the script feature's entry points in this repo (editor UI, actions,
   execution) and any bundled example scripts.

## Deliverables

- The tour itself (chat, stepped).
- Notes worth keeping get distilled into this folder afterwards (e.g.
  `functionalities.md`, `tv-implementation.md`) — only on request.
