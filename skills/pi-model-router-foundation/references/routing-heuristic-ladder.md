<!-- capsule-v2 -->
# Routing heuristic ladder — how do I classify a turn into a tier deterministically before any LLM call?

**Source:** pi-model-router MIT `main@002b48f9bb03c068e0ef97eb230f49df57a24f93`; Codebase Memory `pi-model-router`. **Question:** What is the exact precedence order and threshold arithmetic of the keyword/shape routing ladder, so a port preserves both the tier outcomes and the sticky-phase feel?

## Heuristic decision kernel
**Path/Symbol:** `extensions/routing.ts:decideRouting` (lines 133–387).
**Signature:** `decideRouting(context, profileName, profile, previousDecision?, pinnedTier?, thinkingOverrides?, phaseBias = 0.5, rules?, isBudgetExceeded = false): RoutingDecision`.
**Data Shape:** Reads only the conversation: last user text (lowercased), recent-conversation text, toolResult count, word count, line count (`>= 4` ⇒ multi-line). Emits a full `RoutingDecision` with human-readable `reasoning` for every branch.

### Decisive source
```ts
const highThreshold = Math.max(40, 120 - (previousDecision?.phase === 'planning' ? phaseBias * 80 : 0));
const lowThreshold  = Math.max(4,   12  - (previousDecision?.phase === 'implementation' ||
                                           previousDecision?.phase === 'planning' ? phaseBias * 8 : 0));
...
} else if (
  previousDecision?.phase === 'planning' &&
  toolResultCount === 0 &&
  wordCount > lowThreshold
) {
  phase = 'planning'; tier = 'high';
  reasoning = 'Kept the planning-phase bias because the conversation still looks exploratory.';
}
```

**Flow (order IS the contract):**
1. `pinnedTier` short-circuits everything (`Pinned to X tier via /router-pin.`).
2. Custom rules (see custom-rule capsule); if none matched:
3. explicitHighHints (`best`, `deep`, `step by step`, `think hard`, `ultrathink`, …) → high/planning.
4. explicitLowHints (`fast`, `cheap`, `brief`, `one sentence`, …) → low/lightweight.
5. summaryKeywords (`summarize`, `changelog`, `tl;dr`, …) → low/lightweight.
6. planningKeywords ∨ prompt startsWith `'why '` ∨ `wordCount >= highThreshold` ∨ multi-line → high/planning.
7. implementationKeywords (`implement`, `fix`, `refactor`, `continue`, `go ahead`, …) → medium/implementation.
8. lookupKeywords ∧ `wordCount <= 24` ∧ `toolResultCount === 0` → low/lightweight.
9. planning-stickiness: prev planning ∧ no tool results ∧ `wordCount > lowThreshold` → high/planning.
10. implementation-stickiness: `toolResultCount > 0` ∨ prev implementation ∨ recent text includes `'plan:'` → medium/implementation.
11. `wordCount <= lowThreshold` → low/lightweight; else default medium ("Defaulted to medium tier for general coding work.").
12. Budget gate (last): if `isBudgetExceeded && tier === 'high'` downgrade to medium/implementation and set `isBudgetForced = true`.

**Invariant:** Every branch assigns a `reasoning` string that names the detected signal; thresholds are floors, never negatives (`Math.max`). Stickiness lowers the planning-entry threshold by up to `phaseBias*80` words and the low-tier ceiling by up to `phaseBias*8` words — a port that drops `previousDecision` input silently changes tier distribution mid-session.
**Probe:** `extensions/routing.test.ts` — hint routing :330–350, budget downgrade :352–371 (`isBudgetForced === true`), planning stickiness :373–422 (both variants assert tier+phase+reasoning), toolResult detection :447–474, `'plan:'` in assistant text :476–495, default-medium :497–510.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-model-router", query: "decideRouting heuristic ladder", limit: 10 });
```

## Verdict
Adopt the pure function shape, branch order, threshold arithmetic, and reasoning-string discipline as-is; adapt the keyword lists to your domain language; omit the Pi `Context` message types by substituting your host's turn shape (only last-user-text, recent text, toolResult count are consumed). Direct tests cited above pin all branches at this commit.
