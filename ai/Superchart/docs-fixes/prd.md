---
id: sc-docs-fixes
---

# PRD: Remaining fixes for documentation tasks (ALTD-1765 / ALTD-1874)

**Date:** 2026-07-22
**Source:** Two independent clean-room integration tests
(`~/ai/Superchart/bugs/docs-clean-room-install-gaps.md`,
`~/ai/Superchart/bugs/docs-clean-room-second-opinion.md`). All findings below
were re-verified against the repo on 2026-07-22 — none are hallucinations.

## Requirements

### R1 — CodeMirror deps must be truly optional (build blocker)
A consumer who does not wire a `ScriptProvider` must be able to run a
production `vite build` **without** any `@codemirror/*` / `@lezer/*` packages
installed. Today the `languageAdapter` chunk statically imports
`@codemirror/language` / `@codemirror/autocomplete` / `@codemirror/view` /
`@codemirror/lint` / `@lezer/highlight`, so the consumer's bundler fails with
`MISSING_EXPORT` against the optional-peer-dep stubs. The docs' "Install only
if you wire up a ScriptProvider" claim must become true, not be reworded.

### R2 — `import '@coinrayio/superchart/styles'` must typecheck (blocker)
The documented stylesheet import must compile under a stock Vite react-ts
tsconfig (`moduleResolution: "bundler"`). The published `./styles` export
needs a `types` condition backed by a shipped `styles.d.ts`.

### R3 — documented resolution helpers must exist
`resolutionToPeriod` / `periodToResolution` are documented in the API
Reference with full signatures but are not exported from any package entry.
Export them from the package root (both editions).

### R4 — Getting Started snippet must be self-consistent
The "Minimum viable chart" `getBars` emits fixed 1-minute bars while the
chart mounts at 1-hour. Derive the bar step from the requested resolution.

### R5 — docs accuracy touch-ups
- Getting Started must state that React (and the chart engine) are bundled
  into the package, with approximate bundle size.
- Getting Started must warn that the stock Vite template's `#root` styles
  box the `100vh` chart (one-line reset tip).
- Getting Started's Install section must point to the GitHub Packages
  registry/auth setup (already documented in Concepts → Branding & Editions).
  Package is not yet published — a broken bare `pnpm add` is acceptable for
  now, but the pointer must exist.

## Non-requirements
- Publishing the package / changing `publishConfig` — pre-release, deliberate.
- Unbundling React or making it a peer dep — deliberate design (vite.config
  comment); only documenting it (R5).
- Clean-room CI job (pack tarball → blank app → `tsc -b && vite build`) —
  recommended follow-up, out of scope here.
- No changes to API Reference prose (verified accurate; R3 makes the
  resolution-helpers section correct as written).
