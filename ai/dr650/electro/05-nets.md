# Net list

Every net, its endpoints, and its function. A "net" here is one electrically common
set of terminals. Where a net's name changes across a connector, that is noted.

Ordered roughly by how much of the bike depends on it.

---

## `B/W` — chassis ground (the largest net)

Return path for everything. Endpoints:

- Battery `−` (via an in-line bullet, plus a chassis ground symbol)
- Regulator / rectifier
- Starter relay coil, low side
- Neutral switch (its `B/W` goes to its own chassis ground symbol)
- Side stand switch (through the diode drawn inside the switch body)
- Ignition coil primary
- CDI shell B
- Ignition switch terminal 4
- Headlight, tail/brake light, license light, speedometer light
- All four turn signal lamps
- Indicator light block pin 2
- Horn button (the button's ground side)

> `B/W` is ground. `W/B` is the brake light. They are different wires. See `02-wire-colors.md`.

## `R` — unswitched battery supply (after the main fuse)

- Battery `+` → **main fuse `F`** (inside the starter relay housing) → `R`
- Regulator / rectifier `R` (charging current returns to the battery here)
- Ignition switch terminal 1

Live at all times with the battery connected, even with the key out. Everything
downstream of the ignition switch depends on it. Handoff figure: **20 A main fuse**.

## `O` — main switched supply (ignition ON)

Fed by the ignition switch `R`—`O` contact in **ON** only.

- Ignition switch terminal 2
- Right handlebar 6-pin connector pin 3
- Left handlebar 9-pin connector (→ horn)
- Horn
- Rear brake switch
- Side stand relay pins 1 and 3
- Turn signal relay `+`
- Indicator light block pin 3 (neutral lamp)

**Tied to `Gr` and `Y/W`** through the splice inside the right handlebar switch
assembly — see below.

## `Gr` — tail light and instrument lighting

- Right handlebar 6-pin connector pin 5 (spliced to `O` inside the assembly)
- Ignition switch terminal 5
- Speedometer illumination bulb
- Tail/brake light, tail filament

## `Y/W` — headlight supply

- Right handlebar 6-pin connector pin 6 (spliced to `O` inside the assembly)
- Left handlebar 9-pin connector
- Dimmer switch common terminal

> **`O`, `Gr` and `Y/W` are one electrical node** because of the right-handlebar
> splice. The diagram gives them three names because they serve three circuits, but a
> meter will show continuity between all three. Confirm this on the bike before
> relying on it (`08-open-questions.md`).

## `Br` — position / parking lights

- Ignition switch terminal 6
- License plate light
- Front position-light stub connector (blank, unused)

Powered two ways: from `Gr` in **ON**, and directly from `R` in **P** (park). This is
the only circuit that is live with the key removed, and it is the likely path behind
the original "lights on with the key out" symptom when the loom shorted.

## `Y` — headlight high beam

Dimmer `HI` → fuse box fuse 1 → headlight `Y` filament, and → indicator light block
pin 1 (high beam lamp).

## `W` — headlight low beam

Dimmer `LO` → fuse box fuse 2 → headlight `W` filament.

## `W/B` — brake light

- Front brake switch terminal B (pigtail `B`, harness `W/B`)
- Rear brake switch
- Tail/brake light, brake filament

The two brake switches are in parallel; either one lights the lamp.

## `O/B` — switched supply after the side stand relay

- Side stand relay pin 4 (relay contact output)
- Right handlebar connector pin 1 → engine kill switch terminal A (pigtail `O/Y`)

## `O/W` — switched supply after the engine kill switch

- Engine kill switch terminal B
- Starter button terminal A (bussed to the same point)
- Right handlebar connector pin 2
- CDI shell B

Gates both the ignition and the starter: kill switch `OFF` kills both.

## `O/Y` — CDI enable / stop line

- CDI shell B
- Ignition switch terminal 3

Connected to ground (`B/W`) through the ignition switch in **ON** only *(inferred:
the ignition switch simply bridges `O/Y` to `B/W`; the CDI's internal use of that is
not shown)*. Turning the key off opens this line as well as removing `O` supply.

## `Y/G` — starter relay coil trigger

Starter button terminal B → in-line bullet → clutch lever position switch (both
terminals `Y/G`) → starter relay coil high side.

Series chain: the clutch must be pulled for the starter to crank.

## `G` — side stand relay coil, low side

- Side stand relay pin 2 (coil)
- Side stand switch
- Diode block (anode)

Grounded when the side stand switch closes, **or** through the diode block into `Bl`
when the neutral switch closes.

## `Bl` — neutral switch line

- Neutral switch (grounds it when in neutral)
- Diode block, common cathode

Also used as a magneto lead — see the duplicate-code warning in `02-wire-colors.md`.

## `Bl/B` — neutral indicator lamp return

Indicator block pin 4 (harness side) → diode block anode → `Bl` → neutral switch → ground.

## `Lbl` — flasher output

Turn signal relay output → left handlebar connector → turn signal light switch common.

## `B` — left turn signal feed

Turn signal switch `L` output → left handlebar connector → front left and rear left
turn signal lamps (harness side `B`, bulb side `B`) → indicator block pin 5.

## `Lg` — right turn signal feed

Turn signal switch `R` output → left handlebar connector → front right and rear right
turn signal lamps (harness side `Lg`, bulb pigtail `B`) → indicator block pin 6
(harness `Lg`, bulb side `Bl/W`).

## `B/Bl` — horn ground trigger

Horn → left handlebar connector → horn button → `B/W` ground when pressed.

## `Y` (×3, stator) — three-phase charging output

Generator stator → 3-pin connector → regulator / rectifier.

> Distinct from the single `Y` headlight high-beam net. Same code, different part of
> the bike; the stator `Y`s are a three-wire group at the engine.

## `W/Bl` — ignition coil primary drive

CDI shell B → coil 2-pin connector → coil primary (coil-side colour `B`).

## `B` (second net) — CDI ↔ magneto

CDI shell B → routes right across the harness → generator coil B. Distinct from the
left-turn `B` net.

## `G/Bl` and `R/B`

`G/Bl` runs from CDI shell B down to a 2-pin stub connector shared with `R/B`.
Purpose **(UNVERIFIED)**.
