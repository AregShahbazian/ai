# Tasks: Bases Overlay — Superchart Storybook

All work in `$SUPERCHART_DIR/.storybook/overlay-stories/`.

Refer to [design](storybook-design.md) for signatures, styles, and API details.

---

## 1. Write helper module `overlays/bases.ts`

File: `.storybook/overlay-stories/overlays/bases.ts`

Currently empty. Implement:

1. Export `Base` and `BaseColors` interfaces per design.
2. Export `getBaseColor(base, colors)` — returns the color string for a base's type.
3. Export `createBaseLine(chart, base, nextBaseFormedAt, colors)`:
   - Main segment: `formedAt` → `crackedAt` or `nextBaseFormedAt` or `Date.now()`.
   - If respected: second thin segment from `crackedAt` → `respectedAt` in `colors.notCracked`.
   - Returns `string[]` of overlay IDs.
4. Export `createSelectedBase(chart, base, colors, showBox, medianDrop)`:
   - Segment: `formedAt` → `respectedAt` or `Date.now()`.
   - If `showBox`: rect fill + bottom border segment (solid) + midline segment (dashed). See design for details.
   - Returns `string[]` of overlay IDs.
5. Export `removeBase(chart, ids)`.

All overlays: `lock: true`, timestamps in ms (klinecharts convention).

### Verify

Type-check only — no runtime test yet.

---

## 2. Rewrite `Bases.stories.tsx`

File: `.storybook/overlay-stories/Bases.stories.tsx`

Currently contains only the `BASES` data constant. Rewrite to a full story:

1. Keep the existing `BASES` array at the top.
2. Define `BasesArgs` interface (all controls).
3. Implement `BasesDemo` component:
   - `useState<Chart | null>` for chart instance, `onChart` callback.
   - `useRef<Record<number, string[]>>` for tracking overlay IDs per base.
   - `useEffect` keyed on `[chart, showBases, showBox, showRespected, showNotRespected, showNotCracked, selectedBaseId, medianDrop, notCrackedColor, crackedColor, respectedColor]`:
     - Clear all tracked overlays.
     - If `!showBases`, return.
     - Filter `BASES` per visibility toggles.
     - Sort by `formedAt`.
     - For each base: if selected → `createSelectedBase`, else → `createBaseLine` with next base's `formedAt`.
     - Track IDs in ref.
     - Cleanup function removes all.
   - Handle initial data loading (setTimeout retry if `getDataList()` empty).
4. Export `meta` with `argTypes` grouped by category (Visibility, Selection, Colors, Chart).
5. Export `Default` story with args per design.

### Verify

Run `pnpm storybook`. Open Overlays/Bases. Confirm:
- 5 base lines render at correct price levels.
- The one respected base (id 277804362) shows a thick red line `formedAt` → `crackedAt`, then a thin gray continuation line `crackedAt` → `respectedAt`.
- Not-cracked bases show gray lines extending to the next base's `formedAt` (or current time for last).

---

## 3. Verify controls

In the running storybook:

1. **Show Bases** off → all lines disappear. On → they return.
2. **Show Respected Bases** off → base 277804362 disappears.
3. **Show Not Cracked Bases** off → all bases except 277804362 disappear (they're all not-cracked).
4. **Show Not Respected Bases** off → base 277804362 is the only one shown (it's the only respected one).
5. **Selected Base** dropdown → pick a base ID:
   - That base's line extends to current time (or `respectedAt` if respected).
   - It's no longer drawn as a regular base.
6. **Show Selected Base Background** on + a base selected → box appears below the base line.
7. **Median Drop** slider → box height changes.
8. **Color pickers** → line colors update.

---

## 4. ~~Fix open questions~~ (Resolved)

Both resolved: Pro overlays use `setProperties` with `OverlayProperties` fields (e.g. `borderWidth`, `backgroundColor`), not `styles.polygon`/`styles.line`. Hex alpha works via canvas passthrough.

---

## 5. Visible-range filtering

File: `.storybook/overlay-stories/Bases.stories.tsx`

Only draw bases within the chart's visible time range:

1. Add `onVisibleRangeChange` callback to `SuperchartCanvas`, track `visibleRange` in state.
2. Add visible-range conditions to filtering:
   - `formedAt < visibleRange.to`
   - If respected: `respectedAt >= visibleRange.from`
3. Add `visibleRange` to the `useEffect` dependency array.
4. If `visibleRange` is null (initial state before first callback), skip visible-range filtering.

### Verify

Pan/zoom in storybook — bases should appear/disappear as they enter/leave the visible range.
