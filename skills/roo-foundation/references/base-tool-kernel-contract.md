<!-- capsule-v2 -->
# BaseTool kernel — how does a tool class receive args, stream partials, and why can't it accept XML?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** What is the minimal contract every tool implementation must satisfy, and what state must it reset between calls?

## Abstract tool class with nativeArgs-only dispatch
**Path/Symbol:** `src/core/tools/BaseTool.ts:BaseTool` (lines 29–162); `hasPathStabilized` :85; `resetPartialState` :97.
**Signature:** `abstract class BaseTool<TName extends ToolName>` with `abstract readonly name: TName`, `abstract execute(params, task, callbacks): Promise<void>`, overridable `handlePartial(task, block): Promise<void>`, entry `async handle(task, block, callbacks): Promise<void>`.
**Data Shape:** `ToolCallbacks = { askApproval, handleError, pushToolResult, toolCallId? }`; params typed via `NativeToolArgs[TName]` when defined else `any`; protected `lastSeenPartialPath: string | undefined` is the ONLY per-instance streaming state.

### Decisive source
```ts
if (block.nativeArgs !== undefined) {
    params = block.nativeArgs as ToolParams<TName>
} else {
    …
    if (paramsText.includes("<") && paramsText.includes(">")) {
        throw new Error("XML tool calls are no longer supported. Use native tool calling (nativeArgs) instead.")
    }
    throw new Error("Tool call is missing native arguments (nativeArgs).")
}
…
// Note: handleError already emits a tool_result via formatResponse.toolError in the caller.
// Do NOT call pushToolResult here to avoid duplicate tool_result payloads.
return
```

**Flow:** `handle()` — if `block.partial` → delegate to `handlePartial` (errors go to `handleError`) and RETURN (never executes); otherwise require `nativeArgs` (legacy XML-shaped params get the loud migration error; missing args a plain error) and call `execute`. Param-parse failures route through `handleError` ONLY — pushing a tool_result there too would double-emit. `hasPathStabilized` returns true only when the current path EQUALS the previously seen one AND is non-empty (two consecutive identical observations), then stores the new value; `resetPartialState()` clears it and should be called at the end of execute on success AND error paths.
**Invariant:** tools are SINGLETONS (`export const editTool = new EditTool()`) so `lastSeenPartialPath` persists across calls — forgetting `resetPartialState()` leaks a stale path into the next invocation's stabilization check. The duplicate-result rule (parse errors → handleError only) is load-bearing for exactly-one-tool_result presentation.
**Probe:** `grep -c 'lastSeenPartialPath' src/core/tools/BaseTool.ts` → 4; `grep -cF 'XML tool calls are no longer supported' src/core/tools/BaseTool.ts` → 1; `grep -cF 'Do NOT call pushToolResult here to avoid duplicate tool_result payloads.' src/core/tools/BaseTool.ts` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "BaseTool handle hasPathStabilized resetPartialState", limit: 10 });
```

## Verdict
Adopt the abstract-class + callbacks contract, the two-observation path-stabilization gate for streaming previews, and the singleton-reset discipline. Adapt ToolParams typing to your host's arg schema source. Omit VS Code task plumbing. Coverage caveat: BaseTool itself has no dedicated spec at pin; its contracts are exercised transitively by editTool/searchReplaceTool/applyPatchTool specs.
