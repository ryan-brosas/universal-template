<!-- capsule-v2 -->
# Session model persistence ladder — how does the session remember its model across turns and prompts?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** When a prompt omits the model, which three sources are consulted in order, and when is the session row rewritten?

## DB row → message history → provider default
**Path/Symbol:** `packages/opencode/src/session/prompt.ts` (`currentModel`, lines 614–633; `createUserMessage` persistence :672–689; variant resolution :646–654).
**Signature:** `currentModel(sessionID): Effect<{providerID, modelID, variant?}>`.
**Data Shape:** Source 1: `SessionTable.model` column (`{providerID, id, variant?}`) — variant "default" is stripped on read. Source 2: `sessions.findMessage(sessionID, m => m.info.role === "user" && !!m.info.model)` — first user message carrying a model. Source 3: `provider.defaultModel()`. Persistence fires only when resolved agent/model differs from stored (agent name, provider, id, or variant with default-normalization).

### Decisive source
```ts
// prompt.ts:673-689 — write ONLY on observable change; "default" normalizes to undefined
if (
  current.agent !== info.agent ||
  current.model?.providerID !== info.model.providerID ||
  current.model?.id !== info.model.modelID ||
  (current.model?.variant === "default" ? undefined : current.model?.variant) !== info.model.variant
) {
  yield* sessions.setAgentModel({ sessionID, agent: info.agent,
    model: { id: info.model.modelID, providerID: info.model.providerID,
             variant: info.model.variant ?? "default" }, time: info.time.created })
}
```

**Flow:** createUserMessage resolves model = input.model ?? agent.model ?? currentModel(sessionID) → variant = input.variant ?? (agent.variant if the resolved model actually HAS that variant and matches the agent's own model — requires fetching full model def; ModelNotFoundError swallowed to undefined) → maybe persist → every later loop step reads lastUser.model (never re-resolves), keeping all steps of one run on ONE model.
**Invariant:** The session's sticky model must survive process restarts (DB) and legacy sessions without rows (history scan). Variant inheritance is CONDITIONAL: an agent's preferred variant applies only when using the agent's own model AND that variant exists — pinned by test where an override model drops the variant but returning to the agent model restores it.
**Probe:** `packages/opencode/test/session/prompt.test.ts:2287` "applies agent variant only when using agent model" (override ⇒ variant undefined; same-model ⇒ "xhigh"; explicit variant:"high" wins); `:583` "legacy prompt emits…" (session created WITH old model keeps it across two prompts; session row reflects build/ref).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", qn_pattern: "packages.opencode.src.session.prompt", limit: 20, detail: "ids" });
```

## Verdict
Adopt the three-source read ladder + diff-gated write + conditional variant inheritance; adapt storage schema; omit drizzle specifics.
