# SuperChart Library Backlog

Work remaining in the SC library (Basty) that blocks full Altrady integration.
Not all TV features need SC equivalents — only what Altrady actually uses.

Last updated: 2026-04-03

---

## Critical Blockers

| # | Feature | Blocks | Status | Details |
|---|---|---|---|---|
| **1** | **Multi-instance support** | Phase 9 | TODO | Global singleton `chartStore.ts` — second instance overwrites first. Affects: /charts page (multi-tab), grid bot backtest modal over settings, quiz editor, CS, training. Reproduction story: `API/MultiChart`. |
| **2** | **Replay candle-push mechanism** | Phase 5 | TODO | No way to push candles outside DataLoader flow. Need `pushCandle(KLineData)` or equivalent via `subscribeBar` callback. Must support partial candle updates (update open candle's OHLCV without creating a new bar). See `ai/superchart-integration/phase-5/replay-current-behavior.md` for full current TV behavior. |
| **3** | **Data reset / re-fetch** | Phase 5, 7 | TODO | Clear all cached candles and force DataLoader to re-fetch from scratch. Needed for: replay start/stop, quiz question transitions, resolution changes during replay. Equivalent to TV's `resetData()` / `resetAllData()`. |

## Important (Feature Parity)

| # | Feature | Blocks | Status | Details |
|---|---|---|---|---|
| **5** | **`onTimezoneChange` callback** | Phase 4 | TODO | Fires when user changes timezone from SC UI. Needed to sync back to Redux `chartSettings.timezone`. |
| **6** | **Drawing tools audit** | Phase 6, 7 | TODO | Which drawing tools are available in SC? Can drawings be programmatically created/read/deleted? Quiz requires: export all shapes from chart, restore specific shapes on question load, selective deletion. |
| **7** | **StorageAdapter validation** | Phase 6 | TODO | Does save/load round-trip correctly for drawings + indicators + chart state? Quiz needs multiple independent saved states per question (not per market). |
| **8** | **Custom indicator support** | Phase 8 | TODO | Verify `registerIndicator()` can handle: multi-plot studies (RSI+Stoch dual plot), custom shapes on candles (`previousCandleOutliers`), feature-gated visibility. 4 custom indicators to port. |
| **9** | **Chart reset view** | Phase 5 | TODO | Equivalent to TV's `executeActionById("chartReset")` — reset zoom/scroll to default view. Needed for replay "reset chart". |

## Nice-to-Have

| # | Feature | Status | Details |
|---|---|---|---|
| **10** | **Font customization on overlays** | TODO | `createOrderLine` accepts font properties (`bodyFont`, `quantityFont`) but they have no visible effect. TV uses Trebuchet MS bold 11px. Low priority — default font is acceptable. |
| **11** | **`onRightClick` on chart background** | TODO | Chart-level right-click (not overlay). Needed for context menu: "Create order at price", "Start replay here", etc. Can work around with DOM event listener on the canvas. |
| **12** | **Drawing selection toolbar extension** | TODO | Custom buttons on TV's floating toolbar when a drawing is selected (save template, trendline-to-alert). Very TV-specific. Not critical for launch. |
| **13** | **`load_last_chart` equivalent** | TODO | TV option to skip restoring saved chart layout on init. Quiz needs clean chart on load. Probably solvable by passing empty/custom StorageAdapter. |

## Resolved

| # | Feature | Resolution |
|---|---|---|
| ~~14~~ | ~~Locale crash on non-en/zh~~ | No longer crashes. SC labels stay English for non-en locales — acceptable, Altrady translates its own UI via i18n yaml files. |
| ~~15~~ | ~~`onSymbolChange` callback~~ | Shipped. |
| ~~16~~ | ~~`onPeriodChange` callback~~ | Shipped. |
| ~~17~~ | ~~`onVisibleRangeChange` callback~~ | Shipped. Uses `getVisibleRangeTimestamps`. |
| ~~18~~ | ~~`createOrderLine` drag + callbacks~~ | Shipped. |
| ~~19~~ | ~~Custom overlay API~~ | Shipped. 3 generic overlays + `ignoreEvent` configurable. |
| ~~20~~ | ~~`getScreenshotUrl`~~ | Shipped. |
| ~~21~~ | ~~`createButton` for header~~ | Shipped. |
| ~~22~~ | ~~PriceLine non-draggable~~ | Resolved with custom `priceLevelLine` overlay. |
| ~~23~~ | ~~Overlay labels uppercase~~ | Resolved — all `createOrderLine` text uses `.toUpperCase()`. |
| ~~4~~ | ~~Period-bar visibility control~~ | Shipped as a deliberate subset: `periodBarVisible: boolean` option + `setPeriodBarVisible()` runtime method for the whole bar. Per-button hide/disable is done via consumer CSS against stable `[data-button="<id>"]` attributes on the eight built-in controls — not a JS API. Altrady-side wiring: `periodBarVisible: false` in `preview-super-chart.js`; global CSS rule in `chart-controller.js._applyTemporaryHacks` hides `indicators`, `timezone`, `settings`, `screenshot`, `fullscreen` across every chart. Full API doc: `$SUPERCHART_DIR/ai/features/period-bar-visibility.md`. |

## Priority Order

Sequenced to maximize unblocked Altrady integration time:

1. **#2 + #3** (replay candle-push + data reset) — unblocks Phase 5, the single biggest remaining phase
2. **#1** (multi-instance) — unblocks all secondary chart pages
3. **#6** (drawing tools audit) — needed before persistence and quiz design work
4. Rest follows as needed
