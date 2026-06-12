---
id: pc-presets
---

# Backtest presets — save & reload a full setup deterministically

A **preset** captures everything needed to reproduce a backtest setup, so the
user can load the app, pick a preset, run, and get the **same deterministic
result** every time.

Built on the backtest tooling (`pc-mvp`), the pivot detector (`pc-pivots`), and
the pivot trading algo (`pc-pivot-trading`) — a preset must capture all of their
settings.

## Requirements

### 1. What a preset captures

- **Market** (symbol) and **resolution** (interval).
- **Backtest range**: absolute start/end times (unix seconds).
- **Algorithm + settings**: mode (replay/headless), algo (`dca`|`pivot`), and
  every algo knob — DCA (buy amount, frequency), pivot (TP/SL ratio, SL cap,
  position size), shared (starting balance, fees) — plus the **pivot options**
  (show pivots, lookback, alternation), since lookback changes the strategy.
- A user-given **name**.

### 2. Save

- A **"Save as preset"** button in the Backtest panel snapshots the current
  setup (market, interval, range, config, pivot options) under a name the user
  provides.
- Presets persist across reloads (browser localStorage, like saved candles).

### 3. Load

- Presets are listed in the panel; selecting one **loads** its full setup into
  the app (market, interval, range, algo + settings, pivot options).
- After loading, pressing **Start** runs exactly that setup. Selecting a preset
  must not auto-start (the user runs it).
- A preset can be **removed**.

### 4. Determinism

- Loading preset X and running it always yields the **same** trades/result,
  across reloads and sessions, because:
  - the range is stored **absolute** (not relative to "now"), so it always
    points at the same immutable historical klines;
  - the pivot algo is a pure stateless simulation of (candles, options, params).
- The app must **warn** when a preset's end time is at/near the present (the
  last candle is still forming → not reproducible).

## Non-requirements

- No server-side preset storage / sharing (localStorage only; export/import is a
  possible later add).
- No auto-run on selection; no scheduling.
- Presets don't snapshot candle data — they reference it by market/interval/range
  and re-fetch (history is immutable, so this stays deterministic).
- DCA runs still create a positions-backend session per run (the *result* is
  deterministic; persistence is a side effect, not part of the preset).
