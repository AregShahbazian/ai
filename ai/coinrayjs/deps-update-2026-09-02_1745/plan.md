# Dependency update — coinrayjs

- **Created:** 2026-09-02 17:45
- **Base branch:** `master` (2.0.15)
- **Work branch:** `chore/deps-update-2026-09` in `~/git/worktrees/coinrayjs-deps-update`
- **Not published, not pushed.** Areg decides when coinrayjs is versioned
  and deployed, and only then does cbsd move to the new version.

## Applied — 4 commits

| Commit | Contents |
| --- | --- |
| `66bc6d2` | in-range: axios 1.20, jose 6.2.10, lodash 4.18.1, phoenix 1.8.13, vitest 4.1.11 |
| `836dcaf` | vite 7→8, uuid 13→14, @types/node 25→26 |
| `cd85c9f` | typescript 5.9→7.0 |
| `f117c6d` | bignumber.js 9→11 |
| `bb70394` | route all BigNumber construction through `bn()` |

Everything on offer was taken. Nothing was dropped.

## Verification

- `yarn test`: 3 suites / 8 tests passing, unchanged at every step. The other
  3 suites (endpoints, cache, candle fetching) are skipped on `master` already
  — they need the network.
- `yarn build`: clean throughout. Noticeably faster under vite 8 (~250ms
  against ~1.4s). The MIXED_EXPORTS warning is pre-existing.
- TypeScript 7 type-checks `lib/` with no errors.
- Smoke-tested inside crypto_base_scanner_desktop — see below.

## Cross-repo work on bignumber.js

Packed with `yarn pack` and installed into the cbsd deps branch as a tarball
rather than `yarn link`, to check resolution: webpack resolves symlinks to their
real path, so a linked coinrayjs loads its *own* bignumber copy and manufactures
a duplicate-instance problem that a published package would not have. The
tarball hoists one copy, which is what production looks like. Confirmed exactly
one `bignumber.js` 11.1.5 in the whole tree.

That first pass looked clean — portfolio balances, the aggregate position panel,
order-form arithmetic (77085.71 × 0.01234 = 951.2376614, no float drift), cbsd
jest and web build all fine. **It was not clean.** Opening the trading terminal
throws:

```
Error: [BigNumber Error] BigNumber, string, number, or BigInt expected: undefined
  at Util.safePrecision (util.js:615)
```

Version 10 made the constructor throw where 9 returned NaN. Green builds,
unchanged tests and a portfolio smoke test all missed it because those paths had
defined values.

Resolved by routing every construction through a `bn()` helper that restores the
old NaN behaviour — `lib/bn.ts` here (13 sites, 4 files), `src/util/bn.js` in
cbsd (526 sites, 81 files). Details in the cbsd plan's addendum.

## Still to do before release

cbsd is currently consuming this branch through `yarn link`, so its
`node_modules/coinrayjs` points at `~/git/worktrees/coinrayjs-deps-update` and
reads `dist/` — **rebuild after any source change or cbsd sees stale code.**

When Areg decides to release: version and publish coinrayjs, then point cbsd's
`package.json` at the published version and unlink. cbsd's `bignumber.js ^11.1.5`
is already committed, so the two are in step and no follow-up bump is needed.

## Pre-existing issues found, not fixed

1. **Declarations are never emitted.** `tsconfig.types.json` extends
   `tsconfig.json`, which sets `"noEmit": true`; that beats
   `emitDeclarationOnly`, so `tsc -p tsconfig.types.json` exits 0 and writes
   nothing. `package.json`'s `"types": "./dist/types/index.d.ts"` has never
   pointed at a real file, so consumers get no types from the package. Fixing
   it needs `"noEmit": false` plus an explicit `"rootDir": "lib"` (TS 7 raises
   TS5011 without it).
2. **Two lockfiles.** `package-lock.json` sits next to `yarn.lock`; yarn warns
   about it on every command. Only `yarn.lock` is used.
3. **yarn 1 cannot resolve vite incrementally here.** `yarn upgrade` and
   `yarn add vite@^8` both abort with "could not find a copy of vite to link in
   node_modules/vitest/node_modules" and leave node_modules half-built. The
   lockfile has to be deleted and resolved from scratch, which is why
   `836dcaf` carries a large yarn.lock diff.
4. **Stale `master-dep-updates` branch** — one 1.x-era commit, 38 behind
   master. Superseded; worth deleting.
5. **Untracked junk in the main checkout** — `coinrayjs-v1.9.12.tgz` and
   `coinrayjs-v1.9.12/`, 528K of old packaging artifacts.
