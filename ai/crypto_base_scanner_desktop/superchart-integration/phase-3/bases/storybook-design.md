# Design: Bases Overlay — Superchart Storybook

## Overview

Implements the Bases storybook story per the [PRD](storybook-prd.md).
Two files: a helper module (`overlays/bases.ts`) and the story (`Bases.stories.tsx`).

All work in the Superchart repo: `.storybook/overlay-stories/`.

---

## File Layout

```
.storybook/overlay-stories/
  overlays/bases.ts          # create/remove functions (pure, no React)
  Bases.stories.tsx           # story + demo component (already exists, will be rewritten)
```

---

## Helper Module: `overlays/bases.ts`

### Types

```ts
interface Base {
  id: number
  price: number
  formedAt: string       // ISO timestamp
  crackedAt: string | null
  respectedAt: string | null
}

interface BaseColors {
  notCracked: string
  cracked: string
  respected: string
}
```

### Color Resolution

```ts
function getBaseColor(base: Base, colors: BaseColors): string
```

Returns `colors.respected` if `respectedAt`, `colors.cracked` if `crackedAt`, else `colors.notCracked`.

### `createBaseLine`

Draws a non-selected base (PRD R1 + R2). Returns an array of overlay IDs.

```ts
function createBaseLine(
  chart: Chart,
  base: Base,
  nextBaseFormedAt: number | null,  // ms, or null if last base
  colors: BaseColors,
): string[]
```

Internals:
1. Parse `formedAt` to ms timestamp.
2. Determine end time:
   - If `crackedAt`: parse to ms.
   - Else: `nextBaseFormedAt ?? Date.now()`.
3. Create a `segment` overlay: two points at `(formedAt, price)` and `(endTime, price)`, `lock: true`.
   - After creation, call `applyProperties` with `{lineColor, lineWidth: 2, lineStyle: "solid"}`.
   - Note: `styles.line` does NOT work for Pro overlays — they read from the internal properties Map via `setProperties()`.
4. If `respectedAt`: create a second `segment` from `(crackedAt, price)` to `(respectedAt, price)`, `lock: true`.
   - After creation, call `applyProperties` with `{lineColor: colors.notCracked, lineWidth: 1, lineStyle: "solid"}`.
5. Return all created IDs.

### `createSelectedBase`

Draws the selected base (PRD R3 + R4). Returns an array of overlay IDs.

```ts
function createSelectedBase(
  chart: Chart,
  base: Base,
  colors: BaseColors,
  showBox: boolean,
  medianDrop: number,
): string[]
```

Internals:
1. Determine end time: if `respectedAt` → parse to ms, else `Date.now()`.
2. Create a `segment` overlay from `(formedAt, price)` to `(endTime, price)`, `lock: true`.
   - After creation, call `applyProperties` with `{lineColor, lineWidth: 2, lineStyle: "solid"}`.
3. If `showBox`:
   - Compute `dropPrice = price * (100 + medianDrop) / 100`.
   - Compute `midPrice = (price + dropPrice) / 2`.
   - Create a `rect` overlay with two points: `(formedAt, price)` and `(endTime, dropPrice)`, `lock: true`.
   - After creation, call `applyProperties` with `{style: "fill", backgroundColor: color + "33", borderWidth: 0}`.
     - `"33"` = hex for ~20% opacity.
   - Create a `segment` at `dropPrice` from `formedAt` to `endTime` (bottom border), `lock: true`.
   - After creation, call `applyProperties` with `{lineColor: color, lineWidth: 1, lineStyle: "solid"}`.
   - Create a `segment` at `midPrice` from `formedAt` to `endTime` (dashed midline), `lock: true`.
   - After creation, call `applyProperties` with `{lineColor: color, lineWidth: 1, lineStyle: "dashed"}`.
4. Return all created IDs.

### `removeBase`

```ts
function removeBase(chart: Chart, ids: string[]): void
```

Calls `chart.removeOverlay({id})` for each.

### Why `segment` and not `horizontalSegment`

`horizontalSegment` constrains both points to the same value but still needs two `{timestamp, value}` points. `segment` with identical `value` on both points achieves the same visual result and is more explicit about what's happening — the timestamps are different but the price is the same. Either works; `segment` is chosen for consistency with the existing Lines story patterns.

---

## Story: `Bases.stories.tsx`

### Data

The `BASES` constant already exists in the file with real Altrady data (5 bases for BINA_USDT_BTC). Keep it as-is.

### Demo Component: `BasesDemo`

Args interface:

```ts
interface BasesArgs {
  showBases: boolean
  showBox: boolean
  showRespected: boolean
  showNotRespected: boolean
  showNotCracked: boolean
  selectedBaseId: string         // base id as string, or "none"
  medianDrop: number
  notCrackedColor: string
  crackedColor: string
  respectedColor: string
  symbol: string
}
```

Component flow:

1. Render `<SuperchartCanvas symbol={symbol} onChart={onChart} onVisibleRangeChange={onVisibleRangeChange} />`.
2. Track `chart` in state via `onChart` callback.
3. Track `visibleRange` (`VisibleTimeRange | null`) in state via `onVisibleRangeChange` callback. `VisibleTimeRange` has `from`/`to` in unix seconds.
4. In a `useEffect` keyed on all control args + `chart` + `visibleRange`:
   a. Clear previous overlays (tracked in `idsRef: Record<number, string[]>`).
   b. If `!showBases`, return early.
   c. Filter bases per PRD filtering logic (toggle filters + visible-range filter).
   d. Sort filtered bases by `formedAt`.
   e. For each base:
      - If it's the selected base (`id === selectedBaseId`), call `createSelectedBase`.
      - Else, call `createBaseLine` with `nextBaseFormedAt` from the next base in the sorted list.
      - Store returned IDs in `idsRef.current[base.id]`.
   f. Cleanup function clears all overlays.

### Visible-range filtering

Applied inside `filterBases` (or alongside it). Given `visibleRange: {from, to}` in seconds:
- `toSeconds(base.formedAt) < visibleRange.to`
- If `base.respectedAt`: `toSeconds(base.respectedAt) >= visibleRange.from`

If `visibleRange` is null (not yet received), skip visible-range filtering and draw all bases.

### Data Loading Timing

The chart may not have data when the effect first runs. Follow the Trades story pattern: check `chart.getDataList().length`; if empty, use a `setTimeout` retry. This only matters for initial load.

### Controls

```ts
const meta: Meta<typeof BasesDemo> = {
  title: "Overlays/Bases",
  component: BasesDemo,
  argTypes: {
    showBases:         {control: "boolean", table: {category: "Visibility"}},
    showBox:           {control: "boolean", table: {category: "Visibility"}},
    showRespected:     {control: "boolean", table: {category: "Visibility"}},
    showNotRespected:  {control: "boolean", table: {category: "Visibility"}},
    showNotCracked:    {control: "boolean", table: {category: "Visibility"}},
    selectedBaseId:    {control: "select", options: ["none", ...BASES.map(b => String(b.id))],
                        table: {category: "Selection"}},
    medianDrop:        {control: {type: "number", min: -10, max: 0, step: 0.5},
                        table: {category: "Selection"}},
    notCrackedColor:   {control: "color", table: {category: "Colors"}},
    crackedColor:      {control: "color", table: {category: "Colors"}},
    respectedColor:    {control: "color", table: {category: "Colors"}},
    symbol:            {control: "text", table: {category: "Chart"}},
  },
}
```

Default story args:

```ts
export const Default: Story = {
  args: {
    showBases: true,
    showBox: true,
    showRespected: true,
    showNotRespected: true,
    showNotCracked: true,
    selectedBaseId: "none",
    medianDrop: -3,
    notCrackedColor: "#8B8D92",
    crackedColor: "#37CB95",
    respectedColor: "#F15959",
    symbol: "BINA_USDT_BTC",
  },
}
```

---

## Klinecharts API Usage

| Need | Overlay | Points | Properties (via `setProperties`) |
|------|---------|--------|----------------------------------|
| Base line (R1, R3) | `segment` | `[{ts, price}, {ts, price}]` | `{lineColor, lineWidth: 2, lineStyle: "solid"}` |
| Continuation line (R2) | `segment` | `[{ts, price}, {ts, price}]` | `{lineColor, lineWidth: 1, lineStyle: "solid"}` |
| Drop zone box (R4) | `rect` | `[{ts, topPrice}, {ts, bottomPrice}]` | `{style: "fill", backgroundColor: color + "33", borderWidth: 0}` |
| Box bottom border (R4) | `segment` | `[{ts, dropPrice}, {ts, dropPrice}]` | `{lineColor, lineWidth: 1, lineStyle: "solid"}` |
| Box midline (R4) | `segment` | `[{ts, midPrice}, {ts, midPrice}]` | `{lineColor, lineWidth: 1, lineStyle: "dashed"}` |

All overlays use `lock: true` (non-interactive).

### Important: Pro Overlays Use `properties`, Not `styles`

Superchart's `segment` and `rect` are **Pro overlays** — their `createPointFigures` reads from an internal properties Map (via `setProperties`), NOT from the `styles` object on the overlay. Passing `styles.line` or `styles.polygon` has no effect because figure-level styles from `createPointFigures` override them.

After calling `chart.createOverlay()`, retrieve the overlay with `chart.getOverlays({id})` and call `setProperties(props, id)` on it.
