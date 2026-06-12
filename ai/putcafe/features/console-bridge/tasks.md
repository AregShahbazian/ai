# Console bridge — tasks

1. **Bridge core** — `src/debug/bridge.ts`: registry (app/chart handles,
   engine), snapshot tap + event ring buffer (seq, 500), waiters
   (`status`/`time`/`trade`/`finished`, timeout), awaitable playback actions,
   `playTo`, `session.*`, `state.*`, `chart.*` passthrough, `backend.*`,
   `verify()`, `dump`, `help`, `ready`, `version`; `window.pc` install.
2. **App wiring** — `App.tsx`: snapshot tap in engine ctor, register
   `AppHandle` (UI-synced `startSession(overrides)` incl. market/interval
   pre-sync, stop/loadPreset/loadSession, ui getters via render-updated ref),
   drop the ad-hoc `pc()` effect.
3. **Chart wiring** — `ChartView.tsx`: capture refs for markers; register
   `ChartHandle` (visibleRange, markers, pivotShapes, priceLines via
   `options()`, rangeHighlight via prop ref, renderedCandles).
4. **Playwright proof** — add `@playwright/test`, `playwright.config.ts`,
   `e2e/bridge.spec.ts` (fixed-range headless verify + replay playTo +
   chart assertions), `yarn e2e` script.
5. **Verify & review** — `tsc -b` + `vite build`; live check via Playwright
   against `yarn dev` + VPS backend; `review.md`.

Status: all done (see review.md).
