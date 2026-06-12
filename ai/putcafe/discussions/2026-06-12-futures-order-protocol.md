# Bot→frontend protocol for hedge-mode futures trading — 2026-06-12

## Summary

Asked whether the current bot→frontend protocol would suffice once the bot
starts making pivot-driven trade decisions on **hedge-mode isolated futures**:
closing/extending a position, opening a position in the same or opposite
direction, with market/limit/ladder entries, take-profit, stop/stop-limit, and
stoploss orders. Conclusion: **no — the protocol and the positions model are
fundamentally insufficient**; they need an extension (new contract + a matching
engine), not a patch.

## Current state (as of `pc-mvp` + `pc-pivots`)

- A bot decision is `{side: "buy", type: "market", quoteAmount}`, executed by
  the frontend as an instant fill at `candle.close` via positions `/orders`.
- The positions-backend is spot buy-only: `quoteBalance`, `baseQty`,
  `avgEntry`. It never sees candles — it only records fills.
- Bot per-step state is `lastTradeTime` + balances.

## Key conclusions — three gaps

1. **No resting orders.** Limit/ladder/stop/TP/SL must live across candles —
   placed, working, filled when price crosses, cancellable/amendable. There are
   no order IDs, no lifecycle, no cancel/amend verbs, and no component that
   matches open orders against each candle's high/low.
2. **No position addressing.** Hedge mode needs `positionSide: long|short` and
   `reduceOnly` on every order to distinguish close/extend/TP/SL from opening
   the opposite side. The bot's state input can't inform such decisions.
3. **No futures model.** No two-sided positions, leverage, isolated margin, or
   liquidation in the positions-backend.

## Suggested direction (to refine in design)

- Keep the topology (frontend ⇄ bot ⇄ positions), change the contract: bot
  returns **order intents** —
  `{op: place|cancel|amend, clientId, positionSide, side,
  type: market|limit|stop_market|stop_limit, price?, stopPrice?, qty,
  reduceOnly?, tp?/sl? bracket}`. A ladder is N `place` ops.
- The **positions-backend owns the order book + matching engine**: per step it
  receives the candle, fills crossed resting orders (incl. TP/SL), returns
  fill/cancel events, and models hedge-mode isolated positions per side.
- The bot's per-step state fetch grows to include **open orders + both
  position sides**.
- The frontend becomes a relay/renderer of events — consider letting the bot
  hit positions directly even in replay (it already does for headless),
  returning `{actions, events}` for rendering.

## Open questions

- Fill semantics inside one candle: OHLC path assumption (e.g. O→H→L→C vs
  O→L→H→C by candle color), whether both a TP and SL crossing in the same
  candle is resolved pessimistically.
- Partial fills — model them or fill-in-full only?
- Funding rates, liquidation mechanics depth (full margin math vs simplified).
- Whether bracket (TP/SL attached to entry) is one intent or separate orders.
- How replay step-back interacts with resting orders (render-only rewind today).

## Ideas to realize

- **Futures order protocol + matching engine** (`pc-futures-orders`): order
  intents from the bot, resting-order lifecycle, hedge-mode isolated futures
  model in positions, per-candle matching, events back to the frontend.
- **Pivot-based futures strategy**: a bot algo consuming pivots to emit those
  intents (separate feature, builds on `pc-pivots` + `pc-futures-orders`).
- **Order/position visualization**: working orders as price lines, fills as
  markers, per-side position panels.
