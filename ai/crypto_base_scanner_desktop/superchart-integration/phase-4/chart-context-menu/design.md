# Chart Background Context Menu — Design

## Architecture

### Data flow

1. **Superchart** fires `onRightSelect(result)` on a right-click anywhere on the chart
   — overlay right-clicks are dispatched natively to overlay `onRightClick` handlers
   first and do not propagate here.
2. **`ContextMenuController`** receives the event via a direct `sc.onRightSelect`
   subscription. It checks `chartController.interaction.active` — if a one-shot
   `InteractionController` consumer is currently running (e.g. replay start-time picker),
   the chart-background menu is suppressed and the event falls through to the picker.
3. Otherwise the controller computes `pageX`/`pageY` from `result.coordinate.x`/`y` plus
   the container's bounding rect, and calls `openChartContextMenu({x, y})`.
4. **React component `ChartContextMenu`** subscribes via
   `setChartContextMenuCallback(fn)` and renders a `ContextMenuPopup` at `{x, y}` with
   an empty `<Popup/>` body.

### Why a direct `sc.onRightSelect` subscription and not `InteractionController`

`InteractionController` is a **single-consumer multiplexer** — `start()` supersedes any
existing consumer. A persistent chart-background context menu consumer would be kicked
out every time a one-shot consumer (replay picker, future drawing tools) starts, and
would have to re-register itself on completion. That is fragile.

SC's `onRightSelect` is a pub/sub — `sc.onRightSelect(fn)` returns an unsub and does
not replace existing subscribers. The chart-background context menu therefore
subscribes **directly** to `sc.onRightSelect` alongside `InteractionController`, and
gates on `chartController.interaction.active` so that while a one-shot consumer is
running, right-click is routed to the consumer (e.g. cancel the replay picker) and does
**not** open the menu. This matches the user's requirement that the menu use "the same
SC api as `interaction-controller.js` is using — the `onRightSelect` callback" without
building the menu on top of the multiplexer.

### Why extend `ContextMenuController` rather than a new controller

The existing controller at `controllers/context-menu-controller.js` is named
`ContextMenuController`, not `OverlayContextMenuController` — it is the single owner of
context-menu state on the chart. Adding chart-background menu state and handlers to
the same controller keeps all context-menu concerns in one file and mirrors the
existing `openOverlayContextMenu` / `closeOverlayContextMenu` / `setOverlayContextMenuCallback`
naming.

### Coordinate bridging

SC's `PriceTimeResult` currently exposes `coordinate.x` / `coordinate.y` (canvas-
relative, not page-relative). `ContextMenuPopup` requires page-relative `x`/`y`. The
controller computes them locally:

```js
const rect = this.c.getContainer()?.getBoundingClientRect()
const x = rect.left + result.coordinate.x
const y = rect.top  + result.coordinate.y
```

This is the same bridging `InteractionController._enrichResult` already performs for
its consumers. The chart-context-menu handler does not go through
`InteractionController`, so it reimplements the bridge inline.

**A comment at the bridging site must call out that once Superchart adds native
`pageX`/`pageY` to `PriceTimeResult`, this local bridging is redundant and should be
replaced with `result.pageX` / `result.pageY` directly.** The same comment should also
point at `InteractionController._enrichResult`, which will become redundant at the
same time.

### State shape

On `ContextMenuController`:

```js
this._chartContextMenuState = null // { x, y } or null
this._onChartContextMenuChange = null // React subscriber callback
```

The state object is intentionally minimal — `{x, y}` only. Future PRDs that add menu
entries will extend the shape with whatever context they need (e.g. `time` for
"Start replay here"). This PRD does not speculatively add fields.

### Subscription lifecycle

`ContextMenuController` gains `mount()` and `dispose()` for the `sc.onRightSelect`
subscription.

- `mount(superchart)` — called at the end of `ChartController` constructor, subscribes:
  `this._unsubRight = superchart.onRightSelect(this._onChartRightSelect)`.
- `dispose()` — called from `ChartController.dispose()`, calls `this._unsubRight?.()`.

(Alternative: subscribe in the constructor. Deferred to `mount()` so the constructor
stays consistent with the other sub-controllers, which receive the already-constructed
`chartController` reference.)

### `_onChartRightSelect` handler

```js
_onChartRightSelect = (result) => {
  if (this.c.interaction?.active) return
  const rect = this.c.getContainer()?.getBoundingClientRect()
  if (!rect) return
  // TODO: Superchart's PriceTimeResult currently only has coordinate.x/coordinate.y
  //       (canvas-relative). When SC adds native pageX/pageY to the result, drop this
  //       bridging and use result.pageX / result.pageY directly. InteractionController
  //       ._enrichResult does the same bridging and should be removed at the same time.
  const x = rect.left + result.coordinate.x
  const y = rect.top  + result.coordinate.y
  this.openChartContextMenu({x, y})
}
```

### Symbol / resolution / unmount cleanup

- `ChartController.syncSymbolToChart` already stops the interaction controller and
  clears overlays. Add `this.contextMenu?.closeChartContextMenu()` so a lingering
  popup from the previous symbol is dismissed when the user switches markets.
- `ChartController.dispose` calls `this.contextMenu?.dispose()` which in turn unsubs
  from `onRightSelect`. The React component's `useEffect` cleanup clears the
  subscriber callback on unmount.
- Resolution change does not need a dedicated close — the popup is a page-level DOM
  popup unaffected by chart period changes. Symbol change is the only sync point where
  the popup's click coordinates could become stale.

### Component structure

```
SuperChartOverlays (in super-chart.js)
  ├── ... overlay components
  ├── OverlayContextMenu
  └── ChartContextMenu          ← new
        └── ContextMenuPopup (from context-menu.js)
              └── Popup (empty — no PopupItems)
```

`ChartContextMenu` mirrors `OverlayContextMenu`:

```js
const ChartContextMenu = () => {
  const {chartController} = useSuperChart()
  const [menuState, setMenuState] = useState(null)

  useEffect(() => {
    if (!chartController) return
    chartController.contextMenu.setChartContextMenuCallback(setMenuState)
    return () => chartController.contextMenu.setChartContextMenuCallback(null)
  }, [chartController])

  const close = useCallback(() => {
    chartController?.contextMenu.closeChartContextMenu()
  }, [chartController])

  if (!menuState) return null

  return (
    <ContextMenuPopup x={menuState.x} y={menuState.y} onClose={close} spanMobile={false}>
      <Popup>
        {/* Intentionally empty — follow-up PRDs will add PopupItems here. */}
      </Popup>
    </ContextMenuPopup>
  )
}
```

No i18n keys are needed in this PRD (no visible text in the empty popup).

### Interaction with the overlay context menu

The two menus share `ContextMenuPopup` but not state — opening one does not close the
other at the controller level. In practice they cannot be visible simultaneously
because:
- Opening the overlay menu requires right-clicking an overlay, which does **not** reach
  `sc.onRightSelect` (klinecharts short-circuits on overlay `onRightClick`).
- Opening the chart menu requires right-clicking empty space, which does not reach any
  overlay handler.

So only one of the two is ever open at a time, and each closes via its own backdrop
dismiss independently.

## File changes

### New files

1. **`super-chart/chart-context-menu.js`** — React component. Mirrors
   `overlays/overlay-context-menu.js` structure. Renders `ContextMenuPopup` with an
   empty `<Popup/>`.

### Modified files

2. **`controllers/context-menu-controller.js`**
   - New state: `_chartContextMenuState`, `_onChartContextMenuChange`, `_unsubRight`.
   - New methods: `mount(superchart)`, `dispose()`, `setChartContextMenuCallback(fn)`,
     `openChartContextMenu(state)`, `closeChartContextMenu()`, `_onChartRightSelect`.

3. **`chart-controller.js`**
   - After `this.contextMenu = new ContextMenuController(this)` (or at end of
     constructor): `this.contextMenu.mount(superchart)`.
   - In `syncSymbolToChart`: `this.contextMenu?.closeChartContextMenu()` alongside the
     existing `interaction?.stop("symbol-change")`.
   - In `dispose`: `this.contextMenu?.dispose()` alongside `this.interaction?.dispose()`.

4. **`super-chart.js`**
   - Import `ChartContextMenu` and mount it inside `SuperChartOverlays` alongside
     `<OverlayContextMenu/>`.

5. **Md files — unblocking references.** All five files listed in the PRD
   "Unblocking follow-ups" section must be edited so the blocker is marked as resolved
   by `[sc-chart-ctx-menu]` while keeping the concrete "Start replay here" / "Jump back
   to here" menu entries themselves as still-pending follow-ups:
   - `ai/superchart-integration/phase-5/deferred.md`
   - `ai/superchart-integration/phase-5/stepback/prd.md`
   - `ai/superchart-integration/phase-5/stepback/tasks.md`
   - `ai/superchart-integration/phase-5/dialogs/prd.md`
   - `ai/superchart-integration/phase-5/replay/prd.md`

## Open questions

- None for this PRD. The empty menu body sidesteps all the per-entry design questions
  (visibility rules, disabled states, i18n) that follow-up PRDs will own.
