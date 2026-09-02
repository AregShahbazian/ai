# Components and terminals

Every component on the diagram, its wires, and its switch table. Colours given are
**as labelled at that component**. Where a connector renames a wire, both names are
given and `04-connectors.md` has the full pin map.

---

## Power source and protection

### Battery
- `+` → heavy lead to the starter relay assembly (feeds both the main fuse and the
  starter contact).
- `−` → `B/W` → chassis ground. A second chassis ground symbol is drawn at the
  battery `−` lead.

### Starter relay assembly
One housing containing the starter relay **and the main fuse `F`**.

| Wire / terminal | Goes to |
|---|---|
| `Y/G` | Relay coil, high side — from the starter button via the clutch switch |
| `B/W` | Relay coil, low side — chassis ground |
| `R` | Output of main fuse `F` → the whole bike's unswitched supply |
| heavy stud | Battery `+` |
| heavy stud | Starter motor `M` |

Internally: battery `+` → fuse `F` → `R`. Battery `+` → relay contact → starter motor.

### Starter motor `M`
One heavy lead from the starter relay contact; case grounded to chassis (ground
symbol on the diagram).

### Fuse box (2 fuses)
Labelled on the diagram: **1: HEADLIGHT (HI), 2: HEADLIGHT (LO)**.

4 pins: `Y`, `Y`, `W`, `W`. Fuse 1 bridges the two `Y` pins; fuse 2 bridges the two
`W` pins. Both fuses sit **in line, downstream of the dimmer switch** — they protect
the headlight filaments only, not the lighting supply feeding the dimmer.

---

## Ignition and engine management

### Ignition switch
6 terminals, 4 positions.

Terminal order left-to-right as printed: `R` `O` `O/Y` `B/W` `Gr` `Br`.

| Position | Terminals connected |
|---|---|
| **P** (park) | `R` — `Br` (the bar spans over `O`, `O/Y`, `B/W`, `Gr` without touching them) |
| **LOCK** | nothing |
| **OFF** | nothing |
| **ON** | `R` — `O` · `O/Y` — `B/W` · `Gr` — `Br` (three independent bridges) |

### CDI unit
Three connector shells on the bottom edge.

| Shell | Pins | Wires |
|---|---|---|
| A (left) | 4 | **(UNVERIFIED)** — unlabelled at the CDI; run down toward the magneto/engine side |
| B (middle) | 6 | `G/Bl`, `B`, `B/W`, `W/Bl`, `O/W`, `O/Y` |
| C (right) | — | drawn empty, no wires |

Shell B roles:
- `O/W` — switched supply in (from the engine kill switch)
- `O/Y` — enable/stop line; grounded through the ignition switch in ON *(inferred)*
- `B/W` — ground
- `W/Bl` — ignition coil primary drive
- `B` — runs back to the generator/magneto
- `G/Bl` — runs down to a 2-pin stub connector shared with `R/B` (see `08-open-questions.md`)

### Ignition coil
- Primary, **coil side**: `B/W` and `B`.
- Primary, **harness side** (below the 2-pin connector): `B/W` and `W/Bl`.
- Secondary: two high-tension paths drawn to chassis ground (spark plug).

`B/W` is ground; the CDI fires the primary via `W/Bl`.

### Engine kill switch (right handlebar)
| | terminal A | terminal B |
|---|---|---|
| **RUN** | ●———● | |
| **OFF** | | |

- Terminal A — `O/Y` on the switch side, **`O/B`** in the harness.
- Terminal B — `O/W` both sides. This terminal is also bussed to the starter button.

> Note the switch-side `O/Y` here is a **different net** from the ignition switch's
> `O/Y`. The kill switch's becomes `O/B` at the connector.

### Generator (magneto)
- **Charging:** 3-phase star stator, three `Y` leads → 3-pin connector → regulator/rectifier.
- **Coil A:** leads `Bl` and `G`.
- **Coil B:** leads `W` and `B`.

Coils A and B are the pickup/signal coils feeding the CDI. Their routing into the CDI
is **(UNVERIFIED)** — see `08-open-questions.md`.

### Regulator / rectifier
5 wires: `Y`, `Y`, `Y` (from stator), `R` (DC out to the `R` supply net), `B/W` (ground).

---

## Starting and interlock

### Starter button (right handlebar)
| | terminal A | terminal B |
|---|---|---|
| **·** (rest) | | |
| **PUSH** | ●———● | |

- Terminal A — on the `O/W` bus (shared with the kill switch's terminal B).
- Terminal B — `Y/G`, leaving the handlebar as a **separate single wire** with its own
  in-line bullet connector (not part of the 6-pin connector).

### Clutch lever position switch
| | Y/G | Y/G |
|---|---|---|
| **ON** | ●———● | |
| **OFF** | | |

In series in the `Y/G` line between the starter button and the starter relay coil.
"ON" = clutch pulled in.

### Neutral switch
| | Bl | B/W |
|---|---|---|
| **OFF** | | |
| **ON** | ●———● | |

`B/W` goes straight to a chassis ground symbol. "ON" = transmission in neutral, which
pulls `Bl` to ground.

### Side stand switch
| | G | B/W |
|---|---|---|
| **ON** | ●———● | |
| **OFF** | | |

A **diode** is drawn in the `B/W` leg inside the switch body. `B/W` is ground.

### Side stand relay
4 pins: `O`, `G`, `O`, `O/B`.

- Coil between pin 1 (`O`, supply) and pin 2 (`G`, switched to ground by the side
  stand switch / neutral diode path).
- Normally-open contacts between pin 3 (`O`, supply) and pin 4 (`O/B`, out to the
  engine kill switch).

### Diode block
3 wires: `Bl/B`, `Bl`, `G`. Two diodes, both with their **cathode on the common `Bl`**:

- `Bl/B` ──▷|── `Bl`
- `G` ──▷|── `Bl`

So both `Bl/B` and `G` can sink to ground through `Bl` when the neutral switch closes,
and neither can backfeed the other.

---

## Lighting

### Headlight
Dual filament, 3 leads: `Y` (HI), `W` (LO), `B/W` (ground).

### Dimmer switch (left handlebar)
| | Y/W | W | Y |
|---|---|---|---|
| **HI** | ●———|———● | | |
| **LO** | ●———● | | |

`Y/W` is the common feed in. **HI** bridges `Y/W` to `Y` (the bar jumps over the `W`
column without touching it). **LO** bridges `Y/W` to `W`.

### Tail / brake light
Dual filament, 3 leads, each on its own in-line bullet connector, same colour both sides:
`Gr` (tail/running), `W/B` (brake), `B/W` (ground).

### License plate light
`Br` + `B/W`, via a 2-pin connector, same colours both sides.

### Speedometer illumination
`Gr` + `B/W`, via a 2-pin connector, same colours both sides.

### Front position light stub (left side of the bike)
A small blank connector carrying `Br` + `B/W` and no load. Same `Br` net as the
license light — i.e. the second position-light output. Unused on this model as drawn.

### Indicator light block
Three bulbs behind one 6-pin connector.

| Bulb | Bulb-side leads | Meaning |
|---|---|---|
| **H** | `Y` + `B/W` | High beam indicator |
| **N** | `O` + `Bl` | Neutral indicator |
| **T** | `B` + `Bl/W` | Turn signal indicator |

The `T` bulb is wired **across the two turn circuits** (left feed and right feed), so
it lights on either side using the opposite side's bulbs as the return path.

---

## Signals

### Turn signal relay (flasher)
2 wires, marked `+` and `−` on the diagram:
- `O` — switched supply in
- `Lbl` — flashing output to the turn signal switch

### Turn signal light switch (left handlebar)
| | Lg | Lbl | B |
|---|---|---|---|
| **L** | | ●———● | |
| **PUSH** | | | |
| **R** | ●———● | | |

`Lbl` is the common (flasher output). **L** connects `Lbl`—`B` (left). **R** connects
`Lbl`—`Lg` (right). The **PUSH** row (cancel) has no contacts.

### Turn signal lamps
All four bulbs have `B` + `B/W` pigtails; the harness side differs by side:

| Lamp | Bulb side | Harness side |
|---|---|---|
| Front turn (R) | `B`, `B/W` | `Lg`, `B/W` |
| Front turn (L) | `B`, `B/W` | `B`, `B/W` |
| Rear turn (R) | `B`, `B/W` | `Lg`, `B/W` |
| Rear turn (L) | `B`, `B/W` | `B`, `B/W` |

---

## Brake light switches

### Front brake switch (right handlebar)
| | terminal A | terminal B |
|---|---|---|
| **OFF** | | |
| **ON** | ●———● | |

- Terminal A — `O` (switched supply, from the internal splice).
- Terminal B — `B` on the switch side, **`W/B`** in the harness.

### Rear brake switch
| | O | W/B |
|---|---|---|
| **ON** | ●———● | |
| **OFF** | | |

Terminal colours are printed in the switch table itself. Both brake switches feed the
same `W/B` brake-light net in parallel.

---

## Horn

### Horn
2 wires: `O` (switched supply) and `B/Bl` (to the horn button).

### Horn button (left handlebar)
| | B/Bl | B/W |
|---|---|---|
| **·** (rest) | | |
| **PUSH** | ●———● | |

The button **grounds** `B/Bl`. The horn is live at all times with the ignition on.
