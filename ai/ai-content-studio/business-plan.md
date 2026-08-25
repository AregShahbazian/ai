# AI Adult Content Studio — Investment & Feasibility Plan

Date: 2026-08-25
Scope: technical/financial side only. Creative work and promotion are
acknowledged as the dominant variables but not planned here.

## 1. Premise

- AI-generated adult content is a top category on clip sites (ManyVids claimed;
  Fanvue is the verified AI-friendly platform — see §7 caveats).
- Production can be hybrid (local GPU + rented cloud GPU), but with budget
  available, **fully local** is the better option.

## 2. Local vs cloud

**Local wins when money is loose:**
- No ToS risk — cloud hosts can terminate accounts for NSFW; local can't.
- Privacy — datasets, LoRAs, outputs never leave the machine.
- No per-clip cost pressure → the 5–10× reject ratio is free to absorb.
- Latency — instant preview loops matter more than raw throughput.

**Caveat — VRAM ceiling.** Best video models want 48–80 GB for full-res, long
clips without offloading. Consumer cards cap at 32 GB.
- RTX Pro 6000 Blackwell (96 GB): ~€8–10k. Single card, runs everything
  unquantized. The "money is no issue" answer.
- 2× 5090: ~€6k, but video pipelines don't split one generation across cards —
  parallel jobs, not bigger jobs.
- Used A100/H100 PCIe: €10–25k, needs server cooling/power. Overkill.

**Cloud still makes sense only** for occasional bursts (e.g. 500 clips
overnight), and only on a host that explicitly permits adult content on
self-managed instances.

## 3. Cost reference (EUR, 2026)

### Local workstation options
| Tier | GPU | Rest of box | Total |
|---|---|---|---|
| Lean | used RTX 4090 24 GB, €1.3–1.8k | €1.2–2k | ~€2.5–3.5k |
| Mid | RTX 5090 32 GB, €2.5–3k | €1.2–2k | ~€4–5k |
| Comfortable | RTX Pro 6000 96 GB, €8–10k | Threadripper/Xeon-W, 128–256 GB RAM, 4–8 TB NVMe + 20 TB HDD, 1600 W PSU | ~€12–15k |

Optional second machine (5090) for LoRA training while the big card renders.

Electricity: ~€30–60/mo under heavy use.

### Cloud GPU (reference only)
- H100 ~€2–3/hr, A100 80 GB ~€1–1.5/hr, 4090 ~€0.35–0.5/hr.
- 5–10 s clip at 720p–1080p ≈ 2–8 GPU-min on H100 → €0.10–0.40/clip raw;
  with 5–10× rejects → **€1–4 per usable clip**.
- Storage/egress €20–50/mo. Realistic burn €200–800/mo.

### Software / models
- Open-weight models + ComfyUI: €0. Major hosted providers prohibit NSFW, so
  the stack is open weights on self-managed hardware.
- Upscalers, consistency tooling, occasional paid LoRA/dataset: €0–50/mo.

### Overhead
- Domain/site, VPN, KYC-friendly banking, accountant for adult income:
  €50–150/mo.
- Platform cuts: ManyVids ~40%, Fanvue ~15–20% (80–85% payout), Fansly ~20%.
  Margin, not investment.

## 4. Chosen investment (comfortable tier)

| Item | Amount |
|---|---|
| GPU workstation (RTX Pro 6000 96 GB build) | €12–15k |
| Storage / backup | €800 |
| Software / models | €0–50/mo |
| Site, VPN, banking, accountant | €100–150/mo |
| Optional hired chatter for DMs | $500–1,500/mo |
| **Upfront** | **~€14–16k** |
| **Monthly opex** | **~€250** |

Hardware retains ~50–60% resale value → downside capped at ~€7–8k.

## 5. Market data (from web research, 2026-08)

### Earnings distribution (Fanvue)
- ~60% of creators <$500/mo; ~25% $500–2,500; ~10% $2,500–10k;
  top 5% >$10k; top 1% $15–50k/mo.
- Year-1 established creators: $1,000–8,000/mo median band.
- AI creators ≈ 15% of Fanvue revenue.

### Time to profitability (reported, not guaranteed)
- Months 0–3: $200–500/mo; target ~50 paying subs; 2–4 h/day of work.
- Months 3–6: $500–3,000/mo.
- Months 6–12: $2,000–10,000/mo with 200–500 active subs + DM/PPV sales.
- Outliers ($12.5k/mo by day 60; $43k first month) — ignore for planning.

### Revenue mix & pricing
- PPV + tips + paid DMs ≈ 60% of revenue; subscriptions are the funnel.
- PPV $5–20 per unlock; photos $5–10, videos $15–25, exclusives $30–50.
- Subscriptions $10–100.

### Cadence & clip length
- Baseline 3 posts/week; aggressive creators 1–2×/day across platforms.
- Teasers 5–15 s (single generation). Paid clips 1–5 min, stitched from
  10–30 generations of 5–10 s. "Full" videos 8–15 min, rare.
- Image sets (20–50 images) remain a large revenue share, cheap to produce.
- Catalog size (100+ items) matters more than cadence; a single consistent
  persona (one LoRA) drives repeat buyers, not length.

### Throughput implication
- ~20 generations per paid clip × 5–10× rejects → 100–200 raw generations.
- At 2–5 min each locally → 4–15 GPU-hours per clip → 1–2 clips/day on a
  96 GB card, more with overnight batches.

## 6. Break-even model

Assumptions: Fanvue 80% payout, €250/mo opex, €15k upfront.

- Cover opex: ~€310/mo gross → month 2–4 for a median-track creator.
- Recoup hardware in 12 months: ~€1,900/mo gross ≈ 150–200 subs at $10 +
  moderate PPV → the "months 6–12" band; plausible, not median.
- Recoup in 24 months: ~€1,000/mo gross → within the 25th–50th percentile
  of year-1 creators.

**Realistic expectation:** cash-flow positive by month 3–4; hardware paid
back in 12–24 months; ~40% chance of stalling under €500/mo if the persona
doesn't land.

## 7. Limiting factors & risks

Creativity and promotion dominate (~80% of ongoing time), but the technical
side is **not flat** (~20%):
1. **Model churn** — open video models improve every few months; re-learn
   workflows and retrain the persona LoRA per major model. ~days/quarter.
2. **Consistency engineering** — same face/body/lighting across hundreds of
   clips; per-clip QA plus periodic LoRA refinement. Never "done".
3. **Curation** — reviewing the 10% that pass scales with output.

Learning curve for the pipeline (ComfyUI, model selection, LoRA training,
upscaling, stitching): ~4–8 weeks to competent.

**Platform / policy risk**
- OnlyFans bans pure-AI accounts quickly. Fanvue explicitly verifies AI
  creators. Fansly tolerates.
- **ManyVids AI policy unverified** — no published rule found. Read current
  ToS / ask support before planning around it.
- Payment-processor rules (Visa/MC on adult AI) can zero revenue overnight.
  Diversify platforms from day one.

**Legal / compliance**
- Age-verification records (2257-style), consent for any likeness/dataset,
  EU AI Act labelling obligations. Low effort, must be correct.

## 8. Physical footprint of the €15k rig

- Single full tower (~55 × 25 × 55 cm, 15–20 kg); ~0.15 m² floor/desk;
  10 cm airflow clearance.
- 1600 W PSU; 600–900 W sustained under render; standard outlet, but not
  shared with heaters/kettles.
- Heat ≈ small room heater; a closed 10 m² room warms noticeably overnight.
- Noise 35–45 dB under load; not a bedroom machine for overnight runs.
- Extras: external 20 TB HDD or small NAS; optional UPS (shoebox, ~10 kg).
- Alternative: 4U rackmount (~18 × 45 × 65 cm) in a closet; louder.

## 9. Sources

- https://sacra.com/c/fanvue/
- https://slobodskyi.com/monetize/memberships/fanvue
- https://aiofm.info/en/guides/fanvue-ai-creators-handbook
- https://www.fanvue.com/blog/how-much-do-content-creators-make
- https://fanvuebest.com/articles/how-much-fanvue-creators-make-2026/
- https://fanvy.ai/blog/fanvue-top-earners-niche-premium-2026
- https://finance.yahoo.com/news/ai-influencers-making-secretive-creators-121608358.html
- https://www.netinfluencer.com/ai-influencers/
- https://aijourn.com/a-brave-new-world-of-ai-influencers/
- https://reelmind.ai/blog/adult-creator-income-statistics-that-matter
- https://www.followmint.net/blog/ai-onlyfans-creators-how-they-make-money-2026/
- https://fanvuemodels.com/blog/is-ai-ofm-profitable
- https://blog.luvi.fans/texas-student-ai-onlyfans-model-43k-month-earnings/
- https://blog.octobrowser.net/how-to-create-an-ai-model-for-onlyfans-and-start-earning
- https://www.ofgenerator.com/blog/fansly-vs-fanvue-ai-creators-2026
- https://affhub.media/en/how-to-earn-money-on-fanvue-using-ai/
- https://sozee.ai/resources/fansly-ppv-content-tools/
- https://arunatalent.com/blog/onlyfans-ai-content-policy-2026/
