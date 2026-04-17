---
id: sc-coexistence
---

# PRD: Phase 10 — TV/SC Coexistence + CandleChart Toggle Widget

## Overview

TV and SC must coexist as fully functional chart implementations. In the Trading
Terminal, a new toggle widget (`CandleChart`) renders either TV or SC, defaulting to SC.
The standalone `SuperChart` dev widget remains available in TT for development. Only one
SC instance may exist at a time. All other chart-using pages mount their chart component
directly — no `CandleChart` widget, no toggle. TV removal (Phase 10f) is deferred —
this PRD covers 10a through 10e.

`CandleChart` replaces `CenterView` everywhere — both TT and Charts page. The old
`CenterView` widget type is fully removed. On the Charts page, `CandleChart` always
renders TV (no toggle, no Redux toggle state) until SC is implemented there.

## Background

During integration, SC was built as a separate widget alongside TV. Some features were
migrated SC-only (grid bot pages, notes screenshot), breaking the TV path. Going
forward, both charts must work independently in TT so SC features can be validated
against TV behavior.

### Current state

| Area | TV | SC | Notes |
|---|---|---|---|
| TT main chart | `CenterView` widget | `SuperChart` widget | Both available in layout |
| Charts page | TV only | — | Not yet migrated |
| Grid bot overview/settings | — | SC only | TV replaced in `e272851` |
| Grid bot backtest | — | SC only | SC hardcoded, no toggle |
| Quiz | TV only | — | Not yet migrated |
| Customer service | TV only | — | Not yet migrated |
| Shared bots | TV only | — | Not yet migrated |
| Notes screenshot | — | SC only | `notes-form.js` imports from `super-chart/screenshot`, checks for `SuperChart` widget |
| Share modal | — | SC only | SC toolbar button, uploads to snapshot endpoint |
| Hotkeys | TV only | — | Phase 3 PRD exists, blocked by Phase 9 |

### Key decisions from design discussion

1. **Toggle is TT-only.** Only the Trading Terminal supports switching between TV and SC.
   All other chart-using pages use `CandleChart` hardcoded to TV (no toggle).
2. **SC and TV can coexist in TT** — a `CandleChart` toggle widget plus the standalone
   `SuperChart` dev widget can both be in the layout, but only one SC instance at a time.
3. **Full cleanup on toggle** — unmount current chart completely (destroy controller,
   unsubscribe, clear overlays, reset state), then mount the other from scratch. No state
   transfer.
4. **Default to SC** — `CandleChart` shows SC unless toggled. Toggle state is stored in
   Redux (persisted per device).
5. **Replay keeps its current chart** — toggle is disabled when `replayMode` is active
   (stays on whichever chart was active when the session started). This is future-facing
   — replay is not yet on SC. Quiz is unaffected (doesn't use `CandleChart`).
6. **Features not yet ported to SC need no work now** — coexistence means keeping TV
   functional for features that haven't been migrated. The integration continues
   forward, building SC features, with this coexistence framework in place.
7. **CenterView is fully removed.** `CandleChart` replaces `CenterView` in all layouts
   (TT and Charts page). `CandleChart` is page-aware: on TT it supports the toggle,
   on Charts page it always renders TV.

## Requirements

### R1 — CandleChart widget (page-aware)

A new widget component `CandleChart` that renders either CenterView (TV) or SuperChart
(SC). Used as a FlexLayout widget in desktop TT, as a tab component in mobile TT, and
as a FlexLayout widget on the Charts page.

**Page-awareness:** `CandleChart` detects which page it is on (TT or Charts) and
behaves accordingly:
- **TT:** toggle enabled, respects Redux `useSuperChart` state, shows `BooleanInput`
  switch
- **Charts page:** toggle hidden, always renders TV regardless of Redux state

How `CandleChart` detects the page: the Charts page renders via `ChartsGridItem`
which does not provide `MarketTabContext` the same way TT does. Use a prop or context
to distinguish. The simplest approach is a `toggleable` prop (default `true` for TT,
explicitly `false` for Charts page).

- Toggle control: `BooleanInput` in the widget (TT only)
- Default: SC (TT), TV (Charts page)
- On toggle: fully unmount the current chart first, then mount the other from scratch
  - SC cleanup: destroy `ChartController`, unregister from `ChartRegistry`, unsubscribe
    datafeed, clear overlays
  - TV cleanup: destroy `tvWidget`, unsubscribe all, cleanup DOM
- **Toggle state is stored in Redux (persisted per device).** It only affects the
  `CandleChart` widget in TT. Charts page ignores it.
- **Mobile:** only `CandleChart` is available (no standalone `SuperChart` dev widget).
  The SC single-instance guard (R2) does not apply on mobile since there is no dev
  widget to conflict with.
- **Mobile layout migration:** mobile widget tabs are persisted locally (Redux Persist).
  Migrate in place: rename `CenterView` → `CandleChart` in `widgetTabs` and
  `activeTab`. Do not bump `MOBILE_LAYOUT_VERSION` — preserve user's custom tab
  ordering and enabled/disabled state. If `CenterView` is not present in persisted
  tabs, the migration is a no-op. Fresh installs always include `CenterView` in the
  default layout, so migration always applies for existing users.

### R2 — SC single-instance guard

Only one SC instance may be mounted at a time (SC does not support multi-instance).

**CandleChart takes priority over the SuperChart dev widget.**

When both `CandleChart` and `SuperChart` dev widget are in the TT layout:
- If toggle is set to SC: `CandleChart` shows SC, dev widget renders empty with a
  short info message (only one SC instance can run at a time)
- If toggle is set to TV: `CandleChart` shows TV, dev widget shows SC normally
- Toggle stays enabled — toggling swaps which widget holds the SC instance:
  - Toggle SC → TV: CandleChart unmounts SC first, then switches to TV. Dev widget
    can now mount SC.
  - Toggle TV → SC: dev widget unmounts SC first, then goes empty. CandleChart
    then mounts SC.

**Mount/unmount ordering:** on any toggle change, the widget losing SC always unmounts
first, before the widget gaining SC mounts. The dev widget watches the toggle state in
Redux and unmounts reactively when toggle becomes SC.

**When the dev widget is removed from layout:** the empty-state scenario no longer
applies, toggle continues to work normally.

### R3 — FlexLayout migration

Existing user layouts reference `CenterView`. Migration needed for both TT and Charts
page:

- Migrate `CenterView` → `CandleChart` in saved layout JSON (both localStorage and
  backend-persisted layouts)
- `SuperChart` widget type stays as-is (dev widget, separate from `CandleChart`)
- Handle edge cases: users with custom layouts, corrupt layout data, layouts saved
  before migration runs
- Migration must be idempotent (safe to run multiple times)
- Follow existing migration patterns in `TradingTabsController` and
  `ChartTabsController` — their migration methods are the reference for structure
  and conventions
- Migration runs in the controller code (same location as existing migrations)
- **TT layouts:** `TradingLayoutsController.correctLayoutOnce` renames `CenterView` →
  `CandleChart`
- **Charts page layouts:** `ChartLayoutsController.correctLayoutOnce` renames
  `CenterView` → `CandleChart`. Code that creates new chart tab nodes
  (`syncWithChartTabs`) must also use `CandleChart`.

### R4 — Screenshots

Notes screenshots always use SC via `ChartRegistry.getActive()`. TV screenshots
produce page URLs (not image URLs) which don't work as note images, so TV is not
supported for notes screenshots.

- `notes-form.js` imports `takeScreenshot` from `super-chart/screenshot` (SC-only)
- Screenshot requires an active SC instance (via `ChartRegistry`)
- If no SC is mounted (e.g. CandleChart is on TV and no dev widget), screenshot
  returns `false` and the note has no screenshot
- Share modal: each chart widget manages its own share button/modal independently.
  TV has its own share modal via its `Screenshot` component. SC has its own via
  `triggerScreenshotShare`.

### R5 — TV feature restoration

Features currently broken for TV that must be fixed:

| Feature | What's broken | Fix |
|---|---|---|
| **Notes screenshot** | `notes-form.js` imports from `super-chart/screenshot`, checks for `SuperChart` widget only | Make `takeScreenshot` chart-agnostic, check for either widget type |
| **Grid bot overview/settings** | TV path removed, only `GridBotSuperChartWidget` renders | Keep SC-only (acceptable — grid bot SC is complete and validated) |

Features that still work on TV (no fix needed):
- TT main chart (still `CenterView`, will become `CandleChart`)
- Charts page (still TV, will become SC when ported)
- Quiz (still TV)
- Hotkeys (still TV-only, SC pending)
- Share modal (TV has its own in `tradingview/screenshot.js`, SC has its own)

### R6 — Per-page behavior

| Page | Chart | Toggle | Notes |
|---|---|---|---|
| **Trading terminal** | `CandleChart` widget + optional `SuperChart` dev widget | Yes | Single-instance guard applies (R2) |
| **Charts page** | `CandleChart` (hardcoded TV) | No | Always TV until SC is ported |
| **Grid bot overview/settings** | SC directly (`GridBotSuperChartWidget`) | No | Already migrated, keep as-is |
| **Grid bot backtest** | SC directly (`GridBotSuperChartWidget`) | No | SC-only, same as overview/settings |
| **Quiz** | TV (`DefaultTradingWidget`) | No | Mounts chart component directly, will mount SC directly when ported |
| **Customer service** | TV (`DefaultTradingWidget`) | No | Same as quiz |
| **Shared bots** | TV (`DefaultTradingWidget`) | No | Same as quiz |

`CandleChart` is used in both TT and Charts page as a FlexLayout widget. On TT it
supports toggle; on Charts page it's hardcoded to TV. Pages outside TT/Charts mount
the chart component directly (e.g. `DefaultTradingWidget`, or
`GridBotSuperChartWidget`) — no FlexLayout widget wrapper, no toggle.

### R7 — Forward compatibility

All remaining integration work must account for coexistence:

- New SC features must not break TV code paths
- Controllers that are SC-specific (`ChartController`, overlay components) stay SC-only
- TV controllers (`DataProvider`, `ChartFunctions`, etc.) stay TV-only
- Shared concerns (notes screenshot, hotkeys) must be chart-agnostic or properly gated
- When porting a feature from TV to SC, do not remove the TV implementation unless the
  page is going SC-only (like grid bot pages)

### R8 — Toggle disabled during active sessions

The `CandleChart` toggle is disabled only when:
- `replayMode` is active on the CandleChart widget (prevents mid-replay chart swap)

The toggle is NOT disabled when both chart widgets are in TT — toggling swaps which
widget holds the SC instance (see R2).

Quiz does not use `CandleChart` (it mounts the chart component directly), so the toggle
is not relevant during quiz sessions.

When disabled, the toggle button should be visually disabled with a tooltip explaining
why (e.g. "Stop replay to switch charts").

### R9 — CenterView removal

`CenterView` is fully removed as a widget type after migration:

- Remove from `WIDGET_SETTINGS`
- Remove from `grid-content.js` switch statement
- Remove from `grid-item-settings.js` and `grid-item-refresh.js`
- All layout JSON uses `CandleChart` after migration

## Non-requirements

- TV removal (Phase 10f) — deferred, not part of this work
- Porting remaining features to SC — continues independently
- Multi-instance SC support — out of scope, single-instance guard handles this
- State transfer between TV and SC on toggle — not needed, full reinit
- Toggle on non-TT pages — Charts page uses `CandleChart` but hardcoded to TV

## Revert: CenterView → CandleChart layout migration (2026-04-02)

### Decision
The CenterView → CandleChart layout migration (R3, R9) was reverted. Default layouts,
custom layout migration, mobile layout migration, and all CenterView removal code were
rolled back. Layouts now use `CenterView` as the widget type.

### Reason
Migrating layouts from `CenterView` to `CandleChart` breaks the old app version. Users
on the old version would see broken layouts because `CenterView` was removed from
`WIDGET_SETTINGS` and `grid-content.js`. The migration is irreversible — once a user's
layouts are migrated server-side, downgrading to the old version fails.

### What was reverted
- Default TT layouts: `CandleChart` → `CenterView`
- Default chart layouts: `CandleChart` → `CenterView`
- `migrateCenterViewToCandleChart` removed from `flex-layouts-controller.js`
- Mobile layout migration removed from `reducers/layout.js`
- `grid-to-flex-migration.js`: `CandleChart` → `CenterView`
- `chart-layouts-controller.js` `syncWithChartTabs`: `CandleChart` → `CenterView`
- Mobile widget default order: `CandleChart` → `CenterView`
- All `activateMobileWidget`/`activateTradingTerminalWidget` calls: `CandleChart` → `CenterView`

### What was kept
- `CenterView` re-added to `WIDGET_SETTINGS`, `grid-content.js` (maps to `CandleChart`
  component), `grid-item-settings.js`, `grid-item-refresh.js`
- `CandleChart` widget type still exists (for the toggle component)
- Layout presence checks (`selectWidgetTabNodeFromCurrentLayout`) check for both
  `CenterView` and `CandleChart`
- Settings modal `onToggle("CandleChart")` calls still work (both widget types map to
  the same settings modal)
