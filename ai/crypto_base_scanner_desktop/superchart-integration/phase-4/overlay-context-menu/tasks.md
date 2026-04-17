# Overlay Context Menu — Tasks

All tasks completed.

## Task 1: Overlay helpers — group classification and ID extraction ✅
**File:** `overlay-helpers.js`
- Group classification sets: `EDITABLE_OVERLAY_GROUPS`, `EDITABLE_POSITION_PREFIXES`,
  `DELETABLE_OVERLAY_GROUPS`, `EDITING_DELETABLE_GROUPS`
- `getContextMenuItems(group)` — returns edit/editType/save/delete/info/hide/color flags
- `getSettingsSection(group)` — maps overlay group to general settings section i18n key
- `getColorSection(group)` — maps overlay group to color settings section data attribute
- `getColorKey(group)` — maps overlay group to specific chartColors key (or null)
- `getOverlayLabel(group)` — human-readable label for info modal
- `extractPositionId(group)`, `extractAlertId(key)` — ID extraction helpers

## Task 2: ChartController — right-click handler and state management ✅
**File:** `chart-controller.js`
- `_createOverlay(options)` — wrapper that appends `onRightClick: this._onOverlayRightClick`
- `_onOverlayRightClick` — handler: preventDefault, lookup, set state with `pageX`/`pageY`
- `_lookupOverlayById`, `openOverlayContextMenu`, `closeOverlayContextMenu`,
  `setOverlayContextMenuCallback` — state management
- `getOverlayContextMenuEditAction` — checks alertsEnableEditing/openOrdersEnableEditing
- `getOverlayContextMenuDeleteAction` — checks alertsEnableEditing+alertsEnableCanceling
- `getOverlayContextMenuSaveAction` — submitAlertsForm or _onSubmitTradeForm
- `getOverlayEntityInfo` — returns {type, id} for info modal

## Task 3: Wire onRightClick into all createOverlay calls ✅
**File:** `chart-controller.js`
- All 6 `chart.createOverlay()` calls replaced with `this._createOverlay()`
- `_createPriceLevelLine` passes `ignoreEvent: false` in extendData
- `_createBaseSegment` passes `ignoreEvent: false` in extendData
- `createTimeAlert`/`createTrendlineAlert` respect `alertsEnableEditing` (lock + callbacks)

## Task 4: Settings modal tab + section selection ✅
**Files:** `grid-item-settings.js`, `settings.js`, `general-settings.js`, `color-settings.js`
- `onToggle(component, initialTab, focusSection)` — three parameters
- `TradingviewSettings` uses `initialTab` prop, passes `focusSection` to both tab components
- `ChartSettingsSection` extracted component in general-settings with `data-settings-section`
- Color settings: `data-settings-section` and `data-color-key` attributes
- Both components: `componentDidMount` finds element by selector, scrollIntoView + highlightElement
- Color: tries specific `data-color-key` first, falls back to `data-settings-section`
- i18n simplified with `t()` shorthand in both files

## Task 5: OverlayContextMenu React component ✅
**File:** `overlays/overlay-context-menu.js`
- Uses `ContextMenuPopup` from `context-menu.js` (no duplicated positioning logic)
- Menu items: Edit alert/position, Save, Delete/Cancel edit, separator, Settings, Color, separator, Info
- `OverlayInfoModal` — type label, entity ID, overlay-specific point details, divider, debug info
- `OverlayPointDetails` — price/time/trendline points based on overlay group

## Task 6: Extract ContextMenuPopup ✅
**File:** `context-menu.js`
- Extracted `checkLocation` as standalone function
- Extracted `ContextMenuPopup` as exported functional component (x, y, onClose, spanMobile, children)
- `ContextMenu` class refactored to use `ContextMenuPopup` internally (backward-compatible)
- Backdrop uses `onMouseDown` (not `onClick`) to avoid right-click release closing the popup

## Task 7: Mount + i18n ✅
**Files:** `super-chart.js`, `en/translation.yaml`, `es/translation.yaml`, `nl/translation.yaml`
- `<OverlayContextMenu/>` added to `SuperChartWidgetWithProvider`
- Context menu keys: editAlert, editPosition, save, delete, cancelEdit, info, settings, color

## Task 8: SC library changes ✅
**Files:** coinray-chart `priceLevelLine.ts`, `box.ts`
- Added `ignoreEvent` property to `PriceLevelLineProperties` and `BoxProperties` (default `true`)
- All figures use the property instead of hardcoded `true`
