<!-- capsule-v2 -->
# Supervisor prompt contract — outcome sandwich, IDLE-must-decide rule, scope-question policy, five-item cheating taxonomy

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** What must the decision prompt and system prompt say so an LLM judge steers usefully, refuses premature "done", and catches shortcut-taking?

## Two-layer prompt: static doctrine + fresh structured context
**Path/Symbol:** System prompt fallback `src/core/prompt-loader.ts:18-105` (BUILTIN_SYSTEM_PROMPT); user prompt builder `src/core/prompt-builder.ts:10-65` (`buildUserPrompt`).
**Signature:** `buildUserPrompt(state, contextText, agentIsIdle, ineffectivePattern?): string`.
**Data Shape:** User prompt = DESIRED OUTCOME → agent status (+reframe guidance) → STRUCTURED CONVERSATION CONTEXT → intervention history w/ ASI → ASI pattern summary → REMINDER of outcome.

### Decisive source
```ts
  const agentStatus = agentIsIdle
    ? `AGENT STATUS: IDLE — the agent has finished its turn and is now waiting for user input.
You MUST return "done" or "steer". Returning "continue" here means the agent stays idle forever.`
    : `AGENT STATUS: WORKING — the agent is actively processing. Only intervene if clearly off track.`;
  ...
  return `DESIRED OUTCOME:
${state.outcome}
...
REMINDER — DESIRED OUTCOME:
${state.outcome}

Has this outcome been fully achieved? Analyze and respond with JSON only.`;
```
System prompt carries the scope-question policy (:28-33): necessary blocking question ⇒ answer with a sensible default and proceed; out-of-scope ⇒ redirect to the missing goal piece; NEVER answer passwords/credentials/secrets. Cheating taxonomy (:52-68): unverified claims / test manipulation / metric gaming / short-circuiting / contradictions — each with a verification action; detection ⇒ refuse done + demand proof + log in ASI. Done criteria bias completion (:48-50): minor polish does NOT block done — prefer stopping over perfection loops.

**Flow:** outcome stated FIRST and LAST (sandwich) around volatile context → status line switches the decision space by liveness → reframe guidance injected only when armed → history+ASI close the memory loop → strict-JSON response schema with required asi on steer.
**Invariant:** IDLE status makes `continue` explicitly illegal (it would wedge the agent forever) — this pairs with the idle-nudge fallback which also never lets idle end in continue. The outcome sandwich protects against long-context attention drift; the reminder is not redundancy but load-bearing placement.
**Probe:** `grep -c "You MUST return \"done\" or \"steer\"" src/core/prompt-builder.ts` → 1; `grep -c "REMINDER — DESIRED OUTCOME:" src/core/prompt-builder.ts` → 1; `grep -c "CHEATING PREVENTION" src/core/prompt-loader.ts` → 1. Direct tests: `tests/engine.test.ts:76` "built-in prompt includes cheating prevention section", `tests/engine.test.ts:235` "shows WORKING status when agent is not idle", `tests/engine.test.ts:423` "shows fallback when no context available".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", name_pattern: "buildUserPrompt|inferOutcome", query: "prompt", limit: 10 });
```

## Verdict
Adopt: outcome sandwich, liveness-switched decision space, explicit scope-question policy with a secrets carve-out, enumerated cheating taxonomy each paired with its verification move, and completion-biased done criteria. Adapt wording freely; keep the JSON-only response contract and the steer-requires-asi rule. Omit pi-specific tool names inside the taxonomy examples.
