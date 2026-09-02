# Circuit walkthroughs

Each circuit traced end to end, in the order current actually flows.

---

## 1. Supply and ground

```
Battery +  ──►  main fuse F (inside the starter relay housing)  ──►  R  ──►  ignition switch t1
Battery +  ──►  starter relay contact  ──►  starter motor M  ──►  chassis
Battery −  ──►  B/W  ──►  chassis
```

`R` is the only unswitched feed into the harness. Everything else on the bike hangs
off the ignition switch. The regulator/rectifier also lands on `R`, so charging
current reaches the battery through the main fuse.

**Consequence:** a blown main fuse kills the whole bike *and* charging.

---

## 2. Ignition ON — what comes alive

Turning the key to **ON** closes three independent contacts at once:

| Contact | Effect |
|---|---|
| `R` — `O` | Powers the whole switched side of the bike |
| `O/Y` — `B/W` | Grounds the CDI enable line |
| `Gr` — `Br` | Powers the position lights from the `Gr` node |

Because `O`, `Gr` and `Y/W` are spliced together inside the right handlebar switch,
closing `R`—`O` alone already powers the lighting node. The `Gr`—`Br` contact exists
to extend that to the position-light circuit (`Br`).

---

## 3. Ignition / spark

```
O  ──►  side stand relay contacts  ──►  O/B  ──►  engine kill switch (RUN)  ──►  O/W  ──►  CDI
O/Y  ──►  ignition switch (ON)  ──►  B/W  ──►  chassis          [CDI enable]
Generator pickup coils  ──►  CDI                                 [timing signal]
CDI  ──►  W/Bl  ──►  coil 2-pin connector  ──►  coil primary (coil-side B)
Coil primary other side  ──►  B/W  ──►  chassis
Coil secondary  ──►  spark plug  ──►  engine ground
```

Three independent things stop the engine:

1. **Key OFF** — removes `O` supply *and* opens the `O/Y` enable line.
2. **Kill switch OFF** — opens `O/B`→`O/W`, unpowering the CDI.
3. **Side stand relay de-energised** — opens `O`→`O/B` upstream of the kill switch.

> Areg's original fault was **no spark with strong cranking**. That symptom points at
> this chain: strong cranking means `R` and the starter relay were fine, so the break
> was between the ignition switch and the CDI — exactly the section that was cut and
> badly reinsulated.

---

## 4. Starting and the interlock

```
O/W (kill switch RUN)  ──►  starter button (PUSH)  ──►  Y/G
Y/G  ──►  in-line bullet  ──►  clutch lever position switch (clutch pulled)  ──►  Y/G
Y/G  ──►  starter relay coil  ──►  B/W  ──►  chassis
Relay energises  ──►  battery +  ──►  starter motor
```

Conditions to crank, all required:
- Key **ON** (gives `O`)
- Side stand relay energised (gives `O/B` → `O/W`)
- Kill switch **RUN**
- Clutch lever pulled in
- Starter button pressed

### The side stand relay

```
Coil high side: O (switched supply)
Coil low side:  G  ──►  side stand switch (stand up)  ──►  B/W  ──►  chassis
        or:     G  ──►  diode  ──►  Bl  ──►  neutral switch (in neutral)  ──►  chassis
```

The two diodes in the diode block both point **into** `Bl`, so `G` and the neutral
lamp return `Bl/B` can each sink to ground through the neutral switch without
backfeeding each other.

Net logic: **the engine may run and crank if the side stand is up OR the gearbox is
in neutral.** With the stand down and in gear, the relay drops out, `O/B` dies, and
both spark and starter are cut.

---

## 5. Charging

```
Generator 3-phase stator (3 × Y)  ──►  3-pin connector  ──►  regulator / rectifier
Regulator  ──►  R  ──►  main fuse node  ──►  battery +
Regulator  ──►  B/W  ──►  chassis
```

Permanent-magnet three-phase alternator with a shunt regulator/rectifier. Output is
unswitched — it charges whenever the engine turns, key position irrelevant.

---

## 6. Headlight

```
O  ──[splice inside right bar switch]──►  Y/W  ──►  left bar connector  ──►  dimmer switch
Dimmer HI  ──►  Y  ──►  fuse box fuse 1  ──►  headlight Y filament
Dimmer LO  ──►  W  ──►  fuse box fuse 2  ──►  headlight W filament
Headlight  ──►  B/W  ──►  chassis
Y also  ──►  indicator block pin 1  ──►  high beam lamp  ──►  B/W
```

Points worth knowing:

- **The headlight is on whenever the key is ON.** There is no headlight switch in the
  stock circuit.
- **The fuses are downstream of the dimmer**, one per filament. They do not protect
  the `Y/W` supply run, the dimmer contacts, the handlebar connector pins, or the
  ignition switch — which all carry full headlight current.
- Full headlight current therefore passes through: ignition switch `R`—`O` contact →
  right bar connector pin 3 → internal splice → pin 6 → left bar connector →
  dimmer contacts → fuse → bulb. That is a long chain of small contacts, and it is
  exactly what Areg's planned relay conversion removes.

---

## 7. Position / tail lighting

```
ON:   O ≡ Gr  ──►  ignition switch Gr—Br  ──►  Br  ──►  license light, front position stub
      Gr  ──►  tail/brake light tail filament
      Gr  ──►  speedometer illumination
P:    R  ──►  ignition switch R—Br  ──►  Br  ──►  license light, front position stub
```

In **P**, only the `Br` circuit is live — the key can be removed while the position
lights stay on. In **ON**, `Gr` and `Br` are both live, so tail + speedo + license +
position stub are all on.

---

## 8. Brake light

```
O  ──►  right bar connector pin 3  ──►  front brake switch  ──►  pigtail B  ──►  pin 4  ──►  W/B
O  ──►  rear brake switch  ──►  W/B
W/B  ──►  tail/brake light brake filament  ──►  B/W  ──►  chassis
```

Both switches feed the same `W/B` net in parallel. Independent of `Gr`, so the brake
light works with the tail filament dead.

---

## 9. Turn signals

```
O  ──►  turn signal relay (flasher)  ──►  Lbl  ──►  left bar connector  ──►  turn signal switch
Switch L  ──►  B   ──►  front left + rear left lamps  ──►  B/W  ──►  chassis
Switch R  ──►  Lg  ──►  front right + rear right lamps  ──►  B/W  ──►  chassis
Indicator T lamp sits between B and Lg
```

The turn indicator bulb bridges the two feeds, lighting from either side through the
opposite side's bulbs. A burnt-out lamp on one side changes how the indicator behaves.

---

## 10. Horn

```
O  ──►  left bar connector  ──►  horn  ──►  B/Bl  ──►  left bar connector  ──►  horn button
Horn button PUSH  ──►  B/W  ──►  chassis
```

The horn is permanently live with the key on; the button switches the **ground** side.

---

## 11. Neutral indicator

```
O  ──►  indicator block pin 3  ──►  N lamp  ──►  Bl (bulb side) / Bl/B (harness side)
Bl/B  ──►  diode  ──►  Bl  ──►  neutral switch (in neutral)  ──►  B/W  ──►  chassis
```

Also switched on the ground side; the diode stops the lamp circuit from energising the
side stand relay coil path.
