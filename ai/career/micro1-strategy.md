# micro1 entry + self-study strategy (2026-08-31)

Context: Altrady unlikely to meet rate wishes (see
[altrady-rate-negotiation.md](altrady-rate-negotiation.md)); most likely
scenario is exit after Superchart (~Nov 2026) + study hiatus. Chosen career
direction: **hybrid** — senior software engineer building AI applications
(not pure frontend, not pure ML). Platform entry: micro1 (Mercor unsupported
for AM residency; micro1 accepts AM individual contractors — brother's
precedent: $50/hr contract, paid via Deel, W-8BEN with AM tax ID).

## Field intel (brother, 2026-08-31, worked there from Jan 2026)

- Application = verbal AI interview + basic tests (his was for non-technical
  subtitle-correction at $50/hr; dev-role tests presumably heavier, but the
  bar is lower than the listings suggest).
- Listing requirements are overstated — don't self-reject against them.
- Company has an overblown budget: overpays, tolerates mediocre work.
  Read: boom-era lab data spending. Get in while it flows; expect eventual
  budget rationalization/quality purges — micro1 is a harvest window, not a
  career. Quality workers likely survive purges longest.

## Core move

Don't "study, then apply" — **get vetted early, study alongside paid task
work.** micro1 is task-wave-based; vetting takes weeks; the work (golden
solutions, evals for AI training) is itself the curriculum, paid.

## Target listings (job IDs on jobs.micro1.ai/post/<id>)

1. **Frontend Engineer** `6057e0a4` $65–120 — entry ticket, zero prep, apply
   immediately (no exclusivity clause for hourly contracts).
2. **AI trainer** `972f4b3e` $100–180 / **AI Domain Expert** `9376db02`
   $140–200 — apply ~month 1, once eval vocabulary is backed by paid work.
3. **Senior SWE polyglot family** (best: `f10ca3ec` $100–150) — after Python
   month.
4. **MCP Expert** `ca549605` $60–120 — after shipping an MCP project.

## Timing

- Pure unpaid hiatus: **4–6 weeks max**, then apply while studying.
- Total blended study investment: **~4 months** — extending blended study is
  cheap; extending unpaid study past 6 weeks buys little.
- micro1's wave-based shape is the one gig that preserves study time; a
  full-time role would end it.

## Study content, by 10-year durability

**Tier 1 (most hours):**
- Verification & evals — the appreciating skill as generation gets free:
  eval harnesses, rubrics, golden references, property-based tests.
- Python to real fluency (~3–4 weeks).
- LLM-system primitives, not frameworks: context management, tool use, agent
  loops, MCP, structured output, retrieval. Raw SDK level; skip
  LangChain-style frameworks.
- System design & architecture fundamentals (what $245–280 listings screen
  for).

**Tier 2:**
- Transformer/LLM conceptual depth (BSc AI refresh, not training math).
- Shipped public portfolio (structure below).

**Excluded deliberately:** model training, deep ML math, Kaggle DS, new JS
frameworks.

## Portfolio structure

Principle: **multiple small, finished repos — one skill each — beat one big
app.** Reviewers judge in ~5 min: does it show the skill, is it finished and
documented, can I run it. Interest sustains completion; legibility gets
hired — represent both.

1. **MCP server over geodata** (orion domain: GPX tracks, routing, map
   tiles). Shows tool/schema design for agents; interest carries it to
   "finished". Orion is substrate only — its long-term product/income value
   is deliberately not assumed; full orion app would bury the AI skills in
   Flutter/maps work.
2. **Domain-neutral agent + eval harness** (coding or data task): raw SDK
   agent loop, golden references, rubrics, regression suite. The artifact
   micro1/AI-lab reviewers instantly recognize as their own work — the
   legibility anchor.
3. **LLM feature with polished React UI** (flagship, weeks 9–12): plays to
   the frontend edge most "AI engineers" lack. Trading or orion domain.

Each repo: README with a run command, one clear demonstrated skill, evals
where applicable.

## Week-by-week sequence

**Weeks 1–2 — enter the pipeline.** micro1 expert profile + AI interview for
Frontend Engineer `6057e0a4`; AM registration paperwork (individual
contractor + tax ID, mirror brother's setup). Python daily (syntax → idiom →
stdlib → pytest).
*Before the AI interview:* do verbal mock-interview rounds with an LLM (voice
mode — ChatGPT or Claude) on the target domain (frontend/React, debugging,
architecture decisions). Rationale (Areg's own): he types about his work all
day but rarely *speaks* about it — verbal articulation is untrained, and
micro1's screening is a verbal AI interview. A few spoken rounds sharpen
exactly the tested skill cheaply.
Also assume the dev-role screen is **proctored and unassisted** (brother's
was monitored: no second screen, anti-cheat; timing unknown, his listing was
non-technical). Prep the unassisted muscle too — ramped, since Areg has written very little
actual logic by hand in 2026: start with easy untimed warm-up katas (daily,
15–20 min, just to get the brain writing logic again), then move to timed
(~30–45 min) cold exercises — no Claude — React/JS katas or medium algorithm
problems, until solo-under-observation feels normal again after a year of
AI-assisted work.

**Weeks 3–4 — Python consolidation.** Port something real to Python (small
Superchart-style data tool); async, typing, packaging. First micro1 test
tasks if vetting passed. Read Anthropic/OpenAI SDK docs end-to-end.

**Weeks 5–6 — LLM primitives.** Build agent loop raw (tool use, structured
output, retries, context budget). Start portfolio #1 (MCP geodata server).
Apply to AI trainer `972f4b3e`.

**Weeks 7–8 — evals.** Build portfolio #2 (domain-neutral agent + eval
harness). Ship #1 public. Apply AI Domain Expert `9376db02`.

**Weeks 9–12 — flagship.** Portfolio #3 (LLM feature + polished React UI).
Transformer conceptual refresh (Karpathy-level, not math-heavy). System
design practice. Apply Senior SWE `f10ca3ec` + MCP Expert `ca549605`.

**Weeks 13–16 — convert.** Paid micro1 work at highest accepted tier;
polish portfolio only if pipeline is quiet. Reassess income vs. own-project
time.

Assumption: similar listings remain available ~6 months; job IDs will churn
— re-run the board scan (prod-api.micro1.ai/api/v1/job/portal) when applying.
