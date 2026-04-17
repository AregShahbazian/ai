# Settings Preview Chart — Deferred Items

Items intentionally excluded from `prd.md` (`sc-settings-preview`). Revisit when
the listed blocker resolves.

_No items currently deferred._

## Resolved

### Hide the SC period-bar on the preview — shipped

SC now exposes `periodBarVisible: boolean` on `SuperchartOptions` and
`setPeriodBarVisible(visible: boolean)` on `SuperchartApi`. Wired in
`preview-super-chart.js` as `new Superchart({ ..., periodBarVisible: false })`.
The preview now renders no period-bar at all.
