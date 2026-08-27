---
name: laptop-slow-triage
description: Huawei MateBook "laptop slow / stuck at 400 MHz" — triage order and the PROCHOT/EC-reset fix live in ~/.claude/system.md
metadata:
  type: reference
---

When the user says the laptop is slow / feels stuck in power-saver despite "performance":
follow the triage at the top of `~/.claude/system.md`. Three known causes (#1 cpupower
conflict, #2 min_perf_pct floor, #3 BD PROCHOT from the EC — fixed 2026-08-26 by an EC
reset: shutdown, unplug, hold power 20 s). Always test frequency *under load* first;
a hard 400 MHz cap under load = PROCHOT, not the pstate floor. Sudo commands must be
handed over as single-line pastes (see [[feedback-user-runs-generation]]).
