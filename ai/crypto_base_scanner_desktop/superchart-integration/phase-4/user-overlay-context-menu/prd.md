---
id: sc-user-overlay-ctx-menu
---

# User-Drawn Overlay Context Menu (Phase 4a-3)

Altrady-rendered right-click context menu for **user-drawn overlays** in the
SuperChart TT main chart — overlays created by the user via SC's drawing bar
(segments, fib, trendlines, shapes, etc.), as opposed to overlays programmatically
created via `chart.createOverlay()` (covered by `sc-overlay-ctx-menu`).

## Motivation

Right-clicking a user-drawn overlay currently opens SC's **built-in** context menu
(see `screenshot.png`). It is not the Altrady-rendered overlay context menu — that
one only shows on overlays we create programmatically. The SC menu cannot match
Altrady's design system, theme, or interaction patterns, and it cannot reuse the
shared `ContextMenuPopup`, settings-modal hooks, or other Altrady-only behavior.

## Scope

- **In scope:** All user-drawn overlays in the SuperChart TT main chart (any
  overlay created through SC's drawing bar or otherwise tracked by SC's
  `StorageAdapter` and not appearing in `ChartController._overlays`).
- **Out of scope:**
  - Overlays created via `chart.createOverlay()` from Altrady code (handled by
    `sc-overlay-ctx-menu`).
  - Overlays created via `createOrderLine` / `createTradeLine`.
  - Grid bot chart overlays (`grid-bot-super-chart.js`).
  - Backtest chart overlays.
  - Empty chart area right-click (handled by `sc-chart-ctx-menu`).
  - Re-implementing SC-native modals/panels (Settings dialog, Object Tree,
    Template manager). Altrady delegates to SC for these via callbacks SC
    must expose — see the companion `sc-feature-request.md`.

## Behavior

### Trigger and dismissal

1. SC's built-in right-click context menu is **disabled** on user-drawn overlays.
2. SC fires a callback (`onUserOverlayRightClick`, name TBD) with the clicked
   overlay's id, name, page coordinates, points, and the current per-overlay
   state needed to render the menu (lock, visible, paneId, available
   visibility-on-intervals options, etc.).
3. The Altrady `OverlayContextMenu` React component receives this event and
   renders its `ContextMenuPopup` at the click coordinates.
4. Same dismissal as the existing overlay context menu: backdrop mousedown,
   scroll, tab/symbol/resolution change.

### Menu items (ported from SC default menu)

Item order matches SC's menu (top to bottom):

| # | Item                       | Has submenu | Keyboard shortcut hint | v1 |
|---|----------------------------|-------------|------------------------|----|
| 1 | Template                   | yes         | —                      | -  |
| 2 | Visual order               | yes         | —                      | -  |
| 3 | Visibility on intervals    | yes         | —                      | -  |
| 4 | Object Tree…               | no          | —                      | -  |
| 5 | Clone                      | no          | `Ctrl + Drag`          | -  |
| 6 | Copy                       | no          | `Ctrl + C`             | -  |
| 7 | Lock                       | no (toggle) | —                      | -  |
| 8 | Hide                       | no (toggle) | —                      | -  |
| 9 | Remove                     | no          | `Del`                  | ✅  |
|10 | Settings                   | no          | —                      | ✅  |

`v1 ✅` means "wire in the first implementation pass." All other items are
ported into the menu **structurally** (rendered, but stubbed or hidden behind
a feature flag) and implemented one by one in subsequent rounds. The order in
which the remaining items get implemented is decided later — this PRD only
fixes the menu surface, the per-item behavior expectations, and the SC-side
APIs each item needs.

The keyboard shortcut hints are rendered as right-aligned monospace chips
matching the SC default menu's styling, and are display-only — actual key
bindings are SC's responsibility.

A separator is rendered between groups, matching SC:
- Above Clone (after Object Tree)
- Above Lock (after Copy)
- Above Settings (after Remove)

### Item behaviors

#### 1. Template ▶ (deferred)

Submenu listing user-saved drawing templates for the clicked overlay's tool
plus the built-in `SYSTEM_DRAWING_TEMPLATES`. Selecting one applies it to
the overlay. Bottom of the submenu: **Save as template…** entry that opens
an SC-native save dialog.

**Why deferred:** Drawing templates are currently disabled in Altrady
(`disabledFeatures: ['drawing_templates']`). When that feature is enabled,
this item becomes active. Until then, the menu item is hidden.

**SC requirement:** Expose either (a) the list of templates per tool plus
an `applyDrawingTemplate(overlayId, templateName)` method, or (b) a single
`openDrawingTemplateMenu(overlayId, anchor)` imperative call that opens
SC's native submenu at the given screen position. Option (b) is preferred —
SC owns the template UI today and replicating it in Altrady is out of scope.

#### 2. Visual order ▶

Submenu with z-order actions:
- Bring to front
- Bring forward
- Send backward
- Send to back

**SC requirement:** Per-action imperative methods on `SuperchartApi` (or
chainable on the overlay handle), e.g. `bringOverlayToFront(id)`,
`bringOverlayForward(id)`, `sendOverlayBackward(id)`, `sendOverlayToBack(id)`.

#### 3. Visibility on intervals ▶

Submenu listing the chart's available periods, each with a toggle showing
whether the overlay is visible on that period. Toggling changes the
per-period visibility for **this overlay only**.

**SC requirement:** A way to read the current per-period visibility mask
and to update it (e.g. `getOverlayVisibleIntervals(id): Period[]` and
`setOverlayVisibleIntervals(id, periods)`), or a single
`openVisibilityOnIntervalsMenu(overlayId, anchor)` imperative call. Either
the data API or the native-menu opener is acceptable.

#### 4. Object Tree…

Opens the SC-native Object Tree panel/dialog.

**SC requirement:** `openObjectTree()` (no argument needed — Object Tree
shows all overlays on the chart).

#### 5. Clone

Duplicates the overlay at a small visual offset, mirroring SC's
`Ctrl + Drag` behavior.

**SC requirement:** `cloneOverlay(id): string` returning the new overlay
id. The duplicated overlay should be persisted via `StorageAdapter` like
any other user-drawn overlay.

#### 6. Copy

Copies the overlay to SC's internal clipboard so the user can paste with
`Ctrl + V` (which remains an SC-handled global shortcut — Altrady is not
adding a `Paste` menu item).

**SC requirement:** `copyOverlay(id)` placing the overlay onto SC's
clipboard.

#### 7. Lock (toggle)

Toggles `lock` on the overlay. Reflect the current lock state in the menu
item label ("Lock" → "Unlock") and icon (open/closed padlock — matching SC
default).

**Implementation:** `chart.getChart().overrideOverlay({id, lock: !currentLock})`.
This already exists in the klinecharts API (see `SUPERCHART_USAGE.md:285`),
so no SC-side change is strictly required for the toggle itself — but SC
must include the current `lock` value in the right-click event payload (or
expose a `getOverlay(id)` lookup) so Altrady can render the correct label.

#### 8. Hide (toggle)

Toggles `visible` on the overlay. Same labelling pattern as Lock
("Hide" → "Show", icon flipped).

**Implementation:** `chart.getChart().overrideOverlay({id, visible: !currentVisible})`
*if* klinecharts supports a `visible` property — needs SC confirmation. If
not, SC must add a `setOverlayVisible(id, visible)` method and include the
current visibility in the right-click event payload.

#### 9. Remove (v1)

Removes the overlay. Routes through `chart.removeOverlay(id)` (the SC
wrapper) — not the klinecharts escape hatch — so persistence and any open
SC dialogs stay in sync (`SUPERCHART_USAGE.md:279`).

#### 10. Settings (v1)

Opens SC's native overlay settings dialog (the modal SC normally shows
when the user clicks the Settings entry in its built-in menu).

**SC requirement:** `openOverlaySettings(overlayId)`. The dialog is
SC-native — Altrady cannot render it (the overlay schema, style options,
and styled controls live inside SC). Required for v1 since otherwise users
who right-click a drawing they want to restyle have no way to reach the
settings.

### Per-item enabling

Items 5–9 are always available on any user-drawn overlay (subject to
v1 ✅ filter). Items 1 / 2 / 3 / 10 require the corresponding SC API
to exist; if SC does not expose it yet, the item is hidden (not greyed
out). Item 4 (Object Tree) is always available.

## Settings respect

There are no Altrady chart-settings toggles that should hide items in this
menu. The existing `alertsEnableEditing` / `openOrdersEnableEditing` flags
apply only to programmatic overlays and are not relevant here.

## Reuse / unification with the existing overlay context menu

Hard requirement: this menu is rendered by the **same** `OverlayContextMenu`
React component and managed by the **same** `ContextMenuController` as the
programmatic overlay menu. The two flows share:

- **`ContextMenuPopup`** (already extracted)
- **`OverlayContextMenu` component file** — must accept both shapes of menu
  state (programmatic vs user-drawn) and render the correct set of items
  via a single `kind` discriminator
- **`ContextMenuController` state slot** — there is one
  `_overlayContextMenuState` (not two parallel slots) so the two menus are
  mutually exclusive by construction and the `closeAllContextMenus()` /
  tab-change cleanup wiring continues to work unchanged
- **`overlay-helpers.js`** — adds a parallel constants block / item resolver
  for user overlays (e.g. `USER_OVERLAY_MENU_ITEMS`), alongside the existing
  `EDITABLE_OVERLAY_GROUPS` / `DELETABLE_OVERLAY_GROUPS` / etc.

Splits of new code (controller methods, helper functions, React item
rendering) should mirror the existing programmatic-overlay split as closely
as possible — `getUserOverlayContextMenuRemoveAction`,
`getUserOverlayContextMenuLockAction`, etc., named symmetrically with
`getOverlayContextMenu*Action`.

## i18n

New keys under `containers.trade.market.marketGrid.superChart.contextMenu.userOverlay.*`:

- `template`, `visualOrder`, `visibilityOnIntervals`, `objectTree`, `clone`,
  `copy`, `lock`, `unlock`, `hide`, `show`, `remove`, `settings`
- Submenu items (visual order): `bringToFront`, `bringForward`,
  `sendBackward`, `sendToBack`
- Save-as-template label (deferred): `saveAsTemplate`

Shortcut chip strings (`Ctrl + Drag`, `Ctrl + C`, `Del`) are NOT
translated — they are keyboard identifiers and should be rendered
verbatim in all locales (matching SC).

## Non-requirements

- No re-implementation of SC-native dialogs (Settings, Object Tree,
  Template manager, Save-as-template). SC owns these.
- No `Paste` menu item — paste remains SC's global `Ctrl + V` shortcut.
- No clone-via-drag handling — that stays an SC behavior, the menu item
  just provides a click-driven alternative.
- No per-period chart-settings toggle to disable specific menu items.
- No Altrady-side Info modal for user-drawn overlays in v1 (the existing
  Info modal for programmatic overlays remains untouched). Can be added
  later if useful — the existing controller helpers can be extended.

## References

- SC default menu screenshot: `screenshot.png` (this folder)
- Programmatic overlay context menu PRD: `../overlay-context-menu/prd.md`
- Programmatic overlay context menu design: `../overlay-context-menu/design.md`
- `ContextMenuController` (existing): `src/containers/trade/trading-terminal/widgets/super-chart/controllers/context-menu-controller.js`
- `OverlayContextMenu` (existing component): `src/containers/trade/trading-terminal/widgets/super-chart/overlays/overlay-context-menu.js`
- `ContextMenuPopup` (shared popup): `src/components/elements/context-menu.js`
- SC feature flag for built-in menu: `right_click_menu` (default true) — see
  `~/ai/crypto_base_scanner_desktop/deps/SUPERCHART_API.md:773`
- klinecharts `overrideOverlay`: `~/ai/crypto_base_scanner_desktop/deps/SUPERCHART_USAGE.md:285`
- Companion SC feature request: `sc-feature-request.md`
