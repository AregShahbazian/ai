# DR650 electrical — knowledge base

Everything about the Suzuki DR650 ('98-on model) electrical system, extracted from
the factory wiring diagram. Read these instead of re-reading the image.

## Source of truth

| File | What it is |
|---|---|
| `wiring-diagram-98plus-rotated.png` | 3508×2481 px, 300 DPI, upright. **The authority.** All docs here derive from it. |
| `wiring-diagram-98plus-source.pdf` | Original PDF. Page is rotated 90° inside the PDF; the PNG is the de-rotated render. |

## Documents

| File | Contents |
|---|---|
| `01-reading-guide.md` | How to read the diagram: junction dots vs. crossings, symbols, and the exact crop recipe to re-verify any claim here. **Read this first if you are going to look at the image.** |
| `02-wire-colors.md` | The 27-code colour legend, plus the traps (codes reused for two different nets). |
| `03-components.md` | Every component, its terminals, and every switch contact table. |
| `04-connectors.md` | Connector pin maps — including the connectors where the wire colour **changes** from one side to the other. This is the single most error-prone thing on this bike. |
| `05-nets.md` | Net list: for each colour, every terminal it lands on, and what the net does. |
| `06-circuits.md` | Circuit-by-circuit walkthroughs: power/ground, ignition & stop, starting & interlock, charging, lighting, signals, brake light, horn. |
| `07-ignition-switch-harness.md` | The 6 ignition-switch wires: function, source, destination, current, plus the rebuild reference (this doubles as the under-seat note). |
| `08-open-questions.md` | What is *not* fully resolved, and how to settle each on the bike. |

## Confidence convention used throughout

- **Plain statement** = read directly off the diagram at high zoom, unambiguous.
- **(inferred)** = not printed on the diagram; deduced from topology. Sound but worth a meter check.
- **(UNVERIFIED)** = could not be resolved from the scan. Listed in `08-open-questions.md`.

## Scope note

This describes the **stock** bike. Anything on Areg's actual DR650 that diverges from
this (the headlight off-switch + relay, LED headlight/tail, USB charger, and the
planned relay-fed headlight and charger circuits) is a modification and is **not**
in the factory diagram — see `07-ignition-switch-harness.md` for where stock and
his setup differ.
