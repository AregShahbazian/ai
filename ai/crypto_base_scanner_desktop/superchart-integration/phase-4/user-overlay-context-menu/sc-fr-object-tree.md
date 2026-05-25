# SC FR — Object Tree: data + actions for an Altrady-rendered dialog

**Target:** Superchart
**Consumer:** Altrady — `feature/superchart-integration`
**Related:** `prd.md` (§ "Object Tree…"), `sc-feature-request.md` (§2b)

## Summary

Altrady wants to render its own Object Tree dialog (matches Altrady design
system) and drive it entirely from SC data + actions. SC's current
built-in Object Tree menu entry is a no-op (verified in dist-enterprise
— its `onClick` just closes the popup), so nothing needs to be torn down
on the SC side. What's needed are read-only listings and a handful of
imperative methods.

## Design constraints

- The dialog lists three categories: candle (main) chart, user-drawn
  overlays, indicators.
- It must NOT list programmatic overlays — i.e. overlays created by
  consumer code for app-state visualization (Altrady alerts, trade lines,
  order lines, etc.), not by the user via the drawing toolbar.
- Distinguishing the two requires explicit tagging at creation time
  (see "Programmatic flag" below). Heuristics (presence of per-overlay
  `onRightClick`, overlay name lookup, etc.) are unreliable — many
  built-in overlay templates set their own `onRightClick` stubs.
- Per-row controls map directly to SC actions: lock/unlock (overlays),
  hide/show (all), remove (overlays + indicators).
- Clicking a row "selects" the item — same selection state SC's own
  left-click sets, so the drawing toolbar appears for overlays.
  Selecting the candle chart / an indicator is a no-op today on SC's
  side (no toolbar), but the row must still highlight as selected so
  consumers can reflect SC's selection state visually.

## Required additions to `SuperchartApi`

Names negotiable.

### Programmatic flag (createOverlay option)

```ts
// Extension to existing createOverlay options:
sc.createOverlay({
  name: 'segment',
  points: [...],
  // programmatic defaults to true — pass false only for custom drawing
  // tools that should behave as if the user drew the overlay.
})
```

- `programmatic` defaults to `true`. Any overlay reaching SC through
  `sc.createOverlay` is treated as consumer-created (alert, trade line,
  …) unless explicitly opted out. SC's internal drawing-bar call site
  is the only place that passes `programmatic: false`.
- Persisted on `SavedOverlay` via `extendData.__sc_programmatic` so the
  flag survives storage round-trips.
- `listUserOverlays()` filters where `!programmatic`.
- `onUserOverlayRightClick` is gated on `!programmatic` — replaces the
  earlier "consumer-set `onRightClick` wins" precedence with a clean
  explicit signal. Programmatic overlays keep their own per-overlay
  `onRightClick` (if any); user-drawn ones route to
  `onUserOverlayRightClick`. Side benefit: no precedence ambiguity from
  template-level `onRightClick` stubs (timeLine, segment, …).

**Consumer impact:** None for the common case — defaults to programmatic.
Consumers building custom drawing tools (rare) opt in via
`programmatic: false`.

### Listing

```ts
sc.listUserOverlays(): UserOverlayInfo[]
sc.listIndicators(): IndicatorInfo[]

interface UserOverlayInfo {
  id: string
  name: string         // klinecharts overlay type (e.g. 'segment', 'fibonacciLine')
  lock: boolean
  visible: boolean
  paneId: string
}

interface IndicatorInfo {
  id: string           // klinecharts indicator id
  name: string         // 'RSI', 'MA', etc.
  visible: boolean
  paneId: string
}
```

`listUserOverlays` MUST exclude overlays created with `programmatic: true`
(see flag above). Restored overlays inherit the flag from `SavedOverlay`.

### Main-chart visibility

```ts
sc.isMainChartVisible(): boolean
sc.setMainChartVisible(visible: boolean): void
```

### Per-overlay visibility (lock already exists)

```ts
sc.setOverlayVisible(id: string, visible: boolean): void
```

Same `modifyOverlay`-style path as `setOverlayLocked`, so autosave +
persistence stay in sync.

### Indicator actions

```ts
sc.setIndicatorVisible(id: string, visible: boolean): void
sc.removeIndicator(id: string): void   // confirm if not already on SuperchartApi
```

### Selection

```ts
sc.getSelectedOverlayId(): string | null
sc.selectOverlay(id: string): void
sc.selectMainChart(): void
sc.selectIndicator(id: string): void   // may be a no-op visually today; still tracks selection state
sc.clearSelection(): void
sc.onSelectionChange(cb: (sel: Selection) => void): () => void  // returns unsubscribe

type Selection =
  | { kind: 'overlay'; id: string }
  | { kind: 'mainChart' }
  | { kind: 'indicator'; id: string }
  | null
```

`selectOverlay(id)` MUST trigger the same internal selection path SC's own
left-click sets — so the drawing toolbar appears, exactly as if the user
had clicked the overlay on the canvas. This is critical for the
"open-on-right-click and the overlay is already selected" UX (consumer
will call `selectOverlay(id)` right after opening the dialog when the
dialog was triggered from an overlay's context menu).

## Hard requirements

- All actions reuse the same internal paths SC's own UI uses — no
  behavioral drift between the SC-internal flow and the consumer-driven
  flow (autosave timing, modify-overlay semantics, selection state
  propagation, etc.).
- `onSelectionChange` fires for selection changes from ANY source (canvas
  click, consumer call, drawing-end), so the consumer can reflect live
  selection in the dialog.

## Out of scope (SC side)

- The dialog UI itself — consumer renders it.
- "Create group" / overlay grouping — explicitly NOT wanted (matches
  Altrady's PRD).
- Rendering the per-row icon buttons, hover styling, etc. — consumer.
- Indicator left-click selection visuals (no SC toolbar today for
  indicators — `selectIndicator` just tracks state for the dialog).

## Acceptance

- `listUserOverlays()` returns user-drawn overlays only, excludes
  overlays created with `programmatic: true` (including restored ones).
- `onUserOverlayRightClick` fires for user-drawn overlays only;
  programmatic overlays use their own per-overlay `onRightClick` if any.
- Toggling lock / visible via the new methods produces the exact same
  observable state as toggling via SC's own UI today.
- `selectOverlay(id)` causes SC to show the drawing toolbar for that
  overlay, identical to a left-click on the canvas.
- `onSelectionChange` fires once per selection change, with the correct
  `Selection` payload, regardless of trigger source.
- No regression for consumers that don't call any of the new methods.
- Documented on `SuperchartApi` and in
  `$SUPERCHART_DIR/docs/api-reference`.
