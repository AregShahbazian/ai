# Design: Overlay Storybook (Superchart Repo)

## Overview

Add Storybook to the Superchart repo. Each story renders a full Superchart instance
with live market data and demonstrates one overlay type with interactive controls.

All work happens in `$SUPERCHART_DIR/`.

---

## Storybook Setup

### Install

Storybook 8 with Vite builder + React. Installed at the **root** of the Superchart
repo (not inside `examples/`):

```
pnpm add -D @storybook/react-vite @storybook/react @storybook/addon-controls storybook
```

### Config — `.storybook/main.ts`

```ts
import type {StorybookConfig} from "@storybook/react-vite"
import path from "path"

const config: StorybookConfig = {
  stories: ["../examples/stories/**/*.stories.@(ts|tsx)"],
  addons: ["@storybook/addon-controls"],
  framework: "@storybook/react-vite",
  viteFinal: (config) => {
    config.resolve ??= {}
    config.resolve.alias = {
      ...config.resolve.alias,
      "@superchart": path.resolve(__dirname, "../src/lib"),
    }
    return config
  },
}
export default config
```

Key points:
- `@superchart` alias matches the example client's alias — resolves to source, not dist
- Stories live in `examples/stories/` alongside the existing `examples/client/`
- `viteFinal` hook reuses the same resolve strategy as `examples/client/vite.config.ts`

### Config — `.storybook/preview.ts`

```ts
import "@superchart/index.less"

export const parameters = {
  layout: "fullscreen",
}
```

Imports the library styles (same as `examples/client/src/main.tsx`).

### Script — `package.json`

Add to root `package.json` scripts:

```json
"storybook": "storybook dev -p 6007",
"build-storybook": "storybook build"
```

Port 6007 to avoid conflicting with Altrady's storybook on 6006.

### Env

Storybook needs `VITE_COINRAY_TOKEN`. Storybook picks up `.env` files automatically
via Vite. The existing `examples/client/.env` can be symlinked or the token can be
set in `.storybook/.env`:

```
VITE_COINRAY_TOKEN=...
```

### StrictMode

Disabled — same as the example client. Superchart uses imperative DOM management
that breaks with double-mount. Storybook's preview doesn't use StrictMode by default,
so no action needed.

---

## Chart Wrapper Helper

Every story needs a running Superchart instance. Extract a shared helper to avoid
duplication:

### `examples/stories/helpers/SuperchartCanvas.tsx`

```tsx
import {useEffect, useRef, useState} from "react"
import {Superchart, createDataLoader} from "@superchart/index"
import {CoinrayDatafeed} from "../datafeed/CoinrayDatafeed"

const TOKEN = import.meta.env.VITE_COINRAY_TOKEN || ""

interface Props {
  symbol?: string          // default: "BINA_USDT_BTC"
  period?: string          // default: "1H"
  theme?: "dark" | "light" // default: "dark"
  onReady?: (chart: Superchart) => void
  onChart?: (chart: ReturnType<Superchart["getChart"]>) => void
}

export function SuperchartCanvas({
  symbol = "BINA_USDT_BTC",
  period = "1H",
  theme = "dark",
  onReady,
  onChart,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<Superchart | null>(null)

  useEffect(() => {
    if (!containerRef.current || !TOKEN) return

    const datafeed = new CoinrayDatafeed(TOKEN)
    const dataLoader = createDataLoader(datafeed)

    const superchart = new Superchart({
      container: containerRef.current,
      symbol: {ticker: symbol, pricePrecision: 2, volumePrecision: 0},
      period: {type: "hour", span: 1, text: period},
      dataLoader,
      theme,
    })

    chartRef.current = superchart
    onReady?.(superchart)

    // Poll for klinecharts instance
    const id = setInterval(() => {
      const kc = superchart.getChart()
      if (kc) {
        clearInterval(id)
        onChart?.(kc)
      }
    }, 100)

    return () => {
      clearInterval(id)
      superchart.dispose()
      datafeed.dispose()
    }
  }, [symbol, theme])

  if (!TOKEN) {
    return <div style={{padding: 20, color: "#f44"}}>Set VITE_COINRAY_TOKEN in .env</div>
  }

  return <div ref={containerRef} style={{width: "100%", height: "100vh"}} />
}
```

The CoinrayDatafeed is the same class from `examples/client/src/datafeed/`. Either:
- Copy it to `examples/stories/datafeed/CoinrayDatafeed.ts`, or
- Move it to a shared location like `examples/shared/datafeed/` and import from both

Recommendation: **copy** it. The stories and client app may diverge. Keep it simple.

---

## Break-Even Story

### `examples/stories/overlays/BreakEven.stories.tsx`

```tsx
import {useState, useCallback, useRef, useEffect} from "react"
import type {Meta, StoryObj} from "@storybook/react"
import {SuperchartCanvas} from "../helpers/SuperchartCanvas"

function BreakEvenDemo({
  showBreakEven,
  price,
}: {
  showBreakEven: boolean
  price: number
}) {
  const chartRef = useRef<any>(null)
  const overlayIdRef = useRef<string | null>(null)

  const onChart = useCallback((chart: any) => {
    chartRef.current = chart
  }, [])

  // Draw / update / remove the break-even overlay
  useEffect(() => {
    const chart = chartRef.current
    if (!chart) return

    if (showBreakEven && price > 0) {
      if (overlayIdRef.current) {
        chart.overrideOverlay({
          id: overlayIdRef.current,
          points: [{value: price}],
        })
      } else {
        overlayIdRef.current = chart.createOverlay({
          name: "priceLine",
          points: [{value: price}],
          styles: {
            line: {color: "#D05DDF", size: 1, style: "dashed"},
            text: {color: "#FFFFFF", backgroundColor: "#D05DDF"},
          },
          lock: true,
        })
      }
    } else if (overlayIdRef.current) {
      chart.removeOverlay({id: overlayIdRef.current})
      overlayIdRef.current = null
    }
  }, [showBreakEven, price])

  return <SuperchartCanvas onChart={onChart} />
}

const meta: Meta<typeof BreakEvenDemo> = {
  title: "Overlays/BreakEven",
  component: BreakEvenDemo,
  argTypes: {
    showBreakEven: {control: "boolean"},
    price: {control: {type: "number", min: 0, step: 100}},
  },
}
export default meta

type Story = StoryObj<typeof BreakEvenDemo>

export const Default: Story = {
  args: {
    showBreakEven: true,
    price: 66000,
  },
}
```

### What this story proves

1. The correct `createOverlay` call for a priceLine with a text label
2. Whether the text label (showing price value) appears on the price axis
3. Whether `styles.text` controls the label appearance
4. The update path via `overrideOverlay`
5. The removal path via `removeOverlay`

### What it intentionally does NOT prove yet

- The "Break even" text string — priceLine's built-in label shows the price value.
  If a custom text label is needed (like "Break even"), that's a Superchart API
  question to resolve: does `extendData` work? Or do we need a second overlay?
  The story makes this visible.

---

## File Layout

```
Superchart/
├── .storybook/
│   ├── main.ts
│   └── preview.ts
├── examples/
│   ├── client/          # existing demo app (unchanged)
│   └── stories/
│       ├── datafeed/
│       │   └── CoinrayDatafeed.ts    # copy from client
│       ├── helpers/
│       │   └── SuperchartCanvas.tsx   # shared chart wrapper
│       └── overlays/
│           └── BreakEven.stories.tsx
├── package.json         # + storybook scripts
└── src/lib/             # library source (unchanged)
```

---

## Future Stories (pattern)

Each future overlay story follows the same shape:

1. Import `SuperchartCanvas`
2. Create a demo component with args matching the overlay's controls
3. Use `onChart` callback to get the klinecharts instance
4. Draw/update/remove overlays in a `useEffect` gated on the args
5. Export `meta` with `argTypes` for Storybook controls

Examples of controls per overlay type:
- **PNL Handle**: toggle, openPrice (number), pnlText (text), canClose (boolean)
- **Bid/Ask**: toggle, bidPrice (number), askPrice (number)
- **Trade Markers**: toggle, trades (JSON array of `{time, price, side}`)
- **Order Line**: toggle, price (number), draggable (boolean)
