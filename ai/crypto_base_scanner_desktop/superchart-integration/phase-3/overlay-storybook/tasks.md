# Tasks: Overlay Storybook (Superchart Repo)

All work in `$SUPERCHART_DIR/`.

## 1. Install Storybook

```bash
pnpm add -D @storybook/react-vite @storybook/react @storybook/addon-controls storybook
```

Add to root `package.json` scripts:
```json
"storybook": "storybook dev -p 6007",
"build-storybook": "storybook build"
```

---

## 2. Create Storybook config

### `.storybook/main.ts`

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

### `.storybook/preview.ts`

```ts
import "@superchart/index.less"

export const parameters = {
  layout: "fullscreen",
}
```

### `.storybook/.env`

```
VITE_COINRAY_TOKEN=<token>
```

---

## 3. Create SuperchartCanvas helper + copy CoinrayDatafeed

### Copy datafeed

Copy `examples/client/src/datafeed/CoinrayDatafeed.ts` to
`examples/stories/datafeed/CoinrayDatafeed.ts`.

### `examples/stories/helpers/SuperchartCanvas.tsx`

Shared chart wrapper for all stories:

```tsx
import {useEffect, useRef} from "react"
import {Superchart, createDataLoader} from "@superchart/index"
import {CoinrayDatafeed} from "../datafeed/CoinrayDatafeed"

const TOKEN = import.meta.env.VITE_COINRAY_TOKEN || ""

interface Props {
  symbol?: string
  period?: string
  theme?: "dark" | "light"
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

    onReady?.(superchart)

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

---

## 4. Create BreakEven story

### `examples/stories/overlays/BreakEven.stories.tsx`

```tsx
import {useState, useCallback, useRef, useEffect} from "react"
import type {Meta, StoryObj} from "@storybook/react"
import {SuperchartCanvas} from "../helpers/SuperchartCanvas"

function BreakEvenDemo({showBreakEven, price}: {showBreakEven: boolean; price: number}) {
  const chartRef = useRef<any>(null)
  const overlayIdRef = useRef<string | null>(null)

  const onChart = useCallback((chart: any) => {
    chartRef.current = chart
  }, [])

  useEffect(() => {
    const chart = chartRef.current
    if (!chart) return

    if (showBreakEven && price > 0) {
      if (overlayIdRef.current) {
        chart.overrideOverlay({id: overlayIdRef.current, points: [{value: price}]})
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

---

## 5. Verify

1. Run `pnpm storybook` — launches on port 6007
2. BreakEven story appears under Overlays/BreakEven
3. Chart loads with live market data
4. Toggle shows/hides the break-even line
5. Price input moves the line
6. **Key question**: does the price label text appear on the line/axis?
