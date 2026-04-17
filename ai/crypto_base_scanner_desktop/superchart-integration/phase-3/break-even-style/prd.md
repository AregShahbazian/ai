# PRD: Break-Even Overlay — Transparent Label Style

## Goal

Update the break-even overlay to use the `createPriceLine` fluent API and render the
label with a transparent background (text only, colored to match the line).

## Current Behavior

- `chartController.createBreakEven()` uses raw `chart.createOverlay()` with a `styles`
  object — this bypasses the `createPriceLine` fluent API
- Label renders with a solid colored background and white text
- No label text is set (empty label)
- Line is locked (not editable)

## Desired Behavior

### Label on chart area
- Background: transparent (no fill)
- Border: line color
- Text color: same as the line color (the break-even color from chart settings)
- Text content: hardcoded "Break even" (matches TV implementation)
- Position: below the line
- Alignment: right
- No padding overrides needed

### Line
- Style: dashed
- Width: 1px
- Color: break-even color from chart settings

### Y-axis label
- Keep solid background with white text (matches current order/price line patterns)
- Background color: line color
- Border color: line color
- Text color: white

### Interactivity
- Not editable (user cannot drag or rename)

## Reference Implementation

`$SUPERCHART_DIR/.storybook/overlay-stories/overlays/break-even.ts` demonstrates the
correct `createPriceLine` usage. The Altrady implementation should match its style but
with transparent label background/border instead of solid, and non-editable.

## Files Affected

- `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js` —
  `createBreakEven`, `updateBreakEven`, `removeBreakEven` methods
- `src/containers/trade/trading-terminal/widgets/super-chart/overlays/break-even.js` —
  update call sites to match new method signatures

## Non-Requirements

- No changes to the PnL order line (separate overlay in the same component)
- No changes to break-even visibility logic or position calculations
- No new chart settings or user-facing configuration
