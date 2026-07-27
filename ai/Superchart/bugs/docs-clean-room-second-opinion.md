# Superchart docs — clean-room integration test (independent second opinion)

**Date:** 2026-07-14
**Method:** Built a blank Vite + React 19 + TS app at `~/git/superchart-consumer-test`, installed
Superchart as an outside consumer would, and rendered a minimum-viable chart following **only**
the Storybook docs (Getting Started, Concepts, API Reference).
**Written independently** — deliberately did not read the prior agent's findings in this folder.

## Experiment integrity

Integrated against the **published artifact**, not the workspace source:

```bash
pnpm build:enterprise
cd dist-enterprise && npm pack          # coinrayio-superchart-enterprise-0.1.0.tgz
# in the consumer app:
npm install "@coinrayio/superchart@file:…/coinrayio-superchart-enterprise-0.1.0.tgz"
```

Verified: no path aliases in `vite.config.ts` / `tsconfig.app.json`, and
`node_modules/@coinrayio/superchart` is a real directory (not a symlink into the monorepo).

Data: CCXT-backed datafeed hitting `examples/server` REST API at `http://localhost:8080/api/datafeed/*`
(`/resolve`, `/klines`, `/markets`, `/last-bar`), same as the Storybook's own `BackendDatafeed`.
No Coinray tokens used.

**Acceptance gates — all three passed, but only after the workarounds below:**

| Gate | Result |
|---|---|
| Chart renders in `vite dev` | pass (real BTC/USDT candles, 0 console errors/warnings) |
| `tsc -b` (real typecheck) | pass |
| Production `vite build` | pass |
| Production bundle renders via `vite preview` | pass (live price updates via `subscribeBars`) |

> Note: plain `npx tsc --noEmit` is a **no-op** on the Vite react-ts template — its root
> `tsconfig.json` is a solution file with `"files": []`. It exits 0 while checking nothing.
> The real check is `tsc -b`. Anyone validating this must use `tsc -b` or they will report a
> false pass.

---

## Bottom line

A minimum-viable chart works — but **not** by following the docs literally. Three defects sit
directly on the happy path, and the worst one is invisible until you try to ship.
The **API** documentation is in good shape; the **packaging** documentation is where it breaks.

---

## Gaps, ranked by how badly they block a real integrator

### 1. BLOCKER — the "optional" CodeMirror deps are mandatory for any production build

Getting Started → *Optional add-ons* says: *"Install only if you wire up a `ScriptProvider`."*
I never wired one up. `vite build` fails anyway:

```
[MISSING_EXPORT] "LanguageSupport" is not exported by "__vite-optional-peer-dep:@codemirror/language:@coinrayio/superchart-enterprise".
[MISSING_EXPORT] "HighlightStyle" is not exported by "__vite-optional-peer-dep:@codemirror/language:…"
[MISSING_EXPORT] "StreamLanguage" is not exported by "__vite-optional-peer-dep:@codemirror/language:…"
[MISSING_EXPORT] "syntaxHighlighting" is not exported by "__vite-optional-peer-dep:@codemirror/language:…"
[MISSING_EXPORT] "snippetCompletion" is not exported by "__vite-optional-peer-dep:@codemirror/autocomplete:…"
```

**Why this is the worst gap:** `pnpm dev` works fine without them. The chart renders, live-updates,
zero console errors. The failure only surfaces at deploy time. The docs state the *opposite* of the
truth.

**Root cause:** the package's `languageAdapter-*.js` chunk *statically* imports `@codemirror/*`, so
the bundler must resolve those named exports regardless of whether the script editor is used. They
are declared as optional `peerDependencies`, so Vite stubs them and the static named imports fail.

**Workaround applied:** install all nine packages from the docs' "optional" list — which drags
~350 KB of unused CodeMirror into the consumer's bundle.

**Suggested fix:** make the language adapter a true dynamic `import()` behind the `ScriptProvider`
code path, so the chunk is never reached when no provider is configured. Failing that, the docs must
say these deps are **required for a production build**.

---

### 2. BLOCKER (typecheck) — the documented stylesheet import has no type declaration

Getting Started → *Stylesheet* tells you to write `import '@coinrayio/superchart/styles'`.
That line does not compile on a stock Vite react-ts template (TS 5, `moduleResolution: "bundler"`):

```
src/main.tsx(4,8): error TS2882: Cannot find module or type declarations for
  side-effect import of '@coinrayio/superchart/styles'.
```

The package's `exports` maps `"./styles": "./superchart.css"` with **no `types` condition**, and
ships no `styles.d.ts`.

**Consequence:** the docs' own **"Minimum viable chart"** snippet does not compile as written.
Copied verbatim into `src/docs-verbatim.ts`, it fails on line 6 — the stylesheet line.
*Everything else in that snippet compiled cleanly.*

**Workaround applied** (never mentioned in the docs):

```ts
// src/superchart-styles.d.ts
declare module '@coinrayio/superchart/styles'
```

**Suggested fix:** ship a `styles.d.ts` and use a conditional export:
`"./styles": { "types": "./styles.d.ts", "default": "./superchart.css" }`.

---

### 3. MEDIUM — `resolutionToPeriod` / `periodToResolution` are documented but do not exist

API Reference → Datafeed → *Resolution helpers* documents both with full signatures and worked
examples. Using the first one as documented:

```
src/datafeed.ts(4,10): error TS2305: Module '"@coinrayio/superchart"'
  has no exported member 'resolutionToPeriod'.
```

Absent from `index.d.ts` **and** from the runtime bundle. They exist in
`src/lib/types/datafeed.ts` (and are re-exported from `src/lib/types/index.ts`), but **no entry file**
— `src/lib/index.ts`, `enterprise.ts`, `community.ts` — re-exports them. They are unreachable from
the package root.

This is exactly the failure the API Reference page promises cannot happen:
*"Every symbol mentioned in this section is exported from the package root… If you discover a useful
symbol that isn't documented, file an issue."*

**Workaround applied:** hand-rolled the resolution → CCXT timeframe mapping.
**Suggested fix:** one line in the entry file — or delete the section from the docs.

---

### 4. MEDIUM — Getting Started's install command fails for everyone

`npm install @coinrayio/superchart`, copied verbatim:

```
npm error code E404
npm error 404 Not Found - GET https://registry.npmjs.org/@coinrayio%2fsuperchart - Not found
```

The package publishes to GitHub Packages with `publishConfig.access: "restricted"`. The required
`.npmrc` setup —

```
@coinrayio:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=…
```

— is documented **only** in Concepts → Branding & Editions, which a new integrator has no reason to
open. Getting Started's install block should carry the registry/auth step or link to it prominently.

---

### 5. LOW — the package silently bundles its own React

No `react` peer dependency, and no bare `react` import in the artifact: React 19 is compiled in
(2.55 MB raw / 566 KB gzip for the ES bundle). The docs say only *"the chart engine and its rendering
pipeline are bundled into the package — nothing else to add"*, which is technically true but leaves a
React consumer shipping two React copies with no way to dedupe. Worth one sentence in the docs
(bundle size + the fact that React is inlined).

---

## Not a bug — worth stating explicitly

The **two package names are correctly documented**. Branding & Editions accurately states
community = `@coinrayio/superchart`, enterprise = `@coinrayio/superchart-enterprise`. For this
exercise the enterprise tarball was aliased to the community name; the docs are self-consistent here.
(The only related nit is discoverability — see gap #4.)

---

## What worked well

- **The `Datafeed` contract is excellent.** A CCXT-backed datafeed was implemented against the API
  Reference page *alone*, with no source-diving, and worked first try. The two easiest things to get
  wrong are called out explicitly and correctly: `Bar.time` is **unix ms**, `PeriodParams.from/to`
  are **unix seconds**. Supporting types (`DatafeedConfiguration`, `LibrarySymbolInfo`,
  `HistoryMetadata`, `SearchSymbolResult`, `PeriodParams`) are documented at the field level.
- **The React mounting snippet is correct as written** — container ref, `createDataLoader`, cleanup
  via `chart.dispose()` in the effect teardown. Survives StrictMode double-mount.
- **The constructor options table is accurate and complete.** Every option exercised behaved as
  documented.
- **Runtime quality is high.** Real candles, dark theme, period bar, volume, live price updates —
  and **zero console errors/warnings** in both dev and the production bundle.
- **Export audit:** all 44 symbols the docs tell you to import from the package root were checked
  against the shipped `index.d.ts`. **Only the two resolution helpers are missing.** Gap #3 is a
  narrow slip, not systemic rot.
  (`loadLocale` initially looked missing but is present — exported as `export { load as loadLocale }`.)

---

## Fix list (suggested priority)

1. Make the CodeMirror language adapter dynamically imported, so no-`ScriptProvider` consumers can
   build without it. *(unblocks production builds)*
2. Ship `styles.d.ts` + a `types` condition on the `./styles` export. *(unblocks typecheck)*
3. Re-export `resolutionToPeriod` / `periodToResolution` from the entry files, or drop them from the
   docs.
4. Add the GitHub Packages registry + auth step to Getting Started's install section.
5. Document that React is bundled, and the resulting bundle size.

## Housekeeping

`build.sh` was already untracked in the Superchart working tree at session start and is unrelated to
this work — left untouched.
