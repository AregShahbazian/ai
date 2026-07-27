# Tasks: sc-docs-fixes

1. **languageAdapter dynamic imports** — `src/lib/widget/script-editor/languageAdapter.ts`:
   remove static `@codemirror/*` / `@lezer/highlight` value imports; add cached
   `loadCodeMirror()`; thread namespaces into helpers; async
   `createLanguageExtension`. Update call site
   `src/lib/widget/script-editor/index.tsx` (`await`).
   Verify: built chunk has no static `@codemirror` imports.
2. **Export resolution helpers** — `src/lib/index.ts`: value-export
   `resolutionToPeriod`, `periodToResolution`.
   Verify: present in `dist-enterprise/index.d.ts`.
3. **styles.d.ts** — `scripts/prepare-edition-package.mjs`: emit stub +
   exports object with `types`; mirror in root `package.json`.
   Verify: file in dist, `types` condition in both package.jsons.
4. **getting-started.mdx edits** — install registry pointer, bundled-React
   sentence, resolution-derived `getBars` step, `#root` reset tip, add-ons
   lazy-load note.
5. **Build + clean-room check** — `pnpm build:enterprise`; optional gold test
   via `~/git/superchart-doc-test` without CodeMirror deps.
6. **review.md** — record verification checklist.
