# Altrady Playwright Guide

Reference for using the Playwright MCP browser tool with this app.
Dev server runs at `http://localhost:5001`. Snapshots go to `~/ai/playwright-mcp/`.

## Browser setup

Playwright opens its own **headed Chrome window** with a persistent profile (`~/ai/playwright-profile/`).
Login is saved — after the first login you stay authenticated across restarts.

**Rule: never close the Playwright window — minimize it instead.** Closing it kills the browser process and breaks all subsequent tool calls until Claude Code is restarted.

If the window is accidentally closed, restart Claude Code to respawn it.

## Common URLs

| Page | URL |
|---|---|
| Dashboard | `http://localhost:5001/#/dashboard` |
| Trade (terminal) | `http://localhost:5001/#/trade` |
| Charts | `http://localhost:5001/#/charts` |
| Portfolio | `http://localhost:5001/#/portfolio` |
| Bots | `http://localhost:5001/#/bots` |
| Settings | `http://localhost:5001/#/settings` |
| Markets | `http://localhost:5001/#/markets` |
| Quiz list | `http://localhost:5001/#/quizzes` |
| Quiz edit (example) | `http://localhost:5001/#/quizzes/edit/18/question/154` |

URL pattern for quiz/question edit: `#/quizzes/edit/<quizId>/question/<questionId>`

## storeGlobal objects

Available on `window` after login. Beware circular references — extract
primitives rather than returning whole objects.

| Object | Available on | What it gives you |
|---|---|---|
| `dispatch` | All pages (logged in) | Dispatch Redux actions directly |
| `getState` | All pages (logged in) | Full Redux state snapshot |
| `util` | All pages (logged in) | App utility helpers |
| `urlController` | All pages (logged in) | Navigate programmatically, read current route |
| `getTradingTabsController()` | All pages (logged in) | Active trading tab state and methods |
| `getTradingLayoutsController()` | All pages (logged in) | Trading panel layout manager |
| `getChartTabsController()` | All pages (logged in) | Chart tab state |
| `getChartsLayoutsController()` | All pages (logged in) | Charts page layout manager |
| `chartRegistry` | All pages (logged in) | `ChartRegistry` singleton — `.getActive()` or `.get(id)` → ChartController |
| `toggleTheme` | All pages (logged in) | Toggle dark/light theme |
| `toggleLanguage` | All pages (logged in) | Switch UI language |
| `quizController` | Quiz edit pages | Full quiz edit state — `.edit.quiz.quizQuestions`, current question, etc. |
| `dashboardLayoutController` | `#/dashboard` | Dashboard panel layout controller |
| `updateDashboard` | `#/dashboard` | Force dashboard re-render |
| `chartController` | `#/trade` (SC active) | Active market-tab SuperChart controller |
| `previewChartController` | `#/trade` (SC active) | Preview chart controller |
| `tradeForm` | `#/trade` | Trade form state and methods |
| `tvWidget` / `chart` / `chartFunctions` / `datafeed` / `getCoinrayCache` | `#/trade` (legacy TV) | TradingView widget internals |

### Useful console snippets

```js
// How many questions in the current quiz?
quizController.edit.quiz.quizQuestions.length

// Current Redux state slice
getState().marketTabs

// Active chart controller
chartRegistry.getActive()

// Current route
urlController.currentPath()
```

## Replay snippets (TT — `#/trade`)

```js
// Start a DEFAULT replay session at a given time (skips mode-pick dialog)
await window.chartController.replay._startReplayInMode(
  new Date("2024-01-15T00:00:00Z").getTime(),
  "DEFAULT"
)

// Step N candles forward (engine.step() is void; add delay between steps)
const engine = window.chartController._superchart.replay
for (let i = 0; i < 5; i++) { engine.step(); await new Promise(r => setTimeout(r, 300)) }

// Buy / sell at current replay price
const trading = window.chartController.replay.trading
if (!trading.amount) trading.setAmount(0.001)  // set amount if not already set
trading.buy()
trading.sell()

// Check replay state
engine.getReplayStatus()           // 'ready' | 'playing' | 'paused' | ...
new Date(engine.getReplayCurrentTime()).toISOString()   // current candle time
trading.trades.length              // number of trades placed this session
```

## Chart navigation (SC `setVisibleRange`)

`setVisibleRange` expects **unix seconds** (not ms). It triggers a data fetch and
throws `SetVisibleRangeError` with `e.code === "no_data_at_time"` if the requested
time is before the earliest available candle (`e.detail.firstCandleTime` in ms).

```js
// Jump to a date range (unix seconds)
await window.chartController._superchart.setVisibleRange({
  from: new Date("2024-01-01T00:00:00Z").getTime() / 1000,
  to:   new Date("2024-01-31T00:00:00Z").getTime() / 1000,
})

// Catch no_data_at_time to find earliest candle
try {
  await c._superchart.setVisibleRange({ from: 1675209600, to: 1677628800 })
} catch(e) {
  console.log(e.code, e.detail?.firstCandleTime)
}

// Quiz draw controller wrapper (handles ms→sec conversion internally)
await window.quizController.draw.setVisibleRange({ from: msFrom, to: msTo })
```

## Common DOM selectors

| Element | Selector |
|---|---|
| SuperChart container | `.superchart` |
| SC chart canvas area | `.superchart-chart-container` |
| Quiz/question edit page root | `[class*="quizzes"]` |
| Top bar | `.top-bar` |

### Measuring layout

```js
// SuperChart width
document.querySelector('.superchart')?.getBoundingClientRect().width

// SC canvas height
document.querySelector('.superchart-chart-container')?.getBoundingClientRect().height
```

## Tips

- **Always show commands in the conversation.** Before every `browser_evaluate` call, write the JS being run in a fenced code block so the user can read it without opening tool output.
- **Circular objects** — never return a controller/state object directly. Extract `.length`, specific primitive fields, or use a custom replacer with `JSON.stringify`.
- **Page not loaded yet** — if a global is `undefined`, the component may not have mounted. Add a short `await page.waitForTimeout(500)` or navigate and wait for a known element first.
- **Snapshots** — Playwright auto-saves page snapshots to `~/ai/playwright-mcp/` on each navigation. Useful for diffing before/after a change.
