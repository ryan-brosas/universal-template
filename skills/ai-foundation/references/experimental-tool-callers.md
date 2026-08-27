<!-- capsule-v2 -->
# Experimental tool callers — how can one tool be hidden from the model yet stay executable, routed through a local caller or a provider-executed caller?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How does the per-step split into modelTools vs executionTools work, and what are the validation rules for the toolCallers config?

## resolveToolCallerConfiguration
**Path/Symbol:** `packages/ai/src/generate-text/tool-caller-configuration.ts:resolveToolCallerConfiguration` (:26-78), `prepareToolsForToolCallers` (:80-158); definition type `packages/provider-utils/src/types/tool-caller.ts:ToolCallerDefinition` (`{type:'local', bind(tools): Tool}` | `{type:'provider', prepareProviderOptions(prev): ProviderOptions}`).
**Signature:** `resolveToolCallerConfiguration({tools?, toolCallers?}): ResolvedToolCallers | undefined` — returns `undefined` when EITHER side is null (feature off). `Experimental_ToolCallers<TOOLS>` maps tool names to arrays of `'AI_SDK_DIRECT_TOOL_CALL' | ToolCallerName<TOOLS>`.
**Data Shape:** `prepareToolsForToolCallers` returns `{executionTools: ToolSet | undefined, modelTools: ToolSet | undefined}`; sentinel `'AI_SDK_DIRECT_TOOL_CALL'` (:9) marks "model may call this tool directly".

### Decisive source
```ts
for (const [toolName, callers] of Object.entries(toolCallers)) {
  if (!Object.prototype.hasOwnProperty.call(tools, toolName))      // own-property check:
    throw new InvalidArgumentError({ parameter: 'experimental_toolCallers',
      message: `unknown tool "${toolName}".` });                   // unknown tool ⇒ hard error
  if (!Array.isArray(callers))
    throw new InvalidArgumentError({ /* must be an array */ });
  resolved[toolName] = callers.map(caller => {
    if (caller === DIRECT_TOOL_CALL) return caller;
    // non-string OR not-an-own-tool OR that tool lacks experimental_toolCaller ⇒ invalid
    if (typeof caller !== 'string' ||
        !Object.prototype.hasOwnProperty.call(tools, caller) ||
        experimental_getToolCaller(tools[caller]) == null)
      throw new InvalidArgumentError({ parameter: 'experimental_toolCallers',
        message: `tool "${toolName}" contains an invalid caller.` });
    return caller;
  });
}
```
```ts
// prepareToolsForToolCallers — visibility rule:
executionTools[toolName] = preparedTool;
if (availableDirectly || availableToProvider) modelTools[toolName] = preparedTool;
else delete modelTools[toolName];        // ONLY local callers ⇒ tool is EXECUTABLE but INVISIBLE
```

**Flow:** validate every entry up front (fail fast before any step runs) → per step, both orchestrators call `prepareToolsForToolCallers({tools: stepActiveTools, toolCallers})` (`generate-text.ts:914`, `stream-text.ts:1962`) → provider-type callers mutate the tool's `providerOptions` via `prepareProviderOptions` and mark it visible; local-type callers collect tools into `localToolsByCaller` and hide them → after the loop, each local caller's tool is REPLACED by `caller.bind(localToolsByCaller.get(callerName) ?? {})` in executionTools (and in modelTools if the caller itself was visible).
**Invariant:** A tool listed under local-only callers stays executable (the bound caller reaches it) but never appears in the wire request — the inverse of normal visibility. Caller binding happens AFTER all collection so one bind receives its complete tool set. Validation uses `Object.prototype.hasOwnProperty`, not `in` — inherited names don't count. An empty/missing bind set still binds (`{}`), never leaves the raw callable.
**Probe:** no dedicated unit file at this pin — behavior pinned via `generate-text.test.ts` / `stream-text.test.ts` integration paths and the shared `tool-caller.ts` helper contract; recorded as coverage caveat.

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"prepareToolsForToolCallers resolveToolCallerConfiguration experimental_toolCaller","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the two-plane split (modelTools → wire request, executionTools → run loop) with validate-up-front configuration; adapt the sentinel string and TS name-ladder types to your surface; omit the experimental_ prefix conventions. Caveat: no direct unit suite at HEAD — port against the orchestrator integration tests.
