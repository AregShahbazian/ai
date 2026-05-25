# SC FR — `setSymbol` autosaves old-symbol overlays under new symbol

**Target:** Superchart
**Consumer:** Altrady — `feature/superchart-integration`
**Severity:** Data corruption across markets. Drawings drawn on one market
end up written under every other market the user visits afterwards.

## Symptom

After switching markets in a single chart instance via `sc.setSymbol`,
drawings drawn on the previous symbol appear in the storage record of the
new symbol. Open enough markets and they all converge to the same drawing
set.

## Repro

1. Open market A. Draw a horizontal line.
2. Switch the same chart to market B via `sc.setSymbol(B)`.
3. Inspect the per-symbol storage record for B.

Expected: B's record unchanged (no line written), or whatever B had before.
Actual: B's record now contains A's drawings (including the line just
drawn on A).

## Diagnosis (from live logs)

Console output during the switch:

```
[syncSymbol] BEFORE setSymbol. from: GDAX_USD_HYPE to: BMEX_USD_LTC
[syncSymbol] AFTER  setSymbol. now: GDAX_USD_HYPE          ← still old symbol
[adapter load @T] symbol: GDAX_USD_HYPE  overlays: [HYPE's 5 IDs]
[adapter save @T] symbol: BMEX_USD_LTC   overlays: [same 5 IDs]
```

Within a single tick after `sc.setSymbol("BMEX_USD_LTC")`:

1. `sc.getSymbol()` still returns the old symbol synchronously.
2. SC calls `adapter.load()` → consumer reads `sc.getSymbol()` →
   `"GDAX_USD_HYPE"` → returns HYPE's drawings.
3. SC eventually flips internal symbol state to `BMEX_USD_LTC`.
4. SC calls `adapter.save()` (triggered by the just-loaded data
   marking state dirty) → consumer reads `sc.getSymbol()` →
   `"BMEX_USD_LTC"` → SC hands the consumer the in-memory overlays
   (still HYPE's) for the consumer to save under LTC.

The `(overlays, symbol)` pair SC passes to `adapter.save()` is incoherent
— overlays belong to symbol A, but `getSymbol()` returns symbol B. The
consumer has no way to detect this and writes the wrong record.

## Root cause hypothesis

`sc.setSymbol(newSymbol)` does not atomically swap `{symbol, overlays}`
before SC's autosave/load pipeline runs. The symbol is updated at one
point, the overlays at another, and the consumer-facing
`adapter.load/save` callbacks fire in between.

## Required fix

Pick whichever is cleaner:

### Option A — Suppress autosave during `setSymbol` transition

`sc.setSymbol(newSymbol)` enters a "transition" mode in which:
- No `adapter.save()` is fired.
- `adapter.load(newSymbol)` is fired exactly once.
- When `load` resolves and overlays are swapped in, the transition ends
  and autosave resumes.

This preserves whatever was previously persisted for both the old and
the new symbol. Nothing in the old symbol's record is rewritten as part
of the swap (it was already saved if dirty before the swap began — the
consumer can re-emit a save before calling `setSymbol` if SC needs that).

### Option B — Atomically swap symbol and overlays before any storage call

`sc.setSymbol(newSymbol)`:
1. Save the current overlays under the OLD symbol (`adapter.save`,
   capturing the symbol at this exact moment, before the swap).
2. Clear in-memory overlays.
3. Update `sc.getSymbol()` to the new symbol.
4. Call `adapter.load()` with the new symbol; populate overlays.

No moment in time should exist where `sc.getSymbol()` returns the new
symbol while in-memory overlays still belong to the old symbol.

### Option C — Pass the symbol explicitly to `adapter.load/save`

Change the adapter contract so `load(symbol)` / `save(symbol, state, …)`
both receive the symbol as an argument (captured by SC at the same
moment as the overlays). The consumer no longer needs to read
`getSymbol()` — it just persists whatever symbol+state SC supplies.

C is the most defensive (eliminates the entire class of "consumer reads
stale symbol" bugs) and the cleanest contract long-term, but A or B work
if a contract change is too invasive.

## Hard requirements

- After `sc.setSymbol(B)` completes, no record other than A's old record
  (if it was dirty pre-swap) should have been written. B's record stays
  untouched unless the user actually edits B's overlays afterwards.
- No regression for in-place edits on a single symbol (autosave continues
  to fire normally as today).
- No regression for the existing programmatic-flag fix or the
  `onUserOverlayRightClick` route.

## Out of scope

- Backend changes (correctly scopes by `(account, coinray_symbol)` —
  verified in source).
- Consumer adapter changes — the consumer is reading `sc.getSymbol()`,
  the natural authoritative source. If SC adopts Option C the consumer
  will adapt; otherwise no consumer change should be needed.

## Notes

- The previous restore-path FR (`sc-fr-programmatic-restore.md`) is now
  fixed in main.
- Consumer's adapter is unchanged from the wiring described in
  `altrady-prompt-object-tree.md`; the `getSymbol` closure reads
  `scRef?.getSymbol?.()?.ticker`.
