# Open questions

What could not be settled from the scan, and how to settle each. Everything else in
this folder was read directly off the diagram at high zoom.

---

## 1. CDI shell A — 4 unlabelled pins

The CDI has three connector shells. Shell B's six wires are labelled (`G/Bl`, `B`,
`B/W`, `W/Bl`, `O/W`, `O/Y`) and shell C is drawn empty. **Shell A's four wires carry
no label at the CDI**, and they descend into the routing field before any label
appears.

The generator has four non-charging leads (`B`, `W`, `Bl`, `G` — two pickup coils), and
CDI shell B's `B` was traced turning right at approximately y 1286 toward the generator
side. The obvious hypothesis is that shell A carries the magneto pickup leads, but
**the four shell-A wires were not traced to their far ends.**

*How to settle:* unplug the CDI and read the four wires' colours directly, or trace
them at 5× along the strip x 1540–1640, y 740–1560.

## 2. `G/Bl` + `R/B` 2-pin stub

`G/Bl` runs from CDI shell B down to a 2-pin connector shared with `R/B`, low in the
diagram near the neutral switch. The connector appears to be a **terminated stub** (no
wires continue below it), drawn in the same style as the unused `Br` + `B/W` position-
light stub. Its purpose is unknown — possibly a market-option or diagnostic connector.

*How to settle:* find it on the bike. If it is a capped 2-pin connector hanging in the
loom with nothing plugged in, the reading is confirmed.

## 3. The `B` + `B/W` 2-pin connector near the fuse box

A 2-pin connector carrying `B` and `B/W` is drawn between the fuse box and the starter
relay. Given the ignition coil's harness side is `B/W` + `W/Bl`, this is **not** the
coil connector. Its far end was not traced.

*How to settle:* trace at 5× from x ≈ 2200, y ≈ 1615 upward.

## 4. Duplicate colour codes — confirm on the bike

Three codes are each used for two unrelated nets:

| Code | Net 1 | Net 2 |
|---|---|---|
| `B` | Left turn signal feed | CDI ↔ magneto |
| `Bl` | Neutral switch line | Magneto lead |
| `G` | Side stand switch line | Magneto lead |

This is unusual for a factory diagram and worth confirming before assuming any black,
blue or green wire in the engine area belongs to the circuit its colour suggests.

*How to settle:* continuity check between the two candidate endpoints of each pair.
They should read open.

## 5. The right-handlebar internal splice — confirm `O ≡ Gr ≡ Y/W`

The diagram shows pins 3, 5 and 6 of the right handlebar connector spliced together on
the **switch side** (junction dots at the pin-3 and pin-5 verticals; the pin-4 wire
crosses that bus with no dot). If correct, `O`, `Gr` and `Y/W` are one electrical node,
and the ignition switch's `Gr`—`Br` contact only serves to extend power to `Br`.

Two things support the reading: it explains why `Gr` is only 0.5 mm² at the ignition
switch (it never carries tail-light current there — the tail is fed from the splice),
and it explains why the headlight is on whenever the key is on with no separate
lighting switch.

*How to settle:* key ON, meter between the ignition switch `O` terminal and the
`Gr` terminal. Should read near zero ohms.

## 6. `O/Y` — the CDI's use of the enable line

Verified: the ignition switch bridges `O/Y` to `B/W` (ground) in **ON**, and `O/Y`
lands on CDI shell B. What the CDI does internally with a grounded `O/Y` is not shown.
Described here as an "enable/stop line" because grounding it coincides with the engine
being permitted to run — but this is *(inferred)*, not printed.

*How to settle:* not really necessary for the rebuild — the wire's routing is
unambiguous. Only matters if the CDI itself is ever suspected.

## 7. Physical connector pin numbering

All pin numbers in these docs are **left-to-right as drawn on the diagram**, a
schematic order. The physical cavity numbering on the real connectors was not derived.

*How to settle:* photograph each connector before unplugging (this is already build
rule #1 in `07-ignition-switch-harness.md`).

---

## Still open on the bike itself (not diagram questions)

- **Unwrap the loom and scope the actual damage depth.** Decision point: local repair
  vs. cutting deeper. Extent inside the taped bundle is unknown until unwrapped.
- **ПВАМ vs ПГВА flexibility** unresolved — buy on published strand count, or count
  strands on arrival.
- **Verify 1.5 mm² fits the aftermarket terminal wire barrels** before committing.
- Shopping list remainder: coloured heatshrink (white + yellow essential), ratcheting
  open-barrel crimper, spare terminals + seals, loom tape / split conduit.
