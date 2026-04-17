---
id: sc-hotkeys
---

# PRD: Hotkey Registration — SuperChart Migration

## Overview

Migrate the hotkey registration system from the dual Mousetrap + TradingView `onShortcut` approach to Mousetrap-only. TradingView required dual registration because its iframe captured keyboard focus — hotkeys registered with Mousetrap stopped working when the TV chart was focused. SuperChart renders as a regular DOM element (no iframe), so Mousetrap bindings work regardless of which SC instance has focus. The TV `onShortcut` layer and all `inChart` dual-registration logic can be removed.

## Background: Current System

### Why dual registration exists

TradingView renders inside an iframe. When the user clicks the TV chart, the iframe captures keyboard focus and Mousetrap (which listens on the parent document) stops receiving key events. To work around this, hotkey components are rendered twice:

1. Without `inChart` — registers with Mousetrap (works when TV is not focused)
2. With `inChart` — registers with `tvWidget.onShortcut()` (works when TV is focused)

### Current hotkey components

| Component | Category | Current registration |
|---|---|---|
| `TradingviewHotkeys` | Chart-specific (trading + replay buy/sell) | Mousetrap + TV `onShortcut` |
| `ReplayHotkeys` | Chart-specific (replay controls) | Mousetrap + TV `onShortcut` |
| `ModalsHotkeys` | Context-specific (esc/enter for modals) | Mousetrap + TV `onShortcut` |
| `MarketHotkeys` | Trading Terminal page | Mousetrap only |
| `ChartsHotkeys` | Charts page | Mousetrap only |
| `GlobalHotkeys` | App-wide | Mousetrap only |
| `BalloonsHotkeys` | Context-specific (esc/enter for balloons) | Mousetrap only |

## Requirements

### R1 — Remove dual registration

All `inChart` rendering and `tvWidget.onShortcut` registration must be removed. Every hotkey is registered with Mousetrap only, once.

### R2 — Hotkey categories and lifecycle

#### R2.1 — Chart-specific hotkeys

`TradingviewHotkeys` and `ReplayHotkeys` (to be renamed as appropriate):

- Must only be registered when an SC instance is mounted
- Must be unregistered when the SC instance unmounts
- Must route to the correct chart's controllers (trading, replay)

#### R2.2 — Page-level hotkeys

- `MarketHotkeys` — registered when on the Trading Terminal page, works with or without a mounted SC instance
- `ChartsHotkeys` — registered when on the Charts page, works with or without mounted SC instances

#### R2.3 — App-level hotkeys

- `GlobalHotkeys` — always registered, regardless of page

#### R2.4 — Context-specific hotkeys

- `ModalsHotkeys` and `BalloonsHotkeys` — stay as-is (Mousetrap only, scoped to their modal/balloon lifecycle). Remove `inChart` logic and `ChartContext` dependency from `ModalsHotkeys`.

### R3 — Click-to-focus for multi-chart (Charts page)

On the Charts page, multiple SC instances can be mounted simultaneously. Chart-specific hotkeys (R2.1) must target a single "focused" chart:

- **Focus by click**: clicking anywhere on a chart's container (the chart widget area) marks that chart as the focused chart. This is analogous to how TV iframe focus worked — intuitive and immediate.
- **Fallback to selected tab**: if no chart has been clicked yet (e.g., page just loaded), the chart tab with `selected: true` is used as the focus target, but only if that tab has a mounted chart widget.
- **Single registration**: only one set of chart-specific hotkeys is registered at a time. When focus moves to a different chart, the previous bindings are torn down and new bindings for the focused chart's controllers are registered.
- **Unmount handling**: if the focused chart's widget unmounts (e.g., tab closed, layout change), the hotkeys are unregistered. Focus falls back to the selected tab per the fallback rule above.

### R4 — Trading Terminal (single chart)

On the Trading Terminal page, there is at most one chart. Chart-specific hotkeys are registered when the chart mounts and unregistered when it unmounts. No focus tracking is needed.

### R5 — Replay hotkey overlap

`shift+b` and `shift+s` are shared between trading (`newBuyOrder`/`newSellOrder`) and replay (`replayBuy`/`replaySell`). The handler must check the focused chart's replay state to route to the correct action. This behavior already exists and must be preserved.

### R6 — HotkeyMapper stays

The `HotkeyMapper` component and its bind/unbind lifecycle logic remain unchanged. It receives `bindFunction` and `unbindFunction` — after migration, these are always `bindHotkey`/`unbindHotkey` (Mousetrap). The `comboToTvCombo` utility and TV-specific bind functions are removed.

## Dependencies

- **Blocked by phase 9 — Charts page implementation.** The click-to-focus mechanism (R3) and multi-chart hotkey routing require the SC-based `/charts` page to be implemented first.

## Non-requirements

- No changes to the hotkey settings UI or key combo customization system
- No changes to the `stopCallback` logic (which combos fire inside input fields)
- No changes to hotkey combo defaults or the `DEFAULT_KEYMAP` definitions
- No new hotkeys are added in this work
- No changes to `BalloonsHotkeys`
