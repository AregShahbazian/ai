# Trigger Timing Offset — Reproducer Logs

Runtime evidence to support `prd.md`. Fill in each scenario by running it in
the app and pasting the captured values / requests below.

## Setup

1. Open a fresh smart replay session on any liquid market, **1h resolution**.
2. Open DevTools → Network tab, filter by `backtests`. Leave it open
   throughout.
3. Note the session start candle's open time (e.g. `2026-04-10 06:00`).

Session start (last drawn) candle open time: `Wed Apr 15 2026 07:00:00 GMT+0400 (Armenia Standard Time)`
Session start time (engine): `Wed Apr 15 2026 08:00:00 GMT+0400 (Armenia Standard Time)`

---

## Scenario A — Alert one-candle offset (frontend trigger)

Steps:

1. Create a price alert with a **time condition** set to the open time of a
   candle ~3 candles ahead of the session start (e.g. `09:00` if session
   started at `06:00`).
2. Step forward one candle at a time.
3. Note the replay cursor time shown in the UI at each step and whether the
   alert fired.

Expected bug: alert fires when cursor reaches `10:00` instead of `09:00`.

- Alert time set: `11:00`
- Cursor time at each step:
  - step 1 → `08:00`
  - step 2 → `09:00`
  - step 3 → `10:00`
  - step 4 → `11:00`
- Cursor time when alert fired: `12:00`

---

## Scenario B — Order time-trigger (backend trigger)

Steps:

1. Place a smart entry order with a **time trigger** at e.g. `09:00`, same
   session.
2. Before stepping, copy the `POST` request that created the order (right-click
   → Copy → Copy as cURL) and paste it below under "Order placement request".
3. Step forward. Note the cursor time at which the order fires.
4. When it fires, copy the resulting `POST` / `PATCH` request body too.

- Time trigger set: `15:00`
- Cursor time when order fired: `16:00`

### Order placement request

```
curl 'https://app.altrady.com/api/v3/backtests/8592/positions' \
  -H 'accept: application/json' \
  -H 'accept-language: en-US,en;q=0.9' \
  -H 'authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3NzcwMTcxMTMsInNlc3Npb24iOnsidG9rZW4iOiJIZm5VUUVWSDh4aWFaUTNRYWttNG1IelgifX0.C1sdWL0oQHduMK8ilJNN7lV-dD8pPoqXpwRSbzwGhfs' \
  -H 'cbs-device-id: 8c93a836-0967-49a7-a374-4f7c55d08d08' \
  -H 'content-type: application/json' \
  -H 'origin: http://localhost:5001' \
  -H 'priority: u=1, i' \
  -H 'referer: http://localhost:5001/' \
  -H 'sec-ch-ua: "Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Linux"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: cross-site' \
  -H 'user-agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36' \
  --data-raw '{"reduceOnly":false,"candle":{"open":73891.62,"high":74016.67,"low":73514,"close":73730.43,"time":1776239999},"resolution":"60","smartPosition":{"isPosition":true,"leverage":1,"positionType":"long","entrySide":"buy","exitSide":"sell","entryType":"MARKET","entryOrders":[{"side":"buy","orderId":"826b7345-cbcf-4c37-84a2-a728e607edfc","status":"new","filled":"0","baseAmount":"0.01355","quoteAmount":"999.60015","price":"0","errors":{},"invalidFields":[],"updatedFields":[],"isValid":true,"amountType":"QUOTE_AMOUNT","simpleOrderType":"NORMAL","orderType":"MARKET","lockedOn":"quoteAmount"}],"entryLadder":{"entryOrExit":"entry","orderId":"1fd558be-b7fa-443e-85ae-4ea800c797e3","enabled":false,"priceScale":"LINEAR","sizeScale":"EQUAL","_lockedOn":"quoteAmount","numOrders":1,"numRemainingOrders":1,"startPrice":"0","endPrice":"0","baseAmount":"0","quoteAmount":"0","errors":{},"ladderType":"SCALED","sizeScales":[1]},"exitOrders":[],"exitLadder":{"entryOrExit":"exit","enabled":false,"exitPriceType":"PERCENTAGE","priceScale":"LINEAR","sizeScale":"EQUAL","sizeScales":["1"],"_quoteAmount":"0","_baseAmount":"0","exitPercentage":"100","keepEntriesOpen":false,"errors":{},"numOrders":0,"numRemainingOrders":0,"ladderType":"FIXED","trailingEnabled":false,"baseAmount":"0.01355"},"entryExpiration":{"enabled":false,"priceEnabled":false,"timeEnabled":false,"expiresAt":0,"price":"0","errors":{},"priceDirection":"down"},"entryCondition":{"enabled":true,"priceEnabled":false,"timeEnabled":true,"startAt":1776250800,"operator":"OR","price":"0","errors":{},"direction":"down"},"autoClose":{"enabled":false,"timeFrame":"hour","amount":0,"errors":{}},"stopLoss":{"side":"sell","orderId":"6298886a-88d0-4489-b39f-18d3f5fb861c","enabled":false,"errors":{},"invalidFields":[],"updatedFields":[],"simpleOrderType":"STOP_ORDER","orderType":"STOP_LOSS_MARKET","coolDown":{"coolDownType":"TIME","coolDownCancelEnabled":false,"candleResolution":5,"amount":0,"timeFrame":"minute"},"coolDownEnabled":false,"status":"new","exitPriceType":"FIXED","protectionType":"NONE","trailingPrice":"0","trailingPercentage":"0","trailingType":"POSITION","trailingDistance":"0","trailingDistancePrice":"0","_stopOffsetPercentage":"0","_limitOffsetPercentage":"0","stopPrice":"0","isValid":true}}}'
```

### Fire-time request (if any)

```
curl 'https://app.altrady.com/api/v3/backtests/8592/trigger' \
  -H 'accept: application/json' \
  -H 'accept-language: en-US,en;q=0.9' \
  -H 'authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3NzcwMTcxMTMsInNlc3Npb24iOnsidG9rZW4iOiJIZm5VUUVWSDh4aWFaUTNRYWttNG1IelgifX0.C1sdWL0oQHduMK8ilJNN7lV-dD8pPoqXpwRSbzwGhfs' \
  -H 'cbs-device-id: 8c93a836-0967-49a7-a374-4f7c55d08d08' \
  -H 'content-type: application/json' \
  -H 'origin: http://localhost:5001' \
  -H 'priority: u=1, i' \
  -H 'referer: http://localhost:5001/' \
  -H 'sec-ch-ua: "Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Linux"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: cross-site' \
  -H 'user-agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36' \
  --data-raw '{"candle":{"open":73864.76,"high":74256.44,"low":73864.76,"close":74201.78,"time":1776254399},"resolution":"60"}'
```

---

## Scenario C — Resolution switch firing

Steps:

1. Same session. Set a new alert at `11:00`.
2. Step forward on 1h until cursor is exactly `11:00`. Confirm it did **not**
   fire.
3. Switch chart to **1m**.
4. Step forward one candle (cursor → `11:01`).
5. Note whether it fires on that step.

- Alert time set: `18:00`
- Did it fire at `18:00` on 1h? `no`
- Did it fire at `18:01` on 1m? `yes`

---

## Scenario D — First-trade cannot be undone via step-back

Steps:

1. Start a **new** smart replay session.
2. On the very first candle, place any smart order and let it fill (or place a
   market order).
3. Click step-back once.
4. Capture from Network tab in this order.
5. Note whether the trade disappeared and whether the cursor actually moved
   back.

- Session start (last drawn) candle open time: `Wed Apr 15 2026 07:00:00 GMT+0400 (Armenia Standard Time)`
- Session start time (engine): `Wed Apr 15 2026 08:00:00 GMT+0400 (Armenia Standard Time)`
- Trade timestamp (as shown on chart): `on candle `Wed Apr 15 2026 07:00:00 GMT+0400 (Armenia Standard Time)``
- Did the trade disappear after step-back? `no`
- Did the cursor move back? `no`

### `PATCH /backtests/:id/reset` request (if one was sent)

```
none was sent
```

### Reset response body

```json
n/a
```

---

## Notes / anything surprising

`
Alerts are handled fully in frontend, and could have been adapted to the backend's behavior. 
This logic could have been ported like this from the TV implementatin
`
