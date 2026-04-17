# Bases Overlay — Bug Fixes

## Round 1: Initial Review (2026-03-13)

### Bug 1: Box fill color for uncracked bases is black-ish

**Root cause:** `createBaseBox` appends `"33"` (hex alpha) to the color string via `color + "33"`. This assumes the color is a 6-digit hex like `#8B8D92`. If `chartColors` returns a color in another format (e.g., `rgb(...)`, `rgba(...)`, or a named color), the concatenation produces an invalid CSS color that renders as black.

Additionally, `"33"` hardcodes a visual detail (20% opacity) in the controller. The controller should be a generic wrapper; visual decisions belong in the caller.

**Fix:**
1. `createBaseBox` accepts `backgroundColor` directly (no alpha append).
2. `drawSelectedBase` creates the background color using a proper `rgba()` conversion helper.

**Files:** `chart-controller.js`, `overlays/bases.js`

---

### Bug 2 (question): Why `color + "33"` in chart-controller.js?

`"33"` is the hex representation of ~20% opacity (0x33 = 51, 51/255 ≈ 0.2). Appended to a 6-digit hex color like `#FF0000`, it creates `#FF000033` — an 8-digit RRGGBBAA color with 20% alpha. This hardcodes a visual constant in the controller. Moved to the caller.

---

### Bug 3: Previously selected base drawn too far right when switching selection

**Root cause:** The filter effect (line 128) excludes the selected base from `filteredBases`. This changes the `nextBase` calculation for surrounding bases.

Example: bases A, B, C sorted by `formedAt`. Select B → `filteredBases = [A, C]`. A's `nextBase` is C, so A's line extends to `C.formedAt` instead of `B.formedAt`. A appears "too far to the right".

The TradingView version keeps the selected base in the iteration list but skips drawing it as a regular base (line 87 of `bases.js`):
```js
if (base.id !== selectedBase?.id) {
  shapes.current.push(...chartFunctions.drawBaseLine(filteredBases[index], nextTime))
}
```

This preserves the selected base's contribution to `nextBase` for the previous base.

The "box enabled looks correct" observation: with the box visible, the filled area visually bridges the gap, masking the off-by-one base in the `nextBase` calculation.

**Fix:** Don't exclude the selected base from `filteredBases`. Skip drawing it as a regular base during the draw iteration instead (matching the TV pattern).

**Files:** `overlays/bases.js`

---

### Summary of changes

**`chart-controller.js`:**
1. `createBaseBox` signature: accept `backgroundColor` instead of `color` + hardcoded alpha

**`overlays/bases.js`:**
2. Add `hexToRgba(hex, alpha)` helper
3. `drawSelectedBase`: pass full `rgba()` background color to `createBaseBox`
4. Remove selected base exclusion from filter effect (line 128)
5. Skip selected base during draw iteration (match TV pattern)

### Verification
- [ ] Box fill for uncracked bases is gray (not black)
- [ ] Box fill for cracked/respected bases has correct color at 20% opacity
- [x] Switching selected base: previous base draws correct length
- [x] With box disabled: same correct behavior
- [ ] Selected base is always drawn regardless of filters

---

## Round 2: Box color still black (2026-03-13)

### Bug 1 (continued): Box fill still black-ish

**Root cause:** Round 1 added `hexToRgba(hex, alpha)` which assumes a hex input (`hex.slice(1, 3)`). But `chartColors` can be in `rgba()` format — user's custom colors are stored as e.g. `rgba(58,104,209,1)`. Parsing `"gba(58,104,209,1)".slice(1,3)` → `"gb"` → `parseInt("gb", 16)` → `NaN`.

**Fix:** Replace custom `hexToRgba` with existing `util.rgba2hex` + `util.hex2rgba`:
```js
util.hex2rgba(util.rgba2hex(color), 0.2)
```
- `util.rgba2hex(color)` normalizes any format (hex or rgba) to hex
- `util.hex2rgba(hex, 0.2)` converts hex to `rgba(r,g,b,0.2)`

**Files:** `overlays/bases.js`

### Bug 3: Fixed
Confirmed by user.

### Verification
- [ ] Box fill correct for custom rgba colors
- [ ] Box fill correct for default hex theme colors
- [x] Switching selected base: previous base draws correct length
