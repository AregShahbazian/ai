# Design: Price/Time Select — SuperChart Port

Two shared inputs (`PriceField` and `DatePickerInput`) call `ChartRegistry.getActive()?.interaction.start({id, once: true, onSelect, onCancel})` — same pattern as `replay-controller.js:301`. No new files, no TV edits, no `ChartController` edits.

- **`PriceField`** — `onSelect: ({point}) => onChange(normalizeValue(point.price))`.
- **`DatePickerInput`** — `onSelect: ({point}) => onChange(moment(point.time * 1000).toDate())`. SC delivers UTC seconds; no timezone correction.
- **`id`** — include a stable per-field suffix (`label` / `name` / mount-time ref) so two inputs on the same form don't collide.
- **`onCancel`** — single hook that clears the input's `selecting*` state. Covers Escape, outside-click, right-click, supersede, symbol change, dispose.

TV `price-time-select.js` and its remaining callers (quiz, TV `edit-alerts`, TV `chart-functions`, `tradingview.js`) are untouched.

## Deferred

Multi-chart focus semantics — `ChartRegistry.getActive()` is last-registered-wins. Fine for TT + grid bot; revisit when the multi-chart Charts page lands.
