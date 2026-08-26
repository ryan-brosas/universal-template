<!-- capsule-v2 -->
# Tool definition & serialization boundary — which tools exist per config, and what crosses to the GUI?

**Source:** continue Apache-2.0 `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does a porter gate an agent's built-in tool set by model/experimental/remote flags, and strip execution machinery before shipping tools to a client?

## Factory-function base list, flag-gated dependent list, destructuring-rest serializer
**Path/Symbol:** `core/tools/index.ts` (whole file, 56 lines): `getBaseToolDefinitions` (:6–16), `getConfigDependentToolDefinitions` (:18–51), `serializeTool` (:53–56). Consumption: `core/config/profile/doLoadConfig.ts:291–319`.
**Signature:** `getBaseToolDefinitions(): Tool[]`; `getConfigDependentToolDefinitions(params: ConfigDependentToolParams): Promise<Tool[]>`; `serializeTool(tool: Tool): Omit<Tool, "preprocessArgs" | "evaluateToolCallPolicy">`.
**Data Shape:** params = `{ rules, enableExperimentalTools, isRemote, modelName, ide }`; each `Tool` carries `function.{name,description,parameters}`, plus optional `uri`, `group`, `mcpMeta`, `preprocessArgs`, `evaluateToolCallPolicy`.

### Decisive source
```ts
// I'm writing these as functions because we've messed up 3 TIMES by pushing to const,
// causing duplicate tool definitions on subsequent config loads.
export const getBaseToolDefinitions = () => [ ...toolDefs ];

export function serializeTool(tool: Tool) {
  const { preprocessArgs, evaluateToolCallPolicy, ...rest } = tool;
  return rest;
}
```

**Flow (gating matrix):** ALWAYS pushed: `requestRule` + `readSkill` (async factories needing config params) and `searchWeb` — unconditionally, pinned by test. `enableExperimentalTools` adds viewRepoMap/viewSubdirectory/codebase/readFileRange. Recommended-agent chat model ⇒ `multiEdit` ELSE `editFile`+`singleFindAndReplace`. `!isRemote` ⇒ `grepSearch` (remote OS calls missing upstream: vscode issue #252269). Consumption at load: doLoadConfig passes chat-role model name + `await ide.isWorkspaceRemote()` (:291–300), then counts tool names and pushes a NON-fatal "Duplicate (N) tools named ... Permissions will conflict" error per collision (:302–319).
**Invariant:** the base list MUST be produced by calling a function — module-level mutable arrays accumulate duplicates across reload fan-outs (three real incidents recorded in-source). Serialization strips EXACTLY the two execution-machinery fields; everything else (including `mcpMeta`) is declarative data safe for the GUI.
**Probe:** `core/tools/definitions/toolDefinitions.test.ts` (every exported definition has type="function" and every required param present in properties with a type) and `core/tools/searchWebGating.vitest.ts` ("searchWeb tool is always available" with empty modelName, experimental off, remote false).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "serializeTool getBaseToolDefinitions getConfigDependentToolDefinitions", limit: 10 });
```

## Verdict
Adopt the factory-not-const rule for reload-rebuilt registries, the explicit gating matrix shape, duplicate-name warning as non-fatal signal, and the two-field destructure serializer as the trust boundary; adapt which flags matter (model tier, remote, experimental) to your agent; omit Continue's specific tool roster. Trap: adding a third field to serializeTool's rest-strip changes the client trust surface — treat the strip list as a reviewed contract, not an implementation detail.
