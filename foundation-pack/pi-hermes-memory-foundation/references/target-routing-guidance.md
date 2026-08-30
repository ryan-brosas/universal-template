<!-- capsule-v2 -->
# Target-routing prompt guidance — one shared routing block injected into review, flush, and correction prompts so both transports agree where facts belong

**Source:** pi-hermes-memory (MIT, `main@71beae8a`); Codebase Memory `pi-hermes-memory`. **Question:** Three different LLM entry points (background review, session flush, correction detector) each decide where a durable fact goes — how do you keep direct and subprocess transports from silently routing to different stores?

## buildMemoryTargetRoutingGuidance
**Path/Symbol:** `src/constants.ts:buildMemoryTargetRoutingGuidance` (:161–176, defined next to the prompt packs it feeds); injected at FIVE sites — background-review subprocess prompt :51 + direct system prompt :225–229, correction-detector subprocess prompt :214–218 + direct system prompt :241–245, session-flush direct system prompt :98–102 and `flushMessage` :120–122.
**Signature:** `buildMemoryTargetRoutingGuidance(hasProjectStore: boolean): string`.
**Data Shape:** four-bullet block titled `**Target routing**:`; the project bullet is CONDITIONAL — with a project store: project-specific facts ⇒ target "project"; without: "do not emit target \"project\"; use target \"memory\" for non-user, non-failure facts."

### Decisive source
```ts
// Review, flush, and correction prompts all inspect the same set of stores.
// Keep the routing rule in one place so direct and subprocess transports do
// not silently disagree about where a durable fact belongs.
export function buildMemoryTargetRoutingGuidance(hasProjectStore: boolean): string {
  const projectRule = hasProjectStore
    ? '- Project-specific facts, conventions, and workflows: use target "project" …'
    : '- No current project memory section is available: do not emit target "project"; '
      + 'use target "memory" for non-user, non-failure facts.';
  return `**Target routing**:
- User identity, preferences, and profile facts: use target "user".
- Global or cross-project facts: use target "memory".
${projectRule}
- Failures, corrections, insights, and tool quirks: use target "failure" (keep these
  categorized as failure memories; do not reroute them to project or global memory).`;
}
```

**Flow:** every prompt assembly (direct system prompt OR subprocess user prompt) splices this block between the base prompt and the conversation/memory payload → the LLM's emitted operations carry targets consistent with what the mutation layer accepts → wrong-target residue is caught downstream by `mutation-target-roundtrip.md`.
**Invariant:** single source of truth — the function is the ONLY place the rule lives, so the two transports cannot drift; the project-store availability flag is resolved per event (via `activeProjectStore !== null`), not baked at registration. The failure bullet explicitly forbids rerouting failure memories into cleaner stores (failure memories lose value if sanitized away).
**Probe:** `npx tsx --test tests/handlers/background-review.test.ts` — "includes explicit target routing for an available project store" (:877, matches `/project-specific facts.*target "project"/`, `/global or cross-project facts.*target "memory"/`, `/failures, corrections.*target "failure"/`), "keeps project target unavailable when no project store is present" (:894, `/do not emit target "project"/` AND no `--- Current Project Memory ---` section); :748/:545 assert `/target routing/i` reached the direct system prompts of review and flush. GREEN under `npx tsx --test`.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "buildMemoryTargetRoutingGuidance Target routing", limit: 5 })`

## Verdict
Adopt one shared, availability-parameterized routing block for every writer prompt feeding the same store set. Adapt target names to your schema. Pair with `mutation-target-roundtrip.md` (enforcement side) and `directive-wall.md` (policy text the model cannot write around).
