# Code review — flexlayout-react 0.7.15 → 0.9.0 upgrade

Captured 2026-04-30, after the bulk of the upgrade work landed (drawer
collapse/expand mechanics, drag-and-drop rewire, ghost-tab handling, layout
locking, default-layout normalization).

**Legend:** R = real bug · S = stale/dead · A = architectural · G = newer-API
adoption · ? = needs user input.

## Real bugs (throwaway-only mutations don't reach the displayed Model)

The stable-Model fix in `flex-grid.js` (memoize Model on `layout?.id`) means
any code path that mutates a throwaway `FlexLayout.Model.fromJson(...)` and
writes JSON back to Redux will *not* update the rendered Model. Several
older paths still do this.

- **R1.** `trading-layouts-controller.activateWidget` (l. 709) — operates on
  a throwaway and writes JSON to Redux. `Actions.selectTab` never reaches
  display. Apply the `this.model || fromJson(...)` pattern used in
  `selectTab` / `toggleWidget`.

- **R2.** `trading-layouts-controller.toggleHeightFixedToScreen` (l. 667) —
  `addBottomDrawer` / `ejectBottomDrawer` mutate a throwaway. Drawer
  add/remove won't apply visually. Same fix.

- **R3.** `chart-layouts-controller.setTabId` (l. 173) — throwaway-only id
  rename. Live keeps stale id; subsequent lookups by the new id won't find
  the node in display.

- **R4.** `trading-layouts-controller.ejectBottomDrawer` (l. 300) —
  `Actions.deleteTab(BOTTOM_DRAWER_GHOST_TAB_ID)` uses the raw constant id;
  on a runtime live Model the ghost id has been decorated by
  `correctTabNodeIds` to `##bottom_drawer_ghost_tab_tab` → no-op delete.
  Find ghost by component (use `findBottomDrawerGhost`).

- **R5.** `trading-layouts-controller.setSplitterSize` (l. 623) dispatches
  `Actions.updateModelAttributes({splitterSize})` — `splitterSize` is no
  longer a Model global in 0.9.0 (CSS variable only). The `doAction` line
  is a no-op.

## Stale / dead code

- **S1.** `correctLayoutOnce` l. 353-354 writes `tabSetTabStripHeight` and
  `splitterSize` to global — both removed/ignored in 0.9.0. Drop.

- **S2.** `default-layouts.js` `FLEX_LAYOUT_BORDER_BOTTOM_HEIGHT = 0` and
  `FLEX_LAYOUT_BORDER_BOTTOM_EMPTY_HEIGHT = 0` — unused. Drop.

- **S3.** `flex-grid.js` l. 195-201 — `useEffect` that recomputes
  `setSplitterSize` from `hasOverflow.y` is moot now that splitter size is a
  CSS variable. The two constants `FLEX_LAYOUT_GAP_SIZE` /
  `FLEX_LAYOUT_GAP_SIZE_OVERFLOW` are also both `2` in `default-layouts.js`,
  so the conditional is meaningless. Drop the effect.

- **S4.** `trading-layouts-controller.handleAdjustSplit` l. 589 + l. 620 —
  `const drawerIdx = ...` followed by `void drawerIdx // silence lint`
  is a debugging artifact; both lines deletable.

- **S5.** `flex-layout.scss` l. 1-9 — `body > div[style*="z-index: 998"]`
  block is entirely commented out; dead.

- **S6.** `flex-layout.scss` l. 86-91 — multi-line commented-out
  drawer-disable rule; dead.

## Architectural

- **A1.** `DEFAULT_WIDGET_TAB_NODE_ID` Proxy in `default-trading-layouts.js`
  decorates **every** component id, including the ghost components
  (`#bottom_drawer_ghost_tab` → `##bottom_drawer_ghost_tab_tab`). That
  decoration is the root cause of multiple workarounds:
  `findBottomDrawerGhost`, `findCenterGhost`, the bug in **R4**, and the
  stale-`centerGhostTab`-after-recursive-`addCenterGhostTab` bug we fixed
  via just-in-time re-lookup.

  Special-casing ghost components in the Proxy (return the constant id
  unchanged for ghosts) eliminates most of those workarounds.

- **A2.** `chart-layouts-controller.syncWithChartTabs` mirrors each action
  on both throwaway and live (`model.doAction(action)` followed by
  `if (liveModel) liveModel.doAction(action)`) — duplicate calls.
  Trading uses a cleaner `live || fallback throwaway` pattern in
  `selectTab` / `toggleWidget`. Unify.

- **A3.** Selectors `selectCurrentLayoutBottomDrawerCollapsed` and
  `selectCurrentLayoutSideDrawerEmpty` (TradingLayoutSelectors) rebuild a
  full Model from JSON inside every `useSelector` call — that's a hot path.
  Read from `Controller.get().model` when available; fall back to `fromJson`
  only when no live Model exists yet.

## Newer-API adoption (PRD goal 3)

- **G1.** `onTabSetPlaceHolder` (added in 0.9.0) replaces the current
  `EmptyTabset` + ghost-component dance for the "Drop a widget here"
  empty-state. It would also remove the need for the bottom-drawer ghost
  tab as a content-area placeholder, simplifying a lot of related logic.

- **G2.** Apply the G1 pattern (`onTabSetPlaceHolder` +
  `enableDeleteWhenEmpty: false`) to the **center** tabset too. Replaces
  the center ghost as the structural anchor: `checkCenterSection`
  dynamically toggles the anchor flag (and `enableDrag: false`) on
  whichever tabset is currently the center singleton. Kills
  `addCenterGhostTab`/`removeCenterGhostTab`, the A1 Proxy special-case,
  ghost branches in `allowDrop`, the `#center_ghost_tab` CSS hide rule,
  ghost children in default JSON, and the ghost case in
  `grid-content.js`.

## Resolved (formerly user-input items)

- **(ex-?1, kept).** Overflow menus stay disabled. The `display:none` rules
  on `FLEXLAYOUT__TAB_BUTTON_OVERFLOW` / `..._COUNT` in
  `flex-grid-wrapper.js` (`tradingGridCss`) are intentional and remain.

- **(ex-?2, removed).** `_glass` SCSS hack at `flex-layout.scss` l. 1-9
  removed. Verified against 0.9.0 source: no `_glass` div, no
  `z-index: 998` anywhere — the selector matched nothing, and the rule
  body was already commented out. Increment 10 closed.

## Suggested ordering

A clean-up pass of **R1–R5 + S1–S6** is mechanical and low-risk — can land
first as a single commit. **A1–A3** and **G1** are bigger and may shake
loose other behavior; do them after the clean-up.

---

# Test suite

Each test is either **V** (visual — perform it in the running app) or **M**
(model — perform an action, then save the layout JSON and paste it here for
me to verify). For M-tests: open DevTools → Redux → `flexLayouts.layouts[i]
.serializedSettings.flexLayout` to grab the JSON.

## G2 — center placeholder + ghost retirement

- **G2.1 (V)** Open default Simple layout. Drag CenterView out of the
  center tabset (e.g. into the right border).
  *Expect:* center tabset stays alive (anchor) and shows the
  "Drop a widget here" placeholder. No console errors. No
  "Unknown widget" placeholder for `#center_ghost_tab`.

- **G2.2 (V)** Drag CenterView (or any widget) back into the empty
  center tabset.
  *Expect:* widget docks; placeholder disappears; tabset still has
  `enableDeleteWhenEmpty: false` (still anchor since count is 1).

- **G2.3 (M)** After G2.1, copy the layout JSON.
  *Expect (I will check):* singleton center tabset has
  `enableDeleteWhenEmpty: false`, `enableDrag: false`, `children: []`.
  No tab anywhere has `component: "#center_ghost_tab"` or
  `id: "#center_ghost_tab"`.

- **G2.4 (V — legacy migration)** Load a saved custom layout that still
  contains a `#center_ghost_tab` tab in JSON.
  *Expect:* opens cleanly, no "Unknown widget" tab visible. Save again
  and re-open — JSON has no ghost child.

- **G2.5 (V — anchor flag transitions, Advanced layout)** Open the
  Advanced layout (3 center tabsets). Empty the OrderBook tabset
  (close/drag away its widget).
  *Expect:* OrderBook tabset gets deleted (default
  `enableDeleteWhenEmpty: true`). Other two tabsets remain. After this,
  empty Trades tabset.
  *Expect:* Trades tabset deleted. The remaining
  `CenterView+MarketDepth` tabset is now the singleton — anchor flags
  applied (no longer draggable, won't delete on emptying).

- **G2.6 (V — split → re-anchor)** From Simple (singleton anchor),
  drag MarketDepth from the right border into the center, splitting
  the center tabset into 2.
  *Expect:* original CenterView tabset's anchor flag is removed (drag
  enabled, deleteWhenEmpty: true) — confirmed by being able to drag it.

- **G2.7 (M — anchor flags after re-anchor)** After G2.5 (down to 1
  center tabset) and after G2.6 (up to 2 center tabsets), copy JSON.
  *Expect (I will check):* tabset count → only the singleton has
  `enableDeleteWhenEmpty: false` and `enableDrag: false`; in
  multi-tabset state, no center tabset has the anchor flags.

- **G2.8 (V — drop on empty center)** With center anchor empty
  (placeholder visible), drag a widget over the center area.
  *Expect:* drop highlight appears, widget docks correctly, no
  drop-into-ghost-index off-by-one.

## G1 — bottom-drawer placeholder + ghost retirement

- **G1.1 (V)** Drag the last widget out of the bottom drawer.
  *Expect:* drawer stays alive at collapsed bar height, with no tab buttons
  and the "Drop a widget here" placeholder visible inside the drawer area.

- **G1.2 (V)** Drag a widget back into that empty drawer.
  *Expect:* widget docks as a tab; placeholder disappears; drawer expands
  to the previously-saved expanded weight.

- **G1.3 (M)** After G1.1, copy the layout JSON.
  *Expect (I will check):* drawer tabset has `enableDeleteWhenEmpty: false`,
  `weight: 0.001`, `children: []`, and **no** child with
  `component: "#bottom_drawer_ghost_tab"`.

- **G1.4 (V — legacy migration)** Use a saved layout from before this
  branch (one that still has a `#bottom_drawer_ghost_tab` child in JSON)
  and load it.
  *Expect:* opens cleanly, drawer renders correctly, no console errors.
  Save again and re-open — JSON no longer contains the ghost child.

- **G1.5 (V)** Drag a widget into the placeholder area of an empty drawer
  (i.e. the placeholder is the drop target, not a tab strip).
  *Expect:* widget docks; placeholder disappears.

## A1 — Proxy ghost-id special-case

A1 became dead code after **G2** retired the center ghost. No tests.

## A2 — chart-layouts `syncWithChartTabs` unify

- **A2.1 (V)** On `/charts` page, add 2 chart tabs. Switch markets in each.
  Reorder them. Close one.
  *Expect:* layout follows along — no duplicate or zombie tabs, no console
  warnings about "node not found".

- **A2.2 (M)** After A2.1, copy chart-layout JSON.
  *Expect (I will check):* tab count and order match the active chart-tabs
  selector; tab ids match `chartTabs[].id`.

## A3 — live-Model drawer-state selectors

- **A3.1 (V)** Open trading layout. Toggle drawer collapse a few times,
  toggle layout lock, switch layouts.
  *Expect:* the collapse/expand button icon (`angle-double-up` ↔
  `angle-double-down`) is in sync with the actual drawer state on every
  click, no flicker, no off-by-one.

- **A3.2 (V — regression)** With the right border (sidebar) emptied of
  widgets vs. populated, the side-drawer empty selector should still
  drive whatever UI hangs off it.
  *Expect:* no visual regression vs. before this branch.

## R1 — `activateWidget` on live Model

- **R1.1 (V)** From the Widgets dropdown, click an *already-mounted* but
  *non-selected* widget (i.e. it's a tab in some tabset, not currently
  active).
  *Expect:* its tabset focuses that tab — the widget becomes visible.

- **R1.2 (V)** Click a *not-yet-mounted* widget from the dropdown.
  *Expect:* widget gets added and selected (this also exercises the
  add-tab path).

## R2 — `toggleHeightFixedToScreen` on live Model

- **R2.1 (V)** Toggle "Fixed to Screen" off (drawer should appear) then
  on (drawer should disappear / be ejected).
  *Expect:* bottom drawer appears/disappears immediately on each toggle.

- **R2.2 (M)** After toggling off, copy JSON.
  *Expect:* root row contains the bottom-drawer tabset.
  After toggling on, copy JSON again.
  *Expect:* root row no longer contains the bottom-drawer tabset.

## R3 — `chart-layouts.setTabId` on live Model

- **R3.1 (V)** On `/charts`, after a chart-tab is created, ensure the
  framework rename (when chart-tab id changes) doesn't leave a stale
  tab id in the rendered model.
  *Expect:* tab keeps interacting normally; switching markets in it works;
  closing it works.

## R4 — `ejectBottomDrawer` ghost-id (now obsolete via G1)

- **R4.1 (V)** Toggle "Fixed to Screen" on with the drawer populated.
  *Expect:* drawer ejects cleanly. After re-enabling, drawer comes back
  with same widgets. No orphan ghost child anywhere in JSON afterwards.

## R5 — `setSplitterSize` Action no-op

- **R5.1 (V)** Splitter visually is 2px in normal state.
  *Expect:* matches what we want; CSS variable controls it (no model
  attribute needed).

## S-series — regression sweep after cleanup

- **S1.1 (V)** Switch through all 4 default trading layouts (Simple,
  Advanced, two breakpoints).
  *Expect:* each renders without console errors; tabsets, splitters,
  sidebar, drawer all correct.

- **S2.1 (V)** Bottom border / right border render with no extra spacing
  artifacts.
  *Expect:* no gap / no overlap from the deleted "border bottom height"
  constants.

- **S3.1 (V)** With many widgets, scroll the trading layout — no
  splitter-resize jitter from the deleted overflow effect.

## Drawer collapse / expand mechanics

These are behaviors the upgrade introduced — none existed in 0.7.15.

- **D1 (V)** Click the collapse button (`angle-double-down`) on the
  drawer.
  *Expect:* drawer shrinks to a thin bar (~40px tab strip), button flips
  to `angle-double-up`.

- **D2 (V)** Click the expand button.
  *Expect:* drawer restores to whatever expanded size it had before
  collapse (not a fixed default), button flips back.

- **D3 (V)** Drag the drawer splitter all the way down.
  *Expect:* drawer auto-collapses on release; collapsed state remembers
  the size you had before starting the drag.

- **D4 (V)** Click expand from a collapse caused by D3.
  *Expect:* drawer expands to the pre-drag size (not a default).

- **D5 (V)** From collapsed, drag the splitter up a small amount.
  *Expect:* drawer expands to *the dragged height* — not the previously
  saved expanded weight. Releasing leaves it there.

- **D6 (V)** From collapsed, click any tab button in the drawer's tab
  strip.
  *Expect:* drawer expands and that tab becomes the active tab.

- **D7 (V)** Drawer has ≥ 2 tabs. Drag the *currently selected* tab
  out to another tabset (move, not delete).
  *Expect:* drawer stays expanded; framework auto-selects a remaining
  tab. **No collapse**. (Regression: pre-fix, drawer collapsed once
  any move left only 1 tab — leftover ghost-era `length === 2` check.)

- **D8 (V)** Remove the *last* tab from the drawer (close via x or
  drag-out the only remaining tab).
  *Expect:* drawer auto-collapses (does not get deleted; placeholder
  hidden because drawer is collapsed).

- **D9 (M)** After D8, copy JSON.
  *Expect (I will check):* drawer tabset has `weight: 0.001`,
  `enableDeleteWhenEmpty: false`, `children: []`, and `config` carries
  `expandedWeight` as the pre-collapse value.

- **D10 (V — legacy)** Open a saved layout where the drawer was
  *expanded but `selected: -1`* (a 0.7.15-style "collapsed" state).
  *Expect:* on load, the migration normalizes it to a real collapsed
  drawer (weight = 0.001).

## Drag-and-drop (HTML5 native in 0.9.0)

- **DD1 (V)** Drag a tab from one tabset to another.
  *Expect:* moves cleanly; source tabset's previously active tab becomes
  selected (or it auto-collapses if it was the drawer with last tab out).

- **DD2 (V)** Drag a tabset header to split off into a new tabset.
  *Expect:* new tabset created at drop location.

- **DD3 (V)** From the right sidebar, drag a widget out into the main
  area.
  *Expect:* widget appears in new tabset *without* the SidebarHeader/`>>`
  chevron carried over (that header is sidebar-only).

- **DD4 (V)** Lock the layout. Try to drag a tab, a tabset, and a
  splitter.
  *Expect:* nothing moves. No drag preview appears.

- **DD5 (V)** On `/charts`, drag a chart's MarketHeaderBar to reorder
  the chart tabs.
  *Expect:* works with mouse. Touch-drag also works (recently fixed).

- **DD6 (V)** Drag a button or input *inside* a header (cursor is
  pointer/text/not-allowed, not grab).
  *Expect:* drag does **not** start (cursor filter blocks it).

- **DD7 (V — drag image follows cursor)** On `/charts`, grab the
  MarketHeaderBar near its **right edge** and drag.
  *Expect:* the drag overlay (small market-name pill) sits right at
  the cursor — not anchored far to the left where the bar starts.
  Drop position lines up with the cursor. Repeat grabbing on the left
  edge — overlay stays on the cursor too.

## Tabset move — preserve previously-active tab

- **TM1 (V)** Tabset A has tabs [t1, t2, t3] with t1 active. Click t2 to
  activate it (so t2 is now the active, t1 the previous). Drag t2 to
  tabset B.
  *Expect:* in tabset A, t1 (the previously-active) becomes selected
  again — not t3 by index, not nothing.

## Layout lock

- **LL1 (V)** Toggle layout lock from the Layout controls.
  *Expect:* lock icon appears next to "Layout" title and in the layouts
  popup. Drag of tabs / tabsets / splitters disabled. Unlock restores.

- **LL2 (V — regression)** With the layout locked, click widget buttons
  in the dropdown / use the collapse-drawer button.
  *Expect:* still work. Lock is for drag, not for actions.

## Layout revert

- **LR1 (V)** Modify the current layout (move widgets around). Hit
  "Revert".
  *Expect:* full reset to default; previously-modified state is gone;
  any drawer/center ghost handling fires fresh.

- **LR2 (M)** Just before revert, copy `layout.flexLayoutEpoch`. Revert.
  Read it again.
  *Expect:* `flexLayoutEpoch` increased — that's what forces the Model
  rebuild.

## Right border / sidebar

- **RB1 (V)** Right sidebar tabs render as icons (SidebarIcon component),
  not text.

- **RB2 (V)** Scroll wheel over the right border.
  *Expect:* the trading-layout container scrolls (wheel-relay).

- **RB3 (V)** Right-border tabset has the locked width
  (`FLEX_LAYOUT_BORDER_RIGHT_WIDTH - FLEX_LAYOUT_GAP_SIZE` ≈ 54px) and
  doesn't shrink even with no tabs selected.

## CSS / styling sanity

- **CSS1 (V)** Splitter is 2px; hover turns it blue (`--border-active`);
  active drag keeps it at 2px (no jump to 8px from `dark.css`).

- **CSS2 (V)** Tab bar minimum height ≈ 40px even when empty (replaces
  removed `tabSetTabStripHeight` global).

- **CSS3 (V)** Tab buttons hover background, selected underline, and
  toolbar buttons (refresh, settings, collapse, max/min) all render
  correctly.

- **CSS4 (V — full-height hover)** Hover any tab in any tabset.
  *Expect:* hover background fills the full tab cell vertically (40px),
  not just the text height. Applies to inactive **and** active tabs.

- **CSS5 (V — no leading padding)** Inspect the leftmost tab in any
  tabset. The tab cell starts flush against the tabbar's left edge —
  no 2px gap before the first tab.

## Default-layout regressions

- **DL1 (V)** Switch through all 4 default trading layouts (Simple,
  Advanced, breakpoint A, breakpoint B). For each:
  *Expect:* renders without errors, drawer/center/sidebar all populated
  per the JSON, no orphan ghost-tab children, no "Unknown widget" tabs.

- **DL2 (V)** For each default layout, the bottom drawer is
  **collapsed** on load (only the tab strip is visible).
  *Expect:* clicking the chevron expands it to ~35% of the layout
  height; clicking again collapses it back to the strip.

- **DL3 (M)** For each default layout, copy JSON immediately after
  selecting it.
  *Expect (I will check):*
  - bottom-drawer tabset has `weight: 0.001`, `selected: -1`,
    `enableDeleteWhenEmpty: false`, and `config.expandedWeight ≈ 35.7`.
  - center singleton tabsets (Simple, breakpoints) have
    `enableDeleteWhenEmpty: false` and `enableDrag: false`; Advanced
    (multi-tabset center) has neither.
  - no tab anywhere has `component: "#bottom_drawer_ghost_tab"` or
    `"#center_ghost_tab"`.
  - all real tab ids decorated as `#<component>_tab`.

## `toggleWidget` (widget dropdown)

- **TW1 (V)** Toggle off the *currently active* tab in a tabset of
  several tabs.
  *Expect:* the next remaining tab becomes selected (no `selected: -1`).

- **TW2 (V)** Toggle off the only tab in a non-drawer tabset.
  *Expect:* tabset is deleted (default `enableDeleteWhenEmpty`).

- **TW3 (V)** Toggle off the only tab in the drawer tabset.
  *Expect:* drawer stays alive (`enableDeleteWhenEmpty: false`),
  auto-collapses, placeholder visible.

- **TW4 (V)** Toggle a widget *back on* from the dropdown.
  *Expect:* added to its default tabset (or wherever the controller
  routes it) and selected.
