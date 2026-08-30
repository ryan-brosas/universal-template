<!-- capsule-v2 -->
# Frontend tool dispatch — how are specific vs wildcard ("*") tools resolved, placeholder results replaced, and results ordered?

**Source:** copilotkit MIT `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** When an assistant message carries tool calls, what is the exact resolution order, the re-execution rule for forwarded placeholders, and where do tool-result messages get inserted?

## Specific-then-wildcard dispatch with placeholder splice in processAgentResult
**Path/Symbol:** `packages/core/src/core/run-handler.ts:RunHandler.processAgentResult` (:578-710), helpers `isFrontendPlaceholderResult` (:712-719) / `normalizeToolResultContent` (:721-757); insertion ladder in `executeSpecificTool` :906-936 and `executeWildcardTool` :1055-1085.
**Signature:** `getTool({ toolName, agentId? }): FrontendTool | undefined` (agent-specific first, then global fallback :267-282); lazy memoized wildcard: `getWildcardTool()` caches so the `"*"` lookup runs at most once per tool call.
**Data Shape:** placeholder = a tool-role message whose normalized content is exactly `"Forwarded to client"` (string, text-part array, or `{text}` object forms all normalized).

### Decisive source
```typescript
const executableTool = tool ?? getWildcardTool();

if (
  existingResult &&
  executableTool?.handler &&
  this.isFrontendPlaceholderResult(existingResult)
) {
  newMessages.splice(existingResultIndex, 1);
  existingResultIndex = -1;
  const agentMsgIdx = agent.messages.findIndex(
    (m) => m.role === "tool" && m.toolCallId === toolCall.id,
  );
  if (agentMsgIdx !== -1) agent.messages.splice(agentMsgIdx, 1);
}

if (existingResultIndex === -1) {
  if (tool) { /* executeSpecificTool */ }
  else { const fallbackTool = getWildcardTool(); /* executeWildcardTool */ }
}
```

**Flow:** for each assistant tool call → exact-name lookup (agent-scoped → global) → on miss, lazily resolve ONE `"*"` wildcard tool (memoized per call) → if a result already exists but is a `"Forwarded to client"` placeholder AND a local handler exists: remove it from BOTH `newMessages` and `agent.messages`, then execute locally → insertion walks past the parent assistant message and any sibling tool messages already inserted in this batch (`while messages[insertAt]?.role === "tool"`) preserving OpenAI-required ordering → follow-up requested iff no error and `tool.followUp !== false`.
**Invariant:** Wildcard handlers receive args wrapped as `{toolName, args}` while specific tools receive parsed args directly — that asymmetry is why `executeWildcardTool` keeps its own wrapping instead of delegating to `executeToolHandler`. Thread-switch race guard: if the parent message vanished from `agent.messages` mid-handler, skip insertion AND the follow-up (never mutate the wrong thread).
**Probe:** `packages/core/src/core/__tests__/run-handler-available.test.ts` + runtime service-adapter suites; deterministic anchor `grep -n "Forwarded to client" packages/core/src/core/run-handler.ts` (:718 sole sentinel literal).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-copilotkit", query: "executeWildcardTool executeSpecificTool isFrontendPlaceholderResult getTool", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the resolution ladder (specific → wildcard → none) and the placeholder-splice re-execution contract for any client-side tool bridge. Adapt the sentinel string to your transport's forwarding marker. Omit nothing from the race guard — dropping it corrupts threads switched mid-tool-run.
