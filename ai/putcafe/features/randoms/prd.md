---
id: pc-randoms
---

# Random backtest range — dice-roll start/end date pickers

**Branch:** `feature/randoms` · **Worktree:** `~/git/worktrees/putcafe/randoms`

Builds on the backtest tooling (`pc-mvp`) and the range/preset model
(`pc-presets`). Origin: ad-hoc request — make it one click to throw the
backtest at a random slice of the current market's history.

## Problem

Picking a backtest range is manual: the user types/scrolls start and end dates
every time they want to sample a different stretch of the market. Exploring how
a strategy behaves across many historical regimes (trend, chop, crash) means
lots of repetitive date entry, and people unconsciously cherry-pick the ranges
they already know.

## Goal

**Random time-picker buttons** in the Backtest panel that fill the start/end
range with a random window inside the **current market + resolution's**
available kline history — one click to jump to an unbiased random slice, then
**Start** runs it as usual.

## Requirements

- **R1 — Randomize button(s).** A control in the Backtest range area that rolls
  a random start/end pair and writes it into the existing range inputs (same
  inputs Start already reads). At minimum a single "🎲 Random range" button;
  optionally separate "random start" / "random end" affordances.
- **R2 — Bounded to the current market.** The roll is constrained to the
  available history for the **currently selected symbol + interval** — start ≥
  first available kline, end ≤ the last *closed* kline (never the still-forming
  candle, for reproducibility per `pc-presets`).
- **R3 — Sane window.** The rolled window has a usable length: a random
  **duration** (within a configurable/min–max bar count) placed at a random
  offset, so it never produces a zero-length or absurdly tiny/huge range.
  Default min/max expressed in candles of the current resolution.
- **R4 — Deterministic-friendly.** The result is just an absolute start/end pair
  in the normal inputs — so it round-trips through presets, the console bridge,
  and Start with the same determinism guarantees as a hand-typed range. Each
  click re-rolls; the chosen range is plainly visible before running.
- **R5 — Console bridge.** Expose the roll via `window.pc` (e.g.
  `pc.backtest.randomRange()` returning the chosen `{start, end}`), and list it
  in `pc.help()`, per the repo's bridge rule.

## Non-requirements

- No new persistence — a rolled range is an ordinary range value; presets cover
  saving it.
- No "random market/interval/algo" — only the **time range** is randomized;
  symbol and resolution stay whatever the user selected.
- No seeded/repeatable RNG UI — re-rolling is expected to differ each click
  (reproducibility comes from the resulting absolute range, not the dice).
- No backend change expected — randomization is a frontend computation over the
  market's known available range.

## Open questions

- Default min/max window length (in bars) per resolution — pick sensible
  defaults, make adjustable if cheap.
- One button vs. separate start/end rolls — start with one, add the split only
  if it earns its keep.
