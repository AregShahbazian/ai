# Phase 5: Replay Step Back — Tasks

PRD: `prd.md` (id `sc-replay-stepback`)
Design: `design.md`
Review: `review.md`

Tasks are ordered to keep each commit independently verifiable. Every task lists the
review item numbers it unlocks so the review checklist can be ticked off
incrementally.

---

## Task 1 — Add `resolutionToMs` helper

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/chart-helpers.js`

- Add `export function resolutionToMs(resolution)` next to `periodToResolution`.
- Handle suffixes: `S` (seconds), `D` (days), `W` (weeks), `M` (months ≈ 30 days),
  and plain numeric strings (minutes).
- Return `0` for falsy / unparseable input.

**Verification:** unit test mentally — `"60" → 3_600_000`, `"1D" → 86_400_000`,
`"1W" → 604_800_000`, `"15" → 900_000`, `"30S" → 30_000`. No review items unlocked
yet (pure helper).

---

## Task 2 — Add `goBackTo`, `handleStepBack`, `canStepBack` to `ReplayController`

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/controllers/replay-controller.js`

1. Import `resolutionToMs` from `../chart-helpers`.
2. Add instance field `_stepInFlight = false` alongside the existing private fields.
3. Add getter `canStepBack` (see `design.md` for exact logic).
4. Add method `goBackTo(time)` — async. Guards, trade revert branching on
   `replayMode`, `engine.setCurrentTime(time)`, `_stepInFlight` try/finally.
5. Add method `handleStepBack` — arrow property, calls `goBackTo` with
   `currentTime − resolutionMs`.
6. Do NOT touch `onReplayStep` wiring — the `direction` arg stays unused. (Unified
   seek path makes it irrelevant.)

**Verification:**
- Review §A items 1–8 (default replay core flow)
- Review §B items 9–16 (smart replay core flow)

---

## Task 3 — Render the step-back button

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/replay/replay-controls.js`

1. Compute `canStepBack` locally from the same Redux inputs the other controls use
   (session `time`, `startTime`, `status`, `replayMode`, current period). Use
   `resolutionToMs` on the current chart period.
2. Add `stepBackButton` `useMemo` block mirroring `stepButton`:
   - `icon: "arrow-left-to-line"`
   - `tooltip: replay.controls.stepBack` with the `replayStepBack` hotkey chord
   - `disabled: !canStepBack`
   - `onClick: () => replayController.handleStepBack()`
3. Render order: `backToStartButton`, **`stepBackButton`**, `stepButton`,
   `playButton`, ... (preserve surrounding separators).

**Verification:**
- §E items 29–32 (placement, tooltip, icon, disabled styling)
- §A items 1 + 6–7 (click behavior and boundary disabling)

---

## Task 4 — Hotkey command + default binding

**File:** `src/actions/constants/hotkeys.js`

1. Add `replayStepBack: "replayStepBack"` to `HOTKEY_COMMANDS`.
2. Add `[HOTKEY_COMMANDS.replayStepBack]: "shift+left"` to the `replay` keymap
   (next to `replayStep`).
3. Add `[HOTKEY_COMMANDS.replayStepBack]: i18n.t("actions.hotkeys.replayStepBack")`
   to the descriptions map.
4. Confirm no other keymap entry already binds `shift+left` (per design §Hotkey
   collision check).

**Verification:** §C item 20 (no collision).

---

## Task 5 — Wire hotkey to controller

**File:** `src/containers/trade/trading-terminal/widgets/super-chart/replay/replay-hotkeys.js`

1. Add `const handleStepBack = util.useImmutableCallback(() => replay?.handleStepBack())`
   next to `handleStep`.
2. Add `[hotkeysMap[HOTKEY_COMMANDS.replayStepBack]]: handleStepBack` to the
   `comboCallbackMap` memo.

**Verification:**
- §C items 17–19 (single-press hotkey)
- §D items 21–28 (held-hotkey serialization — the key feature)

---

## Task 6 — i18n strings

**File:** `src/locales/en/translation.yaml`

Add under the existing
`containers.trade.market.marketGrid.centerView.tradingView.replay` namespace:

```yaml
controls:
  stepBack: "Step Back ({{hotkey}})"
cantGoBackEarlierThanStart: "Can't go back earlier than the replay start time"
stepBackFailed: "Step back failed — try again"
```

And under `actions.hotkeys`:

```yaml
replayStepBack: "Replay step back"
```

Do NOT port to `nl` / `es` in this task — English-first, translations added later
by the localization flow.

**Verification:** Tooltip and toast text render correctly in §A/§B/§E.

---

## Task 7 — Review pass

**File:** `review.md`

Walk through all 40 verification items with the app running. Mark each ✅ as it
passes. For any failures, append `## Round 2: <description>` per workflow format
with root cause / fix / design notes.

**Special focus:**
- §D (held-hotkey) — use the network tab with throttling to validate smart replay
  serialization.
- §F (Trading Terminal context) — tab/symbol/resolution/exchangeApiKeyId changes.

---

## Out-of-task items (will need follow-ups, NOT in this PRD)

- Context-menu "Jump back to here" entry point → ✅ delivered in
  `[sc-chart-ctx-menu-options]`. The entry's onClick calls
  `replay.goBackTo(offsetTime * 1000)` directly.
- Storybook story for the step-back button in isolation — not required by workflow.
- Consolidating the duplicate `resolutionToMs` in `src/actions/ta-scanner.js` with
  the new `chart-helpers.js` export — nice-to-have refactor, separate branch.
- `nl` / `es` translations — localization pipeline.
