# Feature: Period-bar visibility control

## Problem

SC always renders the full `.superchart-period-bar` with all built-in
controls: left-toolbar toggle (hamburger), symbol picker, period picker,
Indicators, Timezone, Settings, Screenshot, Full Screen. The consumer
has no way to hide the bar as a whole, nor to hide or disable individual
controls.

Altrady needs this in several places:

- **Settings-modal preview chart** — a small decorative chart showcasing
  the user's custom colors. No interaction at all; a period-bar is
  visual noise.
- **Quiz play mode** — replay-style playback UI. TradingView was hidden
  entirely via `disabled_features: ["header_widget"]`.
- **Grid-bot chart** — bound to a specific market + timeframe. User
  should still *see* symbol/period (context) but can't change them.
  Drawings are not relevant.
- **Trading terminal main chart** — Altrady ships its own Settings
  button (opens a chart settings modal) and its own Share button
  (upload + share). SC's built-in Settings gear and Screenshot are
  redundant and confusing.

`disableScreenshot?: boolean` (previously proposed in
`SUPERCHART_API.md:745`) is a narrower case of the same need — folds
into this feature.

## Proposed API

### Constructor options

```ts
type ButtonState =
  | boolean                                      // false = hidden; true = visible + enabled (default)
  | { visible?: boolean; enabled?: boolean }     // set axes independently

interface SuperchartOptions {
  // ... existing ...

  // Hide the entire period-bar (`.superchart-period-bar`). Replaces TV's
  // `disabled_features: ["header_widget"]`.
  periodBarVisible?: boolean              // default: true

  // Hide/disable individual built-in controls in the period-bar.
  // `undefined` = default (visible + enabled).
  periodBarButtons?: Partial<{
    leftToolbarToggle: ButtonState        // hamburger — toggles the left drawing bar
    symbolSearch: ButtonState             // symbol/ticker picker
    periodPicker: ButtonState             // period selector
    indicators: ButtonState               // Indicators menu
    timezone: ButtonState                 // Timezone menu
    settings: ButtonState                 // SC's built-in Settings gear
    screenshot: ButtonState               // SC's built-in Screenshot button
    fullscreen: ButtonState               // Full Screen toggle
  }>
}
```

### Runtime methods (on `SuperchartApi`)

Altrady flips some of these at runtime (e.g. entering quiz play mode
mid-session, toggling replay). Setters are needed, not just init-time
options.

```ts
interface SuperchartApi {
  setPeriodBarVisible(visible: boolean): void
  setPeriodBarButtonVisible(id: keyof PeriodBarButtons, visible: boolean): void
  setPeriodBarButtonEnabled(id: keyof PeriodBarButtons, enabled: boolean): void
}
```

## Behavior

- `periodBarVisible: false` — the `.superchart-period-bar` element is
  not rendered at all. The chart canvas reclaims the vertical space.
  Applies to the whole bar; individual `periodBarButtons` entries are
  moot when the bar itself is hidden.
- `periodBarButtons.<id>: false` — that control is removed from the
  layout (as if it weren't there). Neighbouring controls close up.
- `periodBarButtons.<id>: { visible: false }` — same as above.
- `periodBarButtons.<id>: { enabled: false }` — control stays in the
  layout, rendered in a disabled / grayed-out state, not interactive.
  Hover still shows tooltip (or whatever SC's standard disabled style
  is). No click / keyboard activation.
- `periodBarButtons.<id>: { visible: true, enabled: true }` or
  `periodBarButtons.<id>: true` — same as default (no-op).
- `periodBarButtons.<id>: undefined` — default (visible + enabled).

Runtime setters mutate in place without re-initialising the chart.

## Edge cases

- Passing an unknown button id to `periodBarButtons` or
  `setPeriodBarButton*` — ignore (or warn in debug mode), don't throw.
- `periodBarVisible: false` with a non-empty `periodBarButtons` — the
  bar wins; `periodBarButtons` have no visible effect until
  `periodBarVisible` is true again. Engine should still honour the
  per-button state when the bar becomes visible.
- `setPeriodBarVisible(true)` after a construction with
  `periodBarVisible: false` — bar becomes visible, with any
  `periodBarButtons` config applied.
- `hotkeys` — if SC has any hotkeys tied to specific controls (e.g.
  `Ctrl+P` for screenshot), disabling the corresponding button should
  also disable the hotkey. Same for hiding. Otherwise the hidden
  control is still reachable via keyboard.

## Interface addition

Add the above `periodBarVisible` / `periodBarButtons` fields to
`SuperchartOptions`, and the three setters to `SuperchartApi`. Export a
`PeriodBarButtons` type keyed by the button ids listed above. The
`ButtonState` union is an internal type — can be exported if useful to
consumers.

## Folds in / supersedes

- **`disableScreenshot`** — the standalone option previously requested
  in `ai/api-gaps/screenshot-override.md` (if that doc exists) becomes
  `periodBarButtons.screenshot: false`. The companion
  `onScreenshot?: (url: string) => void` callback is a *different*
  concern (screenshot behaviour override, not visibility) and stays as
  its own feature request.

## Consumer usage — concrete examples from Altrady

### 1. Settings-modal preview — hide the whole bar

```js
new Superchart({
  container, symbol, period, dataLoader,
  periodBarVisible: false,
})
```

### 2. Grid-bot chart — disable symbol/period, hide drawing-bar toggle

```js
new Superchart({
  container, symbol, period, dataLoader,
  periodBarButtons: {
    leftToolbarToggle: false,                 // hide — no drawings on bot chart
    symbolSearch: { enabled: false },         // visible (shows current market), not clickable
    periodPicker: { enabled: false },         // visible (shows current timeframe), not clickable
  },
})
```

### 3. Trading terminal — hide duplicate built-ins

```js
new Superchart({
  container, symbol, period, dataLoader,
  periodBarButtons: {
    settings: false,                          // Altrady has its own Settings button
    screenshot: false,                        // Altrady has its own Share flow
    fullscreen: isMobile ? false : undefined, // redundant on mobile
  },
})
```

### Runtime flip (quiz entering play mode)

```js
sc.setPeriodBarVisible(false)
// ... later, back to edit mode ...
sc.setPeriodBarVisible(true)
```

## Storybook testing

Add a "Period-bar visibility" story under API stories with:

1. **Toggle whole bar** — button calling `setPeriodBarVisible(!visible)`;
   verify the period-bar element is/isn't in the DOM and the canvas
   height reflows.
2. **Per-button hide** — toggles for each of the eight button ids;
   verify the specific control is removed and neighbours close up.
3. **Per-button disable** — toggles that set `{ enabled: false }`;
   verify the button is rendered grayed out and does not respond to
   clicks / keyboard activation.
4. **Constructor config** — a story initialised with the three Altrady
   call shapes above; verify each renders as described.

## Altrady cross-references

- Full Altrady-side consolidation: `SUPERCHART_BACKLOG.md` #4 in the
  Altrady repo (`crypto_base_scanner_desktop/ai/superchart-integration/`).
- Altrady scopes blocked on this:
  `phase-9/settings-preview-chart/deferred.md`,
  `phase-4/header-buttons/prd.md` §R9,
  `phase-5/replay-current-behavior.md` (quiz `tvSetup`).

---

## Shipped API (reference for consumers)

The final implementation is a deliberate subset of the original proposal:
only the whole-bar toggle is a typed JS API. Per-button hide/disable is done
entirely via consumer-owned CSS against stable `data-button` attributes.
This keeps SC's surface minimal and gives Altrady full control over what
"hidden" and "disabled" look like.

### What SC provides

```ts
interface SuperchartOptions {
  /** Default: true. When false the period bar is not rendered. */
  periodBarVisible?: boolean
}

interface SuperchartApi {
  /** Show/hide the entire period bar at runtime (e.g. quiz play mode). */
  setPeriodBarVisible(visible: boolean): void
}
```

Each of the eight built-in controls carries a stable attribute:

| `data-button` value   | Control                                 |
| --------------------- | --------------------------------------- |
| `leftToolbarToggle`   | hamburger (toggles the drawing bar)     |
| `symbolSearch`        | symbol / ticker picker                  |
| `periodPicker`        | period selector                         |
| `indicators`          | Indicators menu                         |
| `timezone`            | Timezone menu                           |
| `settings`            | SC's built-in Settings gear             |
| `screenshot`          | SC's built-in Screenshot button         |
| `fullscreen`          | Full Screen toggle                      |

### Consumer usage

**Hide the whole bar** (settings-modal preview chart):

```ts
new Superchart({ /* ... */, periodBarVisible: false })
```

**Hide specific buttons** (trading terminal — replace SC's redundant built-ins):

```css
/* apply to the specific chart's container, not globally */
.my-main-chart .superchart-period-bar [data-button="settings"],
.my-main-chart .superchart-period-bar [data-button="screenshot"] {
  display: none;
}
```

**Disable specific buttons** (grid-bot chart — show context but block changes):

```css
.my-grid-bot-chart .superchart-period-bar [data-button="symbolSearch"],
.my-grid-bot-chart .superchart-period-bar [data-button="periodPicker"] {
  opacity: 0.4;
  pointer-events: none;
}
.my-grid-bot-chart .superchart-period-bar [data-button="leftToolbarToggle"] {
  display: none;
}
```

**Runtime toggle** (quiz entering play mode):

```ts
sc.setPeriodBarVisible(false)
// ... later, back to edit mode ...
sc.setPeriodBarVisible(true)
```

For runtime per-button flipping, add/remove a class on your container
(e.g. `chartContainer.classList.toggle('play-mode')`) and scope the CSS
rules under that class.

### Notes

- The CSS selectors above assume the consumer already scopes styles to
  their own container class. SC does not emit a unique per-chart class.
- Disabling via `pointer-events: none` also disables the underlying click
  handler — no keyboard activation because SC's period-bar items are not
  focusable.
- `periodBarVisible: false` takes precedence: when the bar is not
  rendered, `data-button` rules have no target until it becomes visible
  again.
