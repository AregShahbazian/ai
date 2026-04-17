# Tasks: Break-Even Overlay — Transparent Label Style

## Task 1: Update `chart-controller.js`

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`

1. Add `import {createPriceLine} from "superchart"` at top of file
2. Replace `createBreakEven(price, color)` with `createBreakEven(price, color, label)`
   using the `createPriceLine` fluent API per design
3. Replace `updateBreakEven(id, price, color)` with `updateBreakEven(line, price)` —
   only calls `line.setPrice(price)`
4. Replace `removeBreakEven(id)` with `removeBreakEven(line)` — calls `line.remove()`

**Verify:** No syntax errors, file imports resolve.

## Task 2: Update `break-even.js` call sites

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/overlays/break-even.js`

1. Add `import i18n from "~/i18n"` (if not already imported)
2. Update `createBreakEven` call (line 168) to pass translated label:
   `chartController.createBreakEven(price, chartColors.breakEvenPoint, i18n.t("containers.trade.superchart.overlays.breakEven"))`
3. Update `updateBreakEven` call (line 166) — already passes `(breakEvenRef.current, price)`,
   confirm it matches the new signature (no color arg)

**Verify:** `i18n` import present, call signatures match controller methods.

## Verification

- Open a position with a break-even point on the SuperChart
- Break-even line should be dashed, colored per chart settings
- Label should show translated "Break even" text with no background, text colored same as line
- Y-axis label should show price with solid colored background and white text
- Switching symbol should clear the break-even line without errors
- Break-even price updates when position data changes
