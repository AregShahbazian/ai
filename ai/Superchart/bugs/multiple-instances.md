# Multiple Superchart Instances — Issue Report

## Problem

Mounting more than one `Superchart` instance at a time is broken. The second instance overwrites the first's state, causing shared symbols, leaked overlays, and incorrect chart references.

## Root Cause

All stores are **module-level singletons**. `createSignal()` calls in each store file execute once at import time, producing a single set of signals shared across the entire process. There is no instance-scoping.

### Affected stores

| Store | Key shared state |
|---|---|
| `chartStore.ts` | `instanceApi`, `symbol`, `period`, `theme`, `locale`, `timezone`, and 10+ more signals |
| `tickStore.ts` | `currentTick`, `tickTimestamp` |
| `overlaySettingStore.ts` | popup position/visibility signals, `visibilityMap` (a module-level `Map`) |
| `keyEventStore.ts` | `ctrlKeyedDown`, `widgetRef`, `modalCallbacks` |

### Why it breaks

The `Superchart` constructor (`src/lib/components/Superchart.ts`) directly mutates the shared store:

```ts
store.setSymbol(options.symbol)   // overwrites any existing instance's symbol
store.setPeriod(options.period)   // overwrites any existing instance's period
store.setInstanceApi(chart)       // overwrites the previous Chart reference
```

When two instances coexist:

1. Instance 2's constructor overwrites Instance 1's `symbol`, `period`, `instanceApi`, etc.
2. Both instances subscribe to and render from the same signals — only the last writer's values are visible.
3. `dispose()` calls `resetStore()`, which clears the shared state and breaks any still-mounted instance.

### Concrete example

```ts
const chart1 = new Superchart({ symbol: BTCUSDT, period: '1h', ... })
const chart2 = new Superchart({ symbol: ETHUSDT, period: '4h', ... })

// chart1 now shows ETHUSDT/4h — its state was overwritten
// chart1's instanceApi points to chart2's Chart object
```

## Impact

- **/charts page**: mounts multiple independent chart tabs simultaneously — completely blocked.
- **Grid bot**: settings page + backtest modal both mount SC — overlays leak between them.
- **Any page** mounting SC alongside the main Trading Terminal SC widget.

## Fix Direction

Replace module-level singleton signals with instance-scoped stores. Each `new Superchart()` should create its own store context (via a factory function or a context/DI pattern), so signals are isolated per instance.
