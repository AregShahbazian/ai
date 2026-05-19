# Bug — `PATCH /superchart/layout` doesn't honor unconditional saves (SC's `saveState` always 409s)

PRD: [prd.md](./prd.md) (id: `sc-endpoints`)
Design: [design.md](./design.md)
Reporter: Areg (frontend)
Date observed: 2026-05-19
Backend commit: `88564a22 add SuperChart persistence endpoints [sc-endpoints]`
Frontend branch: `feature/superchart-integration` (Altrady desktop), HTTP storage adapter @
`src/containers/trade/trading-terminal/widgets/super-chart/http-storage-adapter.js`

---

## Symptom

Reproduced on staging from a fresh chart:

```
[sc-storage] save → {activeChartTemplate: 'stag-http-2', expectedRevision: 0}
PATCH https://app-staging.altrady.com/api/v3/superchart/layout 409 (Conflict)
[sc-storage] save ← {status: 409, newRevision: undefined, remoteRevision: 18}
```

Server has `revision: 18`; SC sends a save with no `expectedRevision`; the
frontend adapter falls back to `0`; backend's strict check rejects it. Every
SC code path that uses `saveState` (selecting / creating / deleting a named
layout, clearing chart, etc.) 409s and silently drops the write — that's the
"stale `activeChartTemplate` survives reload" bug too.

## Root cause: contract mismatch

`StorageAdapter.save(key, state, expectedRevision?)` is defined by SC's
contract (`Superchart/src/lib/types/storage.ts`, mirrored in
`superchart/dist/index.d.ts` line 1882):

> If `expectedRevision` is provided and doesn't match the adapter's current
> revision for the key, throw `StorageConflictError` carrying the remote
> state so the caller can merge and retry. **If `expectedRevision` is
> omitted, the save is unconditional (last-write-wins).**

SC has two save paths in `useChartState.ts`:

1. **`withMergeRetry`** (line 208–261) — used for optimistic mutations.
   Calls `adapter.save(key, next, expectedRevision)` with the revision
   read from `adapter.load(key)`. Conflict → merge → retry.
2. **`saveState`** (line 178–193) — used for "unconditional / last-write-
   wins" overwrites: clearState, applying a chart template, autosaves
   triggered by `setActiveChartTemplate`. Calls `adapter.save(key, state)`
   **deliberately omitting** `expectedRevision`. The docstring says so
   verbatim ("Save state to storage unconditionally (last-write-wins)").

Our backend doesn't support the second case. From
`app/api/api_v3/superchart.rb`:

```ruby
desc_endpoint "Save current SuperChart layout", %w(SuperChart)
params do
  use :auth
  requires :state,             type: String
  requires :expected_revision, type: Integer   # ← strict; no omitted path
end
patch "/superchart/layout" do
  layout = current_account.superchart_layout ||
           current_account.build_superchart_layout(revision: 0)

  if params[:expected_revision] != layout.revision   # ← always compares
    error!({remoteState: layout.state, remoteRevision: layout.revision}, 409)
  end

  layout.update!(state: params[:state], revision: layout.revision + 1)
  present({revision: layout.revision})
end
```

`requires :expected_revision` forces SC's unconditional save path to
fabricate a value, which then always mismatches → guaranteed 409.

Drawings already do this correctly:

```ruby
optional :expected_revision, type: Integer

patch "/superchart/drawings/:coinray_symbol" do
  ...
  if params[:expected_revision].present? && params[:expected_revision] != drawing.revision
    error!({...}, 409)
  end
  ...
end
```

Layout should mirror the same pattern.

## Fix

`app/api/api_v3/superchart.rb` — `PATCH /superchart/layout`:

```ruby
desc_endpoint "Save current SuperChart layout", %w(SuperChart)
params do
  use :auth
  requires :state,             type: String
  optional :expected_revision, type: Integer
end
patch "/superchart/layout" do
  layout = current_account.superchart_layout ||
           current_account.build_superchart_layout(revision: 0)

  if params[:expected_revision].present? && params[:expected_revision] != layout.revision
    error!({
      remoteState:    layout.state,
      remoteRevision: layout.revision,
    }, 409)
  end

  layout.update!(state: params[:state], revision: layout.revision + 1)
  present({revision: layout.revision})
end
```

Three minimal changes:
1. `requires :expected_revision` → `optional :expected_revision`.
2. Conflict check gated by `params[:expected_revision].present?`.
3. Update the PRD's "1. Layout record" section to mark `expectedRevision?`
   (with `?`) in the PATCH body schema, matching drawings.

## PRD update

`prd.md` section "1. Layout record":

```
PATCH  /superchart/layout                        body: {state, expectedRevision?}
                                                 → 200 {revision}
                                                 → 409 {remoteState, remoteRevision} on mismatch (only when expectedRevision sent)
```

Add a note mirroring the drawings paragraph:

> `expectedRevision` is optional. When sent, the server enforces
> optimistic concurrency and returns 409 on mismatch. When omitted, the
> save is last-write-wins — used by SC's `saveState` path
> (clearState, applying chart templates, `setActiveChartTemplate`).

## Regression / smoke after fix

Staging curls to confirm:

```bash
# 1. With expected_revision — still 409s on mismatch:
curl -X PATCH "$BASE/superchart/layout" -H "Authorization: $JWT" \
  -H 'Content-Type: application/json' \
  -d '{"state":"{}","expectedRevision":0}'
# → 409 when server revision > 0

# 2. Without expected_revision — succeeds unconditionally:
curl -X PATCH "$BASE/superchart/layout" -H "Authorization: $JWT" \
  -H 'Content-Type: application/json' \
  -d '{"state":"{\"foo\":1}"}'
# → 200 {"revision": N+1}
```

## Frontend mitigation in place

Pending the backend fix, the frontend adapter caches the last-known
revision and substitutes it when SC omits `expectedRevision`:

`http-storage-adapter.js`:
```js
const sentRevision = expectedRevision ?? this._lastLayoutRevision
```

This unblocks staging but violates the contract — when our cache lags
behind reality (multi-device, network races), the adapter raises a
`StorageConflictError` SC's `saveState` didn't ask for. SC silently drops
it (saveState has no retry loop) and the write is lost. Backend fix
above eliminates the need for this workaround; once it ships I'll remove
the `_lastLayoutRevision` cache from the adapter.

## References

- SC source: `Superchart/src/lib/hooks/useChartState.ts:178-193` (saveState)
- SC source: `Superchart/src/lib/hooks/useChartState.ts:208-261` (withMergeRetry — the path that DOES pass expectedRevision)
- SC contract: `Superchart/src/lib/types/storage.ts` `StorageAdapter.save` docstring
- Backend: `app/api/api_v3/superchart.rb` PATCH /superchart/layout
- Frontend adapter: `crypto_base_scanner_desktop/.../super-chart/http-storage-adapter.js` `save()` method
