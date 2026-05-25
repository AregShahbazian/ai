# Altrady prompt — Object Tree integration + `programmatic` flag rollout

**Related:** `sc-fr-object-tree.md`. SC-side now shipped on the
`feature/superchart-integration`-target branch of the Superchart repo.

## What changed on the SC side

### New `createOverlay` option: `programmatic` (default `true`)

```ts
superchart.createOverlay({
  name: 'segment',
  points: [...],
  // programmatic defaults to true — no need to add it for Altrady
  // app-state overlays (alerts, trade lines, etc.)
})
```

Any overlay you create through `superchart.createOverlay` is treated as
consumer-created (alert, trade line, order line, break-even, …) by
default. Pass `programmatic: false` only if you're implementing a custom
drawing tool whose overlays should behave as user-drawings. SC's
built-in drawing bar handles that internally — you almost certainly
don't need to.

The flag is persisted via `extendData.__sc_programmatic` on
`SavedOverlay`, so it survives reloads.

### Behavioral changes gated on `programmatic`

1. **`onUserOverlayRightClick`** — now fires for `!programmatic` overlays
   ONLY. For `programmatic: true` overlays, the per-overlay `onRightClick`
   you pass to `createOverlay({onRightClick})` still wins as before.
   - **This fixes a real bug**: previously, user-drawn overlays whose
     template defined an internal `onRightClick` stub (`segment`,
     `timeLine`, `priceLine`, …) failed to trigger
     `onUserOverlayRightClick`. With the flag in place, that's no longer
     an issue — the gate is the consumer's intent, not handler presence.

2. **`listUserOverlays()`** (new method, below) excludes `programmatic`
   overlays. Until you tag them, Altrady's alerts/trades/order-lines WILL
   appear in the Object Tree.

### New `SuperchartApi` methods

```ts
// Listing (Object Tree)
sc.listUserOverlays(): UserOverlayInfo[]   // {id, name, lock, visible, paneId}
sc.listIndicators():   IndicatorInfo[]     // {id, name, visible, paneId}

// Per-overlay actions (lock already shipped)
sc.setOverlayLocked(id, locked)
sc.setOverlayVisible(id, visible)

// Per-indicator actions
sc.setIndicatorVisible(id, visible)
sc.removeIndicatorById(id)                  // distinct from existing removeIndicator(name)

// Main candle pane visibility — **STUB**: getter returns true, setter no-op.
// Underlying engine has no native hide-candles toggle. Tracked for follow-up;
// render the row as a non-toggleable "visible" indicator for now.
sc.isMainChartVisible():  boolean
sc.setMainChartVisible(visible): void

// Selection (drives drawing toolbar + dialog highlight)
sc.getSelectedOverlayId(): string | null
sc.selectOverlay(id)        // same effect as a canvas left-click — drawing toolbar appears
sc.selectMainChart()        // tracked-only (no visual today)
sc.selectIndicator(id)      // tracked-only (no visual today)
sc.clearSelection()
sc.onSelectionChange(cb: (sel: Selection) => void): () => void

type Selection =
  | { kind: 'overlay'; id: string }
  | { kind: 'mainChart' }
  | { kind: 'indicator'; id: string }
  | null
```

All actions reuse the same internal paths SC's own UI uses
(`modifyOverlay`, `overrideIndicator`, the indicator-tooltip close path,
canvas-click selection). No behavioral drift vs. equivalent in-canvas
interactions.

## What Altrady needs to change

### Step 1 — Build the Object Tree dialog

Driven entirely by `listUserOverlays()`, `listIndicators()`,
`onSelectionChange()`. Per-row controls call the matching imperative
methods. Right-click "Object Tree" menu entry in your already-rendered
context menu opens the dialog.

### Step 2 — Verify

1. Right-click a user-drawn segment → `onUserOverlayRightClick` fires
   reliably (no more "template stub swallows the event" issue).
2. Right-click an Altrady alert → per-overlay `onRightClick` still wins
   (programmatic-by-default keeps the existing alert behavior intact).
3. Object Tree dialog: lists user-drawn overlays + indicators only. No
   alerts/trades/order-lines appear — Altrady programmatic overlays are
   excluded by default.
4. Click an overlay row → SC drawing toolbar appears for that overlay.
5. Lock/hide/remove from a row → state matches SC's own UI.

## Known gap

**Main candle pane visibility** is a no-op stub on SC for now (engine
has no native toggle). Render the "Main chart" row in the Object Tree as
non-interactive (or hide the visibility icon). File a follow-up if
needed.
