# The 6 ignition-switch wires — function map and rebuild reference

This is the working document for the front harness rebuild, and the one to print and
keep under the seat.

## Background

A theft attempt cut the six ignition-switch wires. They were reinsulated badly, and
over time shorted wire-to-wire inside the taped bundle. No fuse blew, because the
wires that touched sit at similar potentials — the shorts just melted insulation.
Symptoms were **no spark with strong cranking** (the ignition feed to the CDI was
compromised) and **lights staying on with the key out, varying with bar position**
(the `R`↔`Br` park path being bridged intermittently by the flexing bundle).

Currently running on a spare ignition lock with intact wires, with ~10 cm of harness
reinsulated as a stopgap.

---

## The six wires

Terminal order as printed on the ignition switch table, left to right.

| # | Colour | Name | Comes from | Goes to | Live when | Current (stock) |
|---|---|---|---|---|---|---|
| 1 | `R` | Red | Battery `+` via main fuse `F` (in the starter relay housing) | Ignition switch t1 | **Always** | Whole-bike load, up to ~12–14 A peak |
| 2 | `O` | Orange | Ignition switch t2 | Right bar switch pin 3 → the entire switched side of the bike | ON | ~7 A continuous, ~12 A peak |
| 3 | `O/Y` | Orange / yellow tracer | CDI shell B | Ignition switch t3 | ON (grounded) | Signal level, mA |
| 4 | `B/W` | Black / white tracer | Chassis ground | Ignition switch t4 | Always (it *is* ground) | Signal level, mA |
| 5 | `Gr` | Gray | The `O` node (spliced inside the right bar switch); also feeds tail + speedo lamps | Ignition switch t5 | ON | Only the `Br` load, ~0.4–0.8 A |
| 6 | `Br` | Brown | Ignition switch t6 | License plate light + front position-light stub | **ON and P** | ~0.4–0.8 A |

### Switch positions

| Position | Connects | Result |
|---|---|---|
| **P** (park) | `R` — `Br` | Position/license lights on, key removable, nothing else live |
| **LOCK** | nothing | Dead |
| **OFF** | nothing | Dead |
| **ON** | `R`—`O`, `O/Y`—`B/W`, `Gr`—`Br` | Bike live, CDI enabled, all lighting on |

### Why the gauges differ

Measured bare with calipers: `R` and `O` are 1.5 mm conductor diameter; `O/Y`, `B/W`,
`Gr` and `Br` are 0.8 mm. That matches the function map exactly and is a good sanity
check on the reading above:

- `R` and `O` carry **the whole bike's current** → heavy. AVS 1.25f nominal; **buy 1.5 mm²**.
- `Gr` and `Br` only carry the position-light circuit (the tail light is fed from `O`
  further along, not through the ignition switch) → **0.5 mm²**.
- `O/Y` and `B/W` only carry the CDI enable line → **0.5 mm²**.

---

## Colour scheme for the rebuild

Tracer wire in these combinations is not sourceable locally, so: plain ПВАМ wire with
**coloured heatshrink ring tracers**.

| Wire | Buy | Marking |
|---|---|---|
| `R` | Red 1.5 mm² | none |
| `O` | Orange 1.5 mm² | none (gauge distinguishes it from `O/Y`) |
| `O/Y` | Orange 0.5 mm² | **yellow** heatshrink rings |
| `B/W` | Black 0.5 mm² | **white** heatshrink rings |
| `Gr` | Gray 0.5 mm² | none |
| `Br` | Brown 0.5 mm² | none |

Rings at both ends and at every splice, so the tracer is visible anywhere the wire is
ever handled.

**The two oranges are the main error risk.** They also differ in gauge (1.5 vs 0.5),
which is the second check — if an orange wire looks thin, it is `O/Y` and it goes to
terminal 3.

Wire type: Russian ПВАМ (ПГВА equivalent for this purpose), −40 to +105 °C.

---

## Build rules (agreed)

1. **Photograph the pinout before cutting anything.**
2. Crimp **bare copper** — never pre-tin a crimp.
3. Open-barrel **ratcheting** crimper. Two crimps per terminal (wire barrel + insulation barrel).
4. Buy spare terminals; the first few crimps go in the bin.
5. **Individual heatshrink per joint, staggered along the run.** Never bundle the
   splices at one point — that is exactly the failure that caused this rebuild.
6. **No joints in the steering-head flex zone** (~40 cm). All splices go frame-side of it.
7. Generous service loop so the bars turn lock to lock without tension.
8. **Cut back past visible damage.** Bend-test the insulation; blackened strands mean
   cut further.
9. Before reassembly: **continuity check on every wire, and an isolation check between
   every adjacent pair.**
10. Keep the written colour-mapping note under the seat.

### Salvaged wire — acceptance criteria

Using stash wire instead of buying is fine, in this priority order:

1. **Multi-strand.** Solid core is disqualified at the flex zone. 7-strand is marginal
   but acceptable with a long service loop.
2. **Copper cross-section ≥ stock**, especially on `R` and `O`.
3. **Healthy insulation.** Appliance wire is often 70 °C PVC — keep it away from the
   engine and exhaust. The front section is fine for it.
4. Flexibility — least important of the four.
5. Colour — least important of all; the heatshrink rings carry the identity.

### Connector

Original is a Sumitomo HM-series 6-pin, green. Being replaced with a matched
aftermarket pair. **Keep the old halves as the pinout reference.** Verify that
1.5 mm² actually fits the new terminals' wire barrels before committing.

---

## Areg's bike vs. stock

| | Stock | Areg's bike |
|---|---|---|
| Headlight | 55/60 W halogen, ~4.1 A, fed through ignition switch + bar connectors + dimmer contacts | Auxito B7 H4 fanless LED, ~18–22 W real (~1.5 A) despite "90 W" marketing |
| Tail | Incandescent | LED |
| Continuous draw | ~7 A | ~4 A |
| Extra loads | — | 2-port USB fast charger (Zenfone 10, up to 30 W/port → 3–5 A with two devices) |
| Peak | ~12–14 A | ~12–14 A with everything on — about the stock design load |

### Planned improvement

Feed **the headlight and the USB charger from separate fused relays off battery `+`**,
triggered from switched power routed through the existing headlight off-switch (he
already has a switch + relay acting as an off-switch — repurpose that into the trigger
line).

- The trigger **must** come from switched power, so the headlight goes off with the key out.
- Result: the rebuilt ignition wires carry **~2–2.5 A** — signal-level — instead of the
  full lighting load.
- This takes the entire headlight current off the ignition switch contacts, the bar
  connector pins and the dimmer contacts, which is the stock design's weak point
  (see `06-circuits.md` §6).

---

## Under-seat card (copy this part)

```
DR650 ignition switch — 6 pin connector
terminal order as on the switch body, left to right:

 1  R     RED    1.5mm²   battery+ (via 20A main fuse in starter relay)  ALWAYS LIVE
 2  O     ORANGE 1.5mm²   switched supply out — everything
 3  O/Y   ORANGE 0.5mm² + YELLOW RINGS   CDI enable  (ON grounds it)
 4  B/W   BLACK  0.5mm² + WHITE  RINGS   chassis ground
 5  Gr    GRAY   0.5mm²   tail/speedo node — feeds Br in ON
 6  Br    BROWN  0.5mm²   license + front position   LIVE IN ON *AND* PARK

P    : R–Br            (park lights, key removable)
LOCK : nothing
OFF  : nothing
ON   : R–O, O/Y–B/W, Gr–Br

Watch out: two oranges. Thick = O (t2). Thin + yellow rings = O/Y (t3).
Br is live with the key out in P.
```
