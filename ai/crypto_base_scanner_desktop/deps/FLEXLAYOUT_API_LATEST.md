# FlexLayout (flexlayout-react) — Latest (0.9.0)

**Source checkout:** `/home/areg/Downloads/temp/FlexLayout`
**Pinned version:** `0.9.0` (release 2026-04-25)
**Hash:** `ae8ad5d78664f15ccaabcc730a01f28473d7c3a7`
**Upstream:** https://github.com/caplin/FlexLayout
**Status:** active, maintained. This doc describes the upgrade target. The
currently-installed version is `0.7.15` — see `FLEXLAYOUT_API.md` for that.

This is the reference for the **planned upgrade** from `0.7.15` → `0.9.0`.
The 0.8.x line was skipped — its breaking changes (drag-and-drop signatures,
removed `titleFactory`, etc.) ship inside 0.9.0.

## Module shape

ESM-only package (`"type": "module"`), no UMD. Entry:

```js
import { Layout, Model, Actions, DockLocation, CLASSES } from "flexlayout-react"
import "flexlayout-react/style/dark.css"   // or alpha_dark, light, alpha_light, alpha_rounded, rounded, gray, underline, combined
```

Re-exports from `src/index.ts`:

- Components: `Layout`, `TabLayout`
- Types: `LayoutTypes` (incl. `ITabSetRenderValues`, `ITabRenderValues`,
  `IIcons`, `DragRectRenderCallback`, `NodeMouseEvent`,
  `ShowOverflowMenuCallback`, `TabSetPlaceHolderCallback`)
- Icons (`Icons.tsx` exports), `I18nLabel`, `CSSClassNames` (the `CLASSES` enum)
- Model: `Model`, `Node`, `RowNode`, `TabSetNode`, `BorderNode`, `TabNode`,
  `Actions`, `BorderSet`, `DockLocation`, `Orientation`, `DropInfo`, `Rect`,
  `ICloseType`, `IDraggable`, `IDropTarget`, `IJsonModel`

## Layout entry point

```jsx
<Layout
  ref={layoutApiRef}             // typed as ILayoutApi (see below)
  model={model}
  factory={factory}
  onAction={...}
  onModelChange={(model, action) => ...}
  onRenderTab={...}
  onRenderTabSet={...}
  icons={...}
  popoutClassName={...}
  classNameMapper={...}
  i18nMapper={...}
  supportsPopout={...}
  popoutURL={...}
  realtimeResize={...}
  onRenderDragRect={...}
  onContextMenu={...}
  onAuxMouseClick={...}
  onShowOverflowMenu={...}
  onTabSetPlaceHolder={...}
  popoutWindowName={...}
  tabDragSpeed={0.3}
/>
```

Defined in `src/view/Layout.tsx`. Note: `Layout` is now a **function component**
(`React.forwardRef`). Refs are of type `ILayoutApi`, not the old class instance.

### `ILayoutApi` (the public ref handle)

```ts
interface ILayoutApi {
  redraw(): void
  addTabToTabSet(tabsetId: string, json: IJsonTabNode): TabNode | undefined
  addTabToActiveTabSet(json: IJsonTabNode): TabNode | undefined
  addTabWithDragAndDrop(
    event: DragEvent,                                 // **HTML5 drag start event**
    json: IJsonTabNode,
    onDrop?: (node?: Node, event?: React.DragEvent) => void
  ): void
  moveTabWithDragAndDrop(
    event: DragEvent,                                 // **HTML5 drag start event**
    node: TabNode | TabSetNode
  ): void
  setDragComponent(event: DragEvent, component: ReactNode, x: number, y: number): void
  getRootDiv(): HTMLDivElement | null | undefined
}
```

**Critical signature change vs 0.7.15:**

- Both `addTabWithDragAndDrop` and `moveTabWithDragAndDrop` now take a real
  `DragEvent` and **must be called from inside an HTML5 drag-start handler**
  (`onDragStart`). They no longer initiate drag programmatically from a
  mouse/touch handler.
- `addTabWithDragAndDropIndirect` is **removed**.
- `setDragComponent(event, component, x, y)` is the new way to customise the
  drag image — call it before the DnD start methods inside the same handler.

Implication for Altrady's `/charts` MarketHeaderBar drag handle: the current
implementation that calls `layout.moveTabWithDragAndDrop(node, dragText)` from
`onMouseDown`/`onTouchStart` will no longer work. The header element must
become `draggable` (HTML5) and the call must move to `onDragStart`.

## Model

`Model.fromJson(json)` / `model.toJson()` are unchanged.

### Methods used (still present in 0.9.0)

- `model.doAction(action)` — dispatch an action
- `model.setOnAllowDrop(fn)` — `(dragNode, dropInfo) => boolean`
- `model.getRoot()`, `model.getNodeById(id)`, `model.getActiveTabset()`,
  `model.getMaximizedTabset()`, `model.visitNodes(cb)`, `model.toString()`
- `model.getSplitterSize()` / `model.setSplitterSize(n)` — still exist, but the
  source of truth is now the **CSS variable** (see "Removed globals" below).
  The model reads the resolved value from CSS at runtime and stores it.

### Global attributes (still present)

`enableEdgeDock`, `enableEdgeDockIndicators`, `rootOrientationVertical`,
`enableRotateBorderIcons`, `tabEnableClose`, `tabCloseType`, `tabEnablePopout`
(alias of removed `tabEnableFloat`), `tabEnablePopoutIcon`,
`tabEnablePopoutFloatIcon`, `tabEnablePopoutOverlay`, `tabEnableDrag`,
`tabEnableRename`, `tabContentClassName`, `tabClassName`, `tabIcon`,
`tabEnableRenderOnDemand`, `tabBorderWidth`, `tabBorderHeight`,
`tabSetEnableDeleteWhenEmpty`, `tabSetEnableDrop`, `tabSetEnableDrag`,
`tabSetEnableDivide`, `tabSetEnableMaximize`, `tabSetEnableClose` (semantics
**changed** — see below), `tabSetEnableCloseButton` (new), `tabSetEnableSingleTabStretch`,
`tabSetAutoSelectTab`, `tabSetEnableActiveIcon`, `tabSetClassNameTabStrip`,
`tabSetEnableTabStrip`, `tabSetEnableTabWrap`, `tabSetTabLocation`,
`tabMinWidth/Height`, `tabSetMinWidth/Height`, `tabMaxWidth/Height`,
`tabSetMaxWidth/Height`, `tabSetEnableTabScrollbar`, `borderSize`, `borderMinSize`,
`borderMaxSize`, `borderEnableDrop`, `borderAutoSelectTab*`, `borderClassName`,
`borderEnableAutoHide`, `borderEnableTabScrollbar`.

### Removed / changed globals (vs 0.7.15)

| Old (0.7.15)                                       | 0.9.0                                                                            |
| -------------------------------------------------- | -------------------------------------------------------------------------------- |
| `splitterSize` global attr                         | **Removed.** Use CSS var `--splitter-size`                                       |
| `splitterExtra` global attr                        | **Removed.** Use CSS var `--splitter-active-size`                                |
| `splitterEnableHandle` global attr                 | **Removed.** Use CSS var `--splitter-handle-visibility`                          |
| `tabDragSpeed` global attr                         | **Removed.** Use `tabDragSpeed` prop on `<Layout/>`                              |
| `font` prop on Layout                              | **Removed.** Use CSS vars `--font-size`, `--font-family`                         |
| `titleFactory` prop                                | **Removed.** Use `onRenderTab` (mutate `renderValues.content`)                   |
| `iconFactory` prop                                 | **Removed.** Use `onRenderTab` (mutate `renderValues.leading`)                   |
| `onTabDrag` prop (custom internal drag)            | **Removed.** Native HTML5 DnD only.                                              |
| `tabSetTabStripHeight` global                      | **Removed.** Tab strip is flexbox; size via CSS / `--font-size`.                 |
| Various `for insets`, `tabset header`, row size attrs | **Removed.**                                                                  |
| `tabSetEnableClose`                                | **Semantics changed.** Now means "tabset can be closed at all". The button is now `tabSetEnableCloseButton` (default `false`). |
| `popouts` JSON key                                 | **Renamed** to `subLayouts`. Old `popouts` still loads but is rewritten on save with a `type: "window"` entry. |

### Action types

`Actions.addNode`, `Actions.deleteTab`, `Actions.selectTab`,
`Actions.setActiveTabset`, `Actions.maximizeToggle`, `Actions.adjustSplit`
(also `ADJUST_BORDER_SPLIT`, `ADJUST_WEIGHTS`), `Actions.moveNode`,
`Actions.updateNodeAttributes`, `Actions.updateModelAttributes`,
`Actions.renameTab`. Plus new popout actions:

- `Actions.popoutTab` / `Actions.closePopout` / `Actions.movePopoutToFront`
  (renamed from the older `*Window*` actions in 0.7.15).

### Drag-allow gate

`model.setOnAllowDrop((dragNode, dropInfo) => boolean)` — unchanged shape.
Used by Altrady's `LayoutsController.allowDrop`.

## `<Layout>` props worth knowing about (new since 0.7.15)

- `onRenderTab(node, renderValues)` — replaces `titleFactory` and
  `iconFactory`. `renderValues` has `leading` (icon area), `content` (label /
  text), `buttons` (per-tab button slots).
- `onRenderTabSet(node, renderValues)` — `renderValues` has `leading` (left of
  tabs, **new in 0.8.15**), `stickyButtons` (after tabs), `buttons` (end of
  tabset), `overflowPosition` (where the overflow `…` button sits among the
  buttons; new in 0.7.11).
- `onContextMenu(node, mouseEvent)` — built-in context-menu hook for tabs and
  tabsets.
- `onAuxMouseClick(node, mouseEvent)` — alt/meta/shift/middle-click handler.
- `onShowOverflowMenu(node, mouseEvent, items, onSelect)` — fully customise
  the overflow popup, e.g. to render it from your own design system.
- `onTabSetPlaceHolder(tabSetNode)` — render content when a tabset is empty.
- `onExternalDrag(event)` — accept drops from outside the layout.
- `onRenderDragRect(content, node?, json?)` — customise the floating drag
  rectangle.
- `icons` — `IIcons`: `close`, `closeTabset`, `popout`, `popoutFloat`,
  `maximize`, `restore`, `more`, `edgeArrow`, `activeTabset`,
  `closeFloatPopout`. Each entry can be a `ReactNode` or a function returning
  one (so it can read the node).
- `realtimeResize` — resize tabs continuously while a splitter drags.
- `tabDragSpeed` — transition time of the drag rectangle (formerly a global
  attr).

## Theming

CSS files in `style/`: `light`, `dark`, `alpha_light`, `alpha_dark`,
`alpha_rounded`, `gray`, `rounded`, `underline`, plus `combined.css` (all
themes; switch by adding `flexlayout__theme_<name>` class to the container).

Theming variables of interest:

- `--splitter-size`, `--splitter-active-size`, `--splitter-handle-visibility`
- `--font-size`, `--font-family`
- `--color-icon` (used by Altrady to recolour icons)
- See `style/_themes.scss` and `style/_base.scss` for the full set.

## Tab events (TabNode listeners)

```js
const id = node.setEventListener("save", () => { node.getConfig().subject = subject })
node.removeEventListener(id)
```

Events: `resize` (`{rect}`), `close`, `visibility` (`{visible}`), `save`.

**Important behaviour change:** in 0.9.0 tabs no longer re-render when their
size changes. To respond to size changes, attach a `ResizeObserver` to the
tab content element rather than relying on a parent re-render.

## Popouts / floating panels (new in 0.9.0)

Two flavours:

- **Popout window** (separate browser window, was already supported) — needs
  `popout.html` co-located with the host page. Uses React Portals; main JS
  context still owns the tree.
- **Floating panel** (new) — `type: "float"` entry in `subLayouts`. Stays
  inside the main window but renders as a draggable, resizable floating
  window. Doesn't need `popout.html` and isn't subject to the popout
  limitations (resize observers, third-party `document` listeners, browser
  zoom, etc.).

`enablePopout`, `enablePopoutIcon`, `enablePopoutFloatIcon` control the icons
that switch a tab between docked / window / float states.

## Sub-layouts (new in 0.9.0)

A tab can host a *sub-layout* (a layout inside a layout), with drag-and-drop
between main and sub-layout. See `TabLayout` export and the demo's
"Sub-layouts" sample.

## CSS class tokens

The full enum is at `src/view/CSSClassNames.ts`. Stable names (still match
0.7.15 in shape, modulo a few added/renamed classes):

- Containers: `FLEXLAYOUT__LAYOUT`, `FLEXLAYOUT__LAYOUT_MAIN`,
  `FLEXLAYOUT__LAYOUT_OVERLAY`, `FLEXLAYOUT__LAYOUT_BORDER_CONTAINER`,
  `FLEXLAYOUT__LAYOUT_TAB_STAMPS`, `FLEXLAYOUT__LAYOUT_MOVEABLES` (new)
- Borders: `FLEXLAYOUT__BORDER`, `FLEXLAYOUT__BORDER_*`,
  `FLEXLAYOUT__BORDER_INNER*`, `FLEXLAYOUT__BORDER_BUTTON*`,
  `FLEXLAYOUT__BORDER_TAB_DIVIDER`, `FLEXLAYOUT__BORDER_TOOLBAR*`
- Splitter: `FLEXLAYOUT__SPLITTER`, `FLEXLAYOUT__SPLITTER_BORDER`,
  `FLEXLAYOUT__SPLITTER_DRAG`, `FLEXLAYOUT__SPLITTER_HANDLE*`,
  `FLEXLAYOUT__SPLITTER_EXTRA`
- Tabset: `FLEXLAYOUT__TABSET`, `FLEXLAYOUT__TABSET_CONTAINER`,
  `FLEXLAYOUT__TABSET_MAXIMIZED`, `FLEXLAYOUT__TABSET_SELECTED`,
  `FLEXLAYOUT__TABSET_TABBAR_INNER*`, `FLEXLAYOUT__TABSET_TABBAR_OUTER*`,
  `FLEXLAYOUT__TABSET_TAB_DIVIDER*`, `FLEXLAYOUT__TABSET_LEADING` (new),
  `FLEXLAYOUT__TABSET_CONTENT`
- Tab buttons: `FLEXLAYOUT__TAB_BUTTON`, `FLEXLAYOUT__TAB_BUTTON_CONTENT`,
  `FLEXLAYOUT__TAB_BUTTON_LEADING`, `FLEXLAYOUT__TAB_BUTTON_TRAILING`,
  `FLEXLAYOUT__TAB_BUTTON_OVERFLOW`, `FLEXLAYOUT__TAB_BUTTON_OVERFLOW_COUNT`,
  `FLEXLAYOUT__TAB_BUTTON_TEXTBOX`, `FLEXLAYOUT__TAB_BUTTON_STAMP`,
  `FLEXLAYOUT__TAB_BUTTON_STRETCH` (new — appears on the single-stretched tab)
- Tab toolbar: `FLEXLAYOUT__TAB_TOOLBAR`, `FLEXLAYOUT__TAB_TOOLBAR_BUTTON*`,
  `FLEXLAYOUT__TAB_TOOLBAR_STICKY_BUTTONS_CONTAINER`,
  `FLEXLAYOUT__TAB_TOOLBAR_BUTTON_CLOSE`, `FLEXLAYOUT__TAB_TOOLBAR_ICON`
- Popup menu: `FLEXLAYOUT__POPUP_MENU`, `FLEXLAYOUT__POPUP_MENU_CONTAINER`,
  `FLEXLAYOUT__POPUP_MENU_ITEM`, `FLEXLAYOUT__POPUP_MENU_ITEM__SELECTED`
- Misc (new): `FLEXLAYOUT__FLOAT_WINDOW*`, `FLEXLAYOUT__FLOATING_WINDOW_CONTENT`,
  `FLEXLAYOUT__MINI_SCROLLBAR*`, `FLEXLAYOUT__ERROR_BOUNDARY_*`,
  `FLEXLAYOUT__DRAG_RECT`, `FLEXLAYOUT__EDGE_RECT*`, `FLEXLAYOUT__OUTLINE_RECT*`

The `_glass` overlay class change in 0.7.x (the unstyled `z-index: 998` div
the Altrady SCSS hacks around) — drag rendering moved to the layout overlay
and edge-rect classes; the glass-overlay workaround in `flex-layout.scss`
should be reviewed during the upgrade.

## Notable behaviour changes worth designing around

1. **Native HTML5 drag-and-drop end-to-end.** Any code that simulates
   programmatic drag from non-HTML5 events (mousedown/touchstart) needs to
   move to a real `dragstart` flow.
2. **Tabs stay mounted on size change.** If something in Altrady relied on a
   re-render on size change, it now needs a `ResizeObserver`.
3. **Tabs only re-render when visible** (0.8.15 change). State updates while a
   tab is hidden land on next visibility — usually fine, but timer / animation
   code in hidden tabs can behave differently.
4. **CSS-driven splitter / font sizing.** Anything that updates these from JS
   via `Actions.updateModelAttributes` will silently no-op; switch to CSS
   variables (set on the layout container).
5. **Popout/Float JSON key rename** (`popouts` → `subLayouts`). 0.9.0 reads
   both, but writes only `subLayouts`. Persisted layouts will migrate on first
   save.
6. **`ILayoutApi` ref typing** (TypeScript projects only — Altrady is mostly
   JS so this is mainly a documentation note).
7. **No UMD build** — only ESM. Webpack and bundlers handle this fine, but
   anything pulling FlexLayout from a `<script>` tag will need a different
   path. Altrady imports through webpack so this is non-blocking.

## Scope outside this doc

This is a deps reference, not a migration plan. The actual upgrade plan and
its feedback loop live in
`~/ai/crypto_base_scanner_desktop/flexlayout-depup/`.
