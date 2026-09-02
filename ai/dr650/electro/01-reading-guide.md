# Reading the DR650 wiring diagram

Conventions of this Suzuki diagram, and the mechanics of re-checking anything in
these docs against the image.

## 1. Connections vs. crossings — the critical rule

The middle band of the diagram (roughly y 850–1650 px) is a dense routing field where
dozens of wires cross. **A crossing is not a connection.**

- **Filled black dot at an intersection = splice.** The wires are electrically common.
- **Plain crossing, no dot = no connection.** The wires pass over/under each other.

Worked example (verified at 9× zoom, full-image coords ≈ x 1075–1265, y 405–570):
inside the right handlebar switch there is a short horizontal splice bus at y ≈ 519
spanning x 1121 → 1177, carrying **dots at x 1121 and x 1160**. The wire at x 1141
(the front brake switch output) crosses that bus at 90° with **no dot** — it is *not*
part of the splice. Reading it as connected would tie the brake-light feed to
switched power permanently.

**Never follow a line by eye across the routing field.** Match colour labels at the two
endpoints instead. Every wire is labelled just below the component it leaves and just
above the component it reaches.

## 2. Symbols

| Symbol | Meaning |
|---|---|
| Wide flat shell with pins above and below | Multi-pin harness connector |
| Small "bow-tie" / bullet shape on a single wire | In-line single-wire bullet connector |
| Small plain rectangle with 1–2 wires and nothing beyond | **Unused / blank connector** (terminated stub, no load) |
| Hatched triangle (⋰) | Chassis ground |
| Circle with filament | Bulb. Two filaments drawn = dual-filament bulb (tail/brake, headlight) |
| Circle with "M" | Starter motor |
| Coil rectangle + contact pair inside a box | Relay (coil left, contacts right) |
| S-shaped squiggle between two pins | Fuse |
| Triangle+bar on a line | Diode; current flows in the direction the triangle points |
| Double-headed arrow to a ground hatch | High-tension (spark plug) path |

## 3. Switch tables

Each switch is drawn as a table: **columns = terminals (labelled with wire colours),
rows = switch positions.** Two circles joined by a bar in a row means those two
terminals are connected in that position. An empty row means that position connects
nothing.

The bar can span *over* an intermediate column without connecting to it — e.g. the
ignition switch `P` row bridges `R` to `Br`, jumping over `O`, `O/Y`, `B/W`, `Gr`.
Likewise the dimmer `HI` row bridges `Y/W` to `Y`, jumping over `W`.

## 4. Colour labels change at connectors

This diagram labels the wire on **both sides** of a connector, and on several
connectors **the two labels differ**. The switch-assembly pigtail colour is not the
harness colour. See `04-connectors.md`. Ignoring this is the fastest way to
mis-wire this bike.

## 5. Re-verification recipe

Working from a downscaled overview is not good enough for connection/no-connection
calls — dots vanish. Crop and zoom instead.

```bash
python3 - <<'EOF'
from PIL import Image
im = Image.open('/home/areg/ai/dr650/electro/wiring-diagram-98plus-rotated.png')
t = im.crop((1075, 405, 1265, 570))          # x1,y1,x2,y2 in full-image px
t = t.resize((t.width*9, t.height*9))        # 9x for dot/no-dot calls
# t = t.rotate(-90, expand=True)             # add this to read the rotated wire labels
t.save('/tmp/crop.png')
EOF
```

Guidance on scale:
- **2×** — reading component names and switch tables.
- **5–6×** — reading wire colour labels reliably (`B` vs `Bl` vs `B/W` are easy to confuse).
- **8–10×** + `rotate(-90)` — settling an ambiguous label. Wire labels are printed
  rotated 90°; rotating the crop makes them read left-to-right.

## 6. Landmark coordinates (full-image px)

Handy anchors for cropping. All are approximate centres.

| Feature | x | y |
|---|---|---|
| Speedometer / indicator lights | 850–1000 | 300–740 |
| Engine kill sw / front brake sw / starter button | 1000–1250 | 400–530 |
| Right handlebar 6-pin connector | 1080–1180 | 725–760 |
| Ignition coil + its 2-pin connector | 1370–1490 | 570–760 |
| CDI unit + its 3 connector shells | 1560–1800 | 570–700 |
| Diode block | 1930–2060 | 570–700 |
| Side stand switch / rear brake switch | 2050–2300 | 350–480 |
| Side stand relay / turn signal relay | 2330–2560 | 590–700 |
| Headlight / front turn signals / Br stub | 380–700 | 1000–1360 |
| Left handlebar 9-pin connector | 700–880 | 1620 |
| Horn button / turn signal switch / dimmer / **ignition switch** | 840–1500 | 1780–1930 |
| Clutch sw / neutral sw / reg-rectifier / generator | 1430–2050 | 1600–1960 |
| Fuse box / starter relay (main fuse) / battery | 2040–2600 | 1560–1920 |
| Tail-brake / license / rear turn lights | 2480–3010 | 1020–1360 |
| Wire colour legend | 2620–3070 | 1420–2200 |
