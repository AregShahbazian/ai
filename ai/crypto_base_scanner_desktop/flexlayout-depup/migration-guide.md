# FlexLayout 0.7.15 → 0.9.0 — Altrady migration guide

Recipes for every Altrady tweak / call site that the upgrade affects. Each
section is: **what we do today** → **what changes in 0.9.0** → **the
recipe** → **risks / verification hints**.

Source-of-truth references:
- New API: `~/ai/crypto_base_scanner_desktop/deps/FLEXLAYOUT_API_LATEST.md`
- Upstream CHANGELOG: `/home/areg/Downloads/temp/FlexLayout/CHANGELOG.md`
  (entries for 0.8.0, 0.8.10, 0.8.14, 0.8.15, 0.8.19, 0.9.0 are the ones
  with breaking changes that affect us).

The list below is exhaustive for the call sites I surveyed in the existing
codebase — but anything new that surfaces during the upgrade should be
appended here as it's discovered, not just fixed silently.

---

## 1. `Layout` ref: `class Layout` → `ILayoutApi`

**Today (0.7.15):** the ref returned by `<FlexLayout.Layout ref={...} />` is
the class instance, with public methods directly on it.

**Now (0.9.0):** `Layout` is a function component (`React.forwardRef`). The
ref is an `ILayoutApi` handle exposing only the public methods.

**Recipe:**
- The current `layoutRef = useCallback((instance) => LayoutsController.setLayoutInstance(instance), ...)`
  in `flex-grid.js:155–157` keeps working — the callback receives the
  `ILayoutApi`. No change needed at the call site.
- TypeScript users would change `useRef<Layout>` → `useRef<ILayoutApi>`.
  Altrady is JS — non-issue here.

**Verify:** `ChartLayoutsController.get().layoutInstance` after mount has
`addTabToTabSet`, `moveTabWithDragAndDrop`, `getRootDiv`, etc. Run
`Object.keys(ChartLayoutsController.get().layoutInstance)` in devtools.

---

## 2. `moveTabWithDragAndDrop(node, dragText)` → `(event, node)` from `dragstart`

**Today** — `charts-grid-item.js:38–49`, `flex-grid.js:154–157`:

```js
const handleHeaderDragStart = (e) => {
  if (e.type === "mousedown" && e.button !== 0) return
  const cursor = getComputedStyle(e.target).cursor
  if (cursor !== "grab" && cursor !== "grabbing") return
  const layout = ChartLayoutsController.get()?.layoutInstance
  if (!layout) return
  const dragText = currentMarket ? util.marketName({coinraySymbol}) : undefined
  layout.moveTabWithDragAndDrop(node, dragText)   // ← old signature
}
// wired with onMouseDown / onTouchStart
```

**Now** — `moveTabWithDragAndDrop(event: DragEvent, node)` and *must* be
called from inside an HTML5 drag-start handler. Mouse/touch events are no
longer the trigger.

**Recipe:**
1. The wrapper `<div>` in `charts-grid-item.js:57` must become
   `draggable={true}` (HTML5 attribute), and the listener must be
   `onDragStart` instead of `onMouseDown` / `onTouchStart`.
2. The handler signature becomes `(e: React.DragEvent) => { ... layout.moveTabWithDragAndDrop(e.nativeEvent, node) }`.
3. The "only primary mouse button" gate isn't needed — HTML5 dragstart
   only fires for the primary button.
4. The cursor-based gate (only drag when cursor is `grab`/`grabbing`)
   stays — but now you'd use `e.target` from the dragstart event. To
   exclude buttons/inputs you can also set `draggable={false}` on those
   children, or check the cursor as today.
5. To set the drag preview text/image, call `layout.setDragComponent(e.nativeEvent, <span>{dragText}</span>, x, y)`
   *inside the same dragstart handler, before* `moveTabWithDragAndDrop`.
6. Touch — HTML5 drag-and-drop on iOS/Android needs the
   `pointerdown`/touch-drag polyfill behaviour built into FlexLayout 0.8+
   (it uses `dragstart` natively, browsers map long-press to it on
   mobile). The recent commit `6d23166130 fix: enable touch-drag on
   /charts MarketHeaderBar` explicitly added a touch path; **verify after
   upgrade whether touch-drag still works** without that path. If it
   doesn't, we may need a touch-event shim that synthesises a dragstart.

**Risks:**
- Buttons/inputs inside the header (close button, market picker) need
  `draggable={false}` so their clicks aren't hijacked.
- Long-press-to-drag on iOS may behave differently from the current
  `onTouchStart` path.

**Verify:**
- Desktop: drag the `MarketHeaderBar` of a chart on `/charts`; chart
  reorders into another tabset.
- Mobile (or device-emulator with touch enabled): long-press → drag
  works.
- Drag preview text shows the symbol (`BTC/USDT` etc.).
- Clicking the close button on the header still closes; clicking the
  market picker still opens it.

---

## 3. `splitterSize` global attr (dynamic update) → CSS variable

**Today** — `default-trading-layouts.js:41`, `default-chart-layouts.js:10`,
and dynamic update in `flex-grid.js:145–151` and `trading-layouts-controller.js:478–481`:

```js
TRADING_LAYOUT_GLOBAL = { ..., splitterSize: FLEX_LAYOUT_GAP_SIZE }
// ...
useEffect(() => {
  const newSplitterSize = hasOverflow.y ? FLEX_LAYOUT_GAP_SIZE_OVERFLOW : FLEX_LAYOUT_GAP_SIZE
  if (model.getSplitterSize() !== newSplitterSize) {
    TradingLayoutsController.get().setSplitterSize(model, newSplitterSize)
  }
}, [hasOverflow.y])
// inside the controller:
setSplitterSize = async (model, splitterSize) => {
  model.doAction(FlexLayout.Actions.updateModelAttributes({splitterSize}))   // ← will silently no-op
}
```

**Now** — `splitterSize` is no longer a global attribute. It's read from
the CSS variable `--splitter-size` (and `--splitter-active-size`,
`--splitter-handle-visibility`).

**Recipe:**
- Drop `splitterSize` from the JSON globals (it's harmless if it stays —
  the model just ignores unknown attrs — but it's misleading).
- Set `--splitter-size` on the layout container element. Easiest is on
  `.flex_grid_wrapper` in `flex-grid-wrapper.js`:
  ```js
  css`--splitter-size: ${gapSize}px;`
  ```
- For dynamic updates (`hasOverflow.y` toggles between `FLEX_LAYOUT_GAP_SIZE`
  and `FLEX_LAYOUT_GAP_SIZE_OVERFLOW`), read `hasOverflow.y` in
  `FlexGridWrapper` (it's already in scope via `ScrollViewContext` — or pass
  it down as a prop) and toggle the CSS variable directly.
- Remove `setSplitterSize` from `flex-layouts-controller.js` and
  `trading-layouts-controller.js`. The `useEffect` in `flex-grid.js:145`
  goes away.
- `model.getSplitterSize()` still returns a number (read from CSS at
  runtime by the layout). It's only useful for read-back; keep if there's
  a use, drop if not.

**Risks:** `model.getSplitterSize()` returns `8` (the FlexLayout default)
until the CSS variable resolves and the model picks it up. Any code that
runs synchronously on first render and relies on a precise value will see
`8`, not `FLEX_LAYOUT_GAP_SIZE`. The only such code today is the
`useEffect` we're removing — fine.

**Verify:** the gap between the trading-grid widgets is the right width;
when the parent scroll area gets overflow on Y the gap thins/widens
(whichever the existing constants encode).

---

## 4. `tabSetTabStripHeight` global → tab strip auto-sizes

**Today** — `default-trading-layouts.js:38`,
`default-chart-layouts.js:9`:
```js
tabSetTabStripHeight: FLEX_LAYOUT_TAB_STRIP_HEIGHT
```
Sets the explicit tab-bar height in pixels.

**Now** — removed entirely. Tab strip height is dictated by tabbar content
(font, padding) under flexbox.

**Recipe:**
- Drop `tabSetTabStripHeight` from both globals.
- If the resulting tab strip height visually differs from
  `FLEX_LAYOUT_TAB_STRIP_HEIGHT`, control it via CSS on
  `.flexlayout__tabset_tabbar_outer` (the `flex-grid-wrapper.js` already
  styles this class). Match `min-height: ${FLEX_LAYOUT_TAB_STRIP_HEIGHT}px`
  on the outer tabbar to pin to the legacy value.

**Risks:** the existing `FLEX_LAYOUT_TAB_STRIP_HEIGHT` constant is
referenced for layout calculations elsewhere (e.g.
`TradingLayoutSelectors.selectCurrentLayoutMinHeight`); keep the constant,
just don't pass it through the model anymore.

**Verify:** trading-terminal and `/charts` tabbars are the same pixel
height as the baseline screenshot.

---

## 5. `barSize` on border node → `size` attribute / CSS

**Today** — `default-trading-layouts.js:47`:
```js
const TRADING_LAYOUT_BORDER_RIGHT = {
  type: "border", location: "right",
  barSize: FLEX_LAYOUT_BORDER_RIGHT_WIDTH,    // ← removed in 0.9
  size: FLEX_LAYOUT_DRAWER_RIGHT_WIDTH,
  children: [],
}
```
`barSize` controlled the closed-state thickness of the right border (the
"sidebar icon" strip).

**Now** — `barSize` (and the global `borderBarSize`) is no longer in the
attribute set. The bar is sized by tabbar content under flexbox.

**Recipe:**
- Drop `barSize` from `TRADING_LAYOUT_BORDER_RIGHT`.
- The existing CSS in `flex-grid-wrapper.js:163–166` already sizes the
  right border's tab container explicitly:
  ```js
  .${CLASSES.FLEXLAYOUT__BORDER_INNER_TAB_CONTAINER_ + "right"} {
    height: ${FLEX_LAYOUT_BORDER_RIGHT_WIDTH - FLEX_LAYOUT_GAP_SIZE}px !important;
    left:   ${FLEX_LAYOUT_BORDER_RIGHT_WIDTH - FLEX_LAYOUT_GAP_SIZE}px !important;
  }
  ```
  Verify this still pins the right-border bar to the desired width. If
  the new flexbox layout uses different anchoring (e.g. `width` instead
  of `height`/`left` for vertical borders), the rule may need adjusting
  to set `width` on the toolbar/bar element directly.

**Verify:** the right-side sidebar icon strip is the same width as the
baseline screenshot, and the open drawer slides out to
`FLEX_LAYOUT_DRAWER_RIGHT_WIDTH` minus that strip.

---

## 6. `titleFactory` prop → `onRenderTab` mutates `renderValues.content`

**Today** — `flex-grid.js:88–97, 164`:
```jsx
const titleFactory = useCallback((node) => { ... return label }, [...])
<FlexLayout.Layout titleFactory={titleFactory} onRenderTab={onRenderTab} ... />
```

**Now** — `titleFactory` and `iconFactory` props are gone. `onRenderTab`
is the single hook for both icon (`renderValues.leading`) and label
(`renderValues.content`).

**Recipe:**
- Delete the `titleFactory` prop.
- Inside the existing `onRenderTab` callback, set
  `renderValues.content = <title from titleFactory>`.
- Altrady's current `onRenderTab` already mutates `renderValues.content`
  for the right-border sidebar icons — merge: set the sidebar-icon
  branch when on the right border, otherwise set the title-derived
  content.
- Add `marketTabs` and `inTrade` to the `onRenderTab` deps array (since
  they were previously deps of `titleFactory`).

**Verify:**
- Trading terminal tabs show the widget title (e.g. "Order book", "My
  trades") via `i18n.t(\`widgets.${component}.title\`)`.
- `/charts` tabs show the market name (e.g. "BTC/USDT").
- Right-border tabs show the sidebar icons, not the title.

---

## 7. Drag preview / drag image — `setDragComponent`

**Today** — `moveTabWithDragAndDrop(node, dragText)` accepted a string for
the drag preview.

**Now** — preview is set with `layout.setDragComponent(event, component, x, y)`
called *before* `moveTabWithDragAndDrop`/`addTabWithDragAndDrop`, both
inside a dragstart handler.

**Recipe:** in the `/charts` `MarketHeaderBar` `onDragStart` (see §2):
```js
layout.setDragComponent(e.nativeEvent, <span style={{padding: "4px 8px", ...}}>{dragText}</span>, 8, 8)
layout.moveTabWithDragAndDrop(e.nativeEvent, node)
```
Match the look of the existing drag rectangle from the baseline
screenshot.

**Verify:** the drag rectangle while dragging a chart header shows the
market symbol, sized/styled like the baseline.

---

## 8. `_glass` overlay z-index hack — re-evaluate

**Today** — `src/flex-layout.scss:5–9`:
```scss
body > div[style*="z-index: 998"] {
  // ...workaround for the unstyled glass overlay used for drag/overflow
}
```

**Now** — drag rendering and edge indicators have moved to
`flexlayout__layout_overlay`, `flexlayout__drag_rect`,
`flexlayout__edge_rect_*` classes; the overflow popup uses
`flexlayout__popup_menu*`. Whether an unstyled `z-index: 998` div still
exists is unclear without running it.

**Recipe:**
1. Leave the rule in place initially.
2. After the upgrade, ask the user to confirm: does dragging a tab over
   a Highcharts/SuperChart cell still work (no event-eating overlay)?
3. If yes — i.e. the bug the rule was working around is gone — delete
   the rule (and the comment block).
4. If the bug is still there, find the new selector
   (`.flexlayout__layout_overlay` or `.flexlayout__drag_rect`) and update
   the rule.

**Verify:** drag a tab across the chart area; (a) drag completes, (b)
overflow menu items remain clickable.

---

## 9. `popouts` JSON key → `subLayouts`

**Today** — Altrady doesn't currently use popouts (no `popouts` key in
`default-*.js`). But user-saved layouts might in theory contain it
(unlikely; popouts have to be enabled per tab).

**Now** — `popouts` is read on load and rewritten as `subLayouts` on
save, with each entry getting `type: "window"` (or `type: "float"` for
the new floating panels).

**Recipe:** no migration code needed — 0.9.0 handles it. Just be aware
that any persisted-layout snapshots used in tests/storybook may flip
`popouts` → `subLayouts` after a single load + save cycle.

**Verify:** load the app, save a layout, reload, layout still works.

---

## 10. `tabSetEnableClose` semantics changed

**Today** — Altrady doesn't set `tabSetEnableClose` (default `true` in
0.7.15 controlled the visibility of a per-tabset close button).

**Now** — `tabSetEnableClose: true` (default) means "this tabset can be
closed at all"; the close *button* is now `tabSetEnableCloseButton`
(default `false`).

**Recipe:** none, since Altrady doesn't set either. Note for future:
showing a close button on a tabset now requires
`tabSetEnableCloseButton: true`. Keep an eye on this if anyone tries to
add tabset-close UI later.

---

## 11. `tabEnableFloat` alias → `tabEnablePopout`

**Today** — Altrady doesn't set either. Note only.

**Now** — `tabEnablePopout` is the canonical name. `tabEnableFloat` is
read as an alias for backwards compatibility but should not be used in
new code.

---

## 12. CLASSES references — mostly stable, double-check

**Today** — `flex-grid.js`, `flex-grid-wrapper.js` use ~30 entries from
`CLASSES`. All of these still exist in 0.9.0 (see CSSClassNames.ts in the
deps doc).

**Recipe:** none expected — but during increment 4 (visual parity), if
any of these stop matching DOM, the new class might be:
- `FLEXLAYOUT__TABSET_LEADING` (new — left of tabs slot)
- `FLEXLAYOUT__TAB_BUTTON_STRETCH` (new — present when single-tab stretch
  is enabled)
- `FLEXLAYOUT__LAYOUT_MOVEABLES`, `FLEXLAYOUT__LAYOUT_TAB_STAMPS` (new —
  internals for tab-content portalling)

Watch for the existing rules that hide the ghost tabs:
```js
.${CLASSES.FLEXLAYOUT__BORDER_BUTTON}, .${CLASSES.FLEXLAYOUT__TAB_BUTTON} {
  &.${CENTER_GHOST_TAB_CLASSNAME}, &.${BOTTOM_DRAWER_GHOST_TAB_CLASSNAME} {
    width: 0; padding: 0; opacity: 0; pointer-events: none;
  }
}
```
These rely on the custom `className` prop on the tab JSON propagating to
the rendered `flexlayout__tab_button` / `flexlayout__border_button`
element. That propagation still exists in 0.9.0 via the `tabClassName`
attribute path; verify by inspecting the DOM.

**Verify:** ghost tabs are zero-width / invisible in both the trading
terminal center tabset and the bottom drawer.

---

## 13. Tabs no longer re-render on size change

**Today** — Altrady's tab content components (e.g. `charts-grid-item`)
mostly use `withSizeProps` which has its own `ResizeObserver`. So we
already don't depend on FlexLayout-driven re-renders for size.

**Now** — confirmed: tabs only re-render when *visible* and when their
*model attributes* change. Size changes do not trigger a re-render.

**Recipe:** none expected. But during testing, if any widget shows stale
dimensions after a splitter drag, attach a `ResizeObserver` (or check
that `withSizeProps` is in the chain).

---

## 14. Action types — names mostly stable, popout actions renamed

**Today** — Altrady's controllers use:
- `Actions.SELECT_TAB`, `MOVE_NODE`, `MAXIMIZE_TOGGLE`, `ADJUST_SPLIT`,
  `UPDATE_MODEL_ATTRIBUTES`, `SET_ACTIVE_TABSET`, `DELETE_TAB`
- `Actions.addNode`, `deleteTab`, `selectTab`, `maximizeToggle`,
  `updateNodeAttributes`, `updateModelAttributes`

**Now** — all of those still exist. The renamed ones (irrelevant to
Altrady today, but noted for completeness) are the popout actions:
`Actions.popoutTab`, `closePopout`, `movePopoutToFront` (formerly
`*Window*`).

**Recipe:** none. If a future feature uses popouts/floats, use the new
names.

---

## 15. `tabSetEnableTabStrip: false` — still works, with caveats

**Today** — `default-chart-layouts.js:8` sets
`tabSetEnableTabStrip: false` to hide the tabbar entirely on `/charts`.

**Now** — same attribute name, same effect. But verify that hiding the
tabbar doesn't also hide the new `leading` slot if we ever start using
it.

**Verify:** `/charts` page has no tabbar; close button is in
`MarketHeaderBar` (already the case after `c58a0248bb`).

---

## 16. `font` prop — gone

**Today** — Altrady doesn't pass `font`. Note only.

**Now** — use CSS variables `--font-size`, `--font-family` on the
container (or rely on inherited body styles).

---

## Process — running this guide

These recipes are inputs to the increments in the PRD, not a parallel
plan:

- §1, §6 → increment 2 (compile).
- §2, §7 → increment 5 (drag).
- §3 → increment 6 (splitter).
- §4, §5, §12, §15 → increment 4 (visual parity).
- §8 → increment 10 (overflow / glass).
- §9, §10, §11, §14 → increment 8 (persistence) or "no change needed".
- §13, §16 → notes only.

Anything that doesn't fit cleanly: stop and ask, don't improvise.
