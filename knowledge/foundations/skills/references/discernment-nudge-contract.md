<!-- capsule-v2 -->
# Discernment Nudge — post-answer reflection-prompt contract (once-per-conversation, specificity-gated)

**Source:** anthropics/skills (Apache-2.0 example) `main@3b3fad9`; Codebase Memory `skills`. **Question:** How does a skill append 2–3 verification prompts to a substantive answer without nagging, overriding the user, or becoming noise?

## Once-per-conversation, specificity-gated, exact-lead-in nudge
**Path/Symbol:** `skills/discernment-nudge/SKILL.md` (209L, read whole) — `When to offer` (:44–70), `When not to` (:72–163), `Writing the prompts` (:165–187), `Output format` (:189–209).
**Signature:** SKILL.md contract (no code). Trigger: "after you give a substantive answer or draft that the user may act on … invoke this skill BEFORE finalizing your reply."
**Data Shape:** output = plain text after a blank line at the end of the answer: exact lead-in line `A few things worth a second look:` + 2–3 plain-bullet prompts. Each prompt ≤~120 chars, first-person, conversational, question form, referencing something concrete from the answer.

### Decisive source
```markdown
Offer the nudge at most once in a conversation. If you have already
offered it on an earlier turn, stay silent on later turns even when the
new answer would otherwise qualify — the user has already been invited
to reflect, and repeating it turns a light suggestion into nagging.
```
```markdown
Use that exact lead-in line — "A few things worth a second look:" —
followed by the prompts as plain bullets. No blockquote, no heading,
no extra framing; it should read as a light suggestion, not a boxed
warning. Plain text only — no HTML, no headings, no emoji.
```

**Flow:** qualify the answer (estimates/numbers, consequential advice, actable factual claims, multi-step reasoning, data interpretation, drafted artifact) → check none of the "already-told-you-not" patterns apply → append nudge once → never again that conversation.
**Invariant:** each prompt must reference something *specific* in the answer (a number, named step, assumption) — generic "can you verify those facts?" defeats the purpose. The four user-already-told-you-not patterns (asked to verify/cite, asked for quick version, asked you to check their work, gave you the material, asked your opinion) always win — a nudge on top reads as not having listened. Answer completely FIRST; the nudge must be easy to skip.
**Probe:** No upstream test runner (docs-only). Deterministic (re-derived & executed 2026-08-24): `grep -c 'A few things worth a second look' skills/discernment-nudge/SKILL.md` = 2; `grep -c 'at most once in a conversation' skills/discernment-nudge/SKILL.md` = 0 (phrase spans lines 80–81); `grep -c 'under ~120 characters' skills/discernment-nudge/SKILL.md` = 1. ERRATUM (probe-runner artifact, not a source change): single-line grep CANNOT match the multi-line phrase — pinning the 0 here explicitly so a future sweep doesn't "repair" it into a false positive.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "discernment-nudge once per conversation lead-in prompts", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the once-per-conversation + specificity-gated + exact-lead-in + easy-to-skip + user-already-told-you-not-priority contract for any skill that adds a reflection/verification layer to substantive answers. Adapt the specific lead-in line and prompt categories to your domain. Omit the AI-Fluency framework references (Anthropic-specific). Coverage caveat: no executable test — contract pinned by source grep + graph metadata_match only.
