# Review: sc-docs-fixes

## Round 1: implementation verification (2026-07-22)

Fact-check first: all clean-room findings were re-verified against the repo by
independent sub-agents before any fix — none were hallucinations. Per user
decision, the unpublished-registry state itself is accepted (package not
released yet); only a docs pointer was added.

### Changes
- `src/lib/widget/script-editor/languageAdapter.ts` — all CodeMirror/lezer
  value imports converted to cached dynamic imports (`loadCodeMirror()`);
  `createLanguageExtension` now async. Call site awaits it
  (`script-editor/index.tsx:270`), already inside try/catch → same graceful
  degradation.
- `src/lib/index.ts` — value-exports `resolutionToPeriod`, `periodToResolution`.
- `scripts/prepare-edition-package.mjs` — emits `styles.d.ts` stub; `./styles`
  export now `{ types, default }`. Root `package.json` mirrored.
- `.storybook/docs/getting-started.mdx` — registry pointer to Branding &
  Editions; bundled-React + size sentence; `getBars` derives step from
  `resolution`; lazy-load note on add-ons; `#root` reset tip after framework
  tabs.

### Verification
1. ✅ `pnpm build:enterprise` and `pnpm build:community` pass (agent-free,
   run directly).
2. ✅ Built `languageAdapter-*.js/.cjs` chunks contain **zero** static
   `@codemirror` imports; dynamic `import("@codemirror/…")` present.
3. ✅ `resolutionToPeriod`/`periodToResolution` in both editions' `index.d.ts`.
4. ✅ `styles.d.ts` emitted in both dists; `./styles` has `types` condition in
   both generated package.jsons + root.
5. ✅ **Gold clean-room test** (`~/git/superchart-doc-test`): repacked
   enterprise tarball, removed all 9 CodeMirror/lezer packages and the TS2882
   shim → `tsc -b --force` PASS, `vite build` PASS.
6. ✅ Helpers importable from package root in the clean-room app (typecheck).
7. Runtime script-editor smoke test (open editor with a ScriptProvider,
   syntax highlighting still works via the new async path) — **not run**;
   needs Storybook/manual check.
8. Trading Terminal context tests — N/A (packaging/docs change, no Altrady
   integration surface touched).

### Notes
- Clean-room CI job (pack → blank app → `tsc -b && vite build`) remains the
  recommended follow-up (out of scope, see PRD non-requirements).
- Test app `~/git/superchart-doc-test` was mutated (deps stripped, shim
  removed) — it now represents the post-fix consumer state.
