# AI route planning & beach-run terrain scan

**Date:** 2026-08-18
**Status:** exploratory — both ideas are *long-future*, post-backend

## Summary

Explored adding an AI/LLM layer to Orion that lets users plan routes in natural
language ("find a 200km ride from A to B and back, passing area C, with at least
10km of mild offroad"). Conclusion: the LLM's job is only to parse intent into a
structured constraint object (start/end, distance target, waypoint areas, surface
mix, elevation); the actual geometry must come from a routing engine
(GraphHopper or BRouter with a bike/offroad profile) plus an iterative
loop-generation step that retries candidates until the distance and surface
constraints are satisfied. This breaks Orion's current "offline-first, no backend"
stance — an API key and a routing server can't ship in-app — so it must be an
opt-in, online-only layer rather than core.

A second thread explored terrain that has no roads mapped at all (e.g. beaches
separated by rock outcrops). A VLM on satellite imagery can reliably classify
sand vs. rock vs. water and spot gaps between beaches, but cannot judge
*passability* from ~0.5m/px overhead — tide state alone flips the answer. Correct
shape: OSM `natural=beach/sand` polygons as the routable surface, imagery-VLM as
a hint layer only, and every such segment labelled "unverified — scout on
arrival".

Narrowed to the user's actual near-term need: find the stretch of Philippine
coast with the longest run of consecutive beaches. That is a plain GIS query, not
an AI problem, and is very feasible as a one-off offline script.

## Key conclusions

- **LLM parses, routing engine solves.** Never ask the model to produce geometry.
- **Any of this requires a backend** (routing server + API key custody) and is
  online-only → opt-in layer, not part of the offline-first core.
- **Satellite VLM ≠ passability.** Useful as a hint, never as a routing decision;
  surface any such segment as unverified.
- **`~/git/philippines-json-maps` is unusable for this** — it is administrative
  boundaries (regions / provinces / barangays) only, no coastline or beach detail.
- **Use a Geofabrik OSM extract instead:**
  `download.geofabrik.de/asia/philippines-latest.osm.pbf` (~300–500 MB), then
  `osmium tags-filter ... wa/natural=beach,sand w/natural=coastline` reduces it to
  a few MB — small enough for plain Python/shapely, no PostGIS needed.
- The beach-run scan itself is an afternoon of work and runs entirely offline.

## Open questions

- Self-host the routing engine (e.g. GraphHopper on the phase-12 VPS) or use a
  hosted routing API?
- Should the LLM also *critique* candidate routes ("this segment uses a highway"),
  or purely parse intent?
- What gap length still counts as "consecutive" beaches — 200m of rock, 2km?
- How good is `natural=beach` coverage in the Philippines in practice? May need
  Sentinel-2 sand classification to fill gaps.
- Would public GPS-trace heatmaps be a better passability signal than imagery?
- Output format for the beach scan: ranked coordinate list, or GPX candidates to
  import into Orion?

## Ideas to realize

- **NL route planning layer (long-future, needs backend).** LLM parses a natural
  language request into a structured route-constraint object; a routing engine
  plus a candidate-iteration loop produces the actual geometry. Opt-in, online-only.
- **Self-hosted routing engine on the VPS.** GraphHopper or BRouter with a
  bike/offroad profile, reusing the phase-12 edge/VPS infrastructure.
- **Surface-aware routing constraints.** Support "at least N km of mild offroad" by
  routing on OSM `surface`/`tracktype` tags.
- **Loop-route generation.** Generate A→B→A circuits that hit a target total
  distance while passing through named areas.
- **Unverified-segment rendering.** Draw AI/imagery-derived or unmapped segments
  differently (dashed / warning color) and label them "unverified — scout on
  arrival".
- **Satellite VLM hint layer.** Classify sand / rock / water from imagery to
  suggest connections where OSM has no way mapped — advisory only, never routed on.
- **Beach-run coastal scan (near-term, standalone).** Offline Python script over a
  Geofabrik PH extract: project `natural=beach` polygons onto the coastline, find
  the longest runs with small gaps, rank by total sand length. Output as ranked
  coordinates or importable GPX.
- **GPS-trace passability signal.** Use public heatmap/trace data as evidence that
  an unmapped connection is actually rideable.
