# Altrady rate negotiation — analysis & plan (2026-08-25)

Purpose: self-contained summary of data, analysis and agreed plan, to get a
second opinion from other LLMs / people. Prepared with Claude (Fable 5).

## 1. Who / what

- Areg Shahbazian, freelance frontend engineer for **Altrady**. Armenian,
  immigrated to NL young; raised/educated in NL, fluent Dutch, Dutch work
  culture; lives mostly in Armenia and the Philippines — not a standard
  offshore hire.
- Altrady: crypto trading platform, Altrady BV, Den Haag; earlier invoiced
  via Web2000 BV.
- Since **Sep 2018**. Fully remote, different timezone, flexible hours,
  vacations scattered through the year. Hourly rate, no equity.
- Setup: unincorporated individual invoicing from abroad; no VAT (reverse
  charged), no tax ID; Areg pays no income tax on it (legal in his situation).
  For Altrady the rate is the full cost: no employer contributions, no VAT
  cash-flow, no payroll/DBA compliance, no notice period.
- Owner: Benoist Claassen — himself a software engineer, understands code
  quality well. Team also includes Roman Ivanov (UI designer, with the company
  since 2018).
- Current task: **Superchart** integration (new charting engine replacing
  TradingView), started early 2026, expected delivery ~Nov 2026.
- Personal fork after delivery: either substantially better terms at Altrady,
  or leave, live with family for a while, and build something own (mapping
  app "orion" is the candidate).

## 2. Hard data

### 2.1 Invoices (72 invoices, Sep 2018 – Jun 2026, `~/Dropbox/work/web2000/invoice`)

- Every invoice is exactly **160 hours**; invoicing cadence ≈ 1 per 1.3 months.
- Rate history: $20 (2018) → $21 (mid-2019) → $21.5 (2020) → $22.5 (2021)
  → **€20.20** (Apr 2021) → €20.79 (2022) → €23 (2024) → €24 (2025) →
  **€25 (2026)**. $20 in Sep 2018 = €17.0, so ≈ +47 % nominal in EUR over 8 years vs ~33 % Dutch CPI → ≈ +10 % real (NL); −16 % real if spending in Armenia, +24 % in the Philippines (see 2.4).
- Total hours ≈ 11,520 → **≈ 1,480 hrs/yr ≈ 28 hrs/week** (Areg had remembered
  it as ~20).
- Total billed ≈ **€256k** over ~7.8 years ≈ **€33k/yr** including yearly
  bonuses of ~€2–4k (three explicit BONUS invoices + larger December invoices
  2019–2022). Effective rate incl. bonus ≈ €27/hr.
- Current monthly budget for Areg ≈ **€4,000** (160 h × €25), paid roughly every
  5–6 weeks.

### 2.2 Git contribution (all Altrady repos in `~/git/altrady`)

`crypto_base_scanner_desktop` (the main desktop app):
- Areg: **5,719 of 11,247 commits (≈ 51 %)**, 2018-06 → 2026-07, ~1M lines touched.
- Share per year: 2018 73 %, 2019 72 %, 2020–24 40–60 %, 2025 **74 %**
  (610 of 828), 2026 to date **~20 %** across all branches.

2026, all branches (to Aug 2026):

| Author | Role | Commits | Lines added |
|---|---|---|---|
| Roman Ivanov | UI designer | 767 | 250k |
| Benoist Claassen | Owner | 536 | 117k |
| Areg | — | 289 (+58 in Superchart repo) | 96k |

For comparison 2025: Areg 610, Benoist 179, Roman 39. I.e. in one year, with
AI assistance, the owner tripled and the designer went from ~0 to top
committer. No new hires — existing people absorbed the work. Areg's 2026 work
is concentrated on the Superchart branches/repo (the hardest feature of the
year), plus coinrayjs (21 commits total) and altrady-webview (16).

### 2.3 Context that changed in 2026

- Most coding now done with Claude; Areg's role shifted to ~half product-owner
  / architect / reviewer (more English than code). Productivity per hour is up;
  rate is not.
- Other team members (designer) commit LLM-assisted code — not slop, but
  "engineer-quality by a non-engineer using an LLM", and nobody senior is
  formally reviewing it.

### 2.4 Purchasing power 2018 → 2026 (hourly rate deflated by local CPI)

Starting rate: $20/hr in Sep 2018 = **€17.0/hr** (ECB EUR/USD 1.1773 on 2018-09-24).
Current rate: **€25/hr** (Aug 2026). Nominal in EUR: **+47 %**.

Sources: CPI annual % — World Bank FP.CPI.TOTL.ZG (2018–2025); 2026 year-to-date
from CBS (NL, 3.2 % y/y Jul 2026), Armstat via arka.am (AM, 4.5 % y/y Jul 2026),
PSA (PH, 5.0 % Jan–Jul 2026 average). FX — ECB reference rates via Frankfurter
(EUR/USD 1.1773, EUR/PHP 63.84 on 2018-09-24; EUR/USD 1.1664, EUR/PHP 71.99 on
2026-08-24); EUR/AMD 569.6 = 2018 annual average (exchange-rates.org), 425.8 on
2026-08-25 (Wise mid-market).

Annual CPI inflation, %:

| Year | Netherlands | Armenia | Philippines |
|---|---|---|---|
| 2018 | 1.70 | 2.52 | 5.31 |
| 2019 | 2.63 | 1.44 | 2.39 |
| 2020 | 1.27 | 1.21 | 2.39 |
| 2021 | 2.68 | 7.18 | 3.93 |
| 2022 | 10.00 | 8.64 | 5.82 |
| 2023 | 3.84 | 1.98 | 5.98 |
| 2024 | 3.35 | 0.27 | 3.21 |
| 2025 | 3.26 | 3.31 | 1.66 |
| 2026 (Jan–Jul, y/y) | 3.2 | 4.5 | 5.0 |

Result (Sep 2018 → Aug 2026; 2018 counted as one quarter, 2026 as 7/12):

| | Netherlands | Armenia | Philippines |
|---|---|---|---|
| Rate 2018 in local currency | €17.0 | 9,683 AMD | 1,085 PHP |
| Rate 2026 in local currency | €25.0 | 10,645 AMD | 1,800 PHP |
| Nominal change | +47 % | +10 % | +66 % |
| Cumulative CPI | ×1.331 | ×1.304 | ×1.337 |
| **Real change in purchasing power** | **+10.5 %** | **−15.7 %** | **+24.0 %** |

Notes: the dram appreciated ~25 % against the euro over the period (569.6 → 425.8),
which offsets most of the euro raises for spending in Armenia. The peso weakened
~13 % against the euro, amplifying them for spending in the Philippines. FX for
the 2018 endpoint uses a single reference date / annual average, so figures are
accurate to roughly ±2 points.

## 3. Analysis (Claude's assessment, agreed by Areg)

1. **€25/hr is far below market.** A senior EU frontend freelancer with deep
   fintech-product context bills roughly €85–125/hr. Even discounting 20–30 %
   for the flexible/remote/part-time arrangement, €25 is a 65–75 % discount.
   €33k/yr gross as a freelancer (no pension/holiday/sick pay) is below a Dutch
   junior salary.
2. **The original reasons expired.** "Startup can't afford it" and "trust the
   platform will grow and reward me" were reasonable in 2018–2020; after 8
   years with no equity and inflation-only raises they are sunk cost.
3. **AI changes the leverage, both ways.** The price of *typing code* is
   falling and the owner is proving weekly that he can ship with Claude; the
   "only Areg can touch this code" leverage is largely gone (2026 numbers
   confirm). What remains: 8 years of *why* the codebase is shaped as it is,
   delivery of Superchart, and the judgment/review role that grows more
   valuable as more AI-generated code flows in. Rate should be attached to
   that role, not to keystrokes — then it won't age into "overpaid".
4. **Timing.** The story ("I built this, I'm carrying Superchart, I should own
   frontend quality") is easiest to tell now; harder after two years as a 20 %
   contributor. So: open the conversation now, effective date after
   Superchart ships. Areg explicitly does **not** want to use Superchart as
   leverage (dignity) — fine: don't mention it; the timing still works.
5. **Real baseline.** Areg invoices 160-h blocks but delivers ~120 h/month on
   average, so the current €4k budget already equals ~€33/hr at real pace.
6. **Owner is an engineer** → no need to explain value; conversation can be
   matter-of-fact. Expect surprise at the *size* of the ask, not the
   principle; he has been getting a good deal and knows it. His raise frame is
   ~€1/hr/year — the number must reset that frame, not extend it.
7. **He may respond by cutting hours rather than refusing the rate.** That can
   be the best outcome (income up, time freed for own project) — decide the
   acceptable hours floor beforehand.
8. **The tax/VAT point cuts both ways.** Benoist may argue €25 untaxed ≈
   €35–40 pre-tax for a Dutch freelancer. Counter: the benchmark is what *he*
   pays for a replacement, not Areg's take-home — and the setup is itself a
   benefit to him (no employer costs, no VAT pre-financing, no DBA risk, no
   notice period) that neither a Dutch freelancer nor a Dutch employee can
   offer, while a typical offshore dev cannot offer the Dutch language and
   work culture. Expect the point; answer it once; don't lead with it. Rates
   unchanged by it.
9. **Accepting "no" (stay at €25–30):** only as a deliberate, time-boxed bridge
   while building the alternative. Never open-ended.

## 4. Numbers for negotiation (current version, 2026-08-25 evening)

Current: €25/hr, ~28 h/week → ~€4.0k per 160-h block, ~€48k/yr base
(€33k/yr realised incl. gaps and bonus). Real baseline at actual pace
(~120 h/month) ≈ €33/hr.

### Rate anchor

- NL senior frontend freelancer: €85–125/hr.
- Senior remote React dev (Armenia / Eastern Europe / Asia): €35–55/hr.
- Areg is neither: Armenian, raised/educated in NL, fluent Dutch, Dutch work
  culture, 8 years of product context, no employer costs / VAT / DBA exposure
  for Altrady. Replacement cost sits between the two bands → defensible rate
  **€50–60/hr**, roughly the same in every option below. What varies between
  options is hours and commitment, not rate.
- Earlier versions (superseded): RAISE 20 h @ €65 / NEUTRAL 20 h @ €50;
  then €50–55 / €45; ChatGPT second opinion said €35–40 / €30 (judged too low,
  anchored on the current €25).

### Four options

**1. GROW — Altrady has a real growth perspective; full availability**
- 32–40 h/week, **€50–55/hr** now; written review to €65–75 within 12 months
  tied to agreed metrics (revenue / paying users).
- Contract (none exists for ~2 years): guaranteed minimum hours (e.g. 120
  h/month), notice period both ways.
- ≈ €50 × 140 h ≈ **€7.0k/month**, ~€84k/yr. Δ to Altrady ≈ +€36k/yr.
- Only exists if he signs minimum hours + review clause. If he won't, that
  answers the growth question → option 2.

**2. CAP — unclear or pessimistic perspective; protect Areg's time**
- Max 20 h/week (min ~12), **€50–55/hr**.
- ≈ €50 × 80 h ≈ **€4.0k/month** — current income, half the hours; other half
  goes to the own project. No long-term commitment needed.
- Δ to Altrady ≈ €0.

**3. TAPER — Altrady fine, but less frontend demand** (AI speed, shorter
feature backlog, owner/designer absorb routine work)
- 8–16 h/week, **€55–60/hr**, high-context work only (architecture, review,
  integrations like Superchart).
- ≈ €55 × 50 h ≈ **€2.8k/month**. Δ to Altrady ≈ −€15k/yr.
- Acceptable only at a senior rate. Fewer hours at €25 is the worst outcome:
  less income *and* still underpriced.

**4. BRIDGE — he says no or offers a token raise (€27–30)**
- €30–35/hr, max 20 h/week, explicitly temporary (3–6 months) while the exit
  is set up. Never open-ended.

### Per-case opening asks

| Case | Open | Settle | Hours |
|---|---|---|---|
| Healthy | €65 | €55–60 | by option 1 or 2 |
| Under pressure | €50 | €45–50 | ≤ 20/week |
| Fine, low demand | €60 | €55 | 8–16/week |

Never below €45/hr; €50 preferred floor.

### Concessions Areg is willing to make

1. **Minimum weekly/monthly hours commitment** (none today). Real value to
   Altrady (predictability), cheap for Areg → lead with it.
2. **Higher-level role** — specs, architecture, review of all frontend
   contributions incl. AI-assisted ones. Not a concession: it is the
   justification for the rate. Present it as what Areg offers.
3. **Incorporating** (company, tax ID, VAT, paying tax). Areg prefers not to.
   It costs him a lot and Altrady almost nothing (VAT is reclaimable), so it
   is not a concession Benoist would value — unless he wants a formal
   contract / DBA-safe structure. Keep in pocket; only if requested, and then
   it justifies a *higher* rate, not the same one.

Message to Benoist in one line: "The rate is what it is; how much of me you
want is your choice."

## 5. How to open the conversation (agreed)

- Scheduled 30-min call, preceded by a one-line heads-up naming the topic
  ("I want to talk about my rate and role going forward").
- Four beats: (1) the fact — €25 since 2018, accepted deliberately, can't
  continue; (2) what changed — role shifted to product/architecture/review,
  productivity up, rate should reflect the role; (3) the ask — one number, one
  effective date, then silence; optionally the frontend-owner role; (4) leave
  room — "I'd rather work this out with you; think about it".
- Don't: mention Superchart, quitting, family or alternatives; apologise or
  over-justify; fill silence; accept a counter on the call.
- Frame budget as well as rate, e.g. "≈€5.5k/month for 80 h instead of €4k for
  160 h", so he compares budgets, not just the 2.6× rate jump.

### 5.1 The script (agreed 2026-08-25)

> My rate has gone from $20 in 2018 to €25 now — after eight years it's barely
> kept pace with inflation. Meanwhile my work has shifted to architecture,
> specs and reviewing what goes in, including the LLM-assisted contributions.
> From 1 December I want to be at €55/hr. I'm fine with fewer hours if the
> budget needs it, down to about 16 a week; I'm also happy to commit to a
> minimum, which we don't have today. Think about it — I'd rather sort this
> out with you than anywhere else.

Variables behind it:

| | Value | Note |
|---|---|---|
| X — rate asked | €55/hr | stop at €50 |
| Y — minimum hours | 16 h/week | |
| Z — resulting income | ≈ €880/week ≈ €3.8k/month | ≈ current income |
| Effective date | 1 December 2026 | after Superchart ships |

Kept in pocket — use only in response to a low counter, never offered upfront:

| | Value |
|---|---|
| A — bridge rate | €40/hr |
| B — bridge end | 1 March 2027 (~3 months after delivery) |
| C — after bridge | automatic step to €55, no second negotiation |
| D — if nothing works | wind down: hand over, stop invoicing by a set date. Never said aloud; he will infer it. |

Deliberately left out of the script: personal reasons (own project, family),
Superchart as leverage, the bridge, the exit. One ask, one date, one
concession, then silence.

Predicted outcomes (assuming mid-way company health / demand / fairness):
- Optimistic (~25 %): he counters €55 with *more* hours → GROW, ~€6.5k/month,
  first written contract in years.
- Realistic (~50 %): he counters €40 same hours; Areg holds rate, flexes hours
  → CAP, €50 × ≤20 h ≈ €4k/month from December.
- Pessimistic (~25 %): defensive, offers €30 → BRIDGE (€35–40, ≤20 h, 6
  months), then planned exit by mid-2027.

Open-ended arrangements are acceptable only at ≥ €50/hr (ideally with a yearly
review date); anything below €45 is a time-boxed bridge only.

## 6. Open questions for a second opinion

- Is €65/hr at 20 h/week realistic for a small, crypto-cyclical SaaS with
  ~10–20 people, given the owner now codes with AI himself?
- Is €50/hr the right floor, or too low given the 8-year history?
- Should the effective date be immediate rather than post-Superchart?
- Anything in the framing that reads as an ultimatum despite intent?
