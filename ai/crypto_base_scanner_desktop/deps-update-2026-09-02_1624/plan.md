# Dependency update — crypto_base_scanner_desktop

- **Created:** 2026-09-02 16:24 (rebased onto 6.0.x and revised the same evening)
- **Base branch:** `release-6.0.x` (was `release-5.4.x`; prod is moving to 6.0.0)
- **Work branch:** `chore/deps-update-6.0` in `~/git/worktrees/cbsd-deps-60`
- **Status:** **done.** Squash-merged into `release-6.0.x` as `b2b9e10c2`
  ("Dependency update sweep for v6") on 2026-09-03 and pushed. Worktree removed.
  Ships with the first v6 release.
- **Repo order:** coinrayjs should have gone first — bignumber.js is gated on
  it. Apply that order to altrady-webview and any future sweep.

---

## Current state — 12 commits on `chore/deps-update-6.0`

| Commit | Contents |
| --- | --- |
| `4a429554` | quickjs 0.31→0.32, yaml-loader 0.8→0.9 |
| `acf218de` | eslint 9→10, @eslint/js 10, globals 17 |
| `d101699c` | webpack toolchain majors + 2 dead imports removed |
| `37c062c6` | electron 42→44, jsdom 27→29 |
| `ab237b4a` | uuid 14, react-moment 2, @sentry/webpack-plugin 5, lottie-react 3 |
| `33c15240` | i18next 26, react-i18next 17, highcharts 13, react-datepicker 9 |
| `26e512bc` | import tidy-up in top-bar and the TA-scanner indicator selector (Areg's) |
| `871bf472` | bignumber.js 9→11 |
| `b3701909` | Group A — everything inside existing semver ranges |
| `2ebefb6d` | route BigNumber construction through `bn()` — **later reverted** |
| `976c7887` | coinrayjs ^2.0.16 |
| `1a9a8694` | revert the `bn()` refactor |
| `4c33e901` | `BigNumber.set({STRICT: false})` — the actual fix |

`2ebefb6d` and `1a9a8694` cancel out. Left in history deliberately: the revert
message explains why the approach was wrong, which is worth keeping.

---

## Applied

**Group A — inside existing ranges (42 packages).** @sentry/react 10.53→10.73,
the @tiptap/* set 3.23→3.31, axios 1.16→1.20, webpack 5.106→5.110, react and
react-dom 19.2.6→19.2.8, react-router-dom 7.15→7.18, styled-components 6.4→6.5,
sass 1.99→1.103, jest 30.4→30.5, electron 42.2→42.11, electron-builder
26.8→26.15, dexie, dompurify, zod, postcss, autoprefixer, eslint 9.39.4→9.39.5,
@modelcontextprotocol/sdk, moment-timezone, country-flag-icons, css-loader,
html-webpack-plugin, babel-plugin-styled-components, lottie-react 2.4.1→2.4.2,
react-moment 1.2.2→1.2.3, @storybook/addon-essentials and @storybook/test.

**Majors.** eslint 10 + globals 17 · webpack-cli 7 · webpack-dev-server 6 ·
webpack-bundle-analyzer 5 · copy-webpack-plugin 14 · compression-webpack-plugin
12 · sass-loader 17 · postcss-nested 8 · electron 44 · jsdom 29 · uuid 14 ·
react-moment 2 · @sentry/webpack-plugin 5 · lottie-react 3 · i18next 26 +
react-i18next 17 · highcharts 13 · react-datepicker 9 · quickjs 0.32 ·
yaml-loader 0.9 · **bignumber.js 11**.

---

## The bignumber.js 9 → 11 saga

Worth reading before touching this dependency again.

### What broke, in two stages

**Stage 1 — the constructor.** The trading terminal crashed on load:

```
Error: [BigNumber Error] BigNumber, string, number, or BigInt expected: undefined
  at Util.safePrecision (util.js:615)  ->  new BigNumber(value)
  at TradeForm.safeBase -> new EntryOrder -> TradeForm.resetState
```

**Stage 2 — the methods.** After routing all 526 `new BigNumber(` sites through
a guarded `bn()` helper, a *different* crash appeared in the desktop app:

```
Error: [BigNumber Error] BigNumber, string, number, or BigInt expected: undefined
  at amount-field.js:59:55
```

Column 55 is `.dividedBy(max)` — `max` is the balance prop, undefined until
balances load. **Every coercing method** behaves like the constructor:
`plus`, `minus`, `dividedBy`, `multipliedBy`, `gt`, `gte`, `lt`, `lte`, `eq`.
That is ~1620 further call sites, on top of the 526 constructors. Guarding them
individually was never viable.

### The actual fix

Reading the changelog properly, which should have happened first:

- **v10.0.0** — *"Remove `BigNumber.DEBUG`, so the behaviour is now always as if
  it was `true`: throw on invalid input instead of returning `NaN`"*
- **v11.0.0** — *"Add `STRICT` configuration option: if `true` (default), throw
  an exception on invalid input. if `false`, return `NaN` on invalid input."*

So v10 removed the escape hatch and v11 restored it under a new name. One line
does what the 526-site refactor could not:

```js
BigNumber.set({STRICT: false})
```

It lands in **`src/polyfill.js`** — the first import in `src/index.js`, so it
runs before anything constructs a BigNumber — and again in **`jest.setup.js`**,
because jest never loads that entry. The Electron main process needs nothing:
`main.js` and `src/assets/` never touch BigNumber. The setting is global to the
module instance, and neither repo calls `BigNumber.clone()`, so nothing resets
it.

coinrayjs needs its **own** call: the vite lib build inlines bignumber.js into
`dist`, so the app's setting never reaches that copy. Done in its `lib/index.ts`.

### Why the code depends on this leniency

Not incidental. `util.numberToCurrency` and `numberToPercentage` branch on
`gte(0)` / `lt(0)` and fall through to `"-"` **only** when the value is NaN —
that dash is how "no value" renders. `safePrecision` has the same shape. Making
missing input throw, or coercing it to 0, both change what the UI shows.

### What did not catch it

A clean build, unchanged jest results, and a Playwright pass over the dashboard,
portfolio and trading terminal all went green while the bug was live. Those
paths had defined values. Stage 1 needed the trade form; stage 2 needed the
first render before balances arrived, reproduced by typing `1` in the amount
field and blurring. **Dependency upgrades of this kind need the app driven by
hand, not just built.**

### Remaining v10/v11 change worth knowing

**Underscores are now valid separators** — `new BigNumber("1_0")` returns `10`,
where v9 gave NaN. Inputs use `inputMode="decimal"`, a hint rather than a
filter, so a pasted `1_0` silently becomes 10 in amount and price fields. Not
fixed; flagged.

Checked and clear: no two-argument `base` constructor calls, no `toFraction`
usage, no global `BigNumber`, and BigNumber serialises to a **string** (not
`{c, e, s}`), so redux-persist rehydration is unaffected by v10's new property
validation.

---

## Dropped, with reasons

1. **tailwindcss 3 → 4** — `twin.macro@3.4.1` peers `tailwindcss >=3.3.1` and
   has no v4 support; v4 removed the JS config surface twin.macro reads at build
   time. Dropping or replacing twin.macro is its own project.
2. **flexlayout-react 0.7.15 → 0.10.8** — compiles, breaks the layout at
   runtime. 6.0.x still calls the 0.7.15 API (`titleFactory`, the
   `tabSetTabStripHeight` and `splitterSize` globals), all removed in 0.9. The
   migration already exists on `feature/superchart-integration` (`6a4466d27`,
   0.7.15 → 0.9.0) — do it there.
3. **@babel/core 7 → 8** — `babel.config.js` uses the `react-app` preset and
   `babel-preset-react-app@10.1.0` (latest, Feb 2025) still depends on
   `@babel/core ^7.16.0`. Babel 8 fails the build outright.
4. **jsdom 30** — requires node `^22.22.2 || ^24.15.0 || >=26`; this machine runs
   24.11.1. Settled on 29. Decided not to bump node: the only gain is a dev-only
   test dep.
5. **Storybook** — `@storybook/builder-webpack5` and `@storybook/cli` are
   stranded on 6.5.16 while the rest sit on 8.6.x (latest 10.5.10). Its own
   project.

---

## Rebasing 5.4.x → 6.0.x

`release-6.0.x` fully contains `release-5.4.x` (0 commits behind; the merge base
*is* the original branch point), so the nine dependency commits cherry-picked
cleanly — only `yarn.lock` conflicted, and that is regenerable.

The mechanical `bn()` commits were **re-derived** rather than cherry-picked,
avoiding 33 conflicting files. That paid off: 6.0.x had **two more** local `bn`
bindings than 5.4.x (`actions/journal.js`,
`journal/backtest-position-review.js`), which a cherry-pick would have clobbered
silently. Moot now that the refactor is reverted, but the lesson stands — a
blind mechanical replace must check for existing bindings of the name first.

One real find: Electron 44 initially broke the install. electron-builder 26.8.1
ships a `node-abi` that does not know Electron 44, so `install-app-deps` dies
with *"Could not detect abi for version 44.1.1"*. Group A's bump to
electron-builder 26.15.3 (node-abi 4.35.0) fixes it — the two must land
together.

Verified after the rebase: every dependency version matches the 5.4-based branch
exactly, nothing lost, and 6.0.x's own four additions (lightweight-charts,
@tiptap/extension-image, remark-breaks, remark-gfm) are intact and already at
latest.

---

## Verification

- Dev and production web builds: clean. The production build emits fully and the
  Sentry sourcemap upload works; only the final S3 push fails, on missing AWS
  credentials locally.
- Electron main bundle builds; electron-builder rebuilt bufferutil,
  register-scheme and utf-8-validate against Electron 44.
- Jest: 40/55 suites, 354 passing, unchanged at every commit. The 15 failing
  suites and 1 failing test pre-date this work.
- ESLint runs under 10.x; 3788 problems against 3769 before, all pre-existing.
- Playwright against production as reference (on the 5.4 branch, still
  representative): dashboard, portfolio and trading terminal render; Highcharts
  13 draws the portfolio line chart, assets donut and sparklines; the
  react-datepicker 9 calendar matches production pixel for pixel, including its
  light popup, which is pre-existing styling; i18next 26 resolves every string;
  the TradingView chart, drawing toolbar and flexlayout panels match a clean
  baseline built side by side; the tiptap 3.31 editor mounts and emits correct
  HTML.
- Areg's smoke test cleared the four lottie-react 3 animations (vault
  create/unlock, both onboarding heroes, replay buttons included), Highcharts
  parity with production, the datepicker re-querying on date selection, note
  save/reload, and language switching.

---

## Also in this branch

Two dead imports removed (`5a64d87c`, carried as `d101699c`): `top-bar.js`
imported `setIncludeWalletStatistics`, which `actions/exchange-api-keys` never
exported, and ta-scanner's `indicator-selector.js` imported `LORS` from
`rule-builder-modal`, which only exports `RULE_COLORS` and a default. Neither
name was referenced. Both pre-date this branch; webpack 5.110 surfaces them as
warnings, which put the dev-server overlay over the whole app.

react-datepicker 9 builds its date-fns locale request at runtime, which webpack
cannot analyse statically, so it emits a "Critical dependency" warning from
inside the library. Filtered via `ignoreWarnings` in the four webpack configs,
scoped to that module and message.

---

## Branch plan (decided 2026-09-02)

Two tracks, deliberately separated:

1. **`chore/deps-update-6.0`** — everything already done and tested. **Merged**
   into `release-6.0.x` as `b2b9e10c2` on 2026-09-03 and pushed; ships with the
   first v6 release.
2. **A second branch/worktree** — the deferred work: Babel 8, the Emotion swap,
   removing twin.macro, Tailwind 4. Not started, and does not hold up the v6
   release. Now planned as two independent stages; `deferred/README.md` is the
   entry point.

Per-item write-ups live in `deferred/`:

| File | Covers |
| --- | --- |
| `deferred/babel.md` | @babel/core 8 — both blockers, and the verified fix |
| `deferred/tailwind.md` | Tailwind 4 + removing twin.macro, with migration patterns and config impact |
| `deferred/styling-stack.md` | Shared research: the Babel 8 experiment, the Emotion risk audit, Superchart findings |
| `deferred/README.md` | **Start here** — the two-stage plan and the blast radius of each stage |

Not yet written: `flexlayout`, `jsdom`, `storybook` — those three remain
described in the "Dropped, with reasons" section above.

## Open

- **Benoist has not published coinrayjs 2.0.17 yet.** He has been notified.
  `package.json` already pins `^2.0.17`, so `yarn install` on a clean checkout
  fails until it is on npm. Whoever picks this up next should check the registry
  first.
- **The deferred styling work** — stages 1 and 2, see `deferred/README.md`. Not
  scheduled; other work has priority.
- **altrady-webview has not been started.** It was third in the sweep order and
  never reached. It does not use coinrayjs, so it carries no bignumber
  coordination.
- **Three leftover branches**, all superseded by `b2b9e10c2` and safe to delete
  once the merge has been running a while: `chore/deps-update-6.0`,
  `chore/deps-update-2026-09`, `chore/deps-update-2026-09-5.4-backup`. Left in
  place deliberately — they hold the unsquashed history, including the reverted
  `bn()` refactor, if the bignumber decision ever needs revisiting.
