# Review: Trendline Alerts — SuperChart Integration

## Round 1: TV trendline doesn't sync with SC edits (2026-03-25)

### Bug 1: SC drag updates form but TV trendline stays at old position

**Symptom:** Moving the editing trendline in SC correctly updates the alert form (Point A/B values), but the TV chart's trendline doesn't move. Moving in TV correctly updates both TV and SC.

**Root cause:** TV's `TrendLineAlert` in `edit-alerts.js` has `useEffect(() => {...}, [])` — empty dependency array (line 76). It draws the trendline once on mount and reads position only via its own `mouse_up` subscriber. It never re-renders when Redux `alertsForm` changes from an external source (SC).

This is a pre-existing TV design limitation, not an SC code issue. TV was built for single-chart interaction — it assumed the user only edits trendlines directly in TV.

**Direction:** SC → TV sync (`alertsForm` → TV re-draw) works for other alert types:
- Price alerts: TV's `edit-alerts.js` PriceAlert does react to `alertsForm` changes (it re-renders the order line).
- Time alerts: TV's `edit-alerts.js` TimeAlert also has empty deps `[]` — same limitation exists for time alerts too.

Both trendline and time alert editing in TV subscribe to `mouse_up` rather than reacting to Redux state.

**Fix:** Restructured TV's `TrendLineAlert` to follow the `TimeAlert` pattern — extracted `clear`/`draw` callbacks with proper deps, added `alert` to `mouseUp` deps, effect now depends on `draw`. When SC dispatches `editAlert()` with new points, the effect re-runs: cleanup removes the old TV entity, draw creates a new one at the updated position.
**Files:** `src/containers/trade/trading-terminal/widgets/center-view/tradingview/edit-alerts.js`

### Verification
- [x] SC drag updates alert form Point A/B values
- [x] SC drag correctly saves to server when form is submitted
- [x] TV → SC sync works (TV drag updates SC overlay position)
- [x] SC → TV sync works (SC drag updates TV trendline position)
- [x] Symbol change clears trendline overlays
- [x] `alertsShow` toggle hides/shows trendline overlays
- [x] Triggered trendline alerts appear when `alertsShowClosed` is on
