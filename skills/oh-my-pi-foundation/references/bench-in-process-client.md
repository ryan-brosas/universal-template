<!-- capsule-v2 -->
# In-process benchmark client — warm-pool shared infra and per-client registry isolation

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you run many benchmarked agent sessions in one process without the ~2-3s CLI startup overhead per task, sharing auth/model discovery while keeping concurrent top-level sessions from clobbering each other?

## InProcessClient + discoverSharedInfra — session facade over warm pools
**Path/Symbol:** `packages/typescript-edit-benchmark/src/in-process-client.ts` — `discoverSharedInfra` (52-75), `InProcessClient` (81-212), `isAgentEvent` (227-229), `AGENT_EVENT_TYPES` (214-225), `SharedInfra` (39-42).
**Signature:** `discoverSharedInfra(options): Promise<SharedInfra>`; `class InProcessClient { constructor(options); start(); setThinkingLevel(level); onEvent(listener); prompt(text); followUp(text); abort(); getSessionStats(); getLastAssistantText(); getMessages(); getState(); dispose(); [Symbol.dispose](); }`.
**Data Shape:** `SharedInfra = { authStorage: AuthStorage, modelRegistry: ModelRegistry }` — discovered ONCE per benchmark run and passed to every client. `InProcessClientOptions = { cwd, model, appendSystemPrompt?, tools?, editVariant?, editFuzzy?, editFuzzyThreshold?, shared? }`. Default tools = `["read","edit","write"]`; `enableMCP:false`, `enableLsp:false`, `disableExtensionDiscovery:true`, `hasUI:false`.

### Decisive source
```ts
// discoverSharedInfra: init the global Settings singleton ONCE (edit knobs via
// Settings overrides, NOT env vars), reuse auth + model registry across tasks
const authStorage = await discoverAuthStorage();
try {
    const modelRegistry = new ModelRegistry(authStorage);
    const overrides: Record<string, unknown> = {};
    if (options.editVariant && options.editVariant !== "auto") overrides["edit.mode"] = options.editVariant;
    // ... edit.fuzzyMatch, edit.fuzzyThreshold
    await Settings.init({ cwd: options.cwd, overrides });
    return { authStorage, modelRegistry };
} catch (error) { authStorage.close(); throw error; }
```
```ts
// InProcessClient.start: each client gets its OWN AgentRegistry
const result = await createAgentSession({
    cwd, modelPattern: this.#options.model,
    authStorage: shared?.authStorage, modelRegistry: shared?.modelRegistry,
    sessionManager: SessionManager.inMemory(this.#options.cwd),
    agentRegistry: new AgentRegistry(),   // per-client — see invariant
    systemPrompt: this.#options.appendSystemPrompt
        ? (defaultPrompt) => [...defaultPrompt, this.#options.appendSystemPrompt!] : undefined,
    toolNames: this.#options.tools ?? ["read", "edit", "write"],
    hasUI: false, enableMCP: false, enableLsp: false, skills: [], rules: [], contextFiles: [],
    disableExtensionDiscovery: true,
});
```
**Flow:** `discoverSharedInfra` resolves auth storage + model registry once and initializes the global `Settings` singleton with edit-mode/fuzzy overrides (so code paths using the global `settings` proxy see them; on failure it closes the auth storage and rethrows) → each `InProcessClient.start()` calls `createAgentSession` with the SHARED auth/model but a **fresh `AgentRegistry`**, an in-memory `SessionManager`, and a disabled MCP/LSP/extension surface → subscribes to session events and forwards only `AgentEvent` types (whitelist set) to its listeners → `prompt`/`followUp` call the session then `waitForIdle()`; `getState` snapshots systemPrompt/model/thinkingLevel/tools → `dispose` unsubscribes, disposes the session, disposes the MCP manager, and clears listeners.
**Invariant:** the global agent registry admits only one "Main" per process generation — later registrations replace earlier refs, which then fail session init — so each concurrent client MUST construct its own `new AgentRegistry()`. Shared infra is only auth + model registry (safe to share); session/registry state is per-client. `dispose` is idempotent and `[Symbol.dispose]` swallows errors so a failed run never leaks.

**Probe:** consumed by `packages/metaharness/adapters/edit/runner.ts` (`BenchmarkClient` facade, `runSingleTask`) — see `bench-edit-agent-loop`; the per-client-registry requirement is the documented reason for `new AgentRegistry()` at `in-process-client.ts:105`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "InProcessClient discoverSharedInfra createAgentSession AgentRegistry SharedInfra", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any in-process agent benchmark harness: discover auth/model once, initialize the global settings singleton once, and give every concurrent session its own registry while sharing the warm pools. Adapt the session-creation call and settings keys to your agent SDK; omit OMP-specific `AgentRegistry`/`SessionManager` internals. The per-client-registry isolation (one-"Main"-per-process) is the invariant a porter gets wrong.
