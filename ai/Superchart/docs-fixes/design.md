# Design: sc-docs-fixes

## R1 — dynamic CodeMirror imports in languageAdapter
`src/lib/widget/script-editor/index.tsx:269` already gates the adapter behind
`await import('./languageAdapter')`, and separately dynamic-imports
`@codemirror/view|state|commands|search` (lines 125-128) — that pattern builds
fine without the deps. The adapter chunk breaks consumers only because its
*own* imports are static: the emitted chunk starts with
`import { LanguageSupport, … } from "@codemirror/language"`, which the
consumer's Rollup must resolve (named-export check) even for a lazily loaded
chunk. Vite stubs missing optional peers → `MISSING_EXPORT`.

Fix inside `languageAdapter.ts` only:
- Keep type-only imports (erased at build).
- Add a cached `loadCodeMirror()` that dynamic-imports the five runtime
  modules (`@codemirror/language`, `@codemirror/autocomplete`,
  `@codemirror/view`, `@codemirror/lint`, `@lezer/highlight`).
- Pass the loaded namespaces into the helper factories; move the module-level
  `HighlightStyle.define` theme tables into a factory (they use `tags` +
  `HighlightStyle` at module scope today).
- `createLanguageExtension` becomes `async` → `Promise<Extension[]>`.
- Call site `index.tsx:270`: `await createLanguageExtension(...)` — already
  inside async + try/catch, so failure still degrades to no-highlighting.

Dynamic `import('@codemirror/…')` leaves named-export access to runtime, so
consumer builds pass; runtime only reaches it when the script editor opens.

## R2 — styles.d.ts + types condition
- `scripts/prepare-edition-package.mjs`: write a `styles.d.ts` stub into the
  dist folder and change the exports map to
  `'./styles': { types: './styles.d.ts', default: './superchart.css' }`
  (`types` first). `files: ['*.d.ts', …]` already picks it up.
- Root `package.json` mirror:
  `"./styles": { "types": "./dist-enterprise/styles.d.ts", "default": "./dist-enterprise/superchart.css" }`.

## R3 — export helpers
One line in `src/lib/index.ts` (both edition entries `export * from './index'`):
`export { resolutionToPeriod, periodToResolution } from './types/datafeed'`.

## R4/R5 — docs edits (`.storybook/docs/getting-started.mdx`)
- Install: note GitHub Packages + link
  `[Branding & Editions](?path=/docs/docs-concepts-branding-editions--docs)`
  for the one-time `.npmrc` auth.
- L22 sentence: extend with "including React" + approx size note.
- `getBars` loop: `const step = (Number(resolution) || 1) * 60_000` using the
  `resolution` param (covers numeric minute-based resolutions incl. '60';
  comment that '1D'/'1W' need a real mapping — or use the now-exported
  `resolutionToPeriod`). Keep snippet minimal.
- React tab area: one-line tip to strip the Vite template's default `#root`
  centering styles so `height: 100vh` renders full-bleed.
- Optional add-ons: keep the optional claim (now true); add "lazily loaded —
  production builds without a ScriptProvider don't need them".

## Verification
`pnpm build:enterprise`; then assert: new `languageAdapter-*.js` chunk has no
static `from "@codemirror"` imports; `dist-enterprise/index.d.ts` contains the
two helpers; `dist-enterprise/styles.d.ts` exists and package.json exports map
has the types condition. Gold test: pack tarball into the existing
`~/git/superchart-doc-test` app with CodeMirror deps removed → `tsc -b && vite build`.
