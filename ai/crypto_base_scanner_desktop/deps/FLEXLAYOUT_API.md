# FlexLayout (flexlayout-react) — Reference

**Source checkout:** `/home/areg/git/FlexLayout`
**Pinned version:** `0.7.15` (matches Altrady's `package.json`)
**Upstream:** https://github.com/caplin/FlexLayout
**Status:** old release branch — likely **no longer maintained / possibly removed from
remote**. Treat the local checkout as the canonical reference; do **not** assume
behaviours from later majors (1.x +) apply.

This is a multi-tab docking layout manager. Altrady uses it for the trading
terminal grid (`TradingLayoutsController`) and the `/charts` page
(`ChartLayoutsController`).

## Layout entry point

`<FlexLayout.Layout model={...} factory={...} onAction={...} onModelChange={...}
onRenderTab={...} onRenderTabSet={...} />` — see Altrady at
`src/containers/trade/trading-terminal/grid-layout/flex-grid/flex-grid.js`.

## Public Layout instance methods (relevant)

Defined in `src/view/Layout.tsx`:

- `moveTabWithDragAndDrop(node: TabNode | TabSetNode, dragText?: string)` — line 788.
  Programmatically initiates the same drag flow the user gets when grabbing the
  tabstrip. Drop targets / overlays / dock-location detection are identical.
- `addTabWithDragAndDrop(dragText, json, onDrop?)` — line 777. Drag starts
  immediately for a *new* tab.
- `addTabWithDragAndDropIndirect(dragText, json, onDrop?)` — line 800. Spawns
  an intermediate floating drag-rectangle the user clicks to start the drag.
- `addTabToTabSet`, `addTabToActiveTabSet` — non-DnD insertion.

These are reachable via a React `ref` on `<Layout/>`.

## Drag plumbing internals (read-only notes)

- `dragStart(...)` (line 176) is the private entrypoint everything funnels into.
- The default tab-strip drag is wired in `TabSet.tsx` / `TabButton.tsx` via
  `onMouseDown` / `onTouchStart` handlers that call `layout.dragStart(...)`.
- `setOnAllowDrop(fn)` on the model gates whether a given drop target accepts a
  given dragged node — Altrady uses this in `flex-grid.js`
  (`model.setOnAllowDrop(LayoutsController.allowDrop)`).

## Tabset / tabstrip toggles

Per-tabset attribute on the model JSON:

- `tabSetEnableTabStrip: false` — hides the tabbar entirely (used on `/charts`
  since commit `c58a0248bb` to free up vertical space; close button was moved
  into `MarketHeaderBar`).
- `tabSetEnableMaximize`, `tabSetEnableDrag`, `tabSetEnableDivide`, etc. —
  granular drag/dock controls per tabset.

When `tabSetEnableTabStrip` is `false`, the user has **no built-in handle** to
grab a tab — the public DnD methods above are the only way back.
