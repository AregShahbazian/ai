# Tasks: Grid Bot Backtest — SuperChart Integration

## Step 1: Dual-chart layout in backtest modal

### Task 1.1: Add SC next to TV in backtest-content.js (desktop)

**File:** `src/containers/bots/grid-bot/backtest/backtest-content.js`

Wrap TV and SC side by side in the chart area:

```jsx
<div tw="flex-1 flex flex-row">
  <div tw="flex-1 min-w-0">
    {coinraySymbol && <GridBotTradingWidget ...existing props.../>}
    {!coinraySymbol && <EmptyChart/>}
  </div>
  <div tw="flex-1 min-w-0">
    {coinraySymbol && <GridBotSuperChartWidget coinraySymbol={coinraySymbol}
                                               orders={orders}
                                               trades={backtestResult ? backtestResult.trades : []}
                                               upperPrice={upperPrice}
                                               lowerPrice={lowerPrice}
                                               updateUpperPrice={updateUpperPrice}
                                               updateLowerPrice={updateLowerPrice}
                                               edited/>}
  </div>
</div>
```

No `backtest` prop to SC yet (step 2). No `stopLoss`/`takeProfit` (backtest doesn't have them).

**Verify:** Open backtest modal. TV (left) and SC (right) both render candles. Sidebar stays on the right.

### Task 1.2: Add SC next to TV in backtest-content-mobile-form.js (mobile)

**File:** `src/containers/bots/grid-bot/backtest/backtest-content-mobile-form.js`

Same side-by-side pattern in the chart toggle area. No `backtest` prop (mobile doesn't have time markers in TV either).

**Verify:** Mobile backtest form — toggle "Show Chart" — both charts visible side by side.

---

## Step 2: Backtest time markers overlay

### Task 2.1: Add overlay group

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/overlay-helpers.js`

Add to `OverlayGroups`:

```js
// Grid bot backtest
backtestTimes: "backtestTimes",
```

### Task 2.2: Add controller method

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/chart-controller.js`

Add in the Grid Bot section:

```js
createBacktestTimeLine(key, timestamp, onUpdate) {
  return this._createTriggerTimeLine(OverlayGroups.backtestTimes, key, timestamp, {
    lock: false,
    onPressedMoveEnd: (event) => {
      const newTimestamp = event?.overlay?.points?.[0]?.timestamp
      if (newTimestamp !== undefined) onUpdate(new Date(newTimestamp))
    },
  })
}
```

Reuses `_createTriggerTimeLine` — triggerPrice color, verticalStraightLine overlay. `lock: false` makes it draggable. Converts timestamp to Date for the form callback.

### Task 2.3: Create BacktestTimes overlay component

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/overlays/grid-bot/backtest-times.js` (new)

```js
import PropTypes from "prop-types"
import {OverlayGroups} from "../../overlay-helpers"
import {useSuperChart} from "../../context"
import useDrawOverlayEffect from "../../hooks/use-draw-overlay-effect"

const BacktestTimes = ({backtest}) => {
  const {chartController} = useSuperChart()
  const {startTime, endTime, updateStartTime, updateEndTime} = backtest

  useDrawOverlayEffect(OverlayGroups.backtestTimes, () => {
    if (startTime) {
      chartController.createBacktestTimeLine("start", new Date(startTime).getTime(), updateStartTime)
    }
    if (endTime) {
      chartController.createBacktestTimeLine("end", new Date(endTime).getTime(), updateEndTime)
    }
  }, [startTime?.getTime?.() ?? startTime, endTime?.getTime?.() ?? endTime])

  return null
}

BacktestTimes.propTypes = {
  backtest: PropTypes.shape({
    startTime: PropTypes.instanceOf(Date),
    endTime: PropTypes.instanceOf(Date),
    updateStartTime: PropTypes.func,
    updateEndTime: PropTypes.func,
  }).isRequired,
}

export default BacktestTimes
```

### Task 2.4: Wire BacktestTimes into GridBotSuperChartWidget

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/grid-bot-super-chart.js`

Import `BacktestTimes`. Conditionally render when `backtest` prop exists:

```jsx
{props.backtest && <BacktestTimes backtest={props.backtest}/>}
```

Add `backtest` propType.

### Task 2.5: Pass backtest prop from backtest-content.js

**File:** `src/containers/bots/grid-bot/backtest/backtest-content.js`

Add `backtest` prop to the SC widget (desktop only):

```jsx
<GridBotSuperChartWidget ...
    backtest={{startTime, endTime, updateStartTime, updateEndTime}}/>
```

**Verify:**
- Desktop: two vertical time lines on SC matching TV positions
- Drag start time line in SC → date picker updates
- Drag end time line in SC → date picker updates
- Change date in picker → both TV and SC lines reposition
- Change market → lines persist at correct timestamps
