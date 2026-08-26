<!-- capsule-v2 -->
# Tool-call layer — how do you parse, repair, execute, and prune tool traffic so nothing is silently dropped and no history reference is orphaned?

**Source:** Vercel AI SDK (Apache-2.0) `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** What is the failure routing for bad tool calls, how do tools start mid-stream under approval gating, and what invariant keeps pruned history valid?

## parseToolCall: typed-error repair with visible degradation
**Path/Symbol:** `packages/ai/src/generate-text/parse-tool-call.ts:parseToolCall` (19–116; helpers `doParseToolCall` 164–226, `parseProviderExecutedDynamicToolCall` 137–162, `refineParsedToolCallInput` 118–135).
**Signature:** `parseToolCall({toolCall, tools?, repairToolCall?, refineToolInput?, instructions?, messages}) => Promise<TypedToolCall>`.
**Data Shape:** three outcomes — parsed call (optionally input-refined), repaired call, or `{invalid: true, dynamic: true, error, input}` invalid part carrying best-effort parsed input.

### Decisive source
```ts
} catch (error) {
  if (
    repairToolCall == null ||
    !(NoSuchToolError.isInstance(error) || InvalidToolInputError.isInstance(error))
  ) {
    throw error;
  }
  let repairedToolCall: LanguageModelV4ToolCall | null = null;
  try {
    repairedToolCall = await repairToolCall({ toolCall, tools, ..., error });
  } catch (repairError) {
    throw new ToolCallRepairError({ cause: repairError, originalError: error });
  }
  if (repairedToolCall == null) {
    throw error;
  }
```
```ts
// use parsed input when possible
const parsedInput = await safeParseJSON({ text: toolCall.input });
const input = parsedInput.success ? parsedInput.value : toolCall.input;
...
return { type: 'tool-call', ..., input, dynamic: true, invalid: true, error, ... };
```
(`parse-tool-call.ts:52–88, 96–114`, verbatim; empty-input → schema-validated `{}` at :189–194 "many LLMs generate empty strings for tool calls with no arguments")

**Flow:** parse → on `NoSuchToolError`/`InvalidToolInputError` ONLY: invoke repair hook with the typed error + per-tool JSON schemas → repair throws ⇒ `ToolCallRepairError{cause, originalError}` (BOTH preserved); repair returns null ⇒ ORIGINAL error rethrows; anything still failing degrades to a visible `invalid` part the model can see and correct next turn.
**Invariant:** invalid inputs are never silently dropped — they become model-visible parts. Repair is keyed to exactly two error types; other errors bypass the hook untouched.
**Probe:** `packages/ai/src/generate-text/parse-tool-call.test.ts` :375 repair result used, :472 null-repair rethrows original, :512 ToolCallRepairError wraps, :277/:314/:363 invalid-part degradation.

## Approval-gated stream-time execution
**Path/Symbol:** `packages/ai/src/generate-text/execute-tools-from-stream.ts:executeToolsFromStream` (34–246); single-tool lifecycle in `execute-tool-call.ts:executeToolCall` (43–223).
**Signature:** `executeToolsFromStream({stream, tools, ..., toolApproval?, toolApprovalSecret?}) => ReadableStream<ExecuteToolsStreamPart>`; `executeToolCall({...}) => {output: ToolOutput|ToolError, toolExecutionMs} | undefined`.
**Data Shape:** every chunk forwards IMMEDIATELY; `tool-call` chunks queue for execution; `model-call-end` drains the queue; new `tool-execution-end {toolCallId, toolExecutionMs}` part emitted before each output.

### Decisive source
```ts
if (toolApprovalStatus.type === 'not-applicable') {
  if (tool.execute != null && chunk.providerExecuted !== true) {
    toolCallsToExecute.push(chunk);
  }
  return;
}
const approvalId = generateId();
const signature = await maybeSignApproval({
  secret: toolApprovalSecret, approvalId,
  toolCallId: chunk.toolCallId, toolName: chunk.toolName, input: chunk.input,
});
```
```ts
case 'model-call-end': {
  await Promise.all(toolCallsToExecute.map(async toolCall => {
    ...
    controller.enqueue({ type: 'tool-execution-end', toolCallId, toolExecutionMs });
    controller.enqueue(result.output);
```
(`execute-tools-from-stream.ts:120–135, 199–230`, verbatim)

**Flow:** tools begin executing AS their inputs finish streaming (queue fills during the response) → approval resolution first: `user-approval` emits request part and STOPS; auto-`denied`/auto-`approved` emit request+response pairs (`isAutomatic: true`, HMAC-signed when secret set) then denied stops / approved executes → provider-executed calls never run locally → errors become `error` parts, not stream failures.
**Invariant:** 'not-applicable' tools must NOT consume an approval id (:116–119 comment) — id sequences stay deterministic for callers. Execution waits for `model-call-end`; preliminary outputs still reach consumers early via `onPreliminaryToolResult`. Per-tool timeout = caller signal merged with `tools['${name}Ms'] ?? toolMs`.
**Probe:** `execute-tools-from-stream.test.ts` :348 approved pair emitted BEFORE execution, :477 denied without executing, :298/:1057 provider-executed skipped, :1115 TypeValidationError precedes approval callbacks; `execute-tool-call.test.ts` :44 no-execute ⇒ undefined, :211 tool-error return.

## pruneMessages: referential-integrity-aware pruning
**Path/Symbol:** `packages/ai/src/generate-text/prune-messages.ts:pruneMessages` (17–196).
**Signature:** `pruneMessages({messages, reasoning?='none', toolCalls?='all'|'before-last-message'|'before-last-N-messages'|'none'|Array<{type, tools?: string[]}>, emptyMessages?='keep'|'remove'})`.
**Data Shape:** DSL normalizes to an array of `{type, tools?}` rules; per rule: keep-window ids collected FIRST from the trailing slice, then global id→name maps built, THEN filtering.

### Decisive source
```ts
// Build global maps from tool call id and approval id to tool name.
// These must be global (not per-message) because a `tool-approval-response`
// lives in a separate `tool` message from its `tool-approval-request`
// (assistant message), so the tool name of a response can only be resolved
// by looking across messages. Resolving names per-message left responses
// unresolved, which caused them to be kept while their request was pruned,
// producing orphaned approval responses.
```
```ts
return (
  toolCall.tools != null &&
  partToolName != null &&
  !toolCall.tools.includes(partToolName)
);
```
(`prune-messages.ts:103–109, 181–185`, verbatim; keep-window scan :83–101; assistant/tool messages with STRING content are never touched :142–149)

**Flow:** collect kept toolCallIds/approvalIds from the retained window wherever those ids appear → build global maps (toolCallId→toolName across all messages; approvalId→toolName via callId lookup) → filter outside-window messages keeping non-tool parts, kept-id parts, and parts of OTHER tools when scoped by name → drop empty messages unless told otherwise.
**Invariant:** name resolution must be GLOBAL and the keep-set collected BEFORE filtering — per-message resolution orphans approval responses whose requests were pruned (the exact regression pinned at :721). A part survives name-scoped pruning only when its tool is NOT in the removal list AND its name resolves; unresolved names are dropped under scoping.
**Probe:** `packages/ai/src/generate-text/prune-messages.test.ts` :722 "should prune the approval response together with its request and tool-call" (regression), :829 "drop unresolved approval responses", :551 before-last-2 windowing, :644 two-tool settings.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", name_pattern: "^(parseToolCall|pruneMessages|executeToolsFromStream|executeToolCall)$", detail: "ids" });
await mcp.codebase_memory.trace_path({ project: "ai", qn: "ai.packages.ai.src.generate-text.execute-tools-from-stream.executeToolsFromStream", direction: "outbound", max_depth: 1 });
```

## Verdict
Adopt the two-error-keyed repair hook with cause-chain preservation, visible invalid-part degradation, queue-at-chunk/drain-at-end streaming execution with signed approval pairs, and global-map keep-window pruning. Adapt error types, approval UX, HMAC secrets, and DSL vocabulary to host. Omit the UI-message conversion (`convertToModelMessages`) and RSC bindings unless a target renders chat. Coverage caveat: index generation 2026-08-16 vs HEAD d25cae2 — decisive ranges read at HEAD this session.
