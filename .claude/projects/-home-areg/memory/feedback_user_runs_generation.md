---
name: feedback_user_runs_generation
description: "User prefers to launch long-running jobs (image generation, model downloads, batch runs) himself — Claude sets up scripts/configs and hands over the command"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2756c346-e980-45c2-b897-4c8cae6bfdc5
  modified: 2026-08-25T17:20:22.925Z
---

Don't start generation/download/batch processes unless explicitly asked; prepare scripts, prompts and configs, then give the exact command to run.

**Why:** He wants control over when heavy jobs (RAM/CPU-hogging, hour-long) run on his laptop, and to learn the stack hands-on.

**How to apply:** In [[project_ai_content_studio]] and similar: "set up, don't run" is the default. Running is fine only when he says "run it"/"do it". Quick checks (ls, status, syntax-validate) are fine.
