# Deferred dependency work

Written 2026-09-02/03, after the main sweep merged into `release-6.0.x`
(`b2b9e10c2`). These are the items that need real work rather than a version
bump.

---

## The plan: two stages

The Babel 8 and Tailwind 4 blockers sit in the same compile-time pipeline, but
they are **not one project**. They split cleanly, and the first stage is cheap.

### Stage 1 — unblock Babel 8

Swap the `css` prop from styled-components to Emotion. That drops
`babel-plugin-styled-components`, the only thing standing between this repo and
`@babel/core` 8.

**twin.macro stays. Tailwind stays on 3. Every `tw` and `css` prop in the app is
untouched.**

Blast radius:

| | Count |
| --- | --- |
| Config files edited | 2 — `babel.config.js`, `babel-plugin-macros.config.js` |
| Package swaps | `styled-components` → `@emotion/react` + `@emotion/styled`; drop `babel-plugin-styled-components`, `babel-preset-react-app` |
| Source files touched | **8** — the only files importing from `styled-components` |
| JSX changed | **none** |

Those 8 files import just three things — `withTheme` (5), `ThemeContext` (2),
`ThemeProvider` (1) — all of which `@emotion/react` exports under the same
names. The 65 `@keyframes` in the codebase are raw CSS inside template
literals, not the styled-components helper, so nothing to port there.

Small, independently shippable, and easy to revert. Details in `babel.md`.

### Stage 2 — unblock Tailwind 4

Remove twin.macro: `tw` props become `className`, and the CSS that cannot be a
utility class stays in an Emotion `css` prop. Then convert the Tailwind config
from JS to v4's CSS-native form.

Blast radius:

| | Count |
| --- | --- |
| Files importing twin.macro | **853** |
| Files with a `tw=` or `css={` prop | **924** of 1695 `src` JS files |
| JSX sites | ~7300 (see the table in `tailwind.md`) |
| Component prop contracts (`extraCss`) | **651 files, 2298 uses** — the real cost |
| twin-only grouped variants | 188 — invalid Tailwind, must be expanded |
| Config files | `tailwind.config.js` rewritten to CSS `@theme`; `postcss.config.js` shrinks; `babel-plugin-macros.config.js` deleted |

Mitigated by one fact: **Tailwind already runs through PostCSS here**, so
`className` works today alongside twin. Stage 2 can go file by file on Tailwind
3, with both systems live. Details in `tailwind.md`.

**Tailwind is not going away — after this it is used more, not less.** Only
twin.macro goes.

---

## Files

| File | Covers |
| --- | --- |
| `babel.md` | @babel/core 8 — both blockers, the verified fix, stage 1 |
| `tailwind.md` | Tailwind 4 and removing twin.macro — stage 2, with migration patterns and config impact |
| `styling-stack.md` | Shared research: the Babel 8 experiment, the Emotion risk audit, Superchart findings |

Not yet written up: `flexlayout-react`, `jsdom 30`, Storybook. Those remain
described in the parent `plan.md` under "Dropped, with reasons". In short:
flexlayout's migration already exists on `feature/superchart-integration`
(at 0.9.0, not the latest 0.10.8); jsdom 30 needs Node ≥ 24.15 and this machine
runs 24.11.1; Storybook has `builder-webpack5` and `cli` stranded on 6.5.16
while the rest sit on 8.6.x.

---

## One correction worth carrying forward

`babel-plugin-styled-components` is **not abandoned**. 2.3.0 shipped
2026-05-21. It simply has not added Babel 8 support yet — it still calls
`t.jSXIdentifier`, an alias Babel 8 removed, and peers `@babel/core ^7.0.0`.

So "wait for upstream" is a legitimate option for stage 1, and should be checked
before doing the work.

**twin.macro is the genuinely stale one**: last release 2024-01-19, and the
maintainer recommends migrating away. That is what forces stage 2 eventually,
whatever happens with Babel.
