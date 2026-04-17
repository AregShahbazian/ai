# PRD: Bases Overlay — Superchart Storybook

## Overview

A Storybook story that renders base-scanner bases on a Superchart instance using real Altrady data for BINA_USDT_BTC. The story must visually replicate how bases appear in the current TradingView-based chart.

## Data

The story uses the hardcoded `BASES` array already present in `Bases.stories.tsx`. Each base object has:

| Field | Description |
|---|---|
| `id` / `baseId` | Unique identifier |
| `formedAt` | ISO timestamp — when the base was formed |
| `price` | The price level of the base (horizontal line) |
| `lowestPrice` | The lowest price reached from this base |
| `drop` | Percentage drop from price to lowestPrice |
| `currentDrop` | Current percentage drop from the base price |
| `crackedAt` | ISO timestamp when the base was cracked, or `null` |
| `respectedAt` | ISO timestamp when the base was respected, or `null` |

### Base type classification

A base's visual type is determined by its `crackedAt` and `respectedAt` fields:

| Type | Condition |
|---|---|
| **Not cracked** | `crackedAt === null` |
| **Cracked (not respected)** | `crackedAt !== null && respectedAt === null` |
| **Respected** | `respectedAt !== null` (implies `crackedAt !== null`) |

## Visual Rendering Requirements

### R1 — Non-selected base line

Each non-selected base is drawn as a **horizontal line** at its `price` level.

- **Start**: `formedAt` timestamp
- **End**:
  - If cracked: the line ends at `crackedAt`
  - If not cracked: the line extends to the `formedAt` of the next base in the list (sorted by `formedAt`), or to the current time if it is the last base
- **Style**: solid line, **2px** width
- **Color**: determined by the base type, using the three color controls (see Storybook Controls)

### R2 — Respected base continuation line

When a base has been respected (`respectedAt !== null`), an additional **thin continuation line** is drawn:

- **Start**: `crackedAt` timestamp
- **End**: `respectedAt` timestamp
- **Style**: solid line, **1px** width
- **Color**: the "not cracked" color (always uses the not-cracked color, regardless of the base's own type)

This visually communicates the "cracked period" — the time between being cracked and being respected.

### R3 — Selected base line

The currently selected base is drawn differently from non-selected bases:

- **Start**: `formedAt` timestamp
- **End**:
  - If respected: `respectedAt` timestamp
  - If not respected (whether cracked or not): current time
- **Style**: solid line, **2px** width
- **Color**: same type-based color as R1

The selected base line always extends to current time unless the base has been respected. This is because the selected base represents the base being actively monitored.

### R4 — Selected base background box

When enabled, the selected base shows a semi-transparent background box:

- **Top edge**: the base `price` (the base line segment from R3 serves as the top border)
- **Bottom edge**: `price * (100 + medianDrop) / 100` — note: `medianDrop` is negative, so the bottom is below the price
- **Bottom border**: a solid horizontal line at the bottom edge (`dropPrice`), same color as the base, **1px** width
- **Midline**: a dashed horizontal line at the midpoint `(price + dropPrice) / 2`, same color as the base, **1px** width
- **Horizontal span**: same start/end as the selected base line (R3)
- **Fill**: the base's type color at **20% opacity** (hex alpha `"33"`)
- **Side borders**: none (no vertical lines)

The `medianDrop` value comes from market stats. For the storybook, use a sensible default (e.g., `-3.0`).

### R5 — Non-selected bases are skipped for the selected base ID

When a base is the currently selected base, it is NOT drawn as a regular base line (R1). It is only drawn using the selected-base rendering (R3 + optionally R4).

## Storybook Controls

### Boolean toggles

| Control | Default | Description |
|---|---|---|
| Show Bases | `true` | Master toggle — hides all base rendering when off |
| Show Selected Base Background | `true` | Toggles the background box (R4) for the selected base |
| Show Respected Bases | `true` | When off, hides bases where `respectedAt !== null` |
| Show Not Respected Bases | `true` | When off, hides bases where `respectedAt === null` |
| Show Not Cracked Bases | `true` | When off, hides bases where `crackedAt === null` |

### Selected base dropdown

- A dropdown control listing all base IDs from the data, plus a "None" option
- Selecting a base ID makes that base the "currently selected" base (rendered per R3/R5)
- Default: "None" (no base selected)

### Color controls

Three color pickers, one per base type. In Altrady these come from chart settings (defaulting to theme values).

| Control | Default | Description |
|---|---|---|
| Not Cracked Color | `#8B8D92` | Color for bases where `crackedAt === null` |
| Cracked Color | `#37CB95` | Color for bases where `crackedAt !== null && respectedAt === null` |
| Respected Color | `#F15959` | Color for bases where `respectedAt !== null` |

### Median drop

- A numeric control for the `medianDrop` value used in the background box height calculation (R4)
- Default: `-3.0`

## Filtering Logic

Bases are filtered based on the boolean toggles:

- A base is shown only if ALL applicable toggle conditions pass:
  - `Show Respected Bases` is on, OR the base is not respected
  - `Show Not Respected Bases` is on, OR the base is respected
  - `Show Not Cracked Bases` is on, OR the base is cracked
- If `Show Bases` is off, nothing is drawn
- The selected base follows the same filtering — if it is filtered out, it is not drawn

### Visible-range filtering

Only bases within the chart's current visible time range are drawn. This matches the real Altrady app behavior:

- `formedAt` must be **before** the right edge of the visible range (`formedAt < visibleRange.to`)
- If `respectedAt` is set, it must be **at or after** the left edge (`respectedAt >= visibleRange.from`) — otherwise the respected base is off-screen to the left and should not be drawn

When the user pans or zooms, bases entering/leaving the visible range are added/removed accordingly.

## Non-requirements

- No interaction with bases (clicking, hovering, tooltips) — purely visual
- No real-time data fetching — hardcoded data only
- No replay mode support
- No theme switching — colors are controlled via Storybook controls with dark-theme defaults
