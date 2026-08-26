<!-- capsule-v2 -->
# LLM boundary conversion — how do harness-native message roles become provider-legal messages?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter adds a harness-only message role (e.g. shell executions) — where and how may it enter the provider payload?

## One function, once per turn; everything becomes user text
**Path/Symbol:** `packages/agent/src/harness/messages.ts:124-168` (`convertToLlm`), role definitions + prefix constants at `:4-61`, renderer `bashExecutionToText` at `:63-79`.
**Signature:** `convertToLlm(messages: AgentMessage[]): Message[]` (filter-map: unknown/unsupported roles → dropped).
**Data Shape:** Harness-only roles convert to USER messages with wrapped text: `bashExecution` → rendered "Ran \`cmd\`" + fenced output (+ cancelled / exit-code / truncated-with-fullOutputPath notes), skippable via `excludeFromContext`; `custom` → its string/content as-is; `branchSummary` and `compactionSummary` → `<summary>…</summary>` wrapped in their distinctive preambles ("history … was compacted…" vs "…came back from a branch…"). Native user/assistant/toolResult pass through unchanged.

### Decisive source
```ts
case "branchSummary":
	return { role: "user", content: [{ type: "text", text: BRANCH_SUMMARY_PREFIX + m.summary + BRANCH_SUMMARY_SUFFIX }], timestamp: m.timestamp };
case "user": case "assistant": case "toolResult":
	return m;
default:
	return undefined;   // silently dropped, never rejected
```

**Flow:** the loop calls `convertToLlm(context.messages)` exactly once per turn inside `streamAssistantResponse` (after optional `transformContext`) → synthetic roles become annotated user turns → provider receives only the three native roles.
**Invariant:** The provider payload contains ONLY user/assistant/toolResult roles — every other role must cross this single boundary or not exist downstream; because conversion is once-per-turn, no caller can double-convert or partially convert history. This is also why entry-point guards can't validate deeper than role checks (agent-loop-modes capsule).
**Probe:** `packages/agent/test/agent-loop.test.ts:166/:221` ("should handle custom message types via convertToLlm" / "should apply transformContext before convertToLlm").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "convertToLlm bashExecution excludeFromContext", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the one-boundary filter-map with user-text wrapping for synthetic roles. Adapt preamble wording to your product voice. Omit nothing. Coverage caveat: bashExecution rendering itself is covered indirectly via custom-role tests.
