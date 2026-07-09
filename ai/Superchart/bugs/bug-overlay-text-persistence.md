# Bug: overlay text / table / image not persisted across reload

**Repo:** Superchart (SC lib + `packages/coinray-chart` engine submodule)
**Reported:** 2026-07-09 (Areg, from Altrady drawing-tools QA)
**Status:** FIXED (uncommitted, pending user test)

## Symptoms (as reported)

- **`text`** — not persisted; gone after reload. (HUD "drawings" count still
  includes it while on-canvas.)
- **`note`, `callout`, `comment`, `priceNote`, `signpost`** — geometry
  persists, but the typed text is lost after reload.
- **`pin`** — custom text IS persisted, shows on hover.
- **`table`** — persistence "forgets" the last change: edit cell A then cell B,
  only A survives reload.
- **`image`** — survives reload. (User asked where the image is stored — answer
  below; user does NOT need image upload, was just curious.)

## Root cause (one unifying bug)

Persistence only flows through `syncOverlay()`
(`src/lib/hooks/useChartState.ts:455-470`), which snapshots `overlay.extendData`
via `overlayToSaved()` (`:33-60`) into `ChartState.overlays`.

In `pushOverlay()`'s `chartInstance.overrideOverlay({...})`
(`useChartState.ts:717-787`), `syncOverlay` is wired to **only** `onDrawEnd`
and `onPressedMoveEnd` — **there is no commit-time save hook for text edits or
property changes.**

All text-family overlays store their text in `extendData` and update it live on
the engine's `onTextChange` (per-template handlers, e.g.
`packages/coinray-chart/src/extension/overlay/text.ts:118-121`), but that
mutation never reaches the StorageAdapter.

- **`text` looks fully gone** (vs. others) because it renders ONLY the text
  figure — no line/box/dot — so a stale-empty snapshot draws nothing.
- **`pin` is NOT special** — identical code. It only "works" because pins get
  dragged into place after typing; the drag fires `onPressedMoveEnd` → sync,
  incidentally capturing the typed text.
- **`table`** = same bug, off-by-one: clicking cell B fires a press that flushes
  A's finished text (what persists); typing into B updates memory only, and no
  press follows → B never flushed. Secondary bug: `overrideOverlay` **clobbers**
  table's own `onPressedMoveEnd` (`table.ts:768-771`, drag-stash cleanup) instead
  of chaining it.
- **`image`** = base64 data URL in `extendData.src`, no server upload; read
  client-side via `FileReader.readAsDataURL` (1.5 MB cap,
  `src/lib/widget/image-upload-modal/index.tsx:77-87`), persisted inside the
  whole-`ChartState` JSON blob by the StorageAdapter (localStorage by default).
  Separate bug: `modifyOverlayProperties` (`useChartState.ts:882-980`) persists
  the upload into `SavedOverlay.properties`, but standard overlays restore from
  `SavedOverlay.extendData` (`:1120-1142`) → uploading + reload without a
  subsequent resize-drag can silently lose the image.

Note: editing text via the **settings-panel Text tab** already persists (a
different path, `modifyOverlayProperties`). Only **inline click-and-type on
canvas** is broken.

## Fixes (all four)

1. **Engine** (`packages/coinray-chart`) — add a `committed` flag to
   `OverlayTextChangeEvent`, set `true` only from `_stopTextEdit(true)`
   (blur/Escape commit, `OverlayView.ts:344-357`), `false` on the per-keystroke
   `onInput` path (`OverlayView.ts:517-523`).
2. **`pushOverlay`** (`src/lib/hooks/useChartState.ts`) — wire the committed
   `onTextChange` → `syncOverlay(...)`, gated like the others (skip `measure`),
   chaining the template's own handler (don't clobber). Fixes ALL text-family
   overlays + the table lost-edit in one place.
3. **`onPressedMoveEnd`** — chain the template's original handler instead of
   overwriting it (restores table drag-stash cleanup).
4. **Image / property persistence** — make `modifyOverlayProperties` persist
   `extendData` updates into `SavedOverlay.extendData` for standard overlays, so
   an upload (and any extendData-routed property edit) survives reload without a
   drag.

## Implementation (2026-07-09)

All four fixes applied; engine `npm run build`, app `tsc`, storybook `tsc`, and
eslint on touched files all clean.

1. **Engine — `committed` flag.** Added `committed: boolean` to
   `OverlayTextChangeEvent` (`packages/coinray-chart/src/component/Overlay.ts`).
   Set `true` in `_stopTextEdit(true)` (blur commit) and `false` in the
   per-keystroke `onInput` path (`packages/coinray-chart/src/view/OverlayView.ts`).
   Note: Escape uses `_stopTextEdit(false)` = cancel (no persist), by design.
2. **`pushOverlay` — persist on text commit.** Captured the template's own
   `onTextChange`/`onPressedMoveEnd` before `overrideOverlay` (which replaces,
   not merges, functions), then wrapped `onTextChange` to chain the template
   hook and call `syncOverlay` only when `event.committed`
   (`src/lib/hooks/useChartState.ts`, in the `overrideOverlay` call ~line 726/
   751). `syncOverlay` snapshots the WHOLE `extendData`, so one commit-on-blur
   flushes every table cell (each written live via `onInput`).
3. **`onPressedMoveEnd` — chain not clobber.** The wrapper now calls the
   captured `enginePressedMoveEndHook` first, restoring the table's drag-stash
   cleanup.
4. **`modifyOverlayProperties` — persist extendData.** Step-3 storage write now
   also merges `EXTEND_DATA_PROPERTY_KEYS` into `SavedOverlay.extendData` (not
   just `.properties`), so settings-panel text edits and image uploads survive
   reload for standard overlays without needing a subsequent drag.

**Cross-repo note:** the `committed` field is a public change to
`OverlayTextChangeEvent` in the engine; it's re-exported through
`src/lib/index.ts` already (the type is bundled). Engine dist must be rebuilt
(`npm run build` in `packages/coinray-chart`) for `src/lib` to typecheck.

**Test manually** in the Persistence story (`Examples/API/Persistence`, drawing
bar + Drawings HUD): draw a note/callout/comment/priceNote/signpost/text/pin,
type text, click away, Ctrl+R → text restored. Table: edit two cells, click
outside the table, reload → both cells restored. Image: upload, reload without
resizing → image restored.

## Follow-up: dot / arrow (same family) + cursor-group icons (2026-07-09)

**dot (`circle`) and arrow inline text still lost** after the four fixes.
Different sub-cause: `arrow.ts` / `circle.ts` are ProOverlays that read `text`
from the closure `properties` Map (`props.text`) and render an `editableText`
figure, but define **no `onTextChange` handler at all** — inline edits were
never captured. And even if captured into the Map, `syncOverlay` doesn't read
the ProOverlay Map (only live `extendData`). Fix: mirror `text.ts` — read text
from `overlay.extendData` and add an `onTextChange` that writes it there
(`packages/coinray-chart/src/extension/overlay/{arrow,circle}.ts`). Now the
committed-text sync from fix #2 persists it, and restore reads it back.

**Cursor-group icons didn't fit the tools**
(`src/lib/widget/drawing-bar/icons/`):
- cursor showed a star → now the mouse-pointer (`cursor: arrowMarker`).
- arrow showed the mouse-pointer → now a real arrow (`iconKey: 'arrow'` →
  `lineToolArrow`).
- brush showed a nib-in-ring → now a pencil (new `pencil.tsx`, Material edit
  glyph). Applied to both brush entries (cursor + trendline groups).

## Progress log

- Investigation complete — root cause confirmed by two SC-source agents.
- All four fixes implemented + typecheck/lint clean; committed
  (submodule `101e2af7`, lib `81869b5`).
- Measure-armed highlight: `e686f26`.
- dot/arrow inline text + cursor-group icons: implemented, engine rebuilt,
  typecheck/lint clean; left uncommitted for user test.
