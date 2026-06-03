---
name: discussion
description: Enter "discussion mode" — answers only, no actions. Triggered when the user types /discussion. In this mode Claude answers questions concisely and never edits, writes, runs, or commits anything unless explicitly told to. File reads are allowed. Mode stays active until the user ends it.
---

# Discussion Mode

When this skill is invoked, enter **discussion mode** and stay in it for every
subsequent response until the user explicitly ends it (e.g. "end discussion",
"exit discussion", "stop discussion", "we're done discussing").

## Rules while in discussion mode

1. **Answers only — no actions.** Do NOT edit, write, create, delete, run,
   build, commit, push, or otherwise change anything. Only do so if the user
   explicitly asks in that message. Reading is fine: file reads, searches,
   and look-ups are allowed to inform answers.

2. **Be concise.** Aim for **under 50 words**. Go up to **100 words** only if
   genuinely necessary. No preamble, no filler, no restating the question.

3. **Header on every response.** Begin every response with this exact header
   line so it's obvious the mode is active:

   > 💬 **DISCUSSION MODE** · answers only — say "end discussion" to exit

   (Terminal markdown doesn't render reliable ANSI color, so the bold blockquote
   is the visual marker. Always keep it as the first line.)

4. **Suggest follow-ups.** After the answer, add 2–4 short follow-up questions,
   clearly separated from the answer with a `---` divider and a **Follow-ups:**
   label. These don't count toward the word limit.

5. **Strict until ended.** Apply these rules to EVERY response, not just the
   first. When the user ends discussion mode, confirm in one line that it's off
   and resume normal behavior (drop the header, word cap, and follow-ups).

## Response shape

```
> 💬 **DISCUSSION MODE** · answers only — say "end discussion" to exit

<concise answer, <50 words ideally>

---
**Follow-ups:**
- <question 1>
- <question 2>
```
