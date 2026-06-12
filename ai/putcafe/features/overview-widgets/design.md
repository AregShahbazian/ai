# Overview widgets — Design

**ID:** `pc-overview-widgets` · refs `prd.md`

## 1. Orders ledger (backend, single source of truth)

`pivot_strategy.simulate` already walks every order-relevant event; it now
*records* them. New `orders` list in the result; trades unchanged.

```python
order = {
    "id": int,                  # creation sequence
    "role": "entry"|"tp"|"sl"|"exit",   # exit = market close on reverse
    "type": "stop_market"|"limit"|"market",
    "side": "buy"|"sell",
    "price": float,             # order/trigger price (market: fill price)
    "qty": float,
    "pct": float|None,          # tp/sl distance % from entry (signed)
    "createdAt": int,
    "status": "open"|"filled"|"cancelled",  # final status (end of range)
    "filledAt": int|None, "fillPrice": float|None,
    "cancelledAt": int|None,
    "tradeIdx": int|None,       # index into trades (entry/tp/sl/exit link)
}
```

Event mapping inside the sim loop:

- **Armed entry stops.** While flat, the gated `last_high`/`last_low` arm a
  buy/sell stop. Once per candle (after pivot reveal, before the path walk),
  sync desired vs armed: price changed → cancel old (`cancelledAt=t`) +
  create new (`createdAt=t`); newly armable → create; gate blocks → nothing
  to sync (armed orders only exist while their pivot stays the gated one).
- **Entry fill.** `open_pos` fills the triggering armed stop
  (`fillPrice=entry`, `filledAt=t`, `tradeIdx` patched at close) and cancels
  the opposite armed stop. A *reverse* entry has no pre-armed order — emit a
  stop_market order created+filled at `t` (price = reverse level).
- **Bracket.** `open_pos` creates the TP (limit) and SL (stop_market)
  conditional orders, `pct` = signed distance from entry.
- **Exit.** `close_pos` resolves the bracket: tp → TP filled + SL cancelled;
  sl → SL filled + TP cancelled; reverse → both cancelled + a market `exit`
  order created+filled at `t`. `tradeIdx` = index of the just-appended trade,
  patched onto the entry + bracket + exit orders.
- **End of range.** Open position → bracket stays `status: "open"`; armed
  stops never hit stay `"open"`.

Invariants (asserted in the verification script): every non-open trade has
exactly one filled entry order, one filled tp/sl/exit order; order fill
prices/times equal the trade's; statuses are consistent (filledAt xor
cancelledAt xor open).

DCA needs no backend change: its orders are derived frontend-side from
`Session.trades` (filled market buys).

## 2. Frontend types + clipping (`api/backend.ts`, `util/orders.ts`)

```ts
export interface PivotOrder { id, role, type, side, price, qty, pct, createdAt,
  status, filledAt, fillPrice, cancelledAt, tradeIdx }
export interface PivotSimResult { ..., orders: PivotOrder[] }
```

`util/orders.ts` — pure helpers, used by both the widget and the chart:

- `orderStatusAt(o, cursorT)` → `"open"|"filled"|"cancelled"|null` (null =
  not yet created → hidden). Filled/cancelled only once their timestamp ≤
  cursor; otherwise an already-created order reads as `open` (no lookahead).
- `ordersAt(orders, cursorT)` → visible orders + at-cursor status.
- `dcaOrders(trades)` → `PivotOrder`-shaped filled market buys.

## 3. Overview widget (`components/OverviewWidget.tsx`)

Layout: inside `.app-main`, below `.chart-wrap` — automatically spans up to
the sidebar. Fixed height (~225px), `border-top`, tab strip header
(Positions / Orders / Sessions) + the Open|Closed filter on the Orders tab
(Altrady my-orders style). Always visible.

- **Positions** — table, max 1 row (Altrady positions-table columns, pruned):
  `Time | Market | Side | Size | Entry | Mark | SL | TP | PnL | PnL %`.
  Pivot → trade open at cursor (`entryTime ≤ cursor < exitTime`), unrealized
  from last visible close. DCA → active/loaded session with `baseQty > 0`
  (side "long", entry = avgEntry). Flat → "No open position".
- **Orders** — table (Altrady my-orders columns):
  `Date | Type | Side | Price | Amount | Status`. Type cell carries the role
  label and the TP/SL % — `Take profit (+1.79 %)`, `Stop loss (−0.89 %)`,
  `Stop market`, `Market`. Open filter = at-cursor `open`; Closed = filled +
  cancelled (status column colors: filled green / cancelled grey). Newest
  first. Pivot → ledger; DCA → derived buys (always Closed/filled).
- **Sessions** — list moved verbatim from BacktestPanel (rows + Clear
  sessions), same self-contained fetch on status change.

Side/price coloring follows Altrady: buy/long green `#43B581`-family, sell/
short red — mapped onto the existing `.pos`/`.neg` classes.

## 4. Chart order rendering (`chart/ChartView.tsx`)

Replaces the bracket-lines effect with an orders effect (clear-then-redraw,
same as Altrady's overlay groups). All **at-cursor open** orders become
dashed price lines (submitted orders are dashed in Altrady SC):

- Armed entry stop: `Buy stop 0.00135 BTC` / `Sell stop …` at the stop price,
  `#43B581` / `#F15959`.
- Open position bracket: `TP 0.00135 BTC +1.79%` (green) and
  `SL 0.00135 BTC −0.89%` (red) — TP label includes the %, per Altrady's
  `TP n: qty base %pct` format, simplified.
- Position entry line stays (Altrady's PnL handle equivalent):
  `Long 0.00135 BTC @ 74,061` in the neutral entry color, now with qty.

Fills/exits keep the existing arrow/circle markers (Altrady's
`createTradeLine` analog). DCA: no resting orders → markers only, unchanged.

## 5. Wiring (`App.tsx`, `BacktestPanel.tsx`, `app.css`)

- App renders `<OverviewWidget snap={s} config={config} onLoadSession=… />`
  under ChartView/PlaybackControls; `.app-main` already a flex column.
- BacktestPanel: Sessions section + its state/fetch removed (`onLoadSession`
  prop moves to the widget).
- CSS: `.overview-widget`, `.ow-tabs`, `.ow-tab(.selected)`, `.ow-filter`,
  `.ow-table` (sticky header, 12px, hover rows), `.ow-empty`, reusing the
  panel's `.pos/.neg`.

## 6. Sync correctness

Cursor is `snap.candles[snap.upTo-1].time` — the same clock the markers and
results use. Step-back re-clips tables and lines render-only (sim is
pre-computed). Live-tuning TP/SL params or pivot options re-runs the sim →
new ledger arrives in the same snapshot emit as the new trades, so tables,
markers, and lines can never disagree.
