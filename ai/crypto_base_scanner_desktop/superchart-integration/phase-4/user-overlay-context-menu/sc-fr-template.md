# SC FR — Per-Overlay Drawing Template: Extract + Apply

**Target:** Superchart
**Consumer:** Altrady — `feature/superchart-integration`
**Related:** `prd.md` (§ "Template ▶"), `sc-feature-request.md` (§2e)

## Summary

Expose two imperative methods on `SuperchartApi` so consumers can render
their own per-overlay "Template" submenu (apply + save-as) instead of SC's
built-in one.

## Context

Altrady has wired `onUserOverlayRightClick` (recently added) and renders
its own context menu. It already owns a `StorageAdapter` implementing
`list/load/save/deleteDrawingTemplate`, so SC does **not** need to expose
template persistence — the consumer reads/writes those directly. What's
missing is the bridge between an existing overlay instance and a
`DrawingTemplate` payload.

## Required methods

Names negotiable.

### `sc.getDrawingTemplate(overlayId: string): { toolName: string; template: DrawingTemplate } | null`

Serializes the overlay's current style/properties into a
`DrawingTemplate`-shaped payload + the `toolName` (the overlay's
registered template name, e.g. `segment`, `fibonacciLine`) — ready to hand
to `StorageAdapter.saveDrawingTemplate(toolName, name, template)`. The
consumer fills in `name` itself (collected from the user).

### `sc.applyDrawingTemplate(overlayId: string, template: DrawingTemplate): void`

Applies a saved template to an existing overlay (mutates style, persists
via autosave). Same code path SC uses when its built-in template submenu
applies a template — please reuse that path so consumer-driven applies
match SC's behavior 1:1 (no drift in which fields are copied, how defaults
are handled, autosave timing, etc.).

## Hard requirement

Both methods MUST use the same internal extract / apply paths SC's own
template menu uses. The consumer's submenu must produce templates
indistinguishable from ones saved via SC's built-in UI, and applying them
must produce identical visual results.

## Out of scope (SC side)

- `list / save / load / delete` of templates — consumer's `StorageAdapter`
  handles all template persistence.
- The submenu UI — consumer renders it.
- The save-as input dialog — consumer renders an Altrady-native modal with
  an input + validation.

## Acceptance

- **Save flow:** right-click overlay → consumer calls
  `getDrawingTemplate(id)` → hands payload to
  `StorageAdapter.saveDrawingTemplate(toolName, name, template)`. Later,
  listing for the same `toolName` returns it; applying it via
  `applyDrawingTemplate(otherOverlayId, template)` matches what SC's
  built-in "save then apply" would have produced.
- **Apply flow:** applying a template SC itself saved (via its built-in
  menu today) through `applyDrawingTemplate` produces the same overlay
  appearance as SC's built-in apply.
- No regression for consumers that don't call either method.
- Documented on `SuperchartApi` and in
  `$SUPERCHART_DIR/docs/api-reference`.
