<!-- capsule-v2 -->
# Extension tool wrapping — how do product-level tool definitions, core agent tools, and runtime-registered extension tools interconvert without leaking extension context into the kernel?

**Source:** pi-mono MIT `main@80e62761f7251a104f1b21d9c73920c720f0ec00`; Codebase Memory `pi-mono`. **Question:** How does an extension system add tools to a core agent loop while the loop stays extension-agnostic — and how do dynamically added tools reach the LLM mid-conversation?

## Two-layer wrapper plane + active-tools diffing
**Path/Symbol:** `packages/coding-agent/src/core/tools/tool-definition-wrapper.ts:wrapToolDefinition` (:5-20) / `createToolDefinitionFromAgentTool` (:36-47); `packages/coding-agent/src/core/extensions/wrapper.ts:wrapRegisteredTool` (:17-37).
**Signature:** `wrapToolDefinition(def: ToolDefinition, ctxFactory?: () => ExtensionContext): AgentTool`; `createToolDefinitionFromAgentTool(tool: AgentTool): ToolDefinition`; `wrapRegisteredTool(registeredTool: RegisteredTool, runner: ExtensionRunner): AgentTool`
**Data Shape:** `ToolDefinition` (extension-facing: prompt metadata + renderers + execute with optional ctx) ↔ `AgentTool` (kernel-facing: name/label/description/parameters/prepareArguments/executionMode/execute).

### Decisive source
```ts
// definition-first registry: plain AgentTools get synthesized definitions
execute: async (toolCallId, params, signal, onUpdate) => tool.execute(toolCallId, params, signal, onUpdate),
// registered tools: diff active tools across execute to announce late arrivals
const activeBefore = runner.getActiveTools();
const result = await execute(toolCallId, params, signal, onUpdate);
const activeAfter = runner.getActiveTools();
if (!activeBefore.every((name) => activeAfter.includes(name))) return result;
const addedToolNames = activeAfter.filter((name) => !beforeNames.has(name));
if (addedToolNames.length === 0) return result;
return { ...result, addedToolNames: [...new Set([...(result.addedToolNames ?? []), ...addedToolNames])] };
```

**Flow:** extension registers a ToolDefinition → `wrapRegisteredTool` closes over `runner.createContext()` so the kernel's `execute(toolCallId, params, signal, onUpdate)` never sees an extension argument → after each execution, the runner diffs its active-tool set: newly-active names are stamped onto the tool RESULT as `addedToolNames` → that field travels inside the ToolResultMessage → provider conversion (`convertToolResult`, see `anthropic-message-normalization`) turns it into `tool_reference` blocks at the tool-result marker, loading deferred tools for the NEXT model turn. If any previously-active tool disappeared during execution, the diff is abandoned (returns unmodified result).
**Invariant:** the kernel consumes only AgentTool; extension context is injected by closure; tool availability changes are data (`addedToolNames` on results), not control flow — so they persist in session history and replay correctly.
**Probe:** `packages/ai/test/deferred-tools.test.ts:188-243` pins the downstream wire effect (`defer_loading: true` in `payload.tools`; `tool_reference` at the marker; sibling-content preservation; no resurrection when the tool is missing from Context.tools). Direct-read this pass; suite itself fixture-blocked at import (generated catalogs). Kernel-side event ordering is pinned GREEN by `packages/agent` pass-1 suite (47 tests).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-mono", query: "extension tool definition wrapper custom tool execute render", limit: 15 });
// executed live this pass: ranked wrapRegisteredTool plane and regressions 4167/5998; whole-file read of
// tool-definition-wrapper.ts (47 lines) confirmed the bidirectional mapping; cross-linked to convertToolResult
// via search "addedToolNames deferred tool reference registered active tools test".
```

## Verdict
Adopt: closure-injected context, definition-first registry with synthesized minimal definitions, and results-as-data tool announcements. Adapt renderer/prompt metadata to your UI. Omit the specific extension event bus (separate seam). Coverage: `no_recorded_issue` ×2 cited source paths at generation 2026-08-24T16:11:21Z.
