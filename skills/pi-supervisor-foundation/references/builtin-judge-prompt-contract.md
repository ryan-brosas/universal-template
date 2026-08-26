<!-- capsule-v2 -->
# Built-in judge prompt contract — which five behavioral clauses make the supervisor safe to point at an agent?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** What must a custom SUPERVISOR.md restate to preserve the built-in's safety behavior?

## BUILTIN_SYSTEM_PROMPT (`src/core/prompt-loader.ts:18-105`)
**Path/Symbol:** `src/core/prompt-loader.ts` `BUILTIN_SYSTEM_PROMPT` template literal (:18-105).
**Signature:** const string; consumed verbatim as the judge's system prompt.
**Data Shape:** Sections: IDLE mandate / WORKING restraint / STEERING RULES / done CRITERIA / CHEATING PREVENTION (5 patterns) / CLOSING THE ASI LOOP / strict JSON schema.

### Decisive source
```text
1. IDLE:  You MUST choose "done" or "steer". Never return "continue" when idle.
   Clarifying questions: answer with a sensible default IF goal-blocking,
   otherwise redirect ("outside the scope..."); NEVER answer for
   passwords/credentials/secrets.
2. SPEAK AS THE USER: steer message is 1-3 sentences, actionable;
   "Do not ask the agent to verify its own work — tell it what to do next."
3. STEERING RULES: "Never repeat a steering message that had no effect —
   escalate or change approach"; shortcuts ⇒ always steer.
4. CHEATING PREVENTION: Unverified Claims (check exit codes) / Test Manipulation /
   Metric Gaming / Short-Circuiting / Contradictions ⇒ "DO NOT accept 'done'",
   require explicit proof, "Log the pattern in ASI".
5. ASI LOOP + SCHEMA: asi REQUIRED when steering, free-form keys;
   respond ONLY with strict JSON {action, message?, reasoning, confidence, asi?}.
```

**Flow:** the parser (`parseDecision`) trusts this contract: action enum, message-on-steer, confidence float, asi object. The prompt-builder reinforces it (idle-forbids-continue, suspicious-pattern warnings). The three modules form a triangle — break one leg and supervision degrades silently.
**Invariant:** (1) "Speak as the user" is what makes followUp-delivered steers indistinguishable from real user input — the agent's reply goes to a human-shaped instruction. (2) The secrets carve-out prevents the supervisor from answering credential questions on the user's behalf. (3) Anti-gaming clauses exist because the supervisor sees tool RESULTS, not just claims — verification language points the judge at evidence. (4) JSON-only output is enforced by BOTH prompt and parser fallbacks.
**Probe:** `tests/engine.test.ts` — `built-in prompt includes cheating prevention section` (:76) asserting 'CHEATING PREVENTION', `built-in prompt includes ASI loop section` (:90) asserting 'CLOSING THE ASI LOOP'/'REQUIRED when steering'; section text pinned at prompt-loader.ts :21-105.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "BUILTIN_SYSTEM_PROMPT cheating prevention ASI loop", limit: 8 });
```

## Verdict
Adopt all five clauses when porting the judge role; treat them as the API between prompt-loader, prompt-builder, and response-parser. Adapt wording/section order freely — keep the clause SET. Omit nothing safety-bearing.
