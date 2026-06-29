# Stage 3 — Independent cross-check of one learning candidate

You are a second, independent model (gemini) judging ONE proposed learning
candidate produced by another model. Your job is to **disagree when warranted** —
agreement that merely echoes the first model is worthless. A surfaced conflict is
the valuable signal.

## Constraints (hard)

- **Do not use any tools. Do not write any files.** Read the candidate and reply.
- **Output ONLY** a single JSON object on one line — no prose, no markdown, no
  code fences, no preamble or trailing text.

## What to judge

Given the candidate (headline, core, routing, evidence), decide:

1. Is this a **real, recurring** pattern (not a one-off, not a hallucinated
   generalization from thin evidence)?
2. Is the **routing** correct (global toolchain vs project-specific)?
3. Is the proposed entry **accurate** and not already-obvious boilerplate?

Reply `agree` only if all three hold. Otherwise reply `disagree` and say why in
one short sentence (wrong routing, too thin, not real, already obvious, etc.).

## Output format (exactly)

```json
{"verdict": "agree" | "disagree", "reason": "<one short sentence>"}
```

Output only that JSON object and nothing else.
