---
id: sc-chart-ctx-menu
---

# Chart Background Context Menu (Phase 4a-1) — ✅ Done

Right-click context menu for the empty chart background in the SuperChart TT main chart.

This PRD lands the plumbing only. The menu body is intentionally empty in this phase —
future PRDs (replay "Start replay here", step-back "Jump back to here", drawing tools,
etc.) will add concrete entries once this foundation is in place.

**Status:** Plumbing landed in commit `2bff0cc78` `[sc-chart-ctx-menu]`. The
empty-body right-click popup is wired via `InteractionController` in persistent
mode and reuses `ContextMenuPopup`. All previously deferred-on-this-PRD references
in phase-5 docs are resolved — the "Unblocking follow-ups" list below is retained
for audit. Concrete menu entries are delivered in the follow-up
`[sc-chart-ctx-menu-options]`.

## Scope

- **In scope:** Right-clicking on empty chart background in the TT main chart opens a
  positioned, dismissible context menu popup. The popup renders with no menu items (empty
  body) — this PRD delivers the wiring, not the menu contents.
- **Out of scope:**
  - Any concrete menu entries (replay, step-back, drawings, etc.) — each will have its
    own follow-up PRD that adds items to this menu.
  - Right-click on overlays — already handled by the overlay context menu
    (phase 4a-2, `sc-overlay-ctx-menu`).
  - Grid bot / backtest charts.
  - Mobile long-press gesture for the chart background (desktop right-click only for now).

## Behavior

### Opening the menu

The chart-background context menu is opened via Superchart's `onRightSelect` callback,
consumed through the existing `InteractionController`. The controller is started in
**persistent mode** (`once: false`) so each right-click on the chart background reopens
the menu — it does not auto-stop after one fire.

```
interactionController.start({
  id: "chart-context-menu",
  once: false,
  onRightSelect: (result) => openChartContextMenu(result),
  onCancel: () => closeChartContextMenu(),
})
```

This follows the exact pattern price-time-select uses, except `once: false`.

### Overlay precedence

Klinecharts delivers overlay right-clicks natively to the overlay's `onRightClick`
handler before the `onRightSelect` callback fires. This means right-clicking on an
overlay opens the **overlay context menu** (phase 4a-2), not the chart-background menu.
To open the chart-background menu the user must right-click on a part of the chart with
no overlay underneath. This is acceptable and requires no extra handling.

### Positioning

The `onRightSelect` callback delivers a result that includes `coordinate.x` and
`coordinate.y` (canvas-relative). The context menu popup is positioned using these
values via the same `ContextMenuPopup` component used by the overlay context menu.

> **TODO (SC library):** Superchart's `PriceTimeResult` currently exposes only
> `coordinate.x` / `coordinate.y` (canvas-relative). Once Superchart adds native
> `pageX` / `pageY` to the result, switch the popup positioning to use those and drop
> the local canvas → page bridging. A code comment at the point where coordinates are
> consumed must call this out explicitly so it is easy to find later.

(Note: `InteractionController._enrichResult` already bridges canvas → page coords today
using the container's bounding rect. The chart-context-menu consumer uses that enriched
result. The comment above still applies to the enrichment itself — once SC provides
native `pageX`/`pageY`, the enrichment becomes redundant and should be removed.)

### Menu body

For this PRD the popup body is **empty**. It renders a visible, dismissible
`ContextMenuPopup` with no `PopupItem` children so future PRDs have a clear place to
hook into. The popup still renders its frame so it is visible during manual testing
and so dismissal behavior (see below) can be verified end-to-end.

Follow-up PRDs will add concrete entries (replay start, step-back jump, drawing tools,
etc.) and are responsible for their own i18n keys, icons, and action wiring.

### Dismissal

The popup is dismissed by any of:
- Mouse down outside the popup (backdrop dismiss, handled by `ContextMenuPopup`).
- Scroll (handled by `ContextMenuPopup`).
- Escape key.
- Another right-click on the chart background (opens a new popup at the new position;
  the previous instance closes first).
- Chart unmount / symbol change / resolution change (cleanup).

`InteractionController`'s existing global listeners handle Escape. Because the consumer
runs with `once: false`, the controller's outside-click listener is **not** installed
(see `_installGlobalListeners`), so the popup itself is responsible for backdrop
dismissal — which is already what `ContextMenuPopup` does.

## Pattern reuse

The chart-background context menu mirrors the overlay context menu architecture
(phase 4a-2) as closely as possible:

- **State shape on `ChartController.contextMenu`:** a single object
  `{x, y}` (plus any future fields added by follow-up PRDs), mirroring the overlay
  menu's `{overlayId, overlayName, group, key, points, x, y}`.
- **Subscription API:** `setChartContextMenuCallback(fn)` / `openChartContextMenu(state)` /
  `closeChartContextMenu()`, mirroring `setOverlayContextMenuCallback` etc.
- **React component:** a new `ChartContextMenu` component under `super-chart/` that
  subscribes via `useSuperChart().chartController` + `useEffect`, stores state with
  `useState`, and renders `<ContextMenuPopup x={state.x} y={state.y} onClose={close}/>`
  with an empty `<Popup/>` child.
- **Mount point:** mounted alongside `OverlayContextMenu` in `super-chart.js`.

Reuse the existing `ContextMenuPopup` from `src/components/elements/context-menu.js` —
do not re-implement positioning, off-screen detection, portal rendering, or scroll
dismissal.

## Lifecycle / cleanup

- The `InteractionController` consumer is started when the chart is ready and stopped
  (via `interactionController.stop()`) on chart unmount, symbol change, and resolution
  change — same lifecycle hooks that reset other chart state.
- Closing the popup does **not** stop the consumer. The consumer stays armed so the
  next right-click reopens the menu.
- On unmount, the popup is closed and the controller stops. Follow the standard
  `useSymbolChangeCleanup` pattern used elsewhere in SC controllers.

## Unblocking follow-ups

Landing this PRD unblocks the following items currently marked as deferred-on-chart-
context-menu. All references must be updated as part of the implementation of this PRD
to mark the blocker resolved and link to `[sc-chart-ctx-menu]`:

1. **`ai/superchart-integration/phase-5/deferred.md`**
   - Lines 93–94: "Only the 'Start replay here' context-menu entry is still deferred —
     blocked on the chart context menu itself"
   - Line 142: "The `InteractionController` also unblocks the 'Context menu entry' bullet"
   - Line 146: "**Context menu entry** — 'Start replay here' in chart background context
     menu. Depends on SC context menu implementation."
2. **`ai/superchart-integration/phase-5/stepback/prd.md`**
   - Line 164: "No 'jump to here' chart context-menu entry (blocked on chart context menu)."
3. **`ai/superchart-integration/phase-5/stepback/tasks.md`**
   - Line 144: "Context-menu 'Jump back to here' entry point → deferred until chart
     context menu lands."
4. **`ai/superchart-integration/phase-5/dialogs/prd.md`**
   - Lines 13–14: "The 'Start replay here' context menu entry is deferred until the
     chart context menu itself lands."
   - Line 130: table row "Context menu 'Start replay here' (right-click on chart) —
     Deferred — no chart context menu yet".
5. **`ai/superchart-integration/phase-5/replay/prd.md`**
   - Line 31: "Chart context menu 'Start replay here'" (listed as out-of-scope
     dependency — reword to note the chart context menu now exists, while the actual
     menu entry is still a follow-up PRD).

The updates must make clear that:
- The chart-background context menu plumbing is now available (as of `[sc-chart-ctx-menu]`).
- The **concrete menu entries** (e.g. "Start replay here", "Jump back to here") are
  still follow-up work, since this PRD only lands the empty shell.

## Non-requirements

- No menu items in this PRD — the popup body is empty.
- No hotkey for opening the chart context menu (it is right-click only).
- No mobile long-press support.
- No custom popup styling — reuse `ContextMenuPopup` as-is.
- No changes to `InteractionController` — it already supports `once: false` persistent
  consumers and already enriches results with `pageX`/`pageY`.
- No changes to the Superchart library. The `coordinate.x`/`coordinate.y` → `pageX`/
  `pageY` bridging stays in `InteractionController` until SC adds native page coords.

## References

- `InteractionController`:
  `src/containers/trade/trading-terminal/widgets/super-chart/controllers/interaction-controller.js`
- `ContextMenuPopup`: `src/components/elements/context-menu.js`
- Overlay context menu (pattern to mirror):
  `src/containers/trade/trading-terminal/widgets/super-chart/overlays/overlay-context-menu.js`
- Overlay context menu PRD (phase 4a-2): `ai/superchart-integration/phase-4/overlay-context-menu/prd.md`
- Price-time-select consumer (example of a `once: true` consumer):
  `ai/superchart-integration/phase-3/price-time-select/prd.md`
