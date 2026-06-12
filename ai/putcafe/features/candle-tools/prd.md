---
id: pc-candle-tools
---

# Candle tools — clear sessions, export range, save candles

Builds on [`../../mvp/prd.md`](../../mvp/prd.md).

## Requirements

### 1. Clear sessions

- Button in the panel's Sessions section: removes **all** previous sessions,
  excluding the currently active one (if any). List refreshes after.

### 2. Export candles (selected range)

- Button, **disabled unless both** start and end candles are selected.
- Downloads a file containing the candles of the selected range for the
  current market/timeframe.
- Filename carries market, interval, and the range datetimes formatted
  day-first (`DD-MM-YYYY-HHmm`).

### 3. Save candles via candle context menu

- Right-clicking a candle adds a **"Save candle"** option to the chart context
  menu; it saves that candle (with market/interval).
- A separate panel section lists saved candles with:
  - an **export** button (file download of all saved candles),
  - a **clear** button.
- Saved candles survive a reload.

## Non-requirements

- No candle de-duplication rules beyond exact same candle, no editing,
  no server-side storage of saved candles, no import.
