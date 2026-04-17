# Overlay Context Menu — Design

## Architecture

### Data flow

1. **klinecharts** fires `onRightClick(event)` on a `createOverlay` overlay
2. **ChartController** receives the event via `_onOverlayRightClick`, calls `preventDefault()`,
   reverse-lookups the overlay in the `_overlays` registry to find `{group, key}`, and sets state
3. **React component** (`OverlayContextMenu`) subscribes to the state via callback and renders
   a `ContextMenuPopup` at the click coords (`event.pageX`/`event.pageY`)
4. **Menu items** dispatch actions (edit, save, delete, open settings modal) and close the popup

### Key decisions

- **Extracted `ContextMenuPopup`** from `context-menu.js` — a standalone component that handles
  positioning, portal rendering, backdrop dismiss, scroll dismiss, and mobile support. Reused by
  both the existing `ContextMenu` (DOM events) and `OverlayContextMenu` (programmatic).

- **State lives on ChartController** as a simple object:
  `{ overlayId, overlayName, group, key, points, x, y }`.
  A React component subscribes via `setOverlayContextMenuCallback(fn)`. No Redux.

- **`onRightClick` wired via `_createOverlay` wrapper.** A single `_createOverlay(options)` method
  wraps `chart.createOverlay()` and appends `onRightClick: this._onOverlayRightClick` to every call.
  All primitives (`_createPriceLevelLine`, `_createTimeLine`, `_createTrendlineLine`, and direct
  calls) go through `_createOverlay`.

- **Settings modal tab + section selection.** `GridItemSettingsContext.onToggle` extended to
  `onToggle(component, initialTab, focusSection)`. `focusSection` is an object `{section, group}`
  (for general settings) or `{section, colorKey, group}` (for color settings). The settings
  components use `data-settings-section` and `data-color-key` DOM attributes to find and highlight
  the relevant section/row via `util.highlightElement()` + `scrollIntoView()`.

### Overlay identification

`_onOverlayRightClick(event)`:
1. Call `event.preventDefault()` to prevent klinecharts from deleting the overlay
2. Get `overlayId = event.overlay.id`
3. `_lookupOverlayById(overlayId)` — iterates `_overlays` Map to find `{group, key}`
4. If not found, ignore
5. Set state: `{ overlayId, overlayName, group, key, points, x: event.pageX, y: event.pageY }`
6. Notify React via `_onOverlayContextMenuChange` callback

### Menu item resolution

`getContextMenuItems(group)` in `overlay-helpers.js` returns:

```js
{
  edit: boolean,          // group is in EDITABLE_OVERLAY_GROUPS or has posId prefix
  editType: "alert" | "position" | null,
  save: boolean,          // group is in EDITING_DELETABLE_GROUPS
  delete: boolean,        // group is in DELETABLE_OVERLAY_GROUPS or EDITING_DELETABLE_GROUPS
  isEditingDelete: boolean,
  info: true,
  hide: true,
  color: true,
}
```

### Action callbacks

Controller methods build callbacks from `group` and `key`:

**Edit** (`getOverlayContextMenuEditAction`):
- Checks `alertsEnableEditing` / `openOrdersEnableEditing` — returns null if disabled
- Alerts: extracts alert ID from key, finds alert in marketTradingInfo, dispatches `editAlert`
- Positions: extracts posId from group, finds order, dispatches `editOrder`

**Save** (`getOverlayContextMenuSaveAction`):
- Editing alerts: dispatches `submitAlertsForm()`
- Editing conditions/expirations: calls `_onSubmitTradeForm()`

**Delete** (`getOverlayContextMenuDeleteAction`):
- Submitted alerts: checks `alertsEnableEditing` + `alertsEnableCanceling`, dispatches `deleteAlert`
- Editing alerts: dispatches `resetAlertForm()`
- Editing conditions/expirations: calls `resetTradeForm(true)`

**Info** (`getOverlayEntityInfo`):
- Returns `{type, id, creating?}` based on group/key and form state

**Settings/Color**: opens `GridItemSettingsContext.onToggle` with appropriate tab and focusSection.

### Component structure

```
SuperChartWidgetWithProvider
  └── OverlayContextMenu
        ├── ContextMenuPopup (from context-menu.js)
        │     └── Popup with PopupItems
        └── OverlayInfoModal
              ├── OverlayPointDetails (price/time/trendline points)
              └── overlay name + ID (below divider)
```

### Settings highlight flow

1. Context menu passes `focusSection` object to `onToggle(component, initialTab, focusSection)`
2. `GridItemSettingsProvider` stores it in state, passes to `GridItemSettings` → `TradingviewSettings`
3. `TradingviewSettings` passes to `GeneralSettings` / `ColorSettings` via `focusSection` prop
4. On `componentDidMount`, the settings component:
   - For color: tries `[data-color-key="${colorKey}"]` first, falls back to `[data-settings-section]`
   - For general: uses `[data-settings-section="${sectionKey}"]`
   - `scrollIntoView({behavior: "smooth", block: "center"})` + `util.highlightElement()`

### SC library changes (coinray-chart)

`priceLevelLine.ts` and `box.ts`: added configurable `ignoreEvent` property (default `true`).
Desktop app passes `ignoreEvent: false` in `_createPriceLevelLine` extendData to enable mouse events.
Base segments pass `ignoreEvent: false` in extendData. Base boxes do not (not needed).

## File changes

### New files

1. **`overlays/overlay-context-menu.js`** — React component with ContextMenuPopup, menu items,
   OverlayInfoModal, OverlayPointDetails

### Modified files

2. **`chart-controller.js`**
   - `_createOverlay(options)` — wrapper that appends `onRightClick`
   - `_onOverlayRightClick` — shared handler
   - `_lookupOverlayById`, `openOverlayContextMenu`, `closeOverlayContextMenu`,
     `setOverlayContextMenuCallback` — state management
   - `getOverlayContextMenuEditAction`, `getOverlayContextMenuDeleteAction`,
     `getOverlayContextMenuSaveAction`, `getOverlayEntityInfo` — action builders
   - All `createOverlay` calls go through `_createOverlay`
   - `_createPriceLevelLine` passes `ignoreEvent: false`
   - `_createBaseSegment` passes `ignoreEvent: false`
   - `createTimeAlert`/`createTrendlineAlert` respect `alertsEnableEditing` (lock + callbacks)

3. **`context-menu.js`** — extracted `ContextMenuPopup` component and `checkLocation` function.
   `ContextMenu` class now uses `ContextMenuPopup` internally (backward-compatible).

4. **`super-chart.js`** — mounts `<OverlayContextMenu/>`

5. **`grid-item-settings.js`** — `onToggle(component, initialTab, focusSection)`, passes all
   three to `GridItemSettings` and through to modal content

6. **`settings.js`** — passes `initialTab` and `focusSection` to GeneralSettings/ColorSettings

7. **`general-settings.js`** — extracted `ChartSettingsSection` component with `data-settings-section`.
   `componentDidMount` highlights section. Simplified i18n with `t()` shorthand.

8. **`color-settings.js`** — added `data-settings-section` and `data-color-key` attributes.
   `componentDidMount` highlights color row or section. Simplified i18n with `t()` shorthand.

9. **`overlay-helpers.js`** — group classification constants, `getContextMenuItems`,
   `getSettingsSection`, `getColorSection`, `getColorKey`, `getOverlayLabel`,
   `extractPositionId`, `extractAlertId`

10. **`en/translation.yaml`, `es/translation.yaml`, `nl/translation.yaml`** — context menu i18n keys
