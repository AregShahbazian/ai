# SC FR — Restore path clobbers `__sc_programmatic`

**Target:** Superchart
**Consumer:** Altrady — `feature/superchart-integration`
**Related:** `sc-fr-object-tree.md` (introduces `programmatic` flag),
`altrady-prompt-object-tree.md`

## Symptom

Every restored overlay — including ones the user originally drew via SC's
drawing toolbar — ends up with `extendData.__sc_programmatic === true`.
Consequence: `listUserOverlays()` returns `[]` after reload; the Object
Tree dialog appears empty even though user-drawn overlays are visible on
the chart.

Confirmed from a live session (Altrady console logs):

```
[OTREE-DBG 1/3] right-click overlay: {"id":"overlay_1779798158690_1","name":"horizontalStraightLine","programmatic":true,"extendDataKeys":["__sc_programmatic"]}
[OTREE-DBG 2/3] listUserOverlays: []
[OTREE-DBG 3/3] ALL overlays via klinecharts: [
  {"id":"overlay_1779798177681_1","name":"styledSegment","programmatic":true},
  {"id":"overlay_1779201067763_1","name":"horizontalStraightLine","programmatic":true},
  {"id":"overlay_1779798177681_2","name":"box","programmatic":true},
  {"id":"overlay_1779720775658_1","name":"brush","programmatic":true},
  ...
]
```

`styledSegment`, `brush`, `horizontalStraightLine` — all user-drawn. All
flagged programmatic on restore.

## Root cause

`createOverlay` (in `useChartState.ts`) is also the wrapper SC's restore
path goes through. Current logic:

```ts
const { save, properties, programmatic: lt, ...rest } = J
lt !== false && (rest.extendData = {
  ...rest.extendData,
  __sc_programmatic: true,
})
```

For restored overlays, the persisted record (`J`) has no top-level
`programmatic` field — it's a create-time-only option that gets baked
into `extendData.__sc_programmatic` and persisted there. So at restore
time, `lt` is `undefined` → `lt !== false` is `true` → the wrapper
overwrites `rest.extendData.__sc_programmatic` to `true`, clobbering the
`false` that was correctly stored when the user originally drew the
overlay.

Net effect: the `programmatic` flag is effectively write-once-then-lost
on the first reload.

## Fix options

Either is acceptable on the SC side — consumer doesn't care which:

### Option A — Honor `extendData.__sc_programmatic` if already present

```ts
const { save, properties, programmatic: lt, ...rest } = J
const persistedFlag = rest.extendData?.__sc_programmatic
const programmatic = lt ?? persistedFlag ?? true   // default true for new
if (programmatic !== false) {
  rest.extendData = { ...rest.extendData, __sc_programmatic: true }
} else {
  // ensure explicit false survives (don't drop it from extendData)
  rest.extendData = { ...rest.extendData, __sc_programmatic: false }
}
```

### Option B — Restore path passes `programmatic` explicitly

When SC's restore code reconstructs an overlay from `SavedOverlay`, read
`saved.extendData?.__sc_programmatic` and pass it as the top-level
`programmatic` option to `createOverlay`. The wrapper then sees `lt`
correctly and the existing `lt !== false` guard does the right thing.

Option B keeps the createOverlay wrapper unchanged; Option A keeps the
restore path unchanged. Pick whichever is cleaner in your code.

## Acceptance

- After reload, overlays the user originally drew via the drawing
  toolbar have `extendData.__sc_programmatic === false`.
- `listUserOverlays()` returns those overlays after reload.
- Programmatic overlays (consumer-created via `sc.createOverlay({...})`
  with default flag, or explicit `programmatic: true`) stay
  `__sc_programmatic: true` across reloads.
- No regression for newly drawn overlays (already correct today).
- `onUserOverlayRightClick` fires for restored user-drawn overlays
  (currently never fires — they look programmatic on restore).

## Out of scope

- Migration of persisted records saved BEFORE the `programmatic` flag
  shipped. If any such records exist they will have no
  `__sc_programmatic` at all — pure absence. Treat absence as the
  default-for-new-overlays (`true`) per the existing rules; consumers can
  re-draw if they need those records reclassified. (No need to back-fill;
  rolling forward is fine.)

## Repro

1. Draw any overlay via SC's drawing toolbar (e.g. horizontal straight
   line).
2. Reload the page — the overlay restores and renders.
3. Call `sc.listUserOverlays()` → returns `[]`.
4. Read `chart.getOverlays()[0].extendData.__sc_programmatic` → `true`,
   when it should be `false`.
