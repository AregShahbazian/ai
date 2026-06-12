# Pivot (swing high/low) detection — 2026-06-12

## Summary

Compared a manual selection of 8 "tops and bottoms" candles (saved via the candle
tools export) against algorithmic pivot detection on a BTCUSDT 1h window
(101 candles, 07–12 Jun 2026). Standard terminology: **swing highs/lows**,
**pivot points**, **local extrema**. A simple symmetric-window pivot detector
(candle's high/low is the extreme of N candles on each side) with **N=3** found
all 8 manual selections among 17 pivots; N=5 kept 7/8. The manual selection
alternated HIGH/LOW perfectly — i.e. the eye naturally picks ZigZag-style
alternating swings — so **alternation enforcement** (collapse consecutive
same-side pivots to the strongest) was decided on as the right default behavior.

## Key conclusions

- Pivot detection with lookback N=3 + alternation reproduces the manual
  "obvious tops and bottoms" almost exactly. Extra detected pivots are minor
  swings the user skipped, not false positives.
- For the bot, this is cheap to compute incrementally on candles-so-far.
- First deliverable is visualization-only: bot returns pivots, frontend marks
  them on the chart. No trading logic on top yet.

## Decisions

- Alternation enforcement becomes a **persisted, togglable option** on
  the bot/session config — editable **before a headless session**, and
  **live-adjustable during a replay session** (live-control interface with
  the bot).
- When the frontend enables the option, the bot runs pivot analysis over the
  candles available so far and returns the pivot candles with their direction.
- Proposed response format (Claude to refine during implementation):

  ```json
  {
    "params": { "lookback": 3, "alternation": true },
    "pivots": [
      { "time": 1780869600, "type": "high", "price": 64234.68 },
      { "time": 1780894800, "type": "low",  "price": 62408.0 }
    ]
  }
  ```

  Optional extras if useful later: `strength` (max N for which the pivot
  holds), `confirmedAt` (time of the candle that confirmed it — a pivot is
  only knowable N candles after the fact).

## Open questions

- Exact lookback default (N=3 worked; expose as a param next to alternation?).
- Whether ZigZag (% reversal threshold) should be an alternative detector mode.
- How the live-control channel during replay sessions is shaped (this is the
  first live-tunable bot option — sets the pattern for future ones).

## Ideas to realize

- **Pivot detection in bot backend**: symmetric-window swing high/low detector
  (lookback N, default 3) over candles-so-far; return pivots
  (`time`, `type: high|low`, `price`) to frontend for chart visualization.
- **Alternation enforcement option**: persisted, togglable; collapses
  consecutive same-side pivots to the strongest, yielding clean alternating
  swing structure.
- **Pre-session option editing**: bot options (incl. alternation) configurable
  before launching a headless session.
- **Live-control interface during replay**: change bot options (incl.
  alternation) mid-replay-session and have the bot re-run/refresh analysis.
- **Frontend pivot visualization**: mark returned pivot candles on the chart,
  distinguishing highs (up) vs lows (down).
- Later candidates: `strength` and `confirmedAt` fields on pivots; ZigZag
  %-threshold detector as an alternative mode; HH/HL trend-structure analysis
  built on alternating pivots.
