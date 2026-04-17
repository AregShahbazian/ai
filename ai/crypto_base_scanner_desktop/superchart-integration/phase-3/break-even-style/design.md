# Design: Break-Even Overlay — Transparent Label Style

## Approach

Replace the raw `chart.createOverlay` / `chart.overrideOverlay` calls with the
`createPriceLine` fluent API from `superchart`. This returns a `PriceLine` object
instead of a string ID, so the caller manages the object reference directly.

## API Changes

### `chart-controller.js`

**`createBreakEven(price, color, label)`** → returns `PriceLine` (was: string ID)

```js
import {createPriceLine} from "superchart"

createBreakEven(price, color, label) {
  const chart = this.getChart()
  if (!chart) return null
  return createPriceLine(chart, {price})
    .setLineColor(color)
    .setLineStyle("dashed")
    .setLineWidth(1)
    .setLabelTextColor(color)
    .setLabelBackgroundColor("transparent")
    .setLabelBorderColor("transparent")
    .setLabelPadding({left: 0, right: 0, top: 0, bottom: 0})
    .setLabelVisible(true)
    .setLabelAlign("center")
    .setLabelPosition("center")
    .setText(label)
}
```

**`updateBreakEven(line, price)`** — takes `PriceLine` object, only updates price

```js
updateBreakEven(line, price) {
  line.setPrice(price)
}
```

**`removeBreakEven(line)`** — takes `PriceLine` object

```js
removeBreakEven(line) {
  line.remove()
}
```

### `break-even.js`

Call sites update to pass the translated label on creation:

```js
chartController.createBreakEven(price, chartColors.breakEvenPoint, i18n.t("containers.trade.superchart.overlays.breakEven"))
```

Update call passes only `(line, price)` — no color:

```js
chartController.updateBreakEven(breakEvenRef.current, price)
```

Remove call passes the line object — `clearBreakEvenLine` already does
`chartController.removeBreakEven(breakEvenRef.current)`, no change needed since
`breakEvenRef.current` will now hold a `PriceLine` instead of a string ID.

## i18n Key

Use existing key: `containers.trade.superchart.overlays.breakEven` → "Break even"
(already in `src/locales/en/translation.yaml` line 1931).
