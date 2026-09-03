# Deferred: tailwindcss 3 → 4 (and removing twin.macro)

**Status:** blocked by twin.macro. Deferred 2026-09-02.
**Prerequisite reading:** `styling-stack.md` — the research, risk audit and
Superchart findings. `babel.md` — the sibling blocker in the same pipeline.

---

## Why it is blocked

`package.json` pins `twin.macro@^3.4.1`, which peers `tailwindcss >=3.3.1` but
has **no Tailwind 4 support**. Tailwind v4 was a rewrite and removed the
internals twin reads. Attempting it fails at compile time:

```
Package subpath './lib/util/toPath' is not defined by "exports"
  in node_modules/tailwindcss/package.json
```

The maintainer recommends migrating away and there is no successor; twin's last
release was 2024-01-19. Details and sources in `styling-stack.md`.

**So this is not a version bump. Tailwind 4 requires removing twin.macro.**

---

## The single most important fact

**Tailwind already runs through PostCSS in this app.**

- `src/tailwind.css` contains `@tailwind base; @tailwind components; @tailwind utilities;`
- `src/index.css` imports it
- `postcss.config.js` runs `tailwindcss` as a PostCSS plugin
- `tailwind.config.js` feeds it

Which means **`className="flex flex-col"` works today**, right now, alongside
twin.macro. Both mechanisms are live and compile from the same config.

The consequence: **the twin removal is incremental, not a big bang.** Migrate
file by file, on Tailwind 3, with both systems working. Each file is
independently testable and shippable. This removes most of the risk.

---

## Scale of the change

Measured on `chore/deps-update-6.0`:

| Pattern | Count | Migration |
| --- | --- | --- |
| `tw="flex flex-col"` | 2374 | → `className="..."` — pure rename |
| `tw={"flex flex-col"}` | 2567 | Sampled: overwhelmingly **static strings in braces**, same rename |
| `css={[ ... ]}` arrays | 2304 | Split classes from real CSS |
| `css={...}` non-array | 125 | Mostly unchanged |
| `&& tw\`…\`` conditionals | 727 | → `clsx("base", cond && "px-2")` |
| grouped variants `x:(a b)` | 188 | **twin-only syntax**, expand to `x:a x:b` |
| `extraCss` prop | 2298 uses, 651 files | The real architectural cost — see below |
| `styled()` / `styled.div` | 8 | Trivial |
| `theme()` / `screen()` | 2 | Trivial |

Roughly **4900 of ~7300 sites are a mechanical rename**, codemoddable with high
confidence.

---

## Migration patterns, from real code in this repo

### 1. `tw` prop → `className`

```jsx
// before — containers/trade/trading-terminal/grid-layout/flex-grid/charts-grid-item.js
<div tw={"flex flex-row my-2"}>
// after
<div className="flex flex-row my-2">
```

### 2. Mixed array → split by kind

```jsx
// before — components/top-bar/push-notifications.js
css={[
  tw`h-full flex flex-col pointer-events-auto bg-widget-background overflow-hidden`,
  css`border: 1px solid var(--border-primary, #303036); border-radius: 16px 0 0 16px;`,
  !inSlider && css`border: none; border-radius: 0;`,
  tw`mobile:(border-0 rounded-none)`,
]}

// after
className={clsx(
  "h-full flex flex-col pointer-events-auto bg-widget-background overflow-hidden",
  "mobile:border-0 mobile:rounded-none",
)}
css={[
  css`border: 1px solid var(--border-primary, #303036); border-radius: 16px 0 0 16px;`,
  !inSlider && css`border: none; border-radius: 0;`,
]}
```

### 3. Grouped variants — twin-only syntax, invalid in plain Tailwind

```
tw`pt-10 desktop:(pt-12)`   →   "pt-10 desktop:pt-12"
tw`mobile:(p-0 w-full relative)`   →   "mobile:p-0 mobile:w-full mobile:relative"
```

188 occurrences. A codemod must expand these; a naive string copy silently drops
the styles.

### 4. `extraCss` component APIs — the genuine cost

```jsx
// before — components/elements/drawer-button.js
css={[
  tw`cursor-pointer flex items-center justify-center min-w-5 bg-transparent`,
  active && tw`bg-button-secondary-active`,
  ...extraCss,
  ...(active ? extraCssActive : []),
]}

// after — the component gains a className prop alongside extraCss
className={clsx(
  "cursor-pointer flex items-center justify-center min-w-5 bg-transparent",
  active && "bg-button-secondary-active",
  className,
  active && classNameActive,
)}
css={[...extraCss, ...(active ? extraCssActive : [])]}
```

**This is the part to scope carefully.** 2298 uses across 651 files, and it is a
change to component *prop contracts*, not just leaf JSX — callers pass CSS
arrays down. Items 1–3 are codemoddable; this one needs judgement per component.

Consider adopting Superchart's `cn()` helper (`clsx` + `tailwind-merge`) rather
than reinventing it — see `styling-stack.md`.

---

## What happens to the config files

### `tailwind.config.js` (520 lines) — survives the twin removal untouched

Today it is read by **both** twin.macro and PostCSS. Afterwards, only PostCSS.
The design tokens, `screens`, the `fontSize` scale and the custom `r-sm`
variant plugin all keep working with no edit. That is what makes the twin
removal safe to do on Tailwind 3 first.

It only changes at the **Tailwind 4** step, which relocates config from JS into
CSS:

| Today (JS) | Tailwind 4 (CSS) |
| --- | --- |
| `theme.extend.colors` — the `var(--…)` design tokens | `@theme { --color-text-primary: var(--text-primary); … }` |
| `darkMode: "class"` | `@custom-variant dark` |
| `plugin(({addVariant, addUtilities}) => …)` — the `r-sm` variant | `@custom-variant` / `@utility`, or keep the JS plugin via `@plugin` |
| `future.hoverOnlyWhenSupported: true` | default behaviour in v4 — delete |
| `content: ["./src/**/*.{js,jsx,ts,tsx,vue}"]` | automatic detection, or explicit `@source` |
| `theme.extend.screens` | `@theme { --breakpoint-… }` |

Superchart has already done exactly this conversion
(`src/design-system/styles/theme.css`) and is a working reference.

### `postcss.config.js` — shrinks

```js
// today
plugins: {"postcss-nested": {}, "tailwindcss/nesting": {}, tailwindcss: {}, autoprefixer: {}}
```

Under Tailwind 4: `tailwindcss/nesting` is gone (native nesting), `autoprefixer`
is built in, `postcss-nested` becomes unnecessary. Left with
`@tailwindcss/postcss` alone.

### `babel-plugin-macros.config.js` — deleted

The only file removed outright. It exists solely to tell twin which preset to
use.

---

## Sequencing

Three independently shippable stages:

1. **Emotion swap** — Babel 8 unblocked. `tailwind.config.js` untouched;
   `babel-plugin-macros.config.js` flips `styled-components` → `emotion`;
   `babel-plugin-styled-components` removed. Syntax unchanged. See `babel.md`.
2. **twin removal** — incremental, file by file, **still on Tailwind 3**.
   Delete `babel-plugin-macros.config.js` at the end. Configs otherwise
   unchanged.
3. **Tailwind 4** — a config migration, with no twin in the way.

Do not attempt 3 before 2. Do 1 first because it is small, independently
valuable, and reversible.

---

## Verifying

Per stage: `yarn test` (baseline 40/55 suites, 354 passing — must not move),
clean dev and production web builds, and **the app run by hand, web and
desktop**. Styling is a compile-time transform here: a wrong pipeline builds
successfully and renders a broken UI, so a green build proves nothing.

For stage 2 specifically, migrate in small batches and compare screenshots
against production — the failure mode is silently missing styles, not errors.
