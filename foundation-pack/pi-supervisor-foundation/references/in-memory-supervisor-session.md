<!-- capsule-v2 -->
# In-memory supervisor session — isolated in-memory session reuse keyed on model identity + system prompt

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How do you run an LLM overseer beside the main agent without touching its context, tools, or session log?

## Isolation flags + reuse key
**Path/Symbol:** `src/session/supervisor-session.ts:19-63` (`ensureStarted`), prompt path :65-93, global singleton `src/session/client.ts:11-24`.
**Signature:** `ensureStarted(ctx, provider, modelId, systemPrompt): Promise<boolean>`; reuse condition compares resolved model object AND system prompt string.
**Data Shape:** Session created with `SessionManager.inMemory()`, `tools: []`, and a loader configured `noExtensions/noSkills/noPromptTemplates/noThemes` + `systemPromptOverride`.

### Decisive source
```ts
    if (this.session && this.model === newModel && this.systemPrompt === systemPrompt) {
      // Session reusable
      return true;
    }
    // Dispose old session if exists
    this.dispose();

    const loader = new DefaultResourceLoader({
      cwd: ctx.cwd,
      agentDir: getAgentDir(),
      noExtensions: true,
      noSkills: true,
      noPromptTemplates: true,
      noThemes: true,
      systemPromptOverride: () => systemPrompt,
    });
```
Prompt path accumulates streamed deltas via subscription and aborts on signal:
```ts
    const onAbort = () => this.session?.abort();
    signal?.addEventListener('abort', onAbort, { once: true });
    const unsubscribe = this.session.subscribe((event) => {
      if (event.type === 'message_update' && event.assistantMessageEvent.type === 'text_delta') {
        responseText += event.assistantMessageEvent.delta;
        onDelta?.(responseText);
      }
    });
```

**Flow:** first analysis creates the isolated session → subsequent analyses with SAME model+prompt reuse it (context window carries over = token efficiency) → model/prompt change ⇒ dispose+recreate → dispose also fires at stop/done/crash-teardown.
**Invariant:** The reuse key is the RESOLVED model object (`registry.find`), not the provider/id strings — registry refreshes invalidate correctly. Isolation is total: in-memory only (nothing persisted), zero tools (the supervisor cannot act), extensions/skills/themes off (no host leakage). Abort listener is `{once:true}` and always removed in `finally`.
**Probe:** `grep -c "noExtensions: true" src/session/supervisor-session.ts` → 1; `grep -c "SessionManager.inMemory()" src/session/supervisor-session.ts` → 1; `grep -c "systemPrompt === systemPrompt" src/session/supervisor-session.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "SupervisorSession ensureStarted in-memory session reuse", limit: 10 });
```

## Verdict
Adopt maximal-isolation side-sessions for any LLM judge/observer sharing credentials with a primary agent. Adapt loader flags to your host's extension surface; keep tools empty unless you want the observer acting. Omit nothing on the dispose discipline — leaked side sessions pin model clients open.
