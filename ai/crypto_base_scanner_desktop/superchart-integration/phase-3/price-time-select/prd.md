---
id: sc-price-time-select
---

# PRD: Price/Time Select — SuperChart Port

## Overview

Restore the "click on the chart to capture a price or time" feature on SuperChart, matching the TradingView parity baseline. This covers the eye-dropper buttons on trade/alert form inputs. The replay start-time pick (same mechanism) has already been migrated in a prior task.

Out of scope for this PRD (and handled separately): the visible-range readers (`getVisiblePriceRange`, `getVisibleTimeRange`) and the form-default helpers (`getPriceOffset`, `getTimeOffset`) that the same TV module happened to export. Those are chart-viewport concerns, not pick-mode concerns, and belong to the trade-form / alerts work that owns their callers.

## Background

The TradingView integration has a `price-time-select` module that two shared design-system eye-dropper inputs (`PriceField` and `DatePickerInput`) currently import from. Both contexts where those inputs are rendered — the trading terminal and the grid bot pages — now run on SuperChart exclusively, so the TV import path in those inputs is dead on every real user flow. SuperChart exposes first-class pointer event callbacks (`onSelect`, `onRightSelect`, `onDoubleSelect`, `onCrosshairMoved`) and a generic `InteractionController` built on top of them, which is the intended host for the pick flows.

This PRD defines **what** needs to work; the design doc will define **how**.

Important clarifications found during exploration:

- TV performs a manual timezone correction (`time + timezone.utcOffset(...) * 60`) on captured times. SuperChart delivers UTC seconds directly and requires no correction.
- SuperChart does **not** reproduce TV's alert-drag / chart-click collision: when an overlay drag handler consumes a click, the chart-click callback does not fire. Verified manually with the replay start-time pick and a time-alert edit handle. No gate is needed — the user can click an empty spot on the chart to commit the pick.
- The trading terminal no longer renders TV. Grid bot pages already use SuperChart exclusively (`grid-bot-super-chart.js`). The shared design-system inputs are therefore always rendered next to an SC chart at runtime — no TV fallback is needed in the input components themselves. TV code (the TV file and its remaining internal callers like quiz and TV `edit-alerts.js`) stays completely untouched.

## Requirements

### R1 — Chart-pick on price inputs

The user can click an eye-dropper button next to any price input in the trade and alert forms (entry price, exit price, take-profit, stop-loss, alert price, and any other price field) to arm a "click on the chart to set this price" mode.

- While armed, the button shows an active state.
- Clicking a candle on the chart populates the price input with the clicked price, normalized to the field's precision using the existing `normalizeValue` helper.
- Only one input across the whole app can be armed at a time. Arming a second input cancels the first.
- Pressing Escape, clicking outside the chart container, or right-clicking the chart cancels the armed state without changing the input.
- Changing TradingTab, coinraySymbol, resolution, or exchangeApiKeyId cancels the armed state.

### R2 — Chart-pick on date/time inputs

The user can click an eye-dropper button next to any date/time input (alert time, entry expiration, etc.) to arm a "click on the chart to set this time" mode.

- While armed, the button shows an active state.
- Clicking a candle populates the time input with the clicked candle's UTC timestamp. Display formatting is the form's responsibility.
- Cancellation rules are identical to R1.

### R3 — TV code untouched

This is an SC-only port. The TV `price-time-select.js` file, the `<PriceTimeSelect/>` component it exports, and every TV-only caller of its functions (TV `edit-alerts.js`, quiz `use-quiz.js`, `question-controller.js`, TV `chart-functions.js`, TV `tradingview.js`) must remain exactly as they are today. No rename, no delete, no export rewiring. TV and SC stay fully separated in code: the shared design-system inputs reach SC directly; TV callers continue to reach TV directly.

## Non-requirements

- **Visible-range readers and form-default offsets** (`getVisiblePriceRange`, `getVisibleTimeRange`, `getPriceOffset`, `getTimeOffset`) are chart-viewport concerns that happen to be exported from the same TV file for convenience. They belong to a separate PRD owned by the trade-form / alerts work that consumes them.
- **Quiz time-pick** is out of scope. Quiz is not yet implemented on SuperChart and still uses TV; the SC quiz port is a separate initiative.
- **Chart-background context menu** ("Start replay here", etc.) is out of scope. It will use the same `InteractionController` but belongs to a separate phase with its own PRD.
- **New visual feedback** beyond what TV already provides (custom cursors, "click to pick" banners, highlight lines) is out of scope. Parity port only.
- **Removal of the TV `price-time-select.js` module** or any of its callers is out of scope. The TV path must stay functional for non-trading-terminal usages.
- **Editing the phase-3 top-level `prd.md:137` status row** ("Price/Time Select | DONE") to reflect the new architecture is a follow-up housekeeping edit, not a requirement of this PRD.

## Open questions (for the design phase)

None — all exploration questions resolved.
