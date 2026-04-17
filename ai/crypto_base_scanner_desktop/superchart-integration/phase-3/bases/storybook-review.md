# Bases Story — Bug Fixes

## Round 1: Initial Review (2026-03-13)

### Bug 1: All bases are blue
**Root cause:** Pro overlays (like `segment`, `rect`) read colors from their internal `properties` Map via `setProperties()`, not from `styles.line` or `styles.polygon`. When calling `chart.createOverlay()` on klinecharts directly, `styles` is set on the overlay object but then overridden by `createPointFigures`' figure-level styles which read from the empty properties Map. Since properties is empty, `DEFAULT_OVERLAY_PROPERTIES.lineColor` (`#1677FF` blue) wins.

**Fix:** After each `chart.createOverlay()`, retrieve the overlay and call `setProperties()` with the correct values. Add a helper:
```ts
function applyProperties(chart: Chart, id: string, props: Record<string, unknown>) {
  const overlay = chart.getOverlays({ id })?.[0]
  if (overlay?.setProperties) overlay.setProperties(props)
}
```
- For segments: `applyProperties(chart, id, {lineColor, lineWidth: size, lineStyle: 'solid'})`
- For rect: `applyProperties(chart, id, {style: 'fill', backgroundColor: colorWithAlpha, borderWidth: 0})`

**Files:** `.storybook/overlay-stories/overlays/bases.ts`

---

### Bug 2: Respected base doesn't change thickness after crackedAt
**Root cause:** Consequence of bug 1. The code already draws two segments — thick (formedAt→crackedAt) and thin (crackedAt→respectedAt) — but since all lines render as default blue, the color/thickness difference is invisible.

**Fix:** Resolved by bug 1 fix. No additional changes needed.

---

### Bug 3: Box not low enough (selected base 280934343)
**Root cause:** Default `medianDrop` is `-3.0`, giving `dropPrice = 68977.91 * 97/100 = 66908.57`. In the real app, the box extends to ~59000, meaning the actual median drop is around `-14.5%`. The `-3` default is unrealistic.

**Fix:**
- Change default `medianDrop` arg from `-3` to `-14.5`
- Widen the control range from `[-10, 0]` to `[-30, 0]`

**Files:** `.storybook/overlay-stories/Bases.stories.tsx`

---

### Bug 4: Box has lines at sides (should only have top/bottom)
**Root cause:** `rect` overlay defaults to `style: 'stroke'` which draws all 4 borders. Setting `borderSize: 0` in `styles.polygon` gets overridden by `createPointFigures` which reads from the empty properties Map (same root cause as bug 1).

**Fix:** Resolved by bug 1 fix — `applyProperties` with `{style: 'fill', borderWidth: 0}` eliminates borders entirely (fill-only, no stroke).

---

### Bug 5: Box background not drawn, only outlines
**Root cause:** Same as bug 4. Default `style` is `'stroke'` (outline only, no fill). The `styles.polygon.color` is overridden by defaults from the empty properties Map.

**Fix:** Resolved by bug 1 fix — `applyProperties` with `{style: 'fill', backgroundColor: color + "33"}` gives the filled background.

---

### Summary of changes

**`.storybook/overlay-stories/overlays/bases.ts`:**
1. Add `applyProperties` helper function
2. In `createSegment`: after `chart.createOverlay()`, call `applyProperties` with `{lineColor, lineWidth, lineStyle}`
3. In `createSelectedBase` rect: after `chart.createOverlay()`, call `applyProperties` with `{style, backgroundColor, borderWidth}`

**`.storybook/overlay-stories/Bases.stories.tsx`:**
4. Change `medianDrop` default from `-3` to `-14.5`
5. Change `medianDrop` control range from `[-10, 0]` to `[-30, 0]`

### Verification
```bash
cd $SUPERCHART_DIR && pnpm storybook
```
Open Overlays/Bases and check:
- [x] Lines are gray/green/red (not blue)
- [x] Respected base: thick red line formedAt→crackedAt, then thin gray crackedAt→respectedAt
- [x] Selected base box: filled background, no side borders
- [ ] Box extends to ~59000 for base 280934343 with default medianDrop

---

## Round 2: Post-fix review (2026-03-13)

Bugs 1, 2, 5 confirmed fixed.

### Bug 3: Box not low enough — DEFERRED
The box height comes from `medianDrop` which in the real app comes from `marketStats.medianDrop`. The storybook default of `-3` is just a placeholder. This will be correct once the real frontend integration passes the actual value. No storybook change needed.

### Bug 4 (updated): Box missing bottom border line
**Round 1** fixed the side borders (no more vertical lines). But the TradingView reference (see `screenshots/bases.png`) shows the box should have:
- A **solid horizontal line at the top** (the base price — already drawn by the base line segment)
- A **solid horizontal line at the bottom** (the drop price)

Currently only the top line exists (it's the base line segment). The bottom line is missing.

**Fix:** Draw an additional `segment` at `dropPrice` spanning the same start→end as the box. Use the same color as the base line, width 1.

**Files:** `.storybook/overlay-stories/overlays/bases.ts`

---

### Bug 6 (new): Missing dashed midline in box
**Source:** TradingView reference (`screenshots/bases.png`) shows a **horizontal dashed line** at roughly the midpoint of the box (halfway between `price` and `dropPrice`).

Looking more carefully at the screenshot, the dashed line appears to be at the `lowestPrice` level (the actual lowest price the base dropped to), not the geometric midpoint. But since the storybook data doesn't include `lowestPrice`, and the line appears at roughly the midpoint in the screenshot, it's likely `price + (dropPrice - price) / 2` or specifically tied to `lowestPrice`.

**Fix:** Draw a `segment` at `(price + dropPrice) / 2` with dashed style, same color as the base, width 1. If the real app uses `lowestPrice`, this can be refined later in the frontend integration.

**Files:** `.storybook/overlay-stories/overlays/bases.ts`

---

### Summary of Round 2 changes

**`.storybook/overlay-stories/overlays/bases.ts`:**
1. In `createSelectedBase`, when `showBox`: add a solid `segment` at `dropPrice` (bottom border)
2. In `createSelectedBase`, when `showBox`: add a dashed `segment` at midpoint `(price + dropPrice) / 2`

### Verification
Open Overlays/Bases with a selected base + box enabled:
- [ ] Solid line at top of box (base price — already exists as base line)
- [ ] Solid line at bottom of box (drop price)
- [ ] Dashed line at midpoint of box
- [ ] Semi-transparent fill between top and bottom
- [ ] No vertical side borders

---

## Round 3: Visible-range filtering (2026-03-13)

### Bug 7 (new): All bases drawn regardless of visible range
**Source:** In the real Altrady app (`bases.js`), only bases within the chart's visible time range are drawn. The storybook currently draws all bases unconditionally.

The real app's filtering logic (lines 49-56 of `bases.js`):
- `formedAt < visibleRange.to` — base must have formed before the right edge
- If respected: `respectedAt >= visibleRange.from` — respected bases are hidden if their respectedAt is before the left edge

**Fix:** Use `SuperchartCanvas`'s `onVisibleRangeChange` callback to track visible range in state. Add visible-range filtering to the existing filter logic in `BasesDemo`. `VisibleTimeRange` has `from`/`to` in unix seconds.

**Files:** `.storybook/overlay-stories/Bases.stories.tsx`

### Verification
- [ ] Pan/zoom chart — bases outside visible range disappear, bases entering range appear
- [ ] Respected base disappears when panning past its `respectedAt`
- [ ] All existing toggle/color/selection controls still work
