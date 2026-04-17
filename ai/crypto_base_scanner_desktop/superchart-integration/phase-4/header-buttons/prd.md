---
id: sc-header-buttons
---

# PRD: Header Buttons — SuperChart Migration

## Overview

Migrate the custom chart header buttons from TradingView's `tvWidget.createButton()` API to SuperChart's `superchart.createButton()`. The trading terminal chart has 5 custom buttons injected into the chart toolbar: Alert, Buy, Sell, Replay, and Settings. On mobile, these toolbar buttons are shown alongside a separate bottom action bar with contextual form buttons (submit/reset). Both systems are needed — header buttons for quick actions, action buttons for active form interaction.

## Background: Current System

### Desktop header buttons (`header.js`)

A React component that renders `null` — its only job is creating buttons on mount via `chartFunctions.createButton()` and managing their enabled/highlight state via effects. Buttons are injected into TradingView's toolbar inside the iframe DOM.

**5 buttons, in order:**

| Button | Icon | Bottom Border | Visibility Condition | Action |
|--------|------|---------------|---------------------|--------|
| Alert | `fa-bell` | Blue `#007FFF` | Hidden if `questionController.active` (quiz playing) | Create price alert at `currentMarket.lastPrice` |
| Buy | `fa-arrow-up` | Green `#06BF7B` | `mainChart` only | Start buy order |
| Sell | `fa-arrow-down` | Red `#F04747` | `mainChart` only | Start sell order |
| Replay | `fa-backward` | None | Hidden if quiz active, UNLESS quiz mode is `EDIT` or `NEW` | Pick replay start time |
| Settings | `fa-gear` | Gray `rgba(20,26,33,0.4)` | Always | Toggle `GridItemSettingsContext.onToggle("CenterView")` |

TV used `<img src="*.svg">` files because FA icons don't work inside TV's iframe (separate document, no access to the parent page's stylesheets/fonts). SC renders in the same DOM, so FA icons work directly — same pattern as the existing Share button (`<i class="fa-solid fa-share">`).

Grid bot charts show no buttons (`gridBotChart ? [] : [...]`).

### Button DOM structure (TV)

`chartFunctions.createButton()` calls `tvWidget.createButton()` which returns a wrapper div, then injects inner HTML:

```html
<div class="tradingViewButtonWrapper" title="...">
  <button class="tradingViewAlertButton tradingViewButton">
    <img src="images/bell.svg" style="width: 12px; margin-right: 6px;"/>
    <span>alert</span>
  </button>
</div>
```

### Button styling (TV CSS)

Buttons are styled via injected CSS in TV's vendored theme files (`default.css` / `dark.css`):

- **Base**: `height: 38px`, `font-size: 12px`, `font-weight: 600`, white background, dark gray text `rgba(20,26,33,0.6)`, flex row, centered
- **Hover**: `background-color: #F9F9F9`
- **Active (pressed)**: `background-color: #F2F2F2`
- **Each button** has a unique colored `border-bottom: 1px solid <color>` (except Replay which has none)
- **Dark theme**: handled by TV's separate dark.css

### Enable/disable logic

Three buttons (Alert, Buy, Sell) are disabled during replay mode or when a backtest is finished:

```javascript
const enabled = !isDefaultReplayMode && !backtestIsFinished
// isDefaultReplayMode = replayMode && replayMode !== REPLAY_MODE.SMART
```

Disabled state is applied via JS on the DOM:
- `opacity: 0.2` on the button element
- `pointerEvents: "none"` on the great-grandparent wrapper (3 levels up in TV's DOM)

### Highlight logic (Replay button)

When `selectingStartTime` is active, the Replay button is highlighted:
- Text color: `#2563EB` (blue)
- Icon: CSS filter to recolor SVG to blue: `brightness(0) saturate(100%) invert(29%) sepia(32%) saturate(5180%) hue-rotate(214deg) brightness(96%) contrast(92%)`

### Conditional callbacks (`conditionalCallback`)

Button actions are gated through a nested check system before executing:

**Alert button:**
- Feature gate: requires `"trading"` feature (subscription check)
- No device or widget requirement

**Buy/Sell buttons:**
- Feature gate: requires `"trading"` feature
- Device gate: `mustBeActive` is true UNLESS in `replayMode` or `exchangeApiKey?.paperTrading`
- No widget requirement (mobile may not have Trade widget)

**Replay button:**
- No feature/device checks
- Calls `replayController.handleSelectReplayStartTimeClick(isMobile)` — passes mobile flag to change selection flow

**Settings button:**
- No conditional checks
- Directly calls `toggleSettingsModal("CenterView")`

### Mobile action buttons (`action-buttons.js`)

On mobile, the existing `ActionButtons` component renders a bottom action bar below the chart with contextual form buttons (submit/reset for the active trade or alert form). This is in ADDITION to the header buttons in the toolbar — they serve different purposes. TV also shows both on mobile.

`ActionButtons` has zero TV dependencies (pure React + Redux) and is reused unchanged — just mounted in the SC widget tree.

### `headerDisabled` flag

The `Header` component is conditionally rendered: `{!headerDisabled && <Header/>}`. `headerDisabled` is true when TradingView's setup config includes `"header_widget"` in `disabled_features`. This flag needs an SC equivalent — when the chart toolbar is hidden, custom buttons should not be created.

### Where buttons are used

- **Trading Terminal main chart**: all 5 toolbar buttons (desktop + mobile) + mobile action bar below chart
- **Trading Terminal secondary charts**: Alert, Replay, Settings (no Buy/Sell — `mainChart` is false)
- **Grid Bot charts**: no buttons
- **/charts page**: NOT these buttons — uses separate SC `createButton` (Share button in chart-controller.js)

## Requirements

### R1 — Desktop header buttons via SC `createButton()`

Create the same 5 buttons (Alert, Buy, Sell, Replay, Settings) using `superchart.createButton(options)` where:

```typescript
ToolbarButtonOptions: {
  align?: 'left' | 'right',  // default: 'right'
  icon?: string,              // SVG/HTML string
  text?: string,
  tooltip?: string,
  onClick?: () => void
}
```

Returns an `HTMLElement` that can be styled/toggled after creation.

Buttons must be created once after the chart is ready (in `ChartController` or via a React component effect), not on every render.

### R1.1 — Button positioning: after Full Screen

SC's `createButton({align: "right"})` appends to a `rightContainer` slot that is positioned **before** the built-in Full Screen button. All custom buttons (Share + header buttons) must be moved after the Full Screen button by appending them to `rightContainer`'s parent element. Order after Full Screen: **Share** (icon only, no label), **Alert**, **Buy**, **Sell**, **Replay**, **Settings**.

The Share button is icon-only (no `text` property) — it was previously labeled but the label is removed to save toolbar space.

### R2 — Button visibility conditions

Same conditional logic as current implementation:

- **Grid bot charts**: Share button only (no Alert, Buy, Sell, Replay, Settings)
- **Alert**: hidden when `questionController.active` (quiz playing)
- **Buy/Sell**: only on `mainChart`
- **Replay**: hidden when quiz active, unless quiz mode is EDIT or NEW
- **Settings**: always shown

SC's `createButton()` returns an HTMLElement — use `element.style.display = 'none'/'flex'` or `element.remove()` for visibility toggling. If buttons need to react to state changes (quiz mode toggling), the React component managing them must update the DOM elements via effects.

### R3 — Button enabled/disabled state

Alert, Buy, and Sell buttons must be disabled during default replay mode or when backtest is finished:

- Disabled: reduce opacity to 0.2, disable pointer events
- Enabled: full opacity, pointer events restored
- "Default replay mode" = `replayMode && replayMode !== REPLAY_MODE.SMART`

SC's `createButton()` returns the HTMLElement directly in our DOM (no iframe). Set `element.style.opacity` and `element.style.pointerEvents` on the returned element — no parent traversal needed (TV required walking 3 levels up because the button was inside TV's iframe DOM structure).

### R4 — Replay button highlight

When `selectingStartTime` is active:
- Button text turns blue (`#2563EB`)
- Button icon turns blue

SC's `icon` option accepts an HTML string (e.g. `<svg fill="..." ...>`), not an image URL. To toggle highlight, swap the icon element's `fill` attribute or `color` style directly — no CSS filter hack needed (TV used a complex `brightness(0) saturate(100%) invert(29%)...` filter because the icon was an `<img>` tag inside an iframe).

When `selectingStartTime` is inactive, revert to default colors.

### R5 — Conditional callback gating

All button actions must go through `conditionalCallback` with the same gates:

- Alert: feature `"trading"`
- Buy: feature `"trading"`, device `mustBeActive` (waived in replay/paper trading)
- Sell: same as Buy
- Replay: no gates, no-op until Phase 5 (will call `replayController.handleSelectReplayStartTimeClick(isMobile)` via SC ReplayContext)
- Settings: no gates, calls `toggleSettingsModal("CenterView")`

### R6 — Mobile action buttons

On mobile (`screen === SCREENS.MOBILE`), the header toolbar buttons are shown as normal (SC's toolbar works fine on mobile — no iframe limitation like TV). Additionally, a bottom action bar renders below the chart with contextual form buttons (trade submit/reset, alert submit/reset).

`ActionButtons` has zero TV dependencies — it's pure React + Redux + design system components. It can be reused directly by mounting it in the SC widget tree with the same conditions (`!replayMode && mainChart && screen === SCREENS.MOBILE`).

The only chart-adjacent dependency is `PickReplayStartButton` which uses `ReplayContext` — that's a Phase 5 concern, not this phase.

### R7 — Styling

Desktop buttons must match the current visual design:
- Colored bottom borders: Alert (blue `#007FFF`), Buy (green `#06BF7B`), Sell (red `#F04747`), Settings (gray), Replay (none)
- Font: 12px, weight 600
- Hover/active states
- Theme-aware (light vs dark backgrounds and text colors)
- Icons use FontAwesome classes (e.g. `<i class="fa-solid fa-bell">`) — no SVG files needed

SC's `createButton()` returns an HTMLElement — styling is applied via the element's `style` property or by adding CSS classes. Determine whether SC's toolbar has its own button styling that can be extended, or if custom CSS must be injected.

### R8 — i18n

All button labels and tooltips must use i18n keys. Button text must update when the language changes (same pattern as the Share button in `chart-controller.js` which listens to `i18n.on("languageChanged", ...)`).

### R9 — SC period-bar customization

Two needs, both resolved via SC's period-bar visibility API:

**a) Hide SC's built-in Settings button (+ Screenshot, Indicators, Timezone, Full Screen).** Altrady ships its own Settings and Share buttons; SC's built-in equivalents are redundant. Resolved by a global CSS rule in `chart-controller.js._applyTemporaryHacks` that targets `.superchart-period-bar [data-button="<id>"]` for each control we don't want. Applies to every chart in the app via a single injection.

**b) Hide the entire period-bar (quiz play mode).** During quiz playback, TV hid the full header via `disabled_features: ["header_widget"]`. SC equivalent: `sc.setPeriodBarVisible(false)` (runtime) or `periodBarVisible: false` (constructor). To be wired in Phase 5 / Phase 7 quiz flows.

### R10 — Cleanup on unmount

All created button elements and event listeners must be cleaned up when the chart is destroyed. SC's `dispose()` may handle this automatically for toolbar elements — verify this. If not, store references and remove manually.

## Non-requirements

- No changes to `conditionalCallback` itself
- No changes to the Settings modal (it's triggered but not part of this scope)
- No changes to replay controller logic (buttons only trigger existing handlers)
- No changes to the alert/order creation actions
- No mobile layout system changes (`activateMobileWidget` stays as-is)
- No /charts page buttons (those are separate, already using SC `createButton`)
- Drawing toolbar buttons (template save/load, trendline-to-alert) are in Backlog, not this scope
