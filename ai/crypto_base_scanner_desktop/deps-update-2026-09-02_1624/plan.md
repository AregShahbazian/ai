# Dependency update — crypto_base_scanner_desktop

- **Created:** 2026-09-02 16:24
- **Target branch:** `release-5.4.x` (baseline for the audit below)
- **Work branch:** to be created off `release-5.4.x`, in a worktree under
  `~/git/worktrees/` (this repo's tree is on `feature/superchart-integration`)
- **Merge policy:** merged only after Areg has tested it.
- **Repo order:** crypto_base_scanner_desktop → coinrayjs → altrady-webview.

Audit taken 2026-09-02 against the npm registry, using `release-5.4.x`'s
`package.json` + `yarn.lock`. 141 direct deps, 74 already current.

---

## Group A — within existing semver ranges (42 packages)

Picked up by a plain `yarn upgrade`; no `package.json` edits needed.

| Package | current → wanted |
| --- | --- |
| @sentry/react | 10.53.1 → 10.73.0 |
| @tiptap/core, /pm, /react, /starter-kit, /suggestion, /extension-history, /extension-placeholder | 3.23.5 → 3.31.0 (7 pkgs) |
| axios | 1.16.1 → 1.20.0 |
| electron (dev) | 42.2.0 → 42.11.1 |
| electron-builder | 26.8.1 → 26.16.0 |
| electron-updater | 6.8.3 → 6.8.9 |
| webpack | 5.106.2 → 5.110.3 |
| webpack-dev-server | 5.2.4 → 5.2.6 |
| react, react-dom | 19.2.6 → 19.2.8 |
| react-router-dom | 7.15.1 → 7.18.3 |
| styled-components | 6.4.2 → 6.5.3 |
| sass | 1.99.0 → 1.103.1 |
| jest, jest-environment-jsdom, babel-jest | 30.4.x → 30.5.1 |
| @babel/core, /plugin-transform-modules-commonjs, /plugin-transform-react-jsx | 7.28–7.29 → 7.29.7 |
| dexie | 4.4.2 → 4.4.5 |
| dompurify | 3.4.11 → 3.4.14 |
| zod | 4.4.3 → 4.5.4 |
| postcss | 8.5.15 → 8.5.26 |
| autoprefixer | 10.5.0 → 10.5.4 |
| eslint, @eslint/js | 9.39.4 → 9.39.5 |
| @modelcontextprotocol/sdk | 1.29.0 → 1.30.0 |
| moment-timezone | 0.6.2 → 0.6.3 |
| country-flag-icons | 1.6.17 → 1.6.20 |
| css-loader | 7.1.4 → 7.1.5 |
| html-webpack-plugin | 5.6.7 → 5.6.8 |
| babel-plugin-styled-components | 2.1.4 → 2.3.0 |
| lottie-react | 2.4.1 → 2.4.2 |
| react-moment | 1.2.2 → 1.2.3 |
| @storybook/addon-essentials, @storybook/test | 8.6.14/8.6.15 → 8.6.18 |

---

## Group B — major / out-of-range (36 packages)

Each needs a `package.json` bump and real testing. Do these in themed commits
so Areg can test and revert per group.

### B1 — low risk (minor bumps, just pinned tight)
- `flexlayout-react` 0.7.15 → 0.10.8 — note `feature/superchart-integration`
  already runs `^0.9.0`; see `../flexlayout-depup/prd.md`
- `quickjs-emscripten-core` + `@jitl/quickjs-wasmfile-release-sync` 0.31 → 0.32
  (must move together — same release train)
- `yaml-loader` 0.8.1 → 0.9.0

### B2 — toolchain majors
- `electron` 42 → 44 (dev; electron-builder already on 26.x)
- `eslint` 9 → 10, `@eslint/js` → 10, `globals` 16 → 17
- `@babel/core` + the 2 plugins 7 → 8
- `webpack-cli` 6 → 7, `webpack-dev-server` 5 → 6,
  `webpack-bundle-analyzer` 4 → 5, `copy-webpack-plugin` 13 → 14,
  `compression-webpack-plugin` 11 → 12, `sass-loader` 16 → 17,
  `postcss-nested` 7 → 8
- `jsdom` 27 → 30
- **Storybook** — inconsistent today: `@storybook/builder-webpack5` and
  `@storybook/cli` are still on **6.5.16** while the rest sit on 8.6.x; latest
  is 10.5.10. Treat as its own mini-project, not part of a general sweep.

### B3 — app-facing majors (need UI testing)
- `tailwindcss` 3.4.19 → 4.3.3 — **DEFERRED, see blocker below**
- `highcharts` 12.6 → 13.0.2
- `i18next` 25 → 26 **+** `react-i18next` 16 → 17 (must move as a pair)
- `bignumber.js` 9.3.1 → 11.1.5 — care needed, it sits in price/precision paths
- `react-datepicker` 8 → 9
- `uuid` 13 → 14
- `lottie-react` 2 → 3
- `react-moment` 1 → 2
- `@sentry/webpack-plugin` 4 → 5

---

## Blocker — tailwindcss 4 is gated by twin.macro (DEFERRED)

Areg recalled a past twin.macro / tailwind incompatibility. Nothing was written
down at the time — searched the commit history across all branches
(`twin`, `tailwind`, `dependenc`, `upgrade`, `deps`, `macro`), and the only
related commits are one-line fixes (`a01c8aadb`, `4a09fb7d2`, `d53434894`) with
no notes. The constraint is nonetheless real and current:

- `package.json` pins `twin.macro@^3.4.1` and `tailwindcss@^3.4.16`.
- `twin.macro@3.4.1` declares `peerDependencies: { tailwindcss: ">=3.3.1" }`
  and has **no Tailwind 4 support** — v4 dropped the JS config/`resolveConfig`
  surface twin.macro reads at build time through `babel-plugin-macros`.

**Decision (2026-09-02): defer the Tailwind 4 upgrade.** It is not a version
bump; it requires either dropping twin.macro (migrating every `tw` prop /
`tw` template usage) or replacing it. Revisit as its own feature, separately
from this deps sweep.

---

## Execution order

1. Create worktree + branch off `release-5.4.x`.
2. Group A — one `yarn upgrade` pass, one commit. Smoke test.
3. B1 — low-risk pins, one commit.
4. B2 — toolchain, split per themed commit (lint / babel / webpack / electron /
   test), each independently revertible.
5. B3 — app-facing, one commit per package (or per pair for i18next).
6. Storybook and Tailwind 4 explicitly out of scope for this sweep.
7. Hand over uncommitted-nothing: everything committed on the branch, not
   pushed, for Areg to test and merge.

---

# RESULTS — 2026-09-02

Branch `chore/deps-update-2026-09` off `release-5.4.x`, in the worktree
`~/git/worktrees/cbsd-deps-update`. Seven commits, none pushed.

| Commit | Contents |
| --- | --- |
| `1d8f5912` | Group A — 42 packages inside existing ranges |
| `e4770795` | quickjs 0.31→0.32, yaml-loader 0.8→0.9 |
| `63d434d7` | eslint 9→10, @eslint/js 10, globals 17 |
| `5a64d87c` | webpack toolchain majors + 2 dead imports removed |
| `1081f0bf` | electron 42→44, jsdom 27→29 |
| `f060987a` | uuid 14, react-moment 2, @sentry/webpack-plugin 5, lottie-react 3 |
| `deb452f7` | i18next 26, react-i18next 17, highcharts 13, react-datepicker 9 |
| `e242841b` | import tidy-up in top-bar and the TA-scanner indicator selector (Areg's edits) |
| `948eea60` | route all BigNumber construction through `bn()` |
| `844480e4` | bignumber.js 9→11 |
| `05d5468e` | fix `bn()` name collisions from that refactor |

## Verification

- Dev web build: clean, no warnings.
- Production web build (`webpack.build-web.config.js`): compiles and emits
  fully, Sentry sourcemap upload works. Only the final S3 push fails, on
  missing AWS credentials locally — not a dependency problem.
- Electron main bundle builds; electron-builder rebuilt bufferutil,
  register-scheme and utf-8-validate against Electron 44.
- Jest: 22/37 suites, 166 passing, unchanged from the branch point through
  every commit. The 15 failing suites and 1 failing test are pre-existing.
- ESLint: runs; 3788 problems vs 3769 before, all in pre-existing code.
- Playwright, logged into staging, with production as the reference:
  dashboard, portfolio and the trading terminal all render; Highcharts 13
  draws the portfolio line chart, the assets donut and the sparklines;
  the react-datepicker 9 calendar matches production pixel for pixel
  (including its light popup, which is pre-existing styling, not a
  regression); i18next 26 resolves every string; the TradingView chart,
  drawing toolbar and flexlayout panels are identical to a clean
  `release-5.4.x` baseline built and served side by side; the tiptap 3.31
  note editor mounts, accepts input and emits correct HTML.

## Dropped from the sweep, with reasons

1. **tailwindcss 3 → 4** — the pre-existing blocker above. twin.macro has no
   Tailwind 4 support.
2. **flexlayout-react 0.7.15 → 0.10.8** — compiles, but breaks the layout at
   runtime. `release-5.4.x` still calls the 0.7.15 API (`titleFactory`, the
   `tabSetTabStripHeight` and `splitterSize` globals), all removed in 0.9.
   Needs the source migration that already exists on
   `feature/superchart-integration` (commit `6a4466d27`, 0.7.15 → 0.9.0).
   Do it there, not here.
3. **@babel/core 7 → 8** — `babel.config.js` uses the `react-app` preset, and
   `babel-preset-react-app@10.1.0` (latest, Feb 2025) still depends on
   `@babel/core ^7.16.0`. With Babel 8 the build dies outright. Unblocking it
   means dropping babel-preset-react-app for an explicit preset list.
4. **jsdom 30** — needs node `^22.22.2 || ^24.15.0 || >=26`; this machine is on
   24.11.1, so yarn refuses it. Took 29 instead. Revisit after a node bump.
5. **bignumber.js 9 → 11** — *no longer dropped; done.* See the addendum below.
6. **Storybook** — left alone. `@storybook/builder-webpack5` and
   `@storybook/cli` are still on 6.5.16 while the rest are on 8.6.x, and latest
   is 10.5.10. Its own project.

## Smoke test — cleared by Areg, 2026-09-02

Everything I could not reach myself has been confirmed working in the browser:

- The four **lottie-react 3** animations (vault create, vault unlock, and both
  onboarding heroes) play correctly, replay buttons included. This was the one
  migration done blind against a rewritten API, so it was the main open risk.
- **Highcharts 13** portfolio charts look identical to production.
- **react-datepicker 9** — picking a date re-queries the chart, not just the
  calendar rendering.
- **tiptap 3.31** — saving and reloading a note works.
- **i18next 26 / react-i18next 17** — language switching works.

No regressions found. The branch is ready to merge whenever Areg wants it.

## Note on ordering

Doing **coinrayjs before the desktop app** would have been better — bignumber.js
is gated on it. Apply that order to the remaining repos.


---

# ADDENDUM — bignumber.js 9 → 11, 2026-09-02 evening

Reversed the earlier decision to defer this. It is now applied in both repos,
and coinrayjs was upgraded in the same session so the two move together.

## What broke

Bumping the version alone crashes the trading terminal on load:

```
Error: [BigNumber Error] BigNumber, string, number, or BigInt expected: undefined
  at Util.safePrecision (util.js:615)  ->  new BigNumber(value)
  at TradeForm.safeBase -> new EntryOrder -> TradeForm.resetState
```

bignumber.js 10 made the constructor **throw** on input it cannot parse
(`undefined`, `null`, `""`, `"abc"`) where 9 returned a NaN BigNumber. The
codebase leans on that leniency — `util.numberToCurrency` and
`numberToPercentage` branch on `gte(0)`/`lt(0)` and fall through to `"-"`
exactly when the value came back NaN.

Note what did *not* catch this: a clean build, unchanged jest results, and a
portfolio/PnL smoke test all passed. Those paths had defined values. Only
opening the trade form triggered it.

## The fix

A single helper, `src/util/bn.js`, that forwards to the constructor and returns
NaN instead of throwing:

```js
export const bn = (...args) => {
  try { return new BigNumber(...args) } catch { return new BigNumber(NaN) }
}
```

All **526** `new BigNumber(` sites across 81 files now call it (13 sites across
4 files in coinrayjs, via `lib/bn.ts`). Mechanical and behaviour-preserving:
`bn()` is the constructor for every input BigNumber already accepted, so the
refactor is a no-op on version 9 and each commit stands alone.

The `BigNumber` import is kept wherever the name is still referenced
(`ROUND_DOWN`, `isBigNumber`, `instanceof`, TS type positions) and dropped where
only comments mentioned it.

## Collisions the blind replace caused

The replace was not scope-aware, and three files already had a local binding
called `bn`. Fixed in `05d5468e`:

- `signal-bot/entry-orders.js` — `toFiniteBig`'s local `bn` ended up assigned
  from itself, a TDZ ReferenceError on every call. Renamed to `big`.
- `signal-bot/legacy-migration.js` — its own `bn` helper had its body rewritten
  to call itself. Renamed to `toAmount`, kept as a distinct helper because it
  falls back to **0** where `bn()` gives NaN, and those values are summed into
  a bot's "Invested" total, which NaN would poison.
- `bots/bot-list-row.js` — two locals shadowed the import harmlessly. Renamed
  to `amount`.

Test files were left alone: 235 `new BigNumber(` calls there, all string
literals, none of which throw.

## Still open

Only two `new BigNumber(` sites in coinrayjs were audited closely
(`safeBigNumber`, guarded by `!d`; and orderbook price keys, always strings).
The rest were literal zeros.

Awaiting Areg's testing with the linked coinrayjs.
