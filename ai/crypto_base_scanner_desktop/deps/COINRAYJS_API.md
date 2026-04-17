# CoinrayJS API Reference

> Source: `$COINRAYJS_DIR`
> Git hash: `b7104d2c890e290acb2e414415fea1e661b1b14f`
> Do NOT explore source — use this doc instead.

## Singleton Access

```javascript
import { getCoinrayCache } from "~/actions/coinray"
const cache = getCoinrayCache()  // CoinrayCache instance
```

## CoinrayCache

### fetchCandles(options) → Promise<Candle[]>

```javascript
const candles = await cache.fetchCandles({
  coinraySymbol: "BINA_BTC_USDT",   // required — format: EXCHANGECODE_BASE_QUOTE
  resolution: "60",                  // required — TradingView resolution string
  start: 1700000000,                 // Unix SECONDS
  end: 1700003600,                   // Unix SECONDS
  useWebSocket: true,                // optional — prefer WS on first data request
})
```

### subscribeCandles(channel, callback) → Promise

```javascript
const callback = ({ candle }) => {
  // candle: { time: Date, open, high, low, close, baseVolume, quoteVolume, numTrades }
}
await cache.subscribeCandles(
  { coinraySymbol: "BINA_BTC_USDT", resolution: "60", lastCandle: candle },
  callback
)
```

### unsubscribeCandles(channel, callback?) → Promise

```javascript
await cache.unsubscribeCandles(
  { coinraySymbol: "BINA_BTC_USDT", resolution: "60" },
  callback  // same reference passed to subscribeCandles
)
```

### getMarket(coinraySymbol) → Market | undefined

```javascript
const market = cache.getMarket("BINA_BTC_USDT")
```

### getExchange(code) → Exchange | undefined

```javascript
const exchange = cache.getExchange("BINA")
```

### getExchanges() → { [code]: Exchange }

### getMarkets(exchangeCode?) → { [coinraySymbol]: Market }

### searchMarkets(query) → { [coinraySymbol]: Market }

Search by currency, pair, or exchange code (e.g., "BTC USDT BINA").

### fetchFirstCandleTime({ coinraySymbol, resolution }) → Promise<Date>

Returns `Date` of earliest available candle for symbol/resolution.

### initialize() → Promise

Must be called before any data access.

### destroy()

Cleans up WebSocket subscriptions and internal state.

### onTokenExpired(callback)

```javascript
cache.onTokenExpired(async () => {
  const newToken = await refreshToken()
  return newToken || false  // false = sign out
})
```

## Candle Shape

```javascript
{
  time: Date,           // JavaScript Date object (NOT a timestamp!)
  open: number,
  high: number,
  low: number,
  close: number,
  baseVolume: number,
  quoteVolume: number,
  numTrades: number,
  skipVolume?: boolean,
}
```

**Converting for charts:**
```javascript
// Candle.time (Date) → Bar.time (ms): candle.time.getTime()
// Candle.time (Date) → seconds:       Math.floor(candle.time.getTime() / 1000)
```

## Market Object

```javascript
market.coinraySymbol        // "BINA_BTC_USDT"
market.exchangeCode         // "BINA"
market.baseCurrency         // "BTC"
market.quoteCurrency        // "USDT"
market.precisionPrice       // number — decimal places for price display
market.precisionBase        // number — decimal places for base amount
market.precisionQuote       // number — decimal places for quote amount
market.minBase              // BigNumber — min base trade size
market.maxBase              // BigNumber
market.minQuote             // BigNumber — min quote trade size
market.baseToUsd            // BigNumber — base→USD rate
market.quoteToUsd           // BigNumber — quote→USD rate
market.baseLogoUrl          // string — logo URL
market.volume               // BigNumber — 24h volume (base)
market.quoteVolume          // BigNumber — 24h volume (quote)
market.makerFee             // number
market.takerFee             // number
market.status               // "ACTIVE" | "DELISTED" | "INACTIVE"

market.getExchange()        // Exchange object
```

Key for chart integration:
- `pricePrecision` → `pricescale: Math.pow(10, market.precisionPrice)`
- `volumePrecision` → `market.precisionBase`
- Exchange name → `market.getExchange().name`

## Exchange Object

```javascript
exchange.name               // "Binance"
exchange.code               // "BINA"
exchange.isFutures          // boolean
exchange.isDex              // boolean
exchange.active             // boolean
exchange.tradingEnabled     // boolean
exchange.logo               // URL
exchange.supportedResolutions  // string[]
exchange.quoteCurrencies    // string[] — e.g., ["BTC", "ETH", "USDT"]
exchange.totalMarkets       // number
exchange.getMarket(symbol)  // Market object by exchange symbol
```

## Resolution Strings (TradingView Convention)

```
Seconds:  "1S", "2S", "3S", "5S", "10S", "15S", "30S"
Minutes:  "1", "2", "3", "5", "10", "15", "30", "60", "120", "240", "360", "720"
Daily+:   "D", "1D", "2D", "W", "1W", "2W", "1M"
```

Minutes are plain numbers. Hours are expressed as minutes (60=1h, 240=4h).

### resolutionToDuration(resolution) → number

Returns duration in seconds. e.g., `resolutionToDuration("60") === 3600`.

## Timestamp Conventions

| Context | Format | Example |
|---------|--------|---------|
| `fetchCandles({ start, end })` | Unix **seconds** | `1700000000` |
| `Candle.time` | JavaScript **Date** | `new Date(...)` |
| `fetchFirstCandleTime()` return | JavaScript **Date** | `new Date(...)` |
| Superchart `Bar.time` | **milliseconds** | `1700000000000` |
| Superchart `PeriodParams.from/to` | **seconds** | `1700000000` |

Converting: `fetchCandles({ start: periodParams.from, end: periodParams.to })` (seconds direct).
Candle→Bar: `{ time: candle.time.getTime(), ... }`. Candle→seconds: `Math.floor(candle.time.getTime() / 1000)`.

## Numeric Values — BigNumber

All prices, volumes, and fees are `BigNumber` objects (`bignumber.js`):
`toNumber()`, `toFixed(n)`, `multipliedBy(x)`, `dividedBy(x)`, `plus(x)`, `minus(x)`.

## Initialization (src/actions/coinray.js)

```javascript
const cache = new CoinrayCache(token, config, undefined, { apiCache, onStoreCache })
cache.onTokenExpired(async () => newToken || false)
await cache.initialize()
```
