# Chart Background Context Menu — Tasks

## Task 1: Extend `ContextMenuController` with chart-background state and handler
**File:** `src/containers/trade/trading-terminal/widgets/super-chart/controllers/context-menu-controller.js`

- Add fields in constructor:
  ```js
  this._chartContextMenuState = null
  this._onChartContextMenuChange = null
  this._unsubRight = null
  ```
- Add `mount(superchart)` — subscribes `_onChartRightSelect` via
  `superchart.onRightSelect(...)`, stores the unsub in `this._unsubRight`.
- Add `dispose()` — calls `this._unsubRight?.()` and nulls it.
- Add `setChartContextMenuCallback(fn)`, `openChartContextMenu(state)`,
  `closeChartContextMenu()` — mirror the existing overlay equivalents.
- Add `_onChartRightSelect = (result) => { ... }`:
  - Return early if `this.c.interaction?.active` (defer to active one-shot consumers).
  - Compute page coords from `this.c.getContainer().getBoundingClientRect()` +
    `result.coordinate.x/y`.
  - Call `openChartContextMenu({x, y})`.
  - Include the `// TODO: Superchart pageX/pageY` comment from the design doc so the
    local canvas→page bridge is easy to find and remove later. Reference
    `InteractionController._enrichResult` in the comment.

**Verification:** `context-menu-controller.js` has the new methods and `_onChartRightSelect`
handler with the TODO comment in place. No behavior change yet (nothing is subscribed).

## Task 2: Wire mount / close / dispose into `ChartController`
**File:** `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`

- After sub-controllers are constructed, call `this.contextMenu.mount(superchart)`.
  (Simplest: add it at the bottom of the constructor, after
  `this.interaction = new InteractionController(this)`.)
- In `syncSymbolToChart`, alongside the existing
  `this.interaction?.stop("symbol-change")`, add
  `this.contextMenu?.closeChartContextMenu()`.
- In `dispose`, alongside `this.interaction?.dispose()`, add
  `this.contextMenu?.dispose()`.

**Verification:** Right-clicking on empty chart background fires `_onChartRightSelect`
(temporary `console.log` during dev is fine to confirm). Symbol change closes any
open menu. Unmounting the chart unsubs cleanly (no errors in console on tab close).

## Task 3: `ChartContextMenu` React component
**File (new):** `src/containers/trade/trading-terminal/widgets/super-chart/chart-context-menu.js`

- Mirror `overlays/overlay-context-menu.js` minimal shape:
  - `useSuperChart()` to get `chartController`.
  - `useState` for `menuState`.
  - `useEffect` subscribes via `chartController.contextMenu.setChartContextMenuCallback(setMenuState)`
    and clears on cleanup.
  - `useCallback` `close` → `chartController.contextMenu.closeChartContextMenu()`.
  - Render `<ContextMenuPopup x={menuState.x} y={menuState.y} onClose={close} spanMobile={false}>`
    with an empty `<Popup>` child.
  - Add a one-line JSX comment inside the `<Popup>` noting that follow-up PRDs add
    `<PopupItem>`s here.
- Import `Popup` from `~/components/design-system/v2/popups` and `ContextMenuPopup`
  from `~/components/elements/context-menu`.

**Verification:** Component file exists, imports resolve, renders nothing when
`menuState` is null.

## Task 4: Mount `ChartContextMenu` in `super-chart.js`
**File:** `src/containers/trade/trading-terminal/widgets/super-chart/super-chart.js`

- Import `ChartContextMenu` from `./chart-context-menu`.
- Inside `SuperChartOverlays`, add `<ChartContextMenu/>` alongside `<OverlayContextMenu/>`.

**Verification:** Right-click on empty chart background opens the empty
`ContextMenuPopup` at the click position. The popup has a visible frame (so it can be
seen during testing) with no `PopupItem`s inside. Backdrop mousedown, scroll, and
Escape all dismiss it. Right-click on an overlay still opens the **overlay** context
menu (unchanged). Right-click during an active replay start-time pick still cancels
the picker and does **not** open the chart menu.

## Task 5: Update blocked-on-chart-context-menu md references
**Files:**
- `ai/superchart-integration/phase-5/deferred.md`
- `ai/superchart-integration/phase-5/stepback/prd.md`
- `ai/superchart-integration/phase-5/stepback/tasks.md`
- `ai/superchart-integration/phase-5/dialogs/prd.md`
- `ai/superchart-integration/phase-5/replay/prd.md`

In each file, edit the lines listed in the PRD's "Unblocking follow-ups" section so
they:
1. Mark the **chart context menu itself** as no longer blocking (resolved by
   `[sc-chart-ctx-menu]`).
2. Keep the **concrete menu entries** ("Start replay here", "Jump back to here") as
   still-pending follow-up work, since this PRD only lands the empty shell.

Exact edits:

- **`phase-5/deferred.md`**
  - Lines 93–94: reword "Only the 'Start replay here' context-menu entry is still
    deferred — blocked on the chart context menu itself (see 'Context menu entry'
    below)." → drop the "blocked on the chart context menu itself" wording; the entry
    is now simply a pending follow-up PRD since the chart context menu has landed.
  - Line 142: reword "The `InteractionController` also unblocks the 'Context menu
    entry' bullet below" → note that with `[sc-chart-ctx-menu]` the chart context menu
    now exists and the "Start replay here" entry is ready to be implemented as its own
    follow-up.
  - Line 146: reword the "Context menu entry" bullet — drop "Depends on SC context
    menu implementation", replace with a note that the chart context menu plumbing
    exists and the entry just needs to be added to it.

- **`phase-5/stepback/prd.md`** line 164: reword "No 'jump to here' chart context-menu
  entry (blocked on chart context menu)." → "No 'jump to here' chart context-menu
  entry in this PRD — the chart context menu landed in `[sc-chart-ctx-menu]`, the
  entry itself is a follow-up."

- **`phase-5/stepback/tasks.md`** line 144: reword "Context-menu 'Jump back to here'
  entry point → deferred until chart context menu lands." → "Context-menu 'Jump back
  to here' entry point → follow-up. Chart context menu plumbing landed in
  `[sc-chart-ctx-menu]`; adding the entry is a separate task."

- **`phase-5/dialogs/prd.md`**
  - Lines 13–14 (status note): reword "The 'Start replay here' context menu entry is
    deferred until the chart context menu itself lands." → "The 'Start replay here'
    context menu entry is a follow-up. The chart context menu itself landed in
    `[sc-chart-ctx-menu]`; the menu entry is pending its own PRD."
  - Line 130 (table row): change the status from "⏳ Deferred — no chart context menu
    yet" to "⏳ Follow-up — chart context menu exists (`[sc-chart-ctx-menu]`), entry
    pending."

- **`phase-5/replay/prd.md`** line 31: the bullet "Chart context menu 'Start replay
  here'" is in an out-of-scope list. Add a parenthetical note that the chart context
  menu itself now exists (`[sc-chart-ctx-menu]`); the entry itself remains out of
  scope for that PRD.

**Verification:** Grepping for "blocked on chart context menu" / "deferred until chart
context menu" / "no chart context menu yet" returns no matches in `ai/` after the
edits. The five files still clearly distinguish between "chart context menu exists"
(done) and "menu entries" (still pending).

## Out-of-task items (follow-ups, NOT in this PRD)

- "Start replay here" menu entry — follow-up PRD owned by replay.
- "Jump back to here" menu entry — follow-up PRD owned by step-back.
- Drawing-tool entries, "Insert object", etc. — future drawing/tools work.
- Superchart library change to add native `pageX`/`pageY` to `PriceTimeResult` — tracked
  by the TODO comment in `_onChartRightSelect`. When done, drop the local bridging here
  **and** in `InteractionController._enrichResult`.
- Mobile long-press gesture for the chart background context menu.
- Hotkey to open the chart context menu (keyboard alternative to right-click).
