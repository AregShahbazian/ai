# Superchart code review — phases 2 and 3

Scope: `5986d63` (`[sc-script-parity]`), `b586329` (`[sc-script-trimmings]`),
the coinray-chart submodule commit `e5f19660`, and the two unpushed review
fixes `f5b604b` and `c04109e`. Reviewed as the code stands, against SC's own
patterns.

**Result: 23 findings, 11 fixed, 12 recorded as NOT BEING DONE.**

Areg's decisions after pass 3: fix 10, drop 9, forget 8 (and 21-item-4 with it).

**On the recorded ones: they are not a backlog.** Areg does not keep tickets —
"we fix or forget". Everything below that is not fixed has been *decided
against*, with the reason. Nothing here is deferred, pending, or awaiting
revisit; if a recorded item ever needs doing, it will be because someone hits
it and rediscovers it, and this file is here so that person finds the analysis
already done. Read "not fixed" as "not doing, because —", never as "to do".
Plus **four corrections to earlier passes**, listed in their own section — the
most important being that the pass-2 "checked and clean" claim about the
persistence filter was false.

Fixes live in `f5b604b` + `c04109e` (passes 1-2), `1749193` (pass-3
persistence + docs), `7e2022e` (findings 17-19, 23) and `84d582a` (finding 10).
All unpushed.

## How this was run

Three passes.

- **Pass 1** (2026-09-01): one line-by-line angle; two finder agents died on
  the account rate limit, so the removed-behaviour and `useChartState` angles
  never ran. Findings 1-6; fixes in `f5b604b`.
- **Pass 2** (same day): the two missing angles plus a critical read of
  `f5b604b`. Findings 7-16; fix in `c04109e`. **Not independent** — the
  terminal restart did not create a new session, so the session that wrote
  pass 1 and directed `f5b604b` also ran pass 2 with all of it in context.
- **Pass 3** (2026-09-01, this one): a genuinely separate session in the
  Superchart repo, confirmed Opus 5, with no prior knowledge of this file or
  of `f5b604b`/`c04109e`. Findings formed **before** reading this document, as
  briefed. Findings 17-23, the corrections section, and the pass-3 fixes.

Pass 3 re-derived findings **1, 2, 3 and 16 independently** (16 in a stronger
form — see the corrections), so those are no longer single-session results.
Findings 4-15 remain reviewed by one session only, but pass 3 read the code
they cover and did not contradict them.

Bar applied, per Areg: fix only what is obviously a defect and obviously needs
fixing; write down anything theoretical and leave the code alone. Pass 3
changed ten things and left thirteen alone.

## The premise that scopes findings 3, 4, 5, 16, 23

These all live on the **`update()` fallback path**, taken when a
`ScriptProvider` has no `updateSettings`. Altrady's `WasmScriptProvider`
implements it as of 0.1.9, so **Altrady never takes this path**; SC's own
reference `WebSocketScriptProvider` (`examples/client`) does not implement it,
so it is the default for every other consumer. That is why none of these
surfaced in browser testing.

Finding 20 breaks that scoping: the same staleness has a `BACKEND_` twin that
is reachable on a plain symbol change, with no fallback path involved.

---

## Pass-3 fixes

Two commits, both `[sc-script-trimmings]`, neither pushed. Each verified
`tsc --noEmit` clean, vitest 36/36, and eslint byte-identical to the
pre-change baseline (41 problems, measured via `git stash`).

### `1749193` — persistence boundaries + docs

`src/lib/hooks/useChartState.ts` — three one-line applications of the existing
`dropEphemeralIndicators` helper, completing what `c04109e` set out to do
(finding 21):
- `withMergeRetry`'s conflict branch — filter the remote merge before it
  becomes the cache.
- `mirrorActiveTemplate` — filter the template body, as its sibling
  `saveChartTemplate` already does.
- the unmount flush — filter, since it bypasses `saveState` and so does not
  inherit that helper's new guard.

`docs/scripts.md` — the four phase-2 contract members that never reached the
docs (finding 22): `ScriptProvider.updateSettings?`, `modules` on `compile()`
and on `ScriptExecuteParams`, and `ScriptDiagnostic.file?`.

### `7e2022e` — findings 17, 18, 19, 23 (approved by Areg after pass 3)

Fixed as a set, per Areg's framing: one omission at four call sites, whose
shared question is *what removing something means when a script owns it*. The
rule now encoded at every site — **a user-facing bulk chart operation never
destroys a runtime-owned object; a script leaves the chart only through its
owner** (`useScriptIndicators.remove`, i.e. the pane-legend ✕ or
`removeScriptIndicator`).

- **17** — `removeAllOverlays`' no-groupId branch removes by id, skipping
  `isScriptOverlay`. The `groupId` bulk path is untouched: that is how the
  owner tears a whole script's primitives down.
- **18** — the object tree filters `isEphemeralIndicatorName` out of its
  indicator listing. Deliberately *not* given teardown branches — hiding the
  rows removes the orphaning path entirely, and the pane legend already routes
  removal correctly. Duplicating that branch is how it would drift.
- **19** — `applyChartTemplate`'s two wipes are filtered. **This reverses the
  recommendation this document made** — see the note below.
- **23** — preconditions moved above the teardown; a rejected re-execute drops
  the record and fires `onRemoved` before propagating. Emission is guarded on
  the delete actually removing the record, so a `remove()` landing during the
  await cannot produce two removal notices for one removal (caught reviewing
  the implementation, not present in the spec).

`isEphemeralIndicatorName` is now exported, which finding 15 also wanted.
`docs/scripts.md` and `docs/storage.md` updated where behaviour changed.

**Reversal on 19, recorded because this document got it wrong.** Findings
17-19 above originally recommended *tearing scripts down properly* on
`applyChartTemplate` (firing `onRemoved`), calling it "the smaller change".
Both halves of that were wrong. `applyChartTemplate` is reachable from three
separate `useChartState` instances (`SuperchartComponent.tsx:191`,
`useChartTemplates.ts:54`, `chart-browser/index.tsx:34`) while
`useScriptIndicators` is instantiated once — so tear-down would have needed a
store-level teardown registry to fire on the layout menu and chart browser,
which is the *larger* change. More importantly it would have given two
different answers to the same question (don't-touch at the object tree,
tear-down at template apply), which is exactly how a sixth site picks the
wrong one. Net behaviour: applying a layout leaves a running script running.

**Still deliberately not fixed**, both now one-liners against the exported
predicate: `lockAllOverlays` and `buildIndicatorsJson` (see Theoretical).
Findings 20 and 21-item-4 also remain open by design.

---

## Corrections to earlier passes

**These matter more than the new findings.**

### C1. "Every write to persisted `indicators` now passes the filter" is false

Pass 2's "Checked and clean" section states this after finding 7's fix. Pass 3
mapped every persistence boundary and found **four** that `c04109e` did not
reach. Two are `adapter.save`/`saveChartTemplate` calls — real durable writes,
not internal bookkeeping. See finding 21. The commit's own message also names
"unmount flush" as covered by the `saveState` fix; the unmount flush does not
go through `saveState` at all (`useChartState.ts:493-500` calls `adapter.save`
directly).

This is not a criticism of the fix's substance — the three boundaries it did
close were the right ones and the diagnosis was correct. The claim of
completeness was the error.

### C2. Finding 16 is understated, not "unreachable"

Pass 2 rated it *Unreachable* on the grounds that a script cannot exist
without a provider and symbol/period are never null after init. Both true. But
the same code block has a **reachable sibling** the rating missed: the
`await provider.executeAsIndicator(...)` on the re-execute leg can *reject*,
and it rejects after the same teardown. See finding 23. The disposition should
be "recorded, needs a policy decision", not "unreachable".

### C3. Finding 8 — retracted and restated (pass 3's own error)

Pass 3 originally wrote here that finding 8 "is no longer purely pre-existing".
**That was wrong, and it is retracted.** Re-derived from the code: neither
`c04109e` nor `1749193` made finding 8 worse or newly reachable. Its mechanism
— `syncToStorage` bumping the stored revision behind `useChartState`'s back, so
a later revision-less `saveState` clobbers the entry — is untouched by both
commits, and the entries it writes are keyed by the stable `definition.name`,
so `dropEphemeralIndicators` never eats them. Pass 2's "pre-existing, out of
scope" rating was correct.

What is true, and what C3 should have said, is narrower: **those same two
`adapter.save` calls carry a second, different defect** — they load the stored
record raw and write it back, re-persisting any `SCRIPT_*`/`BACKEND_*`
pollution already in it. That is **finding 21 item 4, not finding 8**. Two
defects at the same two lines, one inherited and one created by phase 3's
invariant. Conflating them made finding 8 look like something this phase
touched. It isn't.

### C4. Finding 4's mechanism is stronger than recorded

Pass 2 described visibility loss as `renderAndTrack` recreating with
klinecharts defaults. Pass 3 found the ordering is *decided*, not incidental:
`modifyIndicator`'s ephemeral early-return makes `overrideIndicator({visible:
false})` run synchronously while `doUpdate` runs a microtask later and
replaces the template. So the plot deterministically blinks and returns
**visible** while the modal's switch reads off. Same disposition (bundle with
3), better evidence.

---

## New findings (pass 3)

### 17. The object tree's "Remove all" destroys script primitives it deliberately hides — FIXED (`7e2022e`)

`src/lib/widget/object-tree/index.tsx:145` → `useChartState.ts:802`

`onRemoveAll` calls `removeAllOverlays()` with no groupId, which reaches
`chart.removeOverlay(undefined)` — every overlay on the chart, script
primitives included. The engine applies no `lock` exemption
(`Store.removeOverlay`, verified). `reconcilePrimitives` never asks the chart
what exists; it diffs `tracked` against the snapshot only.

Concrete: a script draws 40 markers. The object tree hides all 40 rows (the
phase-2 filter at `:49`). The user clicks "Remove all" to clear their own 3
drawings. All 43 go. `record.primitives` still holds 40 entries with matching
sigs, so on the next snapshot every key hits `existing.sig === sig` →
`continue` and nothing is recreated. On a live script only the last bar
changes per tick, so `affected` is 1-2 and never exceeds `beforeSize/2` — the
full-replace path, the only self-healing route, never fires. The markers are
gone for the life of the script, with no visible cause.

**Same shape, second entry point:** `useChartState.ts:1966`,
`applyChartTemplate`'s `chartInstance.removeOverlay()` wipe — applying a chart
layout produces the identical permanent desync. That one is worse; see 19.

This is the phase-2 filter applied to the tree's *reads* but not to the tree's
own destructive *action*. The same unfiltered call also strands
`utils/alerts.ts`'s registry and `orderLineApi`'s id map, so the fix belongs at
`removeAllOverlays`, not in the reconciler.

**Fixed** by the id loop — at user-drawing scale (tens) the cost is
irrelevant, and the bulk path stays available for the script teardown that
needs it.

### 18. The object tree lists ephemeral indicators, and its ✕ orphans a running script — FIXED (`7e2022e`)

`src/lib/widget/object-tree/index.tsx:75-87` and `:126-130`

The tree filters script *overlays* (`:49`) and then, twelve lines later,
iterates `chart.getIndicators()` with no ephemeral filter at all. Script and
backend templates are real registered indicators, so the user gets a row
titled `humanizeOverlayName('SCRIPT_9f3c1e2a-…')` → "SCRIPT 9f3c1e2a 4b…".

Worse, that row's ✕ routes to `chartState.popIndicator(name, paneId)`, which
only calls `chart.removeIndicator`. The `ActiveScript` record stays in
`activeRef`, `provider.stop()` is never called, `emitRemoved` never fires (so
the host still believes the script is on the chart), the script's primitives
stay drawn, and its sub-panes keep rendering.

Compare `SuperchartComponent.tsx:664-672`, where the **pane-legend** ✕ has
explicit `BACKEND_`/`SCRIPT_` branches routing to the correct teardown. Two ✕
buttons for the same indicator; one is right, one orphans the script. Textbook
"filter applied at one boundary but not its sibling".

**Fixed** by hiding them — consistent with hiding their primitives and with
persistence already treating them as non-existent, and it removes the
orphaning path rather than duplicating a teardown branch that could drift.

### 19. Applying a chart template silently orphans every running script — FIXED (`7e2022e`)

`src/lib/hooks/useChartState.ts:1966-1967`

`applyChartTemplate` wipes with `chartInstance.removeOverlay()` +
`chartInstance.removeIndicator()`, both unfiltered. That removes a running
script's panes *and* its primitives, while `useScriptIndicators`' record
survives intact: `onRemoved` never fires, the host still holds a live
`scriptId`, `ownerOf`/`getActiveByTemplateName` still resolve dead template
names, and the user has no pane legend left to click ✕ on. The script's
subscription keeps running and keeps delivering data to nothing.

Phase 3's PRD is "add to charts persistence across layouts", so scripts and
chart layouts are explicitly meant to coexist — this is in scope, not adjacent
to it.

**Fixed** by (b), preserving them — see the reversal note under `7e2022e`.
The recommendation originally made here, (a) tear-down, was both larger than
claimed and inconsistent with 17's answer.

### 20. The settings-modal staleness has a `BACKEND_` twin, reachable without the fallback path

`src/lib/components/SuperchartComponent.tsx:435-445`,
`src/lib/hooks/useBackendIndicators.ts:502-525`, `ChartWidget.tsx:414`

Finding 3 is scoped to the script fallback path, which Altrady never takes. The
same root cause — the modal keying off an ephemeral template name — reaches
backend indicators through a completely different door: the manual re-subscribe
branch, taken when a provider has no `onSymbolPeriodChange`, does
`activeRef.current.clear()` then re-adds, minting a fresh `BACKEND_<newId>`.

Concrete: open RSI's settings, then change symbol (the modal scrim covers the
chart, so the host's own symbol list is the normal way this happens). `symbol`
is a subscribed store value, so `SuperchartInner` re-renders,
`backendActiveForSettings` returns undefined, `settingDefs` goes undefined, the
Inputs tab disappears entirely, and `onSettingsApply`'s branches are both false
— every further edit silently does nothing. Cancel also stops undoing: the
`initialValues` memo recomputes off the *edited* values once `defs` changes
identity, so "change length 14→50, hit Cancel" leaves it at 50.

**NOT DOING for now** — same fix as finding 3, and it strengthens the case for
it, so the two stand or fall together rather than being ticketed separately.
The
modal should capture the **stable** id at open time (`scriptId` / the backend
`definition.name`) and re-resolve the live template name from it. That is the
one change that fixes 3, 4, 20 and most of 23's blast radius. Separately,
nothing clears `indicatorSettingModalParams` when its target disappears —
there is no cleanup effect anywhere.

### 21. `c04109e` filters three save paths, not every save path

`src/lib/hooks/useChartState.ts:353, ~397, 493-500`;
`src/lib/hooks/useBackendIndicators.ts:256, :275`

Pass 3 enumerated all ten boundaries where an indicator list enters the cache
or leaves for storage. `c04109e` closed three. Four were left open:

1. **`withMergeRetry`'s conflict branch** (`:353`) —
   `stateCache.current = mergeChartStates(next, err.remoteState)`, unfiltered.
   `err.remoteState` comes straight off another writer and `mergeChartStates`
   unions indicator lists by id. This is the *only* remaining way pollution
   enters the cache — and `c04109e`'s own rationale for filtering `loadState`
   was "or merged in from a remote writer". The sibling merge in the debounced
   path (`:479`) is filtered; this one was not.
2. **`mirrorActiveTemplate`** (`~:397`) — writes `cur.indicators` into a
   template body through `adapter.saveChartTemplate`, unfiltered, while its
   sibling `saveChartTemplate` (`:1911`) was filtered by this very commit. A
   template is precisely where an ephemeral entry persists forever instead of
   self-healing.
3. **The unmount flush** (`:493-500`) — calls `adapter.save(key,
   stateCache.current)` directly. The commit message lists this path as covered
   by the `saveState` fix; it does not go through `saveState`.
4. **`useBackendIndicators`' `syncToStorage` / `removeFromStorage`**
   (`:226-256`, `:262-275`) — load the record raw, mutate `state.indicators`
   in place, write it back. Fires on backend add, remove and settings Apply,
   i.e. exactly the interactions phase-3 R4 is about, and re-persists any
   pollution present. (See correction C3.)

**1-3 FIXED** in the working tree — three one-line uses of the existing helper,
which returns the same object when there is nothing to filter, so the common
path is unchanged. **4 — NOT DOING** (Areg, after pass 3). It needs the predicate exported
across hooks, and those two lines already carry finding 8's separate
persistence-ownership question. Both are unreachable in Altrady, which wires
no `indicatorProvider`. Forgotten together with finding 8 rather than
ticketed: if an SC consumer ever hits either, the analysis is here.

*Not a defect:* `syncToStorage` writes under the stable `definition.name`, not
`BACKEND_<id>`, so the phase-3 widening does not eat legitimate backend
persistence. Checked explicitly, because it would have been a bad regression.

### 22. Four phase-2 contract members never reached the docs

`docs/scripts.md` — the `ScriptProvider` block (`:12-51`),
`ScriptExecuteParams`, `ScriptDiagnostic`

Phase-2 T1 listed "Docs: `docs/scripts.md` + `docs/api-reference.md` for the
new members", with the verify step "grep docs signatures match code". Four
members were missing: `ScriptProvider.updateSettings?` (mentioned only in
prose under `updateScriptIndicator`, absent from the interface block), the
`modules?` parameter on `compile()`, `modules?` on `ScriptExecuteParams` /
`ScriptIndicatorParams` (absent from the docs **entirely**), and
`ScriptDiagnostic.file?`.

This is not cosmetic. `ScriptProvider` is the contract third-party provider
authors implement from these blocks, and `updateSettings?` being invisible
there is a plausible contributing reason it goes unimplemented — which is what
puts consumers on the fallback path that findings 3, 4, 5, 16 and 23 all live
on. `modules` being undocumented means the R4 deliverable has no discoverable
contract at all.

**FIXED** in the working tree. The `updateSettings?` entry says why to
implement it.

### 23. A rejected re-execute leaves the chart empty and the record alive — FIXED (`7e2022e`)

`src/lib/hooks/useScriptIndicators.ts:927-975` (`doUpdate`)

This is finding 16's reachable sibling (correction C2). The fallback does
chart-side teardown — cancel rAF, `removeIndicator` every template,
`removeOverlay({groupId})` — and *then* awaits
`provider.executeAsIndicator(...)`. If that rejects, `doUpdate` throws with the
teardown already done: the script is off the chart, the record still sits in
`activeRef` with the old `templates` and old `providerId`, `onRemoved` never
fires, and `docs/scripts.md:291` promises "Never fires
`onScriptIndicatorRemoved`".

Reachable in the ordinary way: a settings dialog is exactly where a user
supplies a value the script rejects. Finding 5's apply-on-every-keystroke makes
it likelier still — an intermediate value like `length: 0` (see the theoretical
note below) is sent to the provider on the way to a valid one.

Note the asymmetry with `add()`, which the design doc cites as precedent for
propagating the rejection: `add()` rejecting leaves nothing behind, because
nothing was rendered yet. `update()` rejecting leaves a hole.

**Fixed** by the first option — record dropped, `onRemoved` fired, rejection
still propagated, docs amended. Finding 16's guards were reordered as part of
the same change (pass 2 had declined to move them alone; with the rejection
case being fixed at the same site, doing both together is what makes the
teardown ordering honest).

---

## Findings 1-16 (passes 1-2)

Unchanged except where the corrections section says otherwise. Summarised here;
the full pass-1/2 text is in this file's git history.

**Fixed:** 1 (late primitives snapshot from a superseded subscription —
identity guard; independently re-derived by pass 3, correct as written),
2 (concurrent `update()` orphans indicators — per-hostId promise chain;
independently re-derived by pass 3, and the chain-map cleanup's identity check
before delete is correct), 7 (ephemeral indicators bypass three save paths —
see finding 21 for what it missed).

**Recorded as not being done:** 3 (settings modal inert after a fallback re-execute —
independently re-derived by pass 3; see also 20), 4 (visibility lost — see
C4), 5 (one provider round trip per control interaction), 6 (`onRemoved`
ordering in the bulk removal path), **10 — FIXED (`84d582a`)** (restore's
deferred indicator pass outlives its gate: it now claims a store-level
generation before its first await and bails when superseded, applyChartTemplate
bumps that generation before its wipe, and the timer is cancelled on unmount
with the chart re-read fresh inside the callback — the 500ms is untouched,
being load-bearing for chart init), **8 — NOT DOING** (backend writes bypass the
chart-state mirror; inherited, unreachable in Altrady, and the fix is a
persistence-ownership decision rather than a repair — see C3), **9 — DROPPED
on evidence** (`restoreChartState` discards unflushed edits: it requires
`autoSaveDelay > 0`, and cbsd measured it at **0** at runtime and passes it
nowhere in `src/`, so there is no pending timer and nothing to lose — the
finding is unreachable, not merely unlikely), 11 (full-replace can lose unchanged overlays on a
failed batch), 12 (paint order depends on the reconcile path), 13 (backend
eye-toggle no longer dirties the template — accepted, stated in the design),
14 (`reconcileApi` closes over the render-time chart), 15 (ephemeral-name
predicates not exported — findings 18 and 21 both now want this), 16
(fallback bails after teardown — see C2 and 23).

---

## Theoretical — recorded, code left alone

- **The engine has no `unregisterIndicator`.**
  `packages/coinray-chart/src/extension/indicator/index.ts:47` is a
  module-global `Record` that only ever grows. Every `add()` and every fallback
  re-execute permanently retains a template closing over that run's `dataStore`
  — a `Map` of every loaded bar — plus its figures and draw callback. Finding 5
  (apply on every keystroke) turns this into one retained bar-history per
  character typed. **This is a third argument for finding 3's recommended
  stable-name scheme:** naming templates `SCRIPT_<hostId>` makes re-registration
  overwrite in place, bounding the registry at one entry per live script. Not
  fixed because it is the same design revision, not a separate repair.
- **Scripts have no symbol/period handling at all.** `useScriptIndicators` has
  exactly one `useEffect` (unmount teardown); `ChartWidget.tsx:414` re-subscribes
  backend indicators only. After a symbol change a script keeps plotting the
  previous symbol's data. This is `plan.md`'s gap #3 (`onSymbolPeriodChange`),
  not a phase-2/3 regression — recorded here because it is the largest version
  of the lifetime question these phases kept running into.
- **Study templates are keyed by an ephemeral indicator name.**
  `StudyTemplatesRow.tsx:102-120` persists `body.indicatorName` verbatim and
  lists by it, so a preset saved from a script's or backend indicator's settings
  modal is keyed `SCRIPT_<uuid>`/`BACKEND_<id>` and becomes unreachable after
  any re-mint or reload, while the adapter accumulates dead rows. Verified by
  pass 3. It is the storage-side twin of the leak `isEphemeralIndicatorName`
  guards, at an adapter the predicate does not cover. Filed as theoretical
  rather than a finding because study templates on a script are a path nobody
  has exercised — promote it the moment anyone uses the feature.
- **Duplicate keys within one snapshot** (`reconcilePrimitives.ts:136-139`,
  `:155-160`): both paths create one overlay per array entry but `tracked.set`
  keeps only the last, orphaning the first inside the group until teardown.
  Violates the documented `key` contract in `types/primitive.ts:64`; depends on
  provider key minting. Independently reached by two pass-3 readers.
- **A provider reusing `indicatorId` across a re-execute** defeats the
  `rec.providerId !== subscription.indicatorId` identity guard and reconciles
  through the stale map — reopening finding 1. The guard rests on a value the
  *provider* controls; an SC-owned generation counter on the record would be
  correct by construction. No provider recycles ids today.
- **`buildIndicatorsJson`** (`widget/top-bar/export.ts:25-34`) exports
  `SCRIPT_*`/`BACKEND_*` templates while `buildDrawingsJson` five lines below
  filters. Arguably correct — a user exporting indicator data may well want the
  script's plotted values — but the internal uuid name leaks either way.
  Asymmetry noted; no fix proposed.
- **Other unfiltered bulk overlay ops:** `lockAllOverlays`
  (`useChartState.ts:785`) unlocks script primitives so the user can drag them;
  `SuperchartComponent.tsx:1105`'s bulk `overrideOverlay({visible})` hides them;
  `DsDrawingBar.tsx:313-318`'s `overlays.every(o => o.lock)` reads
  locked-forever script primitives, so with zero user drawings the lock icon
  reads "locked". All cosmetic and self-correcting; all fall out for free if
  finding 17's fix teaches the bulk ops the filter.
- **`Number('') === 0` reaches the provider.** Clearing a script's number field
  sends `length: 0`; `settingsFromValues` only clamps when the def declares a
  `min`. Sharpens finding 5 and feeds finding 23.
- **`isScriptOverlay`'s prefix** could be matched by a consumer explicitly
  passing `groupId: 'script:…'`, hiding their own persisted overlay from the
  tree and export. The engine's own default is `groupId ??= id` where ids are
  `overlay_<ms>_<n>`, so nothing accidental can collide.
- **No unit tests cover `useScriptIndicators` or `useChartState`**, where every
  fix in `f5b604b` and `c04109e` landed. Deliberately **not** raised as a
  finding: `vitest.config.ts` is `environment: 'node'`, there is no jsdom or
  testing-library dependency, and the config's own comment states the
  convention — "React components are still verified via tsc + the live
  example." Adding hook tests would be against the repo's pattern, not for it.

---

## Checked and clean (pass 3)

- **`reconcilePrimitives`.** Pass 3 tried to break it and could not, so this is
  stated rather than padded. `changedKeys`/`staleKeys` are provably disjoint
  subsets of `tracked`, so `affected ≤ beforeSize` and
  `beforeSize > 0 && affected > beforeSize/2` compares the right quantities with
  no off-by-one. Empty-tracked-huge-snapshot and huge-tracked-empty-snapshot
  both behave. `Store.addOverlays` returns one entry per input in order (`null`
  only for an unregistered name), so the `ids[i]` indexing is sound on both
  paths, and `tracked.delete(key)` on a null id correctly re-queues the key.
  Partial-create and create-fail leave `tracked` consistent with the chart.
- **The `calcParams` guard is correct and complete.** `defs` is one const feeding
  `engineInputs`, `config` and `apply`, with `defs` in every memo's deps — render
  and Apply cannot disagree. `apply` is the only route from this modal to
  `modifyIndicator` (`StudyTemplatesRow.onApply` funnels back through it). The
  guard holds even in finding 3's stale case: `getIndicatorConfig` returns `[]`
  for a `SCRIPT_*`/`BACKEND_*` name, so the stale path writes `{visible}` only,
  never `calcParams: []`. Phase 2's stated fix does what it claims.
- **`script_button` — all five steps done, one gate only.**
  `top-bar/index.tsx:227` + `:402`; `showScript` in `TopBar.tsx` guards only the
  `TbButton`. `openScriptEditor` and the editor mount key off
  `scriptProvider`/`ScriptEditor`, never the flag. Default `true`, present in
  the `FeatureFlag` union, the storybook `FLAG_CATEGORY` map and
  `docs/features.md`.
- **Both `SCRIPT_<id>` and `SCRIPT_<id>_<pane>` resolve**, as the design claimed
  — `renderAndTrack` pushes both shapes into `registeredTemplates` and
  `findByTemplate` does an exact `includes`.
- **`updateScriptIndicator`'s ready-gating** correctly matches
  `removeScriptIndicator` rather than `addScriptIndicator`: a pre-mount call
  cannot hold a valid scriptId, since ids only come from `addScriptIndicator`,
  which itself queues on `onApiReady`.
- **`f5b604b` guards only `onPrimitives` on identity, and that is right.**
  `onData`/`onTick`/`onHistory` from a superseded subscription write to a
  per-execution `dataStore` nobody reads and call `overrideIndicator` on names
  already off the chart — inert. Explicitly checked and explicitly not a
  finding.
- **`hostId` stability** — nothing nulls, reuses or reassigns a host-facing id;
  `stop()`/`updateSettings` are the only `providerId` consumers.
- **`groupId` teardown** — `script:<hostId>`, stable across providerId churn and
  strictly broader than the old per-tracked-id loop.
- **Style thunks** — the four primitive templates and both `tradeArrowFigures`
  figures now return plain objects, matching how `OverlayView.drawFigures`
  spreads them; the tests assert `.styles.color`, so a regression to the thunk
  form would fail. (The `styles: () => …` thunks still in
  `useScriptIndicators`' figure builders are *indicator* figures, where the
  engine does call them — correctly left alone.)
- **The engine changes** — `_sortOverlays(paneId)` scoping is safe; the
  `getOverlaysByFilter` id fast path still appends the progress overlay;
  `drawWideArrow`'s geometry is unchanged after the `wideArrowGeometry`
  extraction. The bulk `removeOverlay` branch is behaviourally equivalent to the
  single-match path for drawing overlays (both skip the array removal; an
  in-progress drawing lives in `_progressOverlayInfo`), confirming finding 6's
  narrower reading.
- **Working tree** — clean apart from an untracked `build.sh` (a two-line local
  convenience script, unrelated to this work).
