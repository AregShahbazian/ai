# Docs gap: a clean-room consumer cannot follow Getting Started end-to-end

**Date:** 2026-07-14
**Context:** Reviewing ALTD-1765 (Documentation for 3rd party use) and ALTD-1874
(API Reference expansion), both on QA. Docs were written by someone else; this is
an independent verification, not a re-implementation.

## What I did

Built a blank React+TS app (`pnpm create vite --template react-ts`) at
`~/git/superchart-doc-test` and integrated Superchart **by following the Storybook
docs literally** — copying the Getting Started snippets verbatim rather than
reaching into the workspace source. Any friction a real third-party integrator
would hit therefore shows up as a real error.

Since `@coinrayio/superchart` is not published yet, the closest faithful
substitute for `pnpm add`: `pnpm build:enterprise` → `npm pack` the `dist-enterprise/`
folder → install the resulting tarball, aliased to the documented package name. This
exercises exactly what a consumer gets (the `files` / `exports` / peer-dep manifest),
not the workspace source.

Data provider: no Coinray tokens. Followed the Storybook's own approach — a
CCXT-backed `Datafeed` hitting the `examples/server` REST API (`/api/datafeed/*`)
on :8080, modeled on `.storybook/helpers/BackendDatafeed.ts`.

**Result:** the chart renders with live Binance candles — but only after five
undocumented deviations, two of which are hard blockers.

## The gap

### 1. BLOCKER — the "optional" CodeMirror deps are mandatory for a production build

Getting Started → "Optional add-ons" says:

> The script editor (used by `ScriptProvider` for in-chart Pine-style code) is built
> on CodeMirror. **Install only if you wire up a `ScriptProvider`.**

I wired up no `ScriptProvider`. `vite build` failed with **9 `MISSING_EXPORT` errors**:

```
[MISSING_EXPORT] "LanguageSupport" is not exported by
  "__vite-optional-peer-dep:@codemirror/language:@coinrayio/superchart-enterprise"
  → languageAdapter-omAiWpbF.js:1:10
[MISSING_EXPORT] "syntaxHighlighting" is not exported by ... (+7 more)
```

Cause: the bundled `languageAdapter-*.js` chunk **statically** imports
`LanguageSupport` / `syntaxHighlighting` / `StreamLanguage` / `HighlightStyle` from
`@codemirror/language`. The deps are declared as *optional* peers, so Vite stubs them
with `__vite-optional-peer-dep`, and Rollup then errors on the missing named exports.

Installing all nine CodeMirror packages makes the build pass.

**Why it's nasty:** `pnpm dev` works fine without them (the chunk is lazily loaded),
so the failure only appears at *build* time — i.e. when the consumer tries to ship.
The docs actively tell them not to install the thing they need.

**Fix (pick one):**
- make `languageAdapter` a true dynamic `import()` so the static edge disappears, or
- stop calling them optional: document the nine packages as required.

### 2. BLOCKER — `import '@coinrayio/superchart/styles'` does not typecheck

Getting Started → "Stylesheet" says to `import '@coinrayio/superchart/styles'` once
at app startup. Under a stock Vite `react-ts` tsconfig this fails:

```
src/main.tsx(4,8): error TS2882: Cannot find module or type declarations for
side-effect import of '@coinrayio/superchart/styles'.
```

The `"./styles"` entry in `exports` maps straight to `superchart.css` with no type
declaration. Consumer workaround is a `declare module '@coinrayio/superchart/styles'`
shim in `vite-env.d.ts` — undocumented, and something they shouldn't have to write.

**Fix:** ship a `styles.d.ts` in the dist and add a `types` condition to the
`"./styles"` export. Publishing does not change this.

### 3. Registry + auth are undocumented

The docs show a bare `pnpm add @coinrayio/superchart`. **Not a naming bug** — the
*community* edition is genuinely named `@coinrayio/superchart`
(`scripts/prepare-edition-package.mjs:44-46`), so the name will resolve once published.

But `publishConfig` (root `package.json`) is:

```json
{ "registry": "https://npm.pkg.github.com/", "access": "restricted" }
```

Publishing to **GitHub Packages, restricted** means a bare `pnpm add` still fails for
a third party. They also need an `.npmrc`:

```
@coinrayio:registry=https://npm.pkg.github.com/
//npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}
```

...plus a token with `read:packages`. The docs never mention any of it.

**Fix:** either publish to npmjs public (in which case `publishConfig` is wrong and
must change), or document the `.npmrc` + token step in Getting Started.

### 4. The "Minimum viable chart" snippet does not produce a working chart

Its `getBars` walks the range in fixed `60_000`ms steps:

```ts
for (let t = params.from * 1000; t < params.to * 1000; t += 60_000) { … }
```

...i.e. it always emits **1-minute** bars regardless of the requested resolution —
while the very same snippet mounts the chart at `period: { type: 'hour', span: 1 }`.
Copy-paste it and the bars don't match the period. Fine as an illustration of the
`Datafeed` shape; misleading as the "smallest possible integration" it's billed as.

**Fix:** derive the step from the requested resolution, or label the snippet
explicitly as pseudo-code / non-runnable.

### 5. `height: 100vh` silently collapses in a stock Vite app

The React tab returns `<div style={{ width: '100%', height: '100vh' }} />`. Vite's
`react-ts` template ships an `index.css` that centers `#root` with `max-width: 1280px`
and padding — so the chart renders boxed and off-center, not full-bleed. Minor, but
that template is the exact scaffold a newcomer starts from.

**Fix:** one line in Getting Started about resetting the root element's styles.

## What is genuinely solid

Worth saying plainly, since the list above is all negative:

- **The public type surface is complete.** A realistic CCXT datafeed needs
  `Datafeed`, `Bar`, `PeriodParams`, `LibrarySymbolInfo`, `DatafeedConfiguration`,
  `HistoryMetadata`, `SearchSymbolResult` — **all are exported from the package root.**
  I built the whole thing against the published artifact with zero reaching into
  internals. That is the hard part of a library API, and it's right.
- The prose, the concept pages, and the per-symbol API Reference depth are good.
- The chart itself works: live Binance candles, correct paging, no console errors.

## Root cause of the gap (the meta-finding)

Every blocker lives in the **install → typecheck → build** path, and none of them in
the API or the prose. That's the signature of docs written against the workspace
source and never once exercised clean-room. Inside the monorepo, CodeMirror is present,
the CSS resolves through the Vite alias, and there's no registry to authenticate to —
so all three blockers are invisible to the author.

**Recommendation:** whatever the fixes, add a CI job that scaffolds a blank app,
installs the packed tarball, and runs `tsc && vite build`. That single job would have
caught gaps 1, 2, and 3 before QA.

## Artifacts

- Test app: `~/git/superchart-doc-test` (not committed to Superchart)
  - `src/datafeed.ts` — CCXT datafeed via `examples/server`, all types from the public package
  - `src/App.tsx` — verbatim from the docs' React tab
  - `src/vite-env.d.ts` — the undocumented TS2882 shim (gap 2)
  - `src/index.css` — root reset (gap 5)
- Run: `pnpm -C examples/server dev` (:8080), then `pnpm -C ~/git/superchart-doc-test dev` (:5199)
