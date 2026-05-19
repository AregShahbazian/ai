# Bug — `activeChartTemplate` not cleared from working layout when its named template is deleted

**Status:** Likely downstream of a separate 409 storm — see "Updated diagnosis"
**Audience:** SC library maintainers (FYI, no fix requested here)
**Reporter:** Areg (Altrady)
**Date observed:** 2026-05-19
**SC commit in use:** `6e9266b` (HEAD of `Superchart` linked into Altrady).
Fix commit `98c1446` ("feat: chart templates (named layouts) + persistence-bypass fixes")
is reachable from HEAD; cleanup code is present in the built bundle
(`superchart.es.js:40096-40097`).

---

## Symptom

After a user deletes a named chart layout in the picker, the period-bar
"Layout" button still shows the deleted layout's name as the active template
after reload. The named-layout list correctly shows "no layouts saved yet".

## Initial hypothesis (wrong)

Originally suspected SC wasn't clearing `activeChartTemplate` from the working
layout when `deleteChartTemplate` ran. SC maintainer confirmed the cleanup is
already implemented in `useChartState.ts:1197-1211` and shipped in `98c1446`
(May 7, 2026). Our pinned SC includes it.

## Updated diagnosis

The cleanup logic runs:

1. `await adapter.deleteChartTemplate(name)` — succeeds (DELETE → 204).
2. Mutate working state: `{...current, activeChartTemplate: undefined}`.
3. `await saveState(next)` — **fails with 409** because of a separate
   in-flight 409 storm on staging.

When step 3 throws, the cleanup write never lands. On reload, storage still
holds the old `activeChartTemplate`, so the period-bar shows the phantom
label. The bug surface visible to the user is "stale name" but the
underlying cause is the 409 storm.

### Why we believe the 409 is the same one

User can also reproduce the 409 just by creating a new named layout from a
clean session — every save flow on staging is currently hitting 409 once
`expected_revision` gets out of sync. SC's merge-retry in `useChartState`
isn't recovering it. Investigation in progress on the Altrady side.

## Action

- **No fix needed in SC for the stale label** — the existing cleanup code is
  correct.
- Altrady investigates the 409 storm on staging. Once that's gone, the
  cleanup save will land and the stale-label symptom disappears.
- If after fixing the 409 we still see the stale label, this file gets
  reopened with new evidence (likely hypothesis 3 from SC: a debounced
  autosave race re-introducing the old name after the clean-write).

## Backend-merge hypothesis (also ruled out)

For the record: SC's clean-write produces `{...current,
activeChartTemplate: undefined}`. `JSON.stringify` drops the `undefined` key.
Our `PATCH /superchart/layout` does `layout.update!(state: params[:state])` —
the `state` column is replaced wholesale, never merged. So even if SC sent
the cleanup write with the key omitted, the backend wouldn't re-introduce
the old value from an earlier record.
