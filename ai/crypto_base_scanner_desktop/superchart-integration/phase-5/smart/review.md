# Phase 5: Replay (Default + Smart) — Comprehensive Review

Manual QA test suite covering both replay modes, mode switching, playback, Trading
Terminal context interactions, trade/alert form side effects, and the edge cases
addressed by recent fixes. Items are grouped by area. Prefix each with ✅ after
verification.

## Round 1: Comprehensive test suite (2026-04-14)

### A. Default Replay — Basic Playback

1. ✅ Random Bar button (header) starts a default replay session at a random historical time
2. `PickReplayStartButton` → "Random Bar" dropdown starts a default replay session
3. ✅ Replay controls panel appears at the bottom of the chart when the session starts
4. ✅ Chart shrinks vertically to make room for the controls (no overflow/clipping)
5. ✅ Engine transitions `idle → loading → ready` cleanly with no error toasts
6. ✅ Time, price, and progress indicators render once the engine reaches `ready`
7. ✅ Play button starts playback (status → `playing`)
8. ✅ Pause button stops playback (status → `paused`)
9. ✅ Step button advances one candle while paused
10. ✅ Step button remains enabled while playing (clicking takes a manual step)
11. ✅ Step button is disabled while status is `loading`
12. ✅ Step button is disabled while status is `finished`
13. ✅ Back-to-Start button re-fetches and resets to the original start time
14. ✅ Back-to-Start clears simulated trades if confirmed
15. ✅ Speed selector shows SC speeds `[1, 2, 5, 10, 20, 50, 100, 200, 400]`
16. ✅ Changing speed while playing updates playback rate without pausing
17. ✅ Changing speed while paused persists and is used when Play is pressed
18. ✅ Stop/Exit button clears the session and hides the controls panel
19. ✅ Stop prompts a confirmation when trades exist, skips when none exist
20. ✅ Finished state: engine end reached → status `finished`, play icon becomes restart
21. ✅ Clicking Play on a finished session restarts from start and plays
22. ✅ Chart resumes live data after Stop
23. ✅ Hotkey `shift+down` play/pauses
24. ✅ Hotkey `shift+right` steps
25. ✅ Hotkey `shift+r` goes back to start
26. ✅ Hotkey `shift+q` stops/exits the session
27. ✅ Hotkey `shift+b` executes a buy in default replay
28. ✅ Hotkey `shift+s` executes a sell in default replay

### B. Default Replay — Simulated Trading

29. ✅ Buy button executes a trade at current replay time + price
30. ✅ Sell button closes position / goes short at current replay time + price
31. ✅ Order amount input accepts valid input, rejects invalid
32. ✅ PnL display appears after a position opens
33. ✅ PnL updates on every step
34. ✅ Trades render on the chart as markers
35. ✅ Trades persist across pause/resume
36. ✅ Restart via Back-to-Start clears trades (after confirmation)
37. ✅ Stop clears trades (after confirmation)
38. ✅ Trading is blocked while status is `loading` or `finished`

### C. Smart Replay — Quick Start

39. ✅ Random Bar with "smart" preset starts a backtest session directly
40. ✅ `quickStartBacktest` creates a new backtest with current market + resolution
41. ✅ Quick-started backtest shows up in the Backtests widget list
42. ✅ Replay controls show smart-specific elements (toggle mode, auto-resume toggle)
43. ✅ Current position and trades sourced from backtest (not ScReplayTradingController)
44. ✅ Backtest's `replayStartAt` matches the chosen random time

### D. Smart Replay — Manual Setup

45. ✅ "New Backtest" in Backtests widget opens the edit modal empty
46. ✅ `BacktestEditModal` form fields render (start/end dates, balances, resolution, etc. ✅)
47. ✅ Submitting the form creates a backtest and starts the smart session
48. ✅ Editing an existing unfinished backtest resumes it at `lastCandleSeenAt`
49. ✅ Viewing a finished backtest opens it read-only (no play, no trading)
50. ✅ `setReplayStartAt` updates the start, and the form picker reflects the new value

### E. Smart Replay — Playback & Triggers

51. ✅ Play advances candles; `onReplayStep` fires; `smart.updateCurrentState(candle)` runs
52. ✅ Triggered price alert fires during playback (up and down direction)
53. ✅ Triggered time alert fires once its timestamp is reached
54. ✅ Triggered trendline alert fires when line is crossed
55. ✅ Position opens when entry trigger fires on the backtest
56. ✅ Position closes when TP/SL trigger fires
57. ✅ Alerts that fire are moved to `triggeredAlerts`
58. ✅ Canceled alerts disappear from `alerts`, reappear in settings
59. ✅ Auto-resume `true` + alert/position change → playback resumes after processing
60. ✅ Auto-resume `false` → playback stays paused after a trigger/alert fires
61. ✅ Finished backtest shows "backtest finished" warning in trade/alert form
62. ✅ `setBacktestFinished` correctly persists `replayEndAt` and cancels pending alerts

### F. Mode Switching — Dialog Prompt

63. ✅ `ReplayModeDialog` appears when `replayShowModeDialog` setting is enabled
64. ✅ Selecting "Default" from the dialog starts a default session at the chosen time
65. ✅ Selecting "Smart" from the dialog starts a backtest at the chosen time
66. ✅ Dialog closes cleanly on Cancel; no session started
67. ✅ `replayShowModeDialog: false` → skips dialog, uses current `isSmartReplay` setting
68. ✅ Dialog is closed on background click
69. ✅ Dialog auto-hides on mobile/tablet

### G. Mode Switching — ToggleReplayModeButton

70. ✅ Button visible only when a replay session is active
71. ✅ In DEFAULT, button text reads "Switch to Backtest mode"
72. ✅ In SMART, button text reads "Switch to Replay mode"
73. ✅ Collapsed variant shows "Backtest" / "Replay" instead of full text
74. ✅ Icon matches current mode (not hardcoded to a setting)
75. ✅ Button in DEFAULT mode, click → opens `BacktestEditModal` pre-filled with the
    current session's `startTime` (see session fix)
76. ✅ Button in SMART mode, click → `exitSmartMode()` → session becomes default
    replay at the backtest's `startTime` with 0 progress (see session fix)
77. ✅ After SMART→DEFAULT switch, button text updates to "Switch to Backtest mode"
78. ✅ After SMART→DEFAULT switch, global `state.replay.replayMode` equals `DEFAULT`
79. ✅ After SMART→DEFAULT switch, the engine's current time is reset to session `startTime`
80. ✅ After DEFAULT→SMART switch, modal's start date is the previous default session's
    `startTime`
81. ✅ After DEFAULT→SMART modal save, smart session starts at that `startTime`
82. ✅ Toggle button works from trade form (position where `ToggleReplayModeButton` is embedded)
83. ✅ Toggle button works from alert form (price/time/trendline)
84. ✅ Toggle button works from replay controls panel

### H. Backtests Widget

85. ✅ Widget lists all backtests with pagination
86. ✅ Filter by status (running, finished, all) works
87. ✅ Search query filters backtests by name
88. ✅ "New Backtest" button opens an empty edit modal
89. ✅ Clicking a row opens its backtest overview
90. ✅ Clicking Play on a running-backtest row resumes it (smart session)
91. ✅ Clicking a finished-backtest row opens read-only overview
92. ✅ Deleting a backtest removes it and refreshes the list
93. ✅ Backtests widget settings (`backtests-settings.js`) toggles visible — apply/persist
94. ✅ Settings toggle for auto-start-from-chart works when enabled/disabled
95. ✅ Backtest stats render (PnL, # trades, win rate, duration)
96. ✅ Backtest positions list renders per-backtest
97. ✅ Overview header shows correct symbol, start/end, and status
98. ✅ Widget reflects mid-session updates (trades open/close) without full reload
99. ✅ Switching backtest while running properly cleans up previous session

### I. Trade Form During Replay

100. ✅ Default replay active → trade form submit button is **disabled**
101. ✅ Default replay active → "Place Order" shows as disabled state (no click)
102. ✅ Smart replay with **running** backtest → submit button **enabled**
     (executes smart trade through backtest)
103. ✅ Smart replay with **finished** backtest → submit button disabled + "backtest
     finished" warning visible
104. ✅ Live mode (no replay) → submit button enabled as normal
105. ✅ Switching from default to smart mid-session re-enables the submit button
106. ✅ Switching from smart to default mid-session disables the submit button
107. ✅ `ToggleReplayModeButton` shown inside trade form when in default replay
108. ✅ Trade form state preserved correctly across mode switches
109. ✅ Submitting in smart mode appends trade to backtest, not live account
110. ✅ Auto-confirm toggle still respected in smart trading
111. ✅ Order type inputs (limit/market/SL/TP) behave identically in smart vs live
112. ✅ Position controls render PnL from backtest in smart mode, from real position in live

### J. Alert Form During Replay

113. ✅ Default replay active → alert form save button **disabled**
114. ✅ Default replay active → `ToggleReplayModeButton` visible inside alert form
115. ✅ Default replay active → time picker shows replay time (not wall-clock)
116. ✅ Smart replay running → save button **enabled** (alert saved to backtest)
117. ✅ Smart replay finished → save button disabled + "backtest finished" warning
118. ✅ Live mode → save button enabled as normal
119. ✅ Price alert form: up/down direction saved to backtest correctly
120. ✅ Time alert form: expiration set relative to replay time, fires at correct tick
121. ✅ Trendline alert form: points coordinates saved, fires on line crossing
122. ✅ Canceling an alert in-session removes it from smart session's `alerts`
123. ✅ Triggered alert in-session shows up in triggeredAlerts list
124. ✅ Alert form state preserved across mode switches
125. ✅ Alert form reopen after switch pre-fills last values (not lost)

### K. Trading Terminal Context — Tab/Symbol/Resolution/APIKey

126. ✅ **Tab switch mid-default-replay:** switching to tab B terminates the session
     on tab A (aligned with TV behavior)
127. ✅ **Tab switch mid-smart-replay:** same — session terminates, replay controls
     disappear, backtests widget no longer thinks we're backtesting
128. ✅ **Tab switch back to A:** no session resumes automatically (we exited on leave)
129. ✅ **Symbol change within same tab (default):** session terminates via engine
     auto-exit, `_onAutoExit` dispatches cleanup
130. ✅ **Symbol change within same tab (smart):** same
131. ✅ **Resolution change (default):** engine re-fetches at new resolution, session
     continues at same time
132. ✅ **Resolution change (smart):** same — backtest playback continues
133. ✅ **Resolution unsupported:** engine rejects → `resolution_change_failed` toast,
     chart period reverts to engine's actual period
134. ✅ **Second-based resolution (1S, 30S):** "Replay is not supported on
     second-resolutions" toast, replay not started
135. ✅ **API key controls disabled during any replay session:** selector / picker
     for exchange API key is non-interactive while default or smart replay is
     active (no actual api-key switching path exists to test — both modes use
     fictional balances, not the live account).
136. ✅ *(reserved — api-key change during session is a non-scenario; both replay
     modes ignore the selected exchange API key and use fictional data)*
137. ✅ Replay-mode-dependent UI re-renders correctly after any of the above
138. ✅ **Tab switch mid-selecting-start-time:** selection mode exits, no session starts

### L. Other Widgets & Components Affected

139. ✅ **Header buttons:** Buy/Sell/Alert buttons disabled during default replay
140. ✅ **Header buttons:** enable states consistent across mode switches
141. ✅ **Replay button header:** highlights when `selectingStartTime` active
142. ✅ **BidAsk overlay:** hidden during default replay, visible during smart/live
143. ✅ **Price alerts overlay:** hidden during default replay, visible during smart/live
144. ✅ **Time alerts overlay:** same as above
145. ✅ **Trendline alerts overlay:** same as above
146. ✅ **Orders overlay:** hidden during default replay, visible during smart/live
147. ✅ **OverlayContextMenu:** hidden during default replay
148. ✅ **Bases overlay:** always mounted, renders correctly in both modes
149. ✅ **Trades overlay:** always mounted, renders correctly in both modes
150. ✅ **PnL handle overlay:** renders in both modes when position open
151. ✅ **Screenshot overlay:** works in both modes
152. ✅ **Position info widget:** `select-position`, `date-selection` reflect correct source
153. ✅ **My Alerts widget:** smart alerts appear, default doesn't show any
154. ✅ **My Orders widget:** smart trades appear, default doesn't show any
155. ✅ **Positions widget:** smart-position actions match backtest state
156. ✅ **ReplayTimelines overlay:** visible in any replay mode, hidden in live
157. ✅ **Break-even overlay:** present in smart (with entry), not in default
158. ✅ **Chart color settings:** applied to both replay modes identically
159. ✅ **General settings:** replay-related toggles (dialog, auto-resume, etc.) persist

### M. Session Fixes — `_sessionChartId` pinning

160. ✅ Start default replay on tab A → `_sessionChartId` stored as tab A's id
161. ✅ Switch to tab B → controller's `_marketTabId` now = B, but session on A still
     reads/writes via pinned `_sessionChartId`
162. ✅ Switch back to tab A → session still belongs to tab A (not orphaned)
163. ✅ Stop session on tab A → `_sessionChartId` cleared AFTER clearReplaySession dispatch
164. ✅ Destroy controller with active session → `_sessionChartId` reset + session cleared
165. ✅ Symbol change triggering auto-exit → `_onAutoExit` clears pinned id in correct order
166. ✅ Opening a second chart (future multi-chart) wouldn't cross-contaminate the pin

### N. Session Fixes — Auto-resume race

167. ✅ Trigger fires mid-playback → controller pauses **synchronously** in step callback
168. ✅ Engine's per-tick for-loop doesn't fire additional steps before pause takes effect
169. ✅ Processing completes asynchronously in `_processTriggerAsync` (alerts, position)
170. ✅ After processing, `autoResumePlayback: true` → resume via `play()` if still paused
171. ✅ After processing, `autoResumePlayback: false` → stay paused
172. ✅ Multiple near-simultaneous triggers are handled serially (no clobber)
173. ✅ `wasPlaying` closure-captured, not read from instance field (no race)
174. ✅ Position change counts as "processed" → triggers resume
175. ✅ Alert triggered counts as "processed" → triggers resume
176. ✅ Alert canceled counts as "processed" → triggers resume
177. ✅ No trigger hit and no alert would fire → early return, no pause/resume

### O. Session Fixes — Default→Smart `startTime` prefill

178. ✅ Start default replay with startTime X
179. ✅ Click `ToggleReplayModeButton` while in default
180. ✅ `handleSwitchReplayMode` captures `this.startTime` before any cleanup
181. ✅ `handleNewBacktest({initiatedFromChart: true, replayStartAt: X})` threads X down
182. ✅ `goToReplayBacktest` passes `{replayStartAt: X}` to `_parseBacktestWithSave`
183. ✅ `BacktestEditModal` opens with start-date picker pre-filled with X
184. ✅ End-date picker uses its default, not X
185. ✅ Submitting the modal creates backtest with `replayStartAt = X`
186. ✅ Smart session starts at X — first candle matches default replay's first candle
187. ✅ Cancel modal → no backtest created, default replay still active (after handleStop)

### P. Session Fixes — Smart→Default exit

188. ✅ Start smart backtest with startTime X, play several candles forward
189. ✅ Click `ToggleReplayModeButton` while in smart
190. ✅ `exitSmartMode` captures startTime X before clearing `_backtest`
191. ✅ Session patch: `replayMode: DEFAULT`, smart-only fields cleared
192. ✅ Global `setReplayMode(DEFAULT)` dispatched → toggle button re-renders
193. ✅ `time`/`price` cleared to force re-sync from engine's next step emission
194. ✅ `setCurrentTime(X)` called on engine → progress resets to 0
195. ✅ After exit: default replay session at X, 0 progress, chart at startTime
196. ✅ Trade form submit button becomes disabled (matches default mode)
197. ✅ Alert form save button becomes disabled (matches default mode)
198. ✅ BidAsk/Orders/Alerts overlays hide (match default mode)
199. ✅ Smart-specific fields (alerts, triggeredAlerts, smartTrades, currentPosition) cleared
200. ✅ `_backtest` and `_lastCandle` cleared on controller

### Q. Session Fixes — Button text by current mode

201. ✅ Button reads `Selectors.selectReplayMode` (global), not `isSmartReplay` (setting)
202. ✅ Settings say smart, active session is default → button text reflects default
203. ✅ Settings say default, active session is smart → button text reflects smart
204. ✅ Button hidden when no session
205. ✅ `discovery` / `icon` props change together with text

### R. Session Fixes — Tab switch terminates session

206. ✅ Default replay on tab A → switch to tab B → session on A terminates
207. ✅ Smart replay on tab A → switch to tab B → session terminates, backtests widget
     no longer shows "currently backtesting"
208. ✅ Cleanup path: engine exit → `onReplayStatusChange(idle)` → `_onAutoExit`
209. ✅ Cleanup order: global `setReplayMode(undefined)` → `clearReplaySession` →
     `trading.reset()` → `smart.reset()` → `_sessionChartId = null`
210. ✅ Tab A's session data does not leak into tab B
211. ✅ Returning to tab A does NOT resume (aligned with TV)

### S. Cleanup, Destroy, Persistence

212. ✅ Chart unmount with active session → `destroy()` clears Redux state
213. ✅ Chart remount → no stale session, clean initial state
214. ✅ Poll-for-engine interval cleared on destroy
215. ✅ `_unsubStatus`, `_unsubStep`, `_unsubError` all called on destroy
216. ✅ `smart.destroy()` propagates, cleans up smart-specific subscriptions
217. ✅ Desktop↔mobile screen-switch aborts session cleanly
218. ✅ Reloading the app during an active session: session not restored (expected
     behavior until `session-persist.md`)
219. ✅ Opening a second tab with replay active then closing the first tab doesn't
     orphan the session

### T. Error Handling

220. ✅ `unsupported_resolution` → toast shown, period reverted to engine's actual period
221. ✅ `no_data_at_resolution` → toast shown, session unaffected
222. ✅ `no_data_at_time` → toast shown, session unaffected
223. ✅ `resolution_change_failed` → toast shown, period reverted
224. ✅ `partial_construction_failed` → toast shown, engine recovers gracefully
225. ✅ Unknown error types → generic `Replay error: <type>` toast
226. ✅ Engine never available after 20 poll attempts → console warn, no crash

### U. Engine & Data Edge Cases

227. ✅ `getFirstCandleTime` returns null → Random Bar silently aborts, no crash
228. ✅ Start time before first candle → backend/engine clamps, toast informs user
229. ✅ Start time in future → rejected (either toast or no-op)
230. ✅ Very long replay run (many hours) → memory usable, no leaks
231. ✅ Mid-session chart color change → colors re-apply without breaking engine state
232. ✅ Mid-session theme toggle → theme applied, replay continues
233. ✅ Mid-session resize → chart resizes, replay unaffected
234. ✅ Mid-session window refocus → status unchanged, playback continues

### V. Multi-component integration

235. ✅ ReplayControls ↔ trade form ↔ alert form all consistent about `replayMode`
236. ✅ `useActiveSmartReplay` hook returns correct controller outside chart tree
237. ✅ `ChartRegistry.get(chartId).replay` accessible from external thunks
238. ✅ `Selectors.selectReplayMode` always matches the UI state shown in the button

---

**Context actions matrix (K) requires these four baseline flows per mode:**

| Mode    | Action            | Expected                               |
|---------|-------------------|----------------------------------------|
| Default | Tab switch        | Session on leave-tab terminates        |
| Default | Symbol change     | Session terminates (engine auto-exit)  |
| Default | Resolution change | Session continues at new resolution    |
| Default | API key change    | N/A — api-key picker disabled in session|
| Smart   | Tab switch        | Session on leave-tab terminates        |
| Smart   | Symbol change     | Session terminates (engine auto-exit)  |
| Smart   | Resolution change | Session continues at new resolution    |
| Smart   | API key change    | N/A — api-key picker disabled in session|
