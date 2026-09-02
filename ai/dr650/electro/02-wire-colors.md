# Wire colour codes

## Legend (as printed on the diagram)

27 codes: 11 solid, 16 with a tracer stripe.

### Solid

| Code | Colour |
|---|---|
| B | Black |
| Bl | Blue |
| Br | Brown |
| G | Green |
| Gr | Gray |
| Lbl | Light blue |
| Lg | Light green |
| O | Orange |
| R | Red |
| W | White |
| Y | Yellow |

### With tracer

| Code | Colour |
|---|---|
| B/Bl | Black with Blue tracer |
| B/Lg | Black with Light green tracer |
| B/O | Black with Orange tracer |
| B/R | Black with Red tracer |
| B/W | Black with White tracer |
| Bl/B | Blue with Black tracer |
| Bl/W | Blue with White tracer |
| G/Bl | Green with Blue tracer |
| O/W | Orange with White tracer |
| O/Y | Orange with Yellow tracer |
| R/B | Red with Black tracer |
| W/B | White with Black tracer |
| W/Bl | White with Blue tracer |
| Y/B | Yellow with Black tracer |
| Y/G | Yellow with Green tracer |
| Y/W | Yellow with White tracer |

`B/Lg`, `B/O`, `B/R` and `Y/B` appear in the legend but are **not used** anywhere on
this diagram — the legend is a generic Suzuki block.

## Traps

### 1. Four look-alike codes

At normal reading size these are routinely misread. Zoom to 8–10× before trusting one.

- `B` (Black) vs `Bl` (Blue) — one letter apart, both short.
- `B/W` (Black w/ White) vs `W/B` (White w/ Black) — **opposite wires**: `B/W` is
  ground, `W/B` is the brake-light feed.
- `Bl/B` vs `Bl/W` vs `B/Bl` — three different nets.
- `W/Bl` (coil primary) vs `W/B` (brake light) vs `B/W` (ground).

### 2. The three oranges

`O`, `O/W`, `O/Y` and `O/B` are four separate nets that all look orange in a dusty
loom. On the physical bike they are the ignition-supply family:

| Code | Role |
|---|---|
| `O` | Main switched supply (ignition ON) |
| `O/B` | Switched supply after the side stand relay contacts |
| `O/W` | Switched supply after the engine kill switch — CDI + starter button |
| `O/Y` | CDI enable/stop line, grounded by the ignition switch in ON |

### 3. Plain `B` is used for two unrelated nets

There are **two electrically separate `B` nets** on this bike:

1. **`B` = left turn signal feed** — turn signal switch → front/rear left indicators.
2. **`B` = CDI ↔ magneto** — a CDI shell-B pin running back to the generator.

They are in different parts of the loom, but if you ever bridge them you will flash
the left indicators off the ignition system. Verify by location, not by colour alone.

Note also that `B` appears a *third* time as a **pigtail-only** colour inside the
right handlebar switch (front brake switch output) — but that one becomes `W/B` at
the connector and never exists as `B` in the main harness. See `04-connectors.md`.

### 4. `Bl` and `G` are each used twice

- `Bl` — neutral switch line **and** a magneto lead.
- `G` — side stand switch line **and** a magneto lead.

Same caution as above.

## Areg's rebuild: colour availability

The 6 ignition-switch wires are `R`, `O`, `O/Y`, `B/W`, `Gr`, `Br`. Tracer wire in
these combinations is not sourceable locally, so the plan is **plain wire + coloured
heatshrink ring tracers**:

- `O/Y` → plain orange 0.5 mm² with **yellow** heatshrink rings
- `B/W` → plain black 0.5 mm² with **white** heatshrink rings
- `R`, `O`, `Gr`, `Br` → plain, no rings needed

Rings go at both ends and at every splice, so the tracer is visible wherever the wire
is ever handled. The two oranges (`O` 1.5 mm² and `O/Y` 0.5 mm²) are the main
mix-up risk — they also differ in gauge, which is a useful second check.
