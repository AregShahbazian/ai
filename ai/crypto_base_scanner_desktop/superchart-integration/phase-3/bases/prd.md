# PRD: Bases Overlay — SuperChart Integration

## Overview

Port the base-scanner bases overlay from the TradingView chart to SuperChart. Bases are horizontal lines drawn on the chart representing price levels identified by the base scanner algorithm. This overlay replaces the existing TradingView-based `bases.js` component.

## Data Sources

### Bases list
- From Redux: `state.baseScanner.marketInfo[coinraySymbol][algorithm].bases`
- Can also be passed as `props.bases` (override)
- Each base has: `id`, `price`, `formedAt`, `crackedAt`, `respectedAt`

### Selected base
- From Redux: `state.baseScanner.selectedBases[coinraySymbol]`
- Can also be passed as `props.base` (override)
- A base is drawable if it has a `price` and (if in replay mode) its `formedAt` is before the replay time

### Median drop
- From Redux: `state.baseScanner.marketInfo[coinraySymbol][algorithm].marketStats.medianDrop`
- Parsed as float, defaults to `-3.0`

### Chart settings (Redux: `state.chartSettings`)
| Setting | Default | Description |
|---|---|---|
| `basesShow` | `false` | Master toggle — all base rendering |
| `basesShowBox` | `true` | Show selected base background box |
| `basesShowRespected` | `true` | Show bases where `respectedAt !== null` |
| `basesShowNotRespected` | `true` | Show bases where `respectedAt === null` |
| `basesShowNotCracked` | `true` | Show bases where `crackedAt === null` |

### Colors (from theme + user overrides via `chartColors`)
| Key | Dark default | Description |
|---|---|---|
| `notCrackedLine2` | `#8B8D92` | Not cracked base color |
| `crackedLine2` | `#37CB95` | Cracked base color |
| `respectedLine2` | `#F15959` | Respected base color |

Colors are resolved per-base: `respectedAt` → respected color, else `crackedAt` → cracked color, else → not-cracked color.

## Visual Rendering Requirements

### R1 — Non-selected base line

Each non-selected base is drawn as a horizontal line at its `price` level.

- **Start**: `formedAt` timestamp
- **End**:
  - If cracked: `crackedAt`
  - If not cracked: `formedAt` of the next base in the sorted/filtered list, or current time if last
- **Style**: solid line, **2px** width
- **Color**: determined by the base's type

### R2 — Respected base continuation line

When a base has been respected (`respectedAt !== null`), an additional thin continuation line is drawn:

- **Start**: `crackedAt` timestamp
- **End**: `respectedAt` timestamp
- **Style**: solid line, **1px** width
- **Color**: the not-cracked color (always, regardless of the base's own type)

### R3 — Selected base line

The currently selected base line:

- **Start**: `formedAt` timestamp
- **End**: if `respectedAt` → `respectedAt`, else → current time
- **Style**: solid line, **2px** width
- **Color**: same type-based color as R1

### R4 — Selected base background box

When `basesShowBox` is enabled and a base is selected:

- **Top edge**: the base `price` (the base line segment from R3 serves as the top border)
- **Bottom edge**: `price * (100 + medianDrop) / 100`
- **Bottom border**: a solid horizontal line at the bottom edge, same color as the base, **1px** width
- **Midline**: a dashed horizontal line at the midpoint `(price + dropPrice) / 2`, same color as the base, **1px** width
- **Horizontal span**: same start/end as the selected base line (R3)
- **Fill**: the base's type color at **20% opacity**
- **Side borders**: none

### R5 — Selected base is always drawn

The selected base is drawn **regardless of filtering**. It is not subject to visibility toggles or visible-range filtering. It is excluded from the regular base iteration (not drawn twice).

## Filtering

### Toggle filters

A base is shown only if all applicable toggle conditions pass:
- `basesShowRespected` is on, OR the base is not respected
- `basesShowNotRespected` is on, OR the base is respected
- `basesShowNotCracked` is on, OR the base is cracked

### Visible-range filter

Only bases within the chart's visible time range are drawn:
- `formedAt < visibleRange.to` — base formed before the right edge
- If `respectedAt`: `respectedAt >= visibleRange.from` — respected base is still visible

### Optimization

Only update the filtered list when the set of included bases actually changes (not on every visibleRange tick). The TradingView version tracks this with a `shouldUpdate` flag comparing current vs previous filtered sets.

## Lifecycle

- Clear all overlays on symbol change (`subscribeCoinraySymbolWillChange`)
- Clear and redraw when settings, filtered bases, selected base, or median drop change
- Clean up all overlays on unmount
- Master toggle `basesShow` controls all rendering — when off, nothing is drawn

## Props

The component accepts optional props for external use (e.g., training chart):
- `base` — override for the selected base
- `bases` — override for the bases list
