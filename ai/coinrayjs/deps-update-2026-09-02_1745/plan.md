# Dependency update — coinrayjs

- **Created:** 2026-09-02 17:45 (revised the same evening)
- **Base branch:** `master` (was 2.0.15)
- **State:** squash-merged into `master`, worktree removed. **Not pushed, not
  published** as of 2026-09-03. Areg decides when it is released; Benoist holds
  the npm credentials and has been asked for 2.0.17.

---

## Current state — `master`

| Commit | Contents |
| --- | --- |
| `431b2c8` | 2.0.16 — dependency updates (squashed from the work branch) |
| `6e36cbd` | replace `bn()` with `BigNumber.set({STRICT: false})` |
| `306e024` | 2.0.17 |

**2.0.17 is the version to publish.** 2.0.16 was handed to Benoist before the
STRICT fix existed; publishing it would ship the `bn()` approach and none of the
real fix.

---

## Applied

Everything on offer. Nothing was blocked or dropped.

- axios 1.12.2 → 1.20.0
- jose 6.1.0 → 6.2.10
- lodash 4.17.21 → 4.18.1
- phoenix 1.8.1 → 1.8.13
- vitest 4.1.3 → 4.1.11
- vite 7 → 8
- uuid 13 → 14
- @types/node 25 → 26
- typescript 5.9 → 7.0
- bignumber.js 9 → 11

`@types/node` 26 describes a newer Node than the machine runs (24.11.1), which
would normally risk type-checking against APIs missing at runtime — but `lib/`
uses **zero** Node APIs (no `node:` imports, no `Buffer`, no `process`). It is
only there to satisfy `"types": ["vite/client", "node"]` in tsconfig, and since
declarations are never emitted (see below) it never reaches consumers either.

---

## bignumber.js 9 → 11 — read this before touching it again

v10 removed `BigNumber.DEBUG` and made invalid input (`undefined`, `null`, `""`,
`"abc"`) **throw** instead of yielding `NaN`. That applies to the coercing
methods — `plus`, `minus`, `dividedBy`, `multipliedBy`, `gt`, `lt`, `eq` — as
well as the constructor. v11 reintroduced the escape hatch as the `STRICT`
option.

The first attempt guarded only construction, via a `bn()` helper across 13 sites
in `lib/`. That was wrong: it left the ~1620 method call sites in the consumer
untouched, and the desktop app duly crashed on `.dividedBy(max)` with an
undefined `max`. `6e36cbd` removes `bn()` entirely — `lib/` is byte-identical to
its pre-refactor state — and replaces it with one line in `lib/index.ts`:

```ts
BigNumber.set({STRICT: false})
```

**It has to live here, not in the consumer.** The vite lib build inlines
bignumber.js into `dist`, so that bundle carries its own private copy; a
consumer setting STRICT on *its* copy never reaches it. Both repos need the
call.

Placement note: ES module bodies run after all imports evaluate, so this
executes after `./coinray` and friends are loaded. Safe today — none of them
construct BigNumbers at import time. If that ever changes it needs to move to a
side-effect module imported first, the pattern cbsd uses in `src/polyfill.js`.

Consumers must move to bignumber.js 11 **in the same step**. If the versions
split, package managers install one copy at the top level and another nested
here, and any `instanceof BigNumber` check on the consumer side silently returns
false for values this library produced.

---

## Cross-repo verification

Packed with `yarn pack` and installed into the cbsd branch as a tarball rather
than `yarn link`, deliberately: webpack resolves symlinks to their real path, so
a linked coinrayjs loads its *own* bignumber copy and manufactures a
duplicate-instance problem a published package would not have. A tarball hoists
one copy, which is what production looks like. Confirmed exactly one
`bignumber.js` 11.1.5 in the whole tree.

That first pass looked clean — portfolio balances, the aggregate position panel,
order-form arithmetic (77085.71 × 0.01234 = 951.2376614, no float drift), cbsd
jest and web build all fine. **It was not clean.** The failure only appeared in
the desktop app on the trade form. Green builds and passing tests are not
sufficient evidence for this kind of upgrade; the app has to be driven by hand.

---

## Verification

- `yarn test`: 6 suites, 17 passing, 1 skipped.
  - Three suites (endpoints, cache, candle boundary) `skipIf(!token)` and were
    silently skipped until a token was supplied. They cover exactly the
    axios/jose/phoenix surface the upgrades touch, so they matter.
  - Token setup already existed and needed nothing built: `.env.example` is
    tracked with `VITE_COINRAY_TOKEN=`, `.gitignore` covers `.env`/`.env.*` with
    `!.env.example`, and the tests read `import.meta.env`. Only the `.env` file
    itself was missing.
  - A first token failed every network test with `403 — Authentication failed
    code: 4005, "Client id missing"`. Cause: `lib/coinray.ts:1043` derives the
    client id from the JWT header's `kid`, and that token had none. A
    client-scoped token with `kid` set fixed it.
- `yarn build`: clean. Noticeably faster under vite 8 (~250ms against ~1.4s).
  The MIXED_EXPORTS warning is pre-existing.
- TypeScript 7 type-checks `lib/` with no errors.

---

## Pre-existing issues found, not fixed

1. **Declarations are never emitted.** `tsconfig.types.json` extends
   `tsconfig.json`, which sets `"noEmit": true`; that beats
   `emitDeclarationOnly`, so `tsc -p tsconfig.types.json` exits 0 and writes
   nothing. `package.json`'s `"types": "./dist/types/index.d.ts"` has never
   pointed at a real file — consumers get no types. Fixing it needs
   `"noEmit": false` plus an explicit `"rootDir": "lib"` (TS 7 raises TS5011
   without it).
2. **Two lockfiles.** `package-lock.json` sits beside `yarn.lock`; yarn warns on
   every command. Only `yarn.lock` is used.
3. **yarn 1 cannot resolve vite incrementally here.** `yarn upgrade` and
   `yarn add vite@^8` both abort with *"could not find a copy of vite to link in
   node_modules/vitest/node_modules"* and leave node_modules half-built. The
   lockfile has to be deleted and resolved from scratch, which is why the
   squashed commit carries a large yarn.lock diff.
4. **CRLF → LF.** Four files (`exchange.ts`, `current-market.ts`,
   `limit-ladder.ts`, `util.ts`) changed line endings during the `bn()` refactor
   and stayed LF after it was removed. The repo is mixed, with no
   `.gitattributes`. Areg reviewed and accepted this.
5. **No release automation.** The only workflow is `docs.yml`, which deploys
   docs to GitHub Pages on push to master. No publish job, no tag trigger, no
   `NPM_TOKEN`, no `prepublishOnly`. Publishing is a manual `npm publish` by
   whoever holds the credentials.
6. **Stale `master-dep-updates` branch** — one 1.x-era commit, 38 behind master.
   Superseded; worth deleting.

---

## Open

- **Benoist to publish 2.0.17** (not 2.0.16). Notified 2026-09-03; not yet on
  npm. Nothing here is pushed either — `master` carries the three commits
  locally only.
- cbsd already pins `^2.0.17` on `release-6.0.x` (`b2b9e10c2`, merged and
  pushed), so **a clean `yarn install` there fails until 2.0.17 is published.**
  That is the one thing blocking anyone else picking up the v6 branch.
- cbsd is the only known consumer: the backend is Ruby and altrady-webview does
  not use coinrayjs, so no other repo needs the coordinated bignumber move.
