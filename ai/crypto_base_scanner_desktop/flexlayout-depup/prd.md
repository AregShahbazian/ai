---
id: fl-depup
---

# FlexLayout 0.7.15 → 0.9.0 upgrade — PRD

## Goals

Three deliverables, in order:

1. **Upgrade** `flexlayout-react` from `0.7.15` to `0.9.0` (the version pinned
   in `package.json`).
2. **Refactor and adapt** Altrady's FlexLayout integration so that **every
   piece of current behaviour and every visual detail is preserved** — the
   trading terminal grid, the `/charts` page grid, custom tabset chrome,
   border behaviour, drag handles, ghost tabs, splitter look, sidebar icons,
   bottom drawer, layout locking, persisted layouts, all CSS overrides.
3. **Adopt newer FlexLayout features where they replace or simplify Altrady's
   tweaks.** Concrete candidates (to be evaluated, not committed):
   - `onContextMenu`, `onAuxMouseClick`, `onShowOverflowMenu` instead of
     hand-rolled handling on top of the layout DOM.
   - `onTabSetPlaceHolder` for empty-state rendering.
   - `onRenderTabSet`'s `leading` slot (added in 0.8.15) and
     `overflowPosition` (added in 0.7.11) instead of CSS workarounds.
   - The new floating panels (`type: "float"`) where popout windows are
     painful (no `popout.html`, no resize-observer issues).
   - Native HTML5 drag-and-drop instead of the bespoke
     `moveTabWithDragAndDrop(node, dragText)` invocation from
     `mousedown`/`touchstart`.
   - CSS variables (`--splitter-size`, `--font-size`, etc.) instead of
     model-attribute writes.

The user has tried this upgrade manually before and got lost in cascading
errors. **The point of this PRD is to define the feedback loop between
assistant and user**, not to enumerate the per-feature behavioural
requirements (those are simply: "everything that works today must still
work").

## Why a feedback-loop PRD

The assistant cannot:

- See the running UI.
- Run the dev server output beyond what's already wired through tooling.
- Verify drag/drop, hover, animations, focus, scroll, mobile gestures.
- Tell which of two pixel-similar styles is the intended one.
- Notice regressions in features it didn't change.

The user can:

- Take screenshots and pair them with a URL/route, viewport, and theme.
- Paste console errors and warnings.
- Run console commands (e.g. inspect `model.toJson()`, dump CSS variables,
  count tab nodes) and paste output.
- Reproduce specific gestures (drag a chart cell into the right border, etc.).
- Confirm or reject "this looks the same as before."

So the only realistic shape for this work is: small change → user verifies →
correct or proceed.

## Process / requirements

### R1. Baseline capture

Verification surfaces are **the trading terminal** and **the `/charts`
page**. Within each increment, **verify on `/charts` first** — it's
closer to stock FlexLayout (no border-right drawer, no bottom drawer,
no ghost tabs, no sidebar icons, fewer CSS overrides). Then verify on
the trading terminal, which carries most of the bespoke tweaks.

This ordering is a diagnostic shortcut: if a generic FlexLayout API
change broke things, both surfaces show it; if only the trading terminal
breaks, the cause is one of Altrady's tweaks. Don't move past `/charts`
verification until that surface is clean.

Before any code change, the assistant **asks for a baseline screenshot set**
of the current `0.7.15` UI. The user provides screenshots of, at minimum:

- Trading terminal grid (default layout) — desktop width.
- `/charts` page (1-chart and multi-chart layouts).
- Right border / drawer (collapsed and expanded).
- Bottom drawer (collapsed and expanded).
- ~~Tab overflow popup.~~ Confirmed N/A — Altrady's layout doesn't expose the overflow popup (suppressed by CSS or never triggered by `tabSetMinWidth:280`).
- A drag-in-progress shot for chart-cell reorder via `MarketHeaderBar`
  (`/charts` page).
- A drag-in-progress shot for a normal tab (trading terminal).
- The **center ghost tab** state on the trading terminal — a tweak that
  keeps a placeholder tab in the center tabset (`#center_ghost_tab`,
  defined in `src/models/flex-layout/default-layouts.js`) so the row /
  tabset isn't deleted when the user drags out the last real tab. Capture
  what this looks like with all real center tabs removed; pair with
  `getTradingLayoutsController().model.toJson()` so the JSON shape of the
  lone ghost tab is recorded. Same applies to the bottom-drawer ghost tab
  (`#bottom_drawer_ghost_tab`) if its visual differs.

These become the "looks-correct" reference set. They live as user-attached
images; we do not commit them. The assistant treats them as truth — if the
post-upgrade UI deviates from any of these, that's a regression to fix.

### R2. Increments

Work proceeds in **small commits**, each landing under the `fl-depup` tag,
each one with one verifiable user-facing effect. Suggested ordering:

1. Upgrade `flexlayout-react` to `0.9.0` in `package.json` and reinstall.
2. Make the codebase **compile** — fix imports, remove
   `addTabWithDragAndDropIndirect`, `titleFactory`, `iconFactory`, etc.,
   resolve removed/renamed CLASSES references. Acceptable to render with
   visual regressions at this stage.
3. Make the trading terminal **load without runtime errors** — fix
   `Layout` ref typing, `setOnAllowDrop` wiring, `Actions.*` usage.
4. Restore visual parity — splitter, tabset chrome, borders, ghost tabs
   (both `#bottom_drawer_ghost_tab` and `#center_ghost_tab`), sidebar
   icons, drawer animations. The center ghost tab is a tweak that keeps
   the row/tabset alive when the user drags out the last real tab; its
   "alone in tabset" visual must match the baseline. (0.9.0's
   `onTabSetPlaceHolder` is a candidate replacement evaluated in goal 3 —
   not adopted in this increment unless trivially equivalent.)
5. Restore drag-and-drop — both default tab drag and the `/charts`
   `MarketHeaderBar` programmatic drag (now via HTML5 `dragstart`).
6. Restore the dynamic splitter-size logic (now via CSS variable update).
7. Restore the layout-locking logic (`tabEnableDrag`/`tabSetEnableDrag`).
8. Restore persisted layout migration (handle `popouts` → `subLayouts`
   silently, and any global-attribute renames).
9. Confirm border-right wheel-scroll relay still works.
10. Confirm overflow menu rendering / `_glass` overlay workaround is still
    needed; remove if obsolete.

The assistant **does not move past one increment until the user confirms**
the previous one looks/behaves correct or has logged an issue to come back
to.

### R3. Feedback loop, per increment

For each increment the assistant:

1. States **what it's about to change and what to verify visually**.
2. Applies the code change.
3. Tells the user the **route to load**, the **gesture/action to perform**,
   and what to look for.
4. Asks for one of:
   - Screenshot at a specific URL/state (`/trade/...`, `/charts`, drawer
     open, layout locked, etc.).
   - Console output of a specific command (e.g.
     `console.log(Object.keys(getComputedStyle(document.querySelector(".flexlayout__layout"))).filter(k => k.startsWith("--")))` —
     dumping CSS variables; `model.toJson()` from a memoised global; etc.).
   - Any console errors/warnings since the previous increment.
5. Reads the user's response, decides:
   - **Pass** — mark increment done, move on.
   - **Visual diff** — propose a CSS/markup fix, repeat from step 2.
   - **Runtime error** — diagnose using the supplied logs, propose a fix,
     repeat from step 2.
   - **Behavioural diff** — ask for a more specific repro (route, gesture,
     before/after screenshot pair) before changing anything.

The assistant **never claims an increment passes on its own**. The user
confirms or supplies counter-evidence.

### R4. What the user can supply

For the assistant to plan around, the user has these affordances:

- **Visual checks** — "this matches the baseline" / "this differs in X".
- **Console errors / warnings** — pasted as text.
- **Console-command output** — the assistant proposes a specific
  command, the user runs it, the user pastes the output.
- **Screenshots** with route, viewport size, theme, and a one-line caption
  describing what's being demonstrated.
- **Screenshot + console pairing** — for race-y issues, a screenshot taken
  at a moment matched with the console output captured in the same window.
- **Layout-state ↔ screenshot pairing** — the user can dump the current
  `model.toJson()` (or the persisted-layout entry) and pair it with a
  screenshot of how that layout actually renders. This is the only way
  the assistant gets to see how the JSON globals/borders/tabset weights
  map to the on-screen pixels for a given default or custom layout.
  Especially valuable for: the trading-terminal default layout, the
  `/charts` 1-/multi-chart layouts, custom user-saved layouts, and any
  edge-case JSON the assistant proposes generating.
- **Generated HTML (devtools-inspector copy)** — for any rendering issue
  the user can right-click the affected element in devtools, "Copy →
  Copy outerHTML", and paste it. The assistant then knows exactly which
  classes, inline styles, and child structure FlexLayout produced under
  0.9.0, without having to guess from CHANGELOG diffs. Ideal for
  CSS-override fixes (which class to target after a rename) and for
  ghost-tab / drag-rect / overflow-popup bugs.

### R4a. Recommended pairings, by symptom

These are the assistant's go-to asks, so the user can pre-empt the loop:

| Symptom                           | What to send                                                              |
| --------------------------------- | ------------------------------------------------------------------------- |
| "Layout looks wrong"              | Screenshot **+** `JSON.stringify(model.toJson(), null, 2)` from console.  |
| "A specific element looks wrong"  | Screenshot **+** outerHTML of that element from devtools.                 |
| "Drag preview is off"             | Screenshot of drag in progress **+** outerHTML of `.flexlayout__drag_rect`. |
| "Overflow / popup misbehaves"     | Screenshot **+** outerHTML of `.flexlayout__popup_menu_container`.        |
| "Ghost tab leaks"                 | outerHTML of the offending `.flexlayout__tab_button` / `__border_button`. |
| "Splitter is wrong size"          | Computed value of `--splitter-size` from `getComputedStyle(layoutEl)`.    |
| "A custom layout doesn't render"  | Persisted-layout JSON **+** screenshot of how it rendered on 0.7.15.      |
| Runtime error                     | Stack trace + the route and gesture that triggered it.                    |

The assistant will name the specific item it needs in each round; the
table is just so the user knows the menu in advance.

### R5. What the assistant must do at every step

- Be explicit about the route, viewport, and gesture being asked about. No
  "does it work?" — always "load `/trade/binance`, drag tab X onto the
  right border at the top edge, screenshot the moment the drop indicator
  appears."
- Keep changes scoped to the increment. No drive-by refactors.
- After every code change in an increment, re-state which baseline shot the
  user should compare against.
- Never delete or rename Altrady tweaks (custom CSS, ghost tabs, drag
  handles, controllers) without showing the user the new equivalent and
  getting confirmation.
- Tag every commit `[fl-depup]`.

### R6. Documentation outputs

By the end of the upgrade:

- `~/ai/crypto_base_scanner_desktop/flexlayout-depup/` contains: this
  PRD, the migration guide, an eventual `design.md` describing the
  integration architecture under 0.9.0, `tasks.md` covering the per-file
  changes, `review.md` capturing each round.
- `~/ai/crypto_base_scanner_desktop/deps/FLEXLAYOUT_API_LATEST.md` is the
  reference for the new API; it is updated if the upgrade surfaces something
  not yet documented there.
- The old `deps/FLEXLAYOUT_API.md` (0.7.15) is **not deleted** until the
  upgrade ships, so we have both versions for reference during the work.

## Non-requirements (explicit scope boundaries)

- **No new features** beyond what 0.9.0 ships with. We are not redesigning
  the trading-terminal grid, not changing default layouts, not changing
  persisted-layout shape beyond what 0.9.0's own migration does, not
  adopting popout windows where Altrady currently doesn't use them.
- **No build-system upgrade.** Altrady stays on its current webpack /
  React 18 / styled-components / twin.macro / scss stack. The
  flexlayout-react upgrade does not pull along React 19 or anything else.
- **No public-API changes to Altrady's controllers** unless required by the
  FlexLayout API change. `TradingLayoutsController`, `ChartLayoutsController`,
  `FlexLayoutsController` keep their public surface; their internals adapt.
- **No mobile-only tweaks.** The recent fix `6d23166130 fix: enable
  touch-drag on /charts MarketHeaderBar` defines the desired mobile drag
  behaviour; we just preserve it.
- **No theme switch.** Altrady stays on `flexlayout-react/style/dark.css`;
  evaluating `combined.css` and dynamic theme switching is out of scope.
- **No new persistence migrations** beyond what 0.9.0's own JSON migration
  forces (`popouts` → `subLayouts`).

## Success criteria

The upgrade is done when:

1. `package.json` pins `flexlayout-react: ^0.9.0`.
2. The app builds and starts without FlexLayout-related errors.
3. The user has compared each baseline screenshot against the
   post-upgrade build and signed off that the layout looks the same (modulo
   any deltas the user explicitly accepts as improvements).
4. All Altrady-specific behaviours from `R2` are restored: trading
   terminal layout, `/charts` layout, drawers, drag handles, ghost tabs,
   sidebar icons, layout locking, splitter sizing, persisted-layout load
   for both new layouts and migrated 0.7.15 layouts.
5. No unresolved FlexLayout-related console errors or warnings on any of
   the baseline routes.
6. Any code that 0.9.0 made obsolete (e.g. the `_glass` z-index 998 SCSS
   hack) is removed only after the user has confirmed it's no longer
   needed; otherwise it stays.
