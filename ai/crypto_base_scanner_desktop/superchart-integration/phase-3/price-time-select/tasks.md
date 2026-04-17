# Tasks: Price/Time Select — SuperChart Port

1. **`price-field.js`** — swap TV import for `ChartRegistry`, rewrite `selectPrice` / `onPriceSelected` per `design.md`.
2. **`date-picker-input.js`** — same pattern, `onSelect` uses `point.time * 1000`.
3. **Delete `price-time-field.js`** — unused, no importers. Confirmed with grep.
4. Walk `review.md` items. Flag any bug as a Round 2 entry.

Single commit `[sc-price-time-select]`. Files under `src/components/design-system/v2/trade/inputs/`.
