---
id: sc-tv-cleanup
---

# PRD: Phase 10 — TV cleanup

## Overview

TV is no longer used as a chart container — SuperChart (SC) has fully replaced it.
The TV chart container (`tradingview.js`) and most of its supporting tree are dead
code. A small set of utilities under `tradingview/` are still imported by SC and
non-chart code, and a few TV-named live files should be moved/renamed before the
folder is removed. The `charting_library.js` script load stays — SC wraps the
TradingView charting library and still requires it.

This phase removes dead TV code, relocates shared utilities out of the
`tradingview/` namespace, and renames remaining live TV-named files. CS-only TV
features (admin chart-management actions) are audited separately.

## Scope

### 1. Dead — safe to delete (~38 files in `center-view/tradingview/`)

- **Container:** `tradingview.js` itself — zero importers
- **Orphaned children** (only imported by the dead container):
  `alerts`, `bases`, `bid-ask`, `break-even`, `edit-alerts`,
  `edit-entry-conditions`, `edit-entry-expirations`, `edit-orders`,
  `grid-bot-orders`, `grid-bot-prices`, `orders`, `trades`, `backtest-times`,
  `custom-indicators`, `ta-scanner-alerts`, `tradingview-component`, `header`,
  `callout`, `multipoint-drawings`
- **TV-only infra:** entire `context/` folder, `controllers/setup.js`,
  `controllers/chart-functions.js`, `controllers/symbol-storage.js`,
  `controllers/save-load-adapter.js`, `controllers/local-save-load-adapter.js`,
  `controllers/ci/` (folder), `tradingview-enhancements.js` + folder,
  `screenshot.js`, `replay/`

### 2. Live but TV-named — move out

- `tradingview/price-time-select.js` → `src/util/`
  (used by trade-form, entry-expiration, price-time-field, trading.js,
  alerts.js, quiz/question)
- `tradingview/controllers/data-provider.js` (only `*_RESOLUTIONS` constants are
  used externally) → `src/models/chart-resolutions.js`
  (used by SC datafeed, quiz form, quiz/question)
- `tradingview/settings/chart-color-picker.js` →
  `src/components/design-system/v2/`

### 3. Live, keep — but rename

- `tradingview/action-buttons.js` — used by SC `trading-terminal-chart.js`;
  rename/move to a neutral path
- `tradingview/settings.js` (`TradingviewSettings`) — used by
  `chart-settings-provider.js`; rename to `ChartSettings`
- `chart-settings.js` reducer (`tvVersion`, `CHART_VERSIONS`) — still drives
  SC's charting library load; renaming the field is optional
- `logged-in.js:321` script load of `charting_library.js` — **leave as-is**
  (SC wraps the TV library)

### 4. Verify before touching

- `actions/customer_service/tradingview-charts.js` +
  `customer-service/account/layouts.js` — admin/CS feature; confirm still in
  use before removing or renaming
- `signal-bot-webhook-builder.js` reference — confirm it's not just a string

## Order of execution

1. **Delete the 38 dead files** (Section 1).
2. **Move the 3 utilities** out of `tradingview/` and update their importers
   (Section 2).
3. **Rename the 2 remaining live files** (`action-buttons`, `settings.js`)
   and update importers (Section 3).
4. **Audit CS-tool TV actions** and decide keep/rename/remove (Section 4).

## Non-requirements

- Do not remove the `charting_library.js` script load.
- Do not rename `tvVersion` / `CHART_VERSIONS` in `chart-settings.js`
  (cosmetic-only, out of scope).
- Do not touch i18n keys prefixed `tradingView.*` in this phase.
