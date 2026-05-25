# SC Feature Request — User-Drawn Overlay Right-Click Callback + Imperative APIs

**Target:** Superchart (`Superchart` + `coinray-chart`)
**Consumer:** Altrady desktop, `crypto_base_scanner_desktop` —
`feature/superchart-integration` branch.
**Related PRD:** `prd.md` (this folder) — `sc-user-overlay-ctx-menu`.

## Summary

Altrady wants to render its own context menu for user-drawn overlays (drawing
bar overlays — segments, trendlines, fib, shapes, etc.) instead of SC's
built-in one, so the menu can match Altrady's design system and integrate
with Altrady-side state.

SC's existing `onRightClick(event)` callback on `createOverlay()` overlays
covers programmatic overlays only. User-drawn overlays still get SC's
default context menu (Template / Visual order / Visibility on intervals /
Object Tree / Clone / Copy / Lock / Hide / Remove / Settings — see
`screenshot.png`).

Two pieces are needed from SC:

1. **A way to suppress the built-in menu and emit a right-click callback
   instead**, with enough payload data for the consumer to render its own.
2. **Imperative methods to invoke the actions** that currently sit behind
   the built-in menu items (especially the ones whose UI is SC-native, like
   Settings and Object Tree).

## 1. Right-click callback for user-drawn overlays

### Behavior

- When the user right-clicks a user-drawn overlay AND the consumer has opted
  in (see "Opt-in mechanism" below), SC must:
  - call `event.preventDefault()` on the underlying mouse event
  - **suppress** its built-in context menu
  - fire the consumer-provided callback with the payload below
- For programmatic overlays (created via `chart.createOverlay()` with
  `onRightClick` set), the existing per-overlay `onRightClick` still wins —
  do not double-fire.
- For programmatic overlays without `onRightClick`, current behavior is
  unchanged (SC's built-in menu fires, or nothing — whatever SC does today).

### Opt-in mechanism — preferred shape

A new top-level option on `SuperchartOptions`:

```ts
onUserOverlayRightClick?: (event: UserOverlayRightClickEvent) => void
```

When this callback is provided, SC suppresses its built-in menu for
user-drawn overlays and routes to the callback instead. When the callback
is not provided, current behavior (built-in menu) is preserved — no
behavior change for other consumers.

> Alternative shape: a new feature flag `user_overlay_right_click_menu`
> (default `true`) disabled via `disabledFeatures` plus a separate listener
> registration `sc.onUserOverlayRightClick(cb): () => void`. Either is fine
> as long as the suppress + callback are wired together and don't require
> the consumer to deal with both.

Note: the existing `right_click_menu` feature flag suppresses the menu but
(as of the current docs) does not appear to provide a replacement callback
— please confirm/clarify in the docs which scenarios that flag covers.

### Payload shape — `UserOverlayRightClickEvent`

The consumer needs everything required to render the menu without further
lookups (or with at most a single helper call). Suggested fields:

```ts
interface UserOverlayRightClickEvent {
  // Identification
  overlayId: string
  overlayName: string            // klinecharts overlay type name (e.g. 'segment', 'fibonacciLine')
  paneId: string

  // Positioning (consistent with existing onRightClick on programmatic overlays)
  pageX: number
  pageY: number

  // Points (so the consumer can render an Info section if it wants to)
  points: Array<{ value?: number; timestamp?: number; dataIndex?: number }>

  // Current per-overlay state needed to render correct labels/icons:
  lock: boolean                  // for the Lock/Unlock toggle label + icon
  visible: boolean               // for the Hide/Show toggle label + icon
  visibleIntervals?: Period[]    // (optional) for the Visibility-on-intervals submenu
  zOrder?: number                // (optional) for the Visual-order submenu

  // The underlying browser event so the consumer can preventDefault / stopPropagation if needed
  originalEvent: MouseEvent
}
```

If `visibleIntervals` / `zOrder` are awkward to compute up-front, a pair of
synchronous getters on `SuperchartApi` (e.g.
`getOverlayVisibleIntervals(id)`, `getOverlayZIndex(id)`) is an acceptable
substitute — the consumer will call them when rendering the relevant
submenu rather than on every right click.

`lock` and `visible` are required in the payload — without them the
consumer cannot render the correct toggle labels on the menu without doing
a klinecharts escape-hatch `getOverlays({id})` lookup, which would be
fragile.

## 2. Imperative APIs for the menu actions

Several SC built-in menu items don't just mutate the overlay — they open
**SC-native UI** (modals, panels, submenus) that the consumer cannot
re-render. For those, the consumer needs an imperative method to *open* the
SC dialog from a click on the Altrady-rendered menu item.

### 2a. Open SC overlay settings dialog

```ts
sc.openOverlaySettings(overlayId: string): void
```

Opens the SC-native overlay style/settings dialog for the given overlay
(the same dialog SC's built-in `Settings` menu entry opens today). This is
**required for v1** of the Altrady menu — without it, users have no way to
restyle a drawing.

### 2b. Open SC Object Tree panel/dialog

```ts
sc.openObjectTree(): void
```

Opens the SC-native Object Tree panel/dialog (lists all overlays on the
chart). No `overlayId` argument — Object Tree is chart-wide.

### 2c. Visibility-on-intervals submenu

Either:

- **Preferred:** an imperative open-at-anchor call
  ```ts
  sc.openVisibilityOnIntervalsMenu(overlayId: string, anchor: { pageX: number; pageY: number }): void
  ```
  so SC opens its own submenu UI at the anchor point.

- **Or:** data-level access so the consumer can render the submenu itself:
  ```ts
  sc.getOverlayVisibleIntervals(id: string): Period[]
  sc.setOverlayVisibleIntervals(id: string, periods: Period[]): void
  ```
  Either is fine — option 1 keeps the UI consistent with SC.

### 2d. Visual order

Four imperative methods (z-order):

```ts
sc.bringOverlayToFront(id: string): void
sc.bringOverlayForward(id: string): void
sc.sendOverlayBackward(id: string): void
sc.sendOverlayToBack(id: string): void
```

If a single `sc.setOverlayZIndex(id, zIndex)` exists or is easier to expose,
the consumer can build the four operations on top of it — but only if a
`getOverlayZIndex(id)` (or a `zOrder` field on the right-click payload) is
also available, so the consumer can compute neighbor z-indexes.

### 2e. Template submenu (deferred on consumer side)

```ts
sc.openDrawingTemplateMenu(overlayId: string, anchor: { pageX: number; pageY: number }): void
```

Opens SC's existing drawing-template submenu at the anchor point. Deferred
on Altrady's side until the `drawing_templates` feature is enabled, but
useful to scope/spec now so the API is in place when we turn it on.

### 2f. Clone / Copy

```ts
sc.cloneOverlay(id: string): string   // returns the new overlay id
sc.copyOverlay(id: string): void      // places overlay onto SC's internal clipboard
```

Clone should persist via `StorageAdapter` like a normal user-drawn
overlay. Copy should be compatible with SC's existing `Ctrl + V` paste
shortcut (so a user can right-click → Copy and then paste with the
keyboard).

### 2g. Lock / Hide / Remove

These already work via existing APIs:

- Lock: `chart.getChart().overrideOverlay({ id, lock })` — works today
  (see `SUPERCHART_USAGE.md:285`).
- Hide: same, with `{ id, visible }` — **needs confirmation that
  klinecharts `overrideOverlay` supports `visible`**. If not, add
  `sc.setOverlayVisible(id, visible)`.
- Remove: `sc.removeOverlay(id)` — works today
  (see `SUPERCHART_USAGE.md:279`).

No new APIs needed for these as long as the right-click payload includes
the current `lock` / `visible` state (see §1).

## Acceptance checklist (SC side)

- [ ] When `onUserOverlayRightClick` is supplied (or the equivalent opt-in
      shape), right-clicking a user-drawn overlay does **not** open SC's
      built-in menu and **does** fire the callback with the payload above.
- [ ] When `onUserOverlayRightClick` is not supplied, current behavior is
      unchanged (no regressions for existing consumers).
- [ ] `onRightClick` on `createOverlay({onRightClick})` overlays still
      takes precedence — the user callback is not double-fired.
- [ ] `sc.openOverlaySettings(id)` works for any user-drawn overlay
      type (matches the dialog SC would open from its built-in menu).
- [ ] `sc.openObjectTree()` opens the Object Tree panel.
- [ ] `sc.openDrawingTemplateMenu(id, anchor)` and
      `sc.openVisibilityOnIntervalsMenu(id, anchor)` open submenu UIs at
      the anchor (or the data-level alternatives exist).
- [ ] z-order methods exist (or `getOverlayZIndex` + `setOverlayZIndex`).
- [ ] `sc.cloneOverlay(id)` and `sc.copyOverlay(id)` exist; cloned overlay
      is persisted by `StorageAdapter`.
- [ ] `lock` and `visible` are present in the right-click payload.
- [ ] `overrideOverlay({id, visible})` works (or a `setOverlayVisible`
      method is added).
- [ ] All new APIs are documented in `$SUPERCHART_DIR/docs/` and reflected
      in `~/ai/crypto_base_scanner_desktop/deps/SUPERCHART_API.md` /
      `SUPERCHART_USAGE.md` (consumer side will sync after SC ships).

## Out of scope for SC

- Any Altrady-specific menu styling or menu structure — the consumer
  renders everything driven by the callback.
- A "Paste" callback — paste remains SC's global `Ctrl + V` shortcut.
- Re-implementing overlay settings as a data API. Settings stay SC-native
  via `openOverlaySettings`.

## References

- Existing `onRightClick` on programmatic overlays: `SUPERCHART_API.md:978`
  (added in SC `42d90ae`).
- Existing `right_click_menu` feature flag: `SUPERCHART_API.md:773`.
- `chart.removeOverlay`: `SUPERCHART_USAGE.md:279`.
- `chart.getChart().overrideOverlay`: `SUPERCHART_USAGE.md:285`.
