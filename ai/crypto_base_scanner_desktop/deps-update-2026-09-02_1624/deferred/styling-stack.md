# The styling stack: research behind the Babel 8 and Tailwind 4 unblocks

Shared background for `babel.md` and `tailwind.md`. Both blockers live in the
same compile-time pipeline, so the research is recorded once here.

Everything below was established on **2026-09-02**, by direct experiment or by
checking the npm registry and GitHub. Where something was verified by running
it, that is stated.

---

## The two blockers, and why they are not the same problem

| | Blocks | Root cause |
| --- | --- | --- |
| `babel-plugin-styled-components` | **@babel/core 8** | Calls `t.jSXIdentifier`, a lowercase-first-letter builder alias Babel 8 removed. Latest is 2.3.0 (2026-05-21), peers `@babel/core ^7.0.0`. No dist-tag has v8 support. |
| `twin.macro` | **tailwindcss 4** | Reads Tailwind internals (`tailwindcss/lib/util/toPath`) that the v4 rewrite removed. Last release 3.4.1, **2024-01-19**. |

They are often conflated because both serve the `css` prop, but they are
separable — and the Babel one has a much cheaper fix.

`babel-plugin-styled-components` is a **direct dependency** listed in
`babel.config.js`. Nothing else requires it; twin.macro's `styled-components`
preset is what makes it necessary.

---

## Finding 1: Emotion frees Babel 8 without touching Tailwind

**Verified by experiment**, not inferred. Built a throwaway project with
`@babel/core@8.0.1`, `@babel/preset-react@8`, `babel-plugin-macros`,
`twin.macro` and `tailwindcss@3.4.19`, and compiled a representative snippet.

Input:

```jsx
import tw, {css} from "twin.macro"
const A = () => <div css={[tw`flex items-center`, css`position:relative;`]} tw="p-4" />
```

Babel config:

```js
presets: [["@babel/preset-react", {runtime: "automatic", importSource: "@emotion/react"}]],
plugins: ["babel-plugin-macros"],
```

Output — correct, under Babel 8:

```js
import { css as _css } from "@emotion/react";
import { jsxDEV as _jsxDEV } from "@emotion/react/jsx-dev-runtime";
const A = () => _jsxDEV("div", {
  css: [{ "display": "flex", "alignItems": "center" }, _css`position:relative;`, { "padding": "1rem" }]
}, void 0, false);
```

**Why this works:** Emotion's `css` prop is enabled through
`@babel/preset-react`'s `importSource` option — the automatic JSX runtime — and
needs **no Emotion Babel plugin**. `@emotion/babel-plugin` is a runtime
dependency of `@emotion/react` and will sit in `node_modules`, but it is only
`require`d by `@emotion/react/macro`, which this approach does not use. Being
in the tree is not being executed; the experiment above had it installed
throughout and compiled fine.

So: **switch twin.macro's preset from `styled-components` to `emotion`, drop
`babel-plugin-styled-components`, and Babel 8 is unblocked** — with the
`css={[tw`…`, css`…`]}` and `tw="…"` syntax completely unchanged, and Tailwind
still on 3.

The same experiment also confirmed `babel-plugin-macros` itself works under
Babel 8, which is what lets twin.macro survive this step.

---

## Finding 2: twin.macro has to go regardless

Not a judgement call — the maintainer's own position. From
[twin.macro discussion #876](https://github.com/ben-rogerson/twin.macro/discussions/876),
Ben Rogerson, 2025-01-27:

- Tailwind v4's rewrite "doesn't surface those same functions" twin relies on;
  he is pessimistic about a fix.
- He recommends users **migrate away**, noting "you're very likely see
  performance gains due to shifting away from css-in-js".
- No successor project exists.
- Separately: Babel macros do not work with Rust bundlers (Turbopack, Rspack),
  so the approach is a dead end beyond Tailwind too.

Corroborated by
[tailwindlabs discussion #16356](https://github.com/tailwindlabs/tailwindcss/discussions/16356).
Last twin.macro release: 2024-01-19.

---

## Finding 3: the replacement stack, and its risk

Proposed: **native Tailwind `className` + `clsx`** for classes, **`@emotion/react`**
for the genuine CSS that remains.

Audited for abandonment risk, since the whole exercise exists because two
dependencies were abandoned.

### Emotion — ACCEPTABLE, not SAFE

The one component carrying real risk. A maintenance inversion worth
internalising:

| | Emotion | styled-components |
| --- | --- | --- |
| Declared maintenance mode | no | **yes** (2025-03-17) |
| Last release | 2025-11-04 | 6.5.3, **2026-08-15** |
| Open issues | **309** (2 closed all year) | 24 |
| Open PRs | **84** | few |

**The library that publicly announced maintenance mode is better maintained
than the one that did not.** Emotion's silence is not evidence of health.

Cause is staffing, not decline. The lead maintainer merged **1 Emotion PR since
January 2025**, against 262 PRs elsewhere in 2026 (mostly microsoft/typescript-go
and changesets). His stated policy since 2021 is that he will not recruit
maintainers unless someone volunteers; two who offered in December 2024 went
unanswered.

Emotion **v12 exists and is roughly 80% done** — a complete `next` branch and an
open Changesets release PR ([#3289](https://github.com/emotion-js/emotion/pull/3289),
opened 2024-12-09, still open) staging `@emotion/react@12.0.0-next.0` (React 19
only, drops `defaultProps`, auto-prefixing, `forwardRef`-based refs). One merge
and one publish from a prerelease, frozen for 20 months. The `next` dist-tag on
npm (`11.0.0-next.10`) is a leftover from the 2020 v11 cycle.

**Concrete watch-triggers**, rather than vague vigilance:
- *Improving:* PR #3400 merges, or `12.0.0-next.0` is published.
- *Treat as abandoned:* continued silence past ~Q4 2026 — at which point v12
  has been one merge away for two years.

**Why take it anyway:** the `importSource` approach depends only on Emotion's
**runtime**, not its Babel tooling — a far smaller and more swappable surface
than the abandoned macro it replaces. And every `tw` moved to `className`
reduces the exposure further. The alternative, `mui/pigment-css`, is labelled
"⚠️ Alpha phase, currently, on hold," and MUI abandoned its own migration to it
as too slow (Olivier Tassinari, 2025-03-31).

### The others

`tailwindcss` v4, `clsx` and `tailwind-merge` were not flagged as risks.
`clsx`'s last publish (2024-04-23) reads as *finished* rather than stale — it is
a tiny utility. `tailwind-merge` 3.6.0 published 2026-05-10.

### A methodology warning

Articles from `pkgpulse.com` and `openreplay.com` ("State of CSS-in-JS 2026")
rank highly and claim Emotion is in decline. Their download figures are off by
**2x for Emotion and 10x for Tailwind** against the npm registry API; they
appear to be AI-generated content farms. The registry shows both Emotion
(78.7M/mo) and styled-components (42.8M/mo) **grew** in 2026. The problem with
Emotion is staffing, not adoption. Do not re-research this and be misled by the
same articles.

---

## Finding 4: Superchart is unaffected

Checked via the `sc-source-explorer` agent against SC at `cb7d57e`.

SC has **none** of twin.macro, styled-components, babel-plugin-styled-components,
babel-plugin-macros or Emotion. It has no Babel config of its own — `@babel/core`
appears only transitively inside `@vitejs/plugin-react` for Fast Refresh. It has
no CSS-in-JS runtime at all, shipping two static CSS artifacts
(`superchart.css` from compiled LESS, `superchart-ui.css` from Tailwind) that
the host imports. No shared config, theme file or design tokens with cbsd.

**So the cbsd migration requires no coordinated change in Superchart**, and
there is no risk of two CSS-in-JS runtimes on one page.

More usefully: **SC already runs the exact stack proposed here** — Tailwind v4
with CSS-native `@theme` config, and `className` composed via `clsx` +
`tailwind-merge` + `class-variance-authority`:

```ts
// SC: src/design-system/lib/cn.ts
import {clsx, type ClassValue} from "clsx"
import {twMerge} from "tailwind-merge"
export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)) }
```

```tsx
// SC: src/design-system/components/Badge/Badge.tsx
const badge = cva("inline-flex items-center gap-1 rounded-full px-2 py-1 ...", {variants: {...}})
<span ref={ref} className={cn(badge({variant}), className)} {...props}>
```

That is a strong signal: the target stack is already proven in-house by the same
team, and cbsd would converge on it rather than diverge. SC's `cn()` helper is
worth copying rather than reinventing.
