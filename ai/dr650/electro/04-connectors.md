# Connectors and pin maps

The diagram labels wires on **both** sides of every connector. On several connectors
the two labels differ — the component pigtail colour is not the harness colour. Those
are listed first because they are the highest-risk items on this bike.

Pin numbering below is **left-to-right as drawn on the diagram**, which is a schematic
order, not necessarily the physical cavity order. Always photograph the real connector
before unplugging it.

---

## Connectors where the colour CHANGES

### Right handlebar switch assembly — 6-pin

The single most confusing connector on the bike. Contains the engine kill switch, the
front brake switch and the starter button feed.

| Pin | Switch side | Harness side | Carries |
|---|---|---|---|
| 1 | `O/Y` | **`O/B`** | Kill switch terminal A ← side stand relay contacts |
| 2 | `O/W` | `O/W` | Kill switch terminal B, bussed to starter button terminal A; → CDI |
| 3 | `O` | `O` | Switched supply in; feeds front brake switch terminal A |
| 4 | `B` | **`W/B`** | Front brake switch terminal B → brake light |
| 5 | `O` | **`Gr`** | Tail light + speedometer light supply |
| 6 | `O` | **`Y/W`** | Headlight supply → dimmer switch common |

**Internal splice:** on the *switch side*, pins 3, 5 and 6 are spliced together
(verified: splice bus with junction dots at the pin-3 and pin-5 verticals; the pin-4
wire crosses that bus with **no** dot). So `O`, `Gr` and `Y/W` are one electrical node
in the harness — the assembly acts as the distribution point for switched power to the
lighting circuits.

> Practical consequence: the tail light and headlight supply current both pass through
> this connector's pins. Corroded pins here dim the lights.

**Not in this connector:** the starter button output `Y/G` leaves the handlebar as a
separate single wire on its own in-line bullet connector.

### Ignition coil — 2-pin

| Pin | Coil side | Harness side |
|---|---|---|
| 1 | `B/W` | `B/W` (ground) |
| 2 | **`B`** | **`W/Bl`** (primary drive from CDI) |

This is why there is a black wire at the coil but no `B` coil wire in the harness.

### Indicator light block — 6-pin

| Pin | Bulb side | Harness side | Circuit |
|---|---|---|---|
| 1 | `Y` | `Y` | High beam |
| 2 | `B/W` | `B/W` | Ground |
| 3 | `O` | `O` | Switched supply (neutral lamp) |
| 4 | `Bl` | **`Bl/B`** | Neutral lamp return → diode block |
| 5 | `B` | `B` | Left turn feed |
| 6 | `Bl/W` | **`Lg`** | Right turn feed |

### Turn signal lamps — 2-pin each

| Lamp | Bulb side | Harness side |
|---|---|---|
| Front turn (R) | `B`, `B/W` | **`Lg`**, `B/W` |
| Front turn (L) | `B`, `B/W` | `B`, `B/W` |
| Rear turn (R) | `B`, `B/W` | **`Lg`**, `B/W` |
| Rear turn (L) | `B`, `B/W` | `B`, `B/W` |

All four bulbs are identical parts with black pigtails; only the harness side tells
you which side of the bike it is.

---

## Connectors where the colour is the same both sides

| Connector | Pins | Wires |
|---|---|---|
| Ignition switch | 6 | `R`, `O`, `O/Y`, `B/W`, `Gr`, `Br` |
| Left handlebar switch assembly | 9 | `B/Bl`, `B/W`, `Lg`, `Lbl`, `B`, `O`, `W`, `Y`, `Y/W` |
| Speedometer | 2 | `Gr`, `B/W` |
| CDI shell B | 6 | `G/Bl`, `B`, `B/W`, `W/Bl`, `O/W`, `O/Y` |
| CDI shell A | 4 | **(UNVERIFIED)** — unlabelled at the CDI |
| CDI shell C | — | drawn empty |
| Diode block | 3 | `Bl/B`, `Bl`, `G` |
| Side stand switch | 2 | `G`, `B/W` |
| Rear brake switch | 2 | `O`, `W/B` |
| Side stand relay | 4 | `O`, `G`, `O`, `O/B` |
| Turn signal relay | 2 | `O`, `Lbl` |
| Fuse box | 4 | `Y`, `Y`, `W`, `W` |
| Starter relay | 3 signal + 2 heavy studs | `Y/G`, `B/W`, `R` + battery `+`, starter `M` |
| Regulator / rectifier | 5 | `Y`, `Y`, `Y`, `R`, `B/W` |
| Generator stator | 3 | `Y`, `Y`, `Y` |
| Tail / brake light | 3 × single bullet | `Gr`, `W/B`, `B/W` |
| License light | 2 | `Br`, `B/W` |
| Clutch lever position switch | 2 | `Y/G`, `Y/G` |
| Neutral switch | 2 | `Bl`, `B/W` |
| Ignition coil harness feed near fuse box | 2 | `B`, `B/W` — *see note below* |

> The 2-pin `B` + `B/W` connector drawn between the fuse box and the starter relay is
> the harness-side mate for a black-pigtailed component in that area. Its far end is
> **(UNVERIFIED)**; see `08-open-questions.md`.

## In-line single-wire bullet connectors

| Wire | Where |
|---|---|
| `Y/G` | Between the starter button and the clutch lever position switch |
| `Bl` | In the neutral switch line |
| `B/W` | In the battery negative / ground line near the battery |
| `Gr`, `W/B`, `B/W` | Three separate bullets at the tail/brake light |

## Blank / unused connectors

These are drawn as small plain rectangles with wires on one side only. They are live
harness stubs, not faults.

| Wires | Location | Note |
|---|---|---|
| `Br` + `B/W` | Left side, below the headlight | Front position-light output, unused as drawn. **`Br` is live in ignition P and ON** — cap it. |
| `G/Bl` + `R/B` | Lower middle, near the neutral switch | Purpose **(UNVERIFIED)** |
