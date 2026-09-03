# Deferred: @babel/core 7 → 8

**Status:** deferred 2026-09-02, but **solved** — a working path was found and
verified the same day. See "The fix for blocker 2".
**Related:** `styling-stack.md` (research and risk audit), `tailwind.md` (the
sibling blocker in the same pipeline).
**Affects:** `@babel/core`, `@babel/plugin-transform-modules-commonjs`,
`@babel/plugin-transform-react-jsx` — all held at `^7.x`.

---

## Blocker 1: babel-preset-react-app (solved)

`babel.config.js` uses the `react-app` preset:

```js
presets: ["react-app"]
```

`babel-preset-react-app@10.1.0` — the latest, published February 2025 — still
declares `"@babel/core": "^7.16.0"`. With Babel 8 installed the build fails
outright, before bundling:

```
ERROR in ./src/index.js
Error: [BABEL] Requires Babel "^7.0.0-0", but was loaded with "8.0.1".
  (While processing: "node_modules/babel-preset-react-app/index.js$0")
```

The preset shipped with Create React App, which is retired. It will not gain
Babel 8 support, so the preset has to go.

**This part works.** The replacement config below was implemented and verified:
jest went from 55/55 suites failing to 39 passing, and the config needed only
one correction against the plan — Babel 8 removed `useBuiltIns` from
`preset-react` (it now transforms JSX spread to object spread natively), so that
option must be omitted.

---

## Blocker 2: babel-plugin-styled-components (solved by switching to Emotion)

With the preset gone, the build failed 26 times with:

```
TypeError: t.jSXIdentifier is not a function
  at babel-plugin-styled-components/lib/visitors/transpileCssProp.js:107
  at PluginPass.JSXAttribute (babel-plugin-styled-components/lib/index.js:25)
```

`babel-plugin-styled-components@2.3.0` — the latest, published May 2026 —
declares `"@babel/core": "^7.0.0"` and calls `t.jSXIdentifier`, one of the
lowercase-first-letter builder aliases Babel 8 removed. No newer version exists
and no dist-tag (`next`, `experimental`, `test`) carries Babel 8 support; they
are all older 1.x/2.0 prereleases.

The failing visitor is the **`css` prop transpiler**, which is load-bearing
here: the codebase has **2432 `css` props and 4943 `tw` props**, and
`twin.macro` compiles every `tw` down to a `css` prop that this plugin then
transpiles. Disabling it via the plugin's `cssProp: false` option would build
successfully and produce an unstyled application.

---

## The fix for blocker 2: switch to Emotion

**Verified by experiment on 2026-09-02** — not inferred. Full write-up in
`styling-stack.md`; the short version:

Emotion's `css` prop is enabled through `@babel/preset-react`'s `importSource`
option (the automatic JSX runtime) and needs **no Emotion Babel plugin**. So
`babel-plugin-styled-components` — the sole remaining Babel 8 blocker —
simply goes away.

Built a throwaway project on `@babel/core@8.0.1` with `babel-plugin-macros`,
`twin.macro` and `tailwindcss@3.4.19`, and compiled:

```jsx
import tw, {css} from "twin.macro"
const A = () => <div css={[tw`flex items-center`, css`position:relative;`]} tw="p-4" />
```

with:

```js
presets: [["@babel/preset-react", {runtime: "automatic", importSource: "@emotion/react"}]],
plugins: ["babel-plugin-macros"],
```

Output was correct under Babel 8:

```js
import { css as _css } from "@emotion/react";
import { jsxDEV as _jsxDEV } from "@emotion/react/jsx-dev-runtime";
const A = () => _jsxDEV("div", {
  css: [{ "display": "flex", "alignItems": "center" }, _css`position:relative;`, { "padding": "1rem" }]
}, void 0, false);
```

Note `@emotion/babel-plugin` **is** a runtime dependency of `@emotion/react` and
will appear in `node_modules` — but it is only `require`d by
`@emotion/react/macro`, which this approach does not use. It was installed
throughout the experiment and never executed.

### What this step involves

- Swap `styled-components` → `@emotion/react` (+ `@emotion/styled` for the 8
  `styled()` call sites)
- `babel-plugin-macros.config.js`: preset `"styled-components"` → `"emotion"`
- Remove `babel-plugin-styled-components`
- Add `importSource: "@emotion/react"` to `preset-react`, which requires
  `runtime: "automatic"` — note this overrides the "keep classic" advice above,
  and is the one deliberate behaviour change in this step

**twin.macro stays. Tailwind stays on 3. The
`css={[tw`…`, css`…`]}` and `tw="…"` syntax is unchanged.** The same experiment
confirmed `babel-plugin-macros` itself works under Babel 8, which is what makes
this possible.

### Caveat worth knowing

Emotion is rated **ACCEPTABLE, not SAFE** — it is under-staffed (309 open
issues, 1 maintainer PR since Jan 2025) though not in declared maintenance
mode. The mitigating argument is that this approach depends only on Emotion's
*runtime*, not its Babel tooling, which is a much smaller and more swappable
surface than the abandoned macro it replaces. Full audit, alternatives
considered, and concrete watch-triggers in `styling-stack.md`.

### Sequencing

Do this **first**, before the twin.macro removal and Tailwind 4. It is small,
independently valuable, independently testable, and reversible. See
`tailwind.md` for stages 2 and 3.

---

## What the preset is actually doing today

Read from `node_modules/babel-preset-react-app/create.js` rather than assumed.
This matters: the replacement has to match it, or output changes silently.

| Setting | Actual value here | Why |
| --- | --- | --- |
| `preset-env` targets | **none** | The preset sets no `targets` for dev/production; it defers to `browserslist`, and `package.json` has no `browserslist` key. |
| `preset-env` targets (test) | `node: "current"` | Separate branch for `BABEL_ENV=test`. |
| `preset-env` `exclude` | `["transform-typeof-symbol"]` | Excluded as a deoptimisation. |
| `preset-env` `useBuiltIns` | `"entry"`, corejs 3 | **Inert.** `entry` mode only rewrites an existing `import "core-js"`, and nothing imports it. core-js 3.50.0 is present only transitively. No polyfills are being injected. |
| `preset-react` `runtime` | **`"classic"`** | `runtime: opts.runtime \|\| 'classic'`, and `babel.config.js` passes no options. |
| `preset-react` `useBuiltIns` | `true` | Applied whenever runtime is not `automatic`. Not portable: Babel 8 removed the option. |
| `preset-react` `development` | true in dev and test | Adds `__self` / `__source` to JSX for React warnings. |

**No targets means preset-env compiles down to ES5** — the widest possible
support. That is the current baseline and the thing to preserve.

---

## The fix: drop the preset, declare what it wrapped

A function config, because three settings differ per environment:

```js
// babel.config.js
module.exports = (api) => {
  const env = api.env()
  const isTest = env === "test"
  const isDevelopment = env === "development"
  api.cache.using(() => env)

  return {
    presets: [
      isTest
        ? ["@babel/preset-env", {targets: {node: "current"}}]
        : ["@babel/preset-env", {exclude: ["transform-typeof-symbol"]}],
      ["@babel/preset-react", {
        runtime: "classic",
        // No useBuiltIns -- Babel 8 removed the option from preset-react
        development: isDevelopment || isTest,
      }],
    ],
    plugins: [
      "babel-plugin-macros",
      "babel-plugin-styled-components",
      ...(isTest ? ["@babel/plugin-transform-modules-commonjs"] : []),
    ],
  }
}
```

### Do NOT add a browserslist

Tempting, and wrong if the goal is "everything that worked keeps working".
There is no `browserslist` key today, so `preset-env` falls back to ES5 output.
Adding `browserslist` — even something generous like `defaults` — *narrows*
support relative to now and changes the emitted syntax.

Introduce one later as a deliberate, separately tested decision, once someone
has established the real floor for the web build and the Electron build. They
are different audiences: the desktop app ships a known Chromium, the web app
does not.

### Keep `runtime: "classic"`

`automatic` is the modern default and removes the need for `React` to be in
scope, but it is a behaviour change across every JSX file. Not worth folding
into a dependency upgrade. Switch it separately if wanted.

### Dependency changes

Add as devDependencies:
- `@babel/preset-env`
- `@babel/preset-react`

Remove:
- `babel-preset-react-app` — the whole point
- `@babel/plugin-transform-react-jsx` — `preset-react` includes it; listing both
  is redundant
- `@babel/plugin-syntax-dynamic-import` — a no-op since Babel 7.8, when dynamic
  `import()` became standard syntax

Keep:
- `@babel/plugin-transform-modules-commonjs` — still needed for the test env
- `babel-plugin-macros` — **required**; `twin.macro` runs on it
- `babel-plugin-styled-components`

Then bump `@babel/core` and `@babel/plugin-transform-modules-commonjs` to `^8`.

---

## What the preset carried that this repo does not need

Verified against its source:

- **`plugin-proposal-*`** — class properties, private methods, private property
  in object, optional chaining, nullish coalescing, numeric separator. All
  standard as of ES2022 and handled by `preset-env`.
- **`preset-typescript`** — `src/` is JavaScript only; no `.ts`/`.tsx`.
- **`plugin-transform-flow-strip-types`** — no Flow.
- **`plugin-proposal-decorators`** — no decorators in `src/`.
- **`plugin-transform-react-display-name`** — only affects DevTools labels for
  `createReactClass`, unused here.
- **`babel-plugin-transform-react-remove-prop-types`** — a production size
  optimisation. Reintroduce deliberately if the bundle grows.
- **`plugin-transform-runtime` / `@babel/runtime`** — helper deduplication.
  Optional; add only if bundle size regresses measurably.

---

## Order of work

Do this **before** the Tailwind 4 migration. `twin.macro` runs through
`babel-plugin-macros`, so both changes touch the same pipeline, and untangling
one at a time is far easier than debugging both together. See `tailwind.md`.

---

## Verifying

1. `yarn test` — baseline is 40/55 suites, 354 passing. Must not move.
2. Dev web build clean, then the production build
   (`webpack.build-web.config.js`) — production is where `preset-env`
   differences actually show up.
3. Compare production bundle size against the previous build. A jump means a
   missing optimisation plugin (most likely `transform-runtime`); a drop is
   fine.
4. **Run the app, both web and desktop.** Styled-components and `tw` props are
   compile-time transforms: if the pipeline is wrong the app builds and then
   looks broken, so a green build proves nothing on its own.
