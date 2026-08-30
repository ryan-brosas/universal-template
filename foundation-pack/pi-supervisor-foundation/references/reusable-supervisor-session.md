<!-- capsule-v2 -->
# Reusable supervisor session — how do you call an LLM repeatedly without re-paying context setup?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How is a persistent judge-session created, reused, and invalidated — and what identity check makes reuse safe?

## SupervisorSession + client singleton (`src/session/supervisor-session.ts`, `src/session/client.ts`)
**Path/Symbol:** `src/session/supervisor-session.ts:SupervisorSession.ensureStarted` (:19-63), `.prompt` (:65-93); `src/session/client.ts:callSupervisorModel` (:30-46), module-level `activeSession` (:11).
**Signature:** `ensureStarted(ctx, provider, modelId, systemPrompt): Promise<boolean>`; `prompt(userPrompt, signal?, onDelta?): Promise<string|null>`; `callSupervisorModel(...): Promise<SteeringDecision>`.
**Data Shape:** One GLOBAL session per supervision goal (`getOrCreateSession` lazily builds; `disposeSession` nulls it). Reuse validity = model object IDENTITY + systemPrompt string EQUALITY.

### Decisive source
```ts
const newModel = ctx.modelRegistry.find(provider, modelId);
if (!newModel) return false;
if (this.session && this.model === newModel && this.systemPrompt === systemPrompt) {
  return true;                       // reusable — same model instance AND same prompt
}
this.dispose();                        // any drift ⇒ full teardown + rebuild
const loader = new DefaultResourceLoader({
  cwd: ctx.cwd, agentDir: getAgentDir(),
  noExtensions: true, noSkills: true, noPromptTemplates: true, noThemes: true,
  systemPromptOverride: () => systemPrompt,
});
const result = await createAgentSession({
  sessionManager: SessionManager.inMemory(),   // NEVER persisted
  tools: [],                                   // the judge gets NO tools
  resourceLoader: loader, ...
});
```

**Flow:** every analysis → get-or-create singleton → ensureStarted validates identity → prompt subscribes to streaming deltas (feeds live UI via onDelta), awaits completion with abort-signal wiring (`signal.addEventListener('abort', ...)` with `{once:true}` + cleanup in finally) → accumulated text returned; `null` on ANY failure → caller maps null/exception to safeContinue. Inference (`inferOutcome`) deliberately constructs a THROWAWAY session instead of the singleton because its system prompt differs.
**Invariant:** (1) The supervisor's conversation ACCUMULATES across analyses in one goal — that is the token-efficiency point — so changing systemPrompt mid-goal silently forks the memory; identity-check both fields or don't reuse. (2) Judge sessions are in-memory + tool-less + extension-less: they cannot touch the user's repo and cannot leak into the supervised transcript. (3) Every failure path (start-fail, prompt-null, throw) resolves to continue at the analyzer layer.
**Probe:** `tests/engine.test.ts` inferOutcome suite (:438-606) — `returns null when model not found in registry` (:472), `extracts outcome successfully` (:509), `cleans up result` (:531), `uses goal extraction system prompt` (:598).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "SupervisorSession ensureStarted createAgentSession inMemory", limit: 8 });
```

## Verdict
Adopt singleton-judge-with-identity-invalidation for repeated LLM evaluation calls. Adapt to your host's session API (any stateful chat client works). Omit pi's DefaultResourceLoader specifics; keep no-tools + non-persistence as the security shape.
