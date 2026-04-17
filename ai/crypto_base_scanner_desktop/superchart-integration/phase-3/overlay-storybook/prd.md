# PRD: Overlay Storybook (Superchart Repo)

## Goal

Set up Storybook in the Superchart library to stage overlay components with
interactive controls. Each overlay is developed and proven in isolation before
being ported to Altrady.

## Context

Direct integration of overlays into Altrady proved difficult to debug — issues
with the klinecharts API (missing text labels on priceLine, unknown overlay
props, broken crosshair interaction) are easier to isolate and fix in a standalone
environment. This phase creates that environment and stages the first overlay
(break-even) as a reference.

## Relationship to Phase 3

Phase 3 (Overlays in Altrady) depends on this. The workflow becomes:

1. **This PRD** — stage overlay in Storybook, prove the API works, fix lib issues
2. **Phase 3 PRD** — port to Altrady using the Storybook story as a template

## Done Looks Like

- Storybook runs in the Superchart repo (`pnpm storybook`)
- Break-even story renders a live Superchart with a toggleable labeled price line
- Story serves as a copy-paste reference for the Altrady overlay

## Scope

### Storybook setup

- Install Storybook with Vite builder (matches existing Vite 7 setup)
- Configure to use the existing `examples/client` datafeed and overlay patterns
- Stories go in `examples/stories/`

### Break-even story

A single story that renders a full Superchart instance and draws a break-even
priceLine overlay.

**Controls:**
- Toggle: show/hide break-even line
- Number input: price value

**Overlay requirements:**
- Purple line (#D05DDF) at the specified price
- Text label "Break even" visible on the price axis or line
- Dashed line style

This is the same overlay that `examples/client/src/overlays/overlays.ts` already
partially demonstrates — but without the text label.

### What the story proves

- The correct API call to create a priceLine with a visible text label
- Whether `extendData`, `text` styles, or a different mechanism controls the label
- The correct overlay update/removal lifecycle

## Future Stories (added per overlay as Phase 3 progresses)

- PNL handle — orderLine with text, quantity, cancel button
- Bid/Ask — live-updating priceLine pair
- Trade markers — buy (up arrow) vs sell (down arrow) with color
- Price/Time Select — crosshair tracking + click callback
- Order lines — draggable interactive price lines
- Alert lines
- Grid bot levels

## Technical Notes

- Superchart repo: Vite 7, React 18/19, TypeScript, pnpm
- Reuse `CoinrayDatafeed` from `examples/client/src/datafeed/`
- Each story renders a full Superchart instance (container, datafeed, dataLoader)
- Storybook controls via `@storybook/addon-controls` (args)
- The chart needs real market data via VITE_COINRAY_TOKEN env var

## Out of Scope

- Altrady integration (Phase 3)
- Stories for overlays not yet needed
- Visual regression testing
- Storybook deployment/hosting
