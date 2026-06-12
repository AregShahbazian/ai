---
id: pc-pivots
---

# Pivot detection — bot-computed swing highs/lows, visualized on the chart

Builds on [`../../mvp/prd.md`](../../mvp/prd.md). Origin:
[`../../discussions/2026-06-12-pivot-detection.md`](../../discussions/2026-06-12-pivot-detection.md)
(+ part 2).

## Requirements

### 1. Detection (bot-backend)

- The bot detects **swing highs/lows (pivots)** over the candles available to
  it so far — seeded history plus stepped/run candles. No lookahead: a pivot
  only exists once `lookback` candles after it have been seen.
- Detector: a candle is a swing high (low) when its high (low) is the extreme
  of the `lookback` candles on each side. Defaults: `lookback = 3`.
- **Alternation enforcement** (togglable, default on): consecutive same-side
  pivots collapse to the strongest, yielding strictly alternating high/low.
- Each pivot reports `time`, `type` (`high`|`low`), `price` (the extreme), and
  `confirmedAt` (time of the candle that confirmed it).

### 2. Options — persisted, editable, live-controllable

- Frontend option set: **show pivots** (on/off), **lookback**, **alternation**.
  Persisted across reloads.
- Editable **before any session** (replay or headless) — sent to the bot with
  the session.
- During an active **replay** session: options stay editable as a live control —
  a change goes to the bot, which recomputes and returns updated pivots
  immediately.

### 3. Visualization (frontend)

- Pivots render as **triangle markers**: above swing highs (pointing down),
  below swing lows (pointing up), visually distinct from trade markers.
- Replay honesty: a pivot's marker appears only when the replay cursor has
  reached its `confirmedAt` (also when stepping back).
- Pivots cover the seeded pre-start history too, and appear on **headless**
  results and on **loaded finished sessions**.

## Non-requirements

- No pivots on the live (non-session) chart.
- No trading logic consuming pivots; visualization only.
- No server-side persistence of pivots or pivot options (frontend persistence
  only); no ZigZag %-threshold mode; no option edits mid-headless-run.
