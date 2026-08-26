<!-- capsule-v2 -->
# Tool execution funnel — what must happen between a model-emitted tool_use block and tool.call()?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Which ordered gates (alias resolution → schema validation → hook input mutation → permission decision → call-input convergence) does one tool invocation pass through, and which invariants keep the transcript byte-stable across them?

## runToolUse + checkPermissionsAndCallTool
**Path/Symbol:** `src/services/tools/toolExecution.ts` — `runToolUse` (:337-490), `checkPermissionsAndCallTool` (:599-1745), `streamedCheckPermissionsAndCallTool` (:492-570), `classifyToolError` (:150-171), `buildSchemaNotSentHint` (:578-597).
**Signature:** `runToolUse(toolUse: ToolUseBlock, assistantMessage, canUseTool, toolUseContext): AsyncGenerator<MessageUpdateLazy, void>` where `MessageUpdateLazy = { message: Message; contextModifier?: { toolUseID; modifyContext } }`.
**Data Shape:** Every terminal path returns exactly one user message whose content carries `{type:'tool_result', tool_use_id}` — error paths set `is_error: true`; success paths append accept-feedback text blocks AFTER the result block. Progress events travel out-of-band via callback into a `Stream`, never as generator yields of results.

### Decisive source
```ts
// :347-356 deprecated-name fallback — ALIAS ONLY
if (!tool) {
  const fallbackTool = findToolByName(getAllBaseTools(), toolName)
  // Only use fallback if the tool was found via alias (deprecated name)
  if (fallbackTool && fallbackTool.aliases?.includes(toolName)) {
    tool = fallbackTool
  }
}
// :775-793 backfill clone — hooks/canUseTool see expanded fields, call() does NOT
// Backfill legacy/derived fields on a shallow clone so hooks/canUseTool see
// them without affecting tool.call(). ... changing it alters the serialized
// is intentional and should reach call().
let callInput = processedInput
const backfilledClone = tool.backfillObservableInput ? ({...processedInput}) : null
// :1203-1205 convergence — only a REAL replacement reaches call()
} else if (processedInput !== backfilledClone) {
  callInput = processedInput
}
```

**Flow:** unknown-name → error result (return) → alias-only deprecated fallback → aborted-signal pre-check emits CANCEL result → zod `safeParse` gate (+ `buildSchemaNotSentHint` when a deferred tool's schema was never sent — hint tells the model to load via ToolSearch first) → per-tool `validateInput` gate → Bash-only speculative classifier warm-up (started here so it overlaps hooks/permission waits) → `_simulatedSedEdit` stripped from model-supplied input (defense-in-depth; field is permission-system-internal) → PreToolUse hooks stream (`message`/`hookPermissionResult`/`hookUpdatedInput`/`preventContinuation`/`stopReason`/`additionalContext`/`stop` variants) → `resolveHookPermissionDecision` (hook allow ≠ rule bypass; deny rules still apply) → non-allow ⇒ rejection result with images at TOP LEVEL (tool_result with is_error rejects non-text content inside itself) + PermissionDenied-hook retry ladder for auto-mode classifier denials → allow ⇒ `updatedInput` adopted → tool.call with progress relay → PostToolUse hooks (MCP tools get their result added only AFTER hooks so `updatedMCPToolOutput` can replace it; non-MCP results are added BEFORE hooks from the pre-mapped block) → structured_output attachment → newMessages → deferred stop attachment if preventContinuation was set earlier → finally: session activity stopped + toolDecisions map cleaned.

**Invariant:** (1) The backfill-clone identity dance exists to keep serialized transcripts/VCR hashes stable — file tools overwrite `file_path` with an expandPath'd clone for observers but `call()` receives the model's original string unless a hook/permission genuinely replaced the object (identity comparison `processedInput !== callInput`, not deep equality). (2) Hook 'allow' never bypasses settings.json deny rules — rule check re-runs inside resolveHookPermissionDecision (inc-4788). (3) Reject-path image blocks go beside, never inside, the is_error tool_result. (4) classifyToolError prefers TelemetrySafeError.telemetryMessage → errno code (`Error:ENOENT`) → stable `.name` → literal `'Error'`, because minified builds mangle constructor names into 3-char identifiers. (5) MCP dual-phase mapping: non-MCP addToolResult runs pre-hooks with the already-mapped block; MCP runs post-hooks remapping from (possibly replaced) toolOutput.

**Probe:** coverage caveat — no upstream tests cover this file (`tests/` holds shell scripts only). Deterministic pins: `grep -n "Only use fallback if the tool was found via alias" src/services/tools/toolExecution.ts` (:352); `grep -n "VCR fixture hashes" src/services/tools/toolExecution.ts` :780); `grep -n "rejects non-text with is_error" src/services/tools/toolExecution.ts` (:1039); graph resolves runToolUse + checkPermissionsAndCallTool + streamedCheckPermissionsAndCallTool line-exact under `src.services.tools.toolExecution`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "runToolUse checkPermissionsAndCallTool permission funnel", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the gate ORDER (validate → hooks → rules → dialog → call) and the two-transcript-stability tricks (backfill clone + top-level reject images); adapt the specific telemetry vocabularies; omit the ant-only speculative-classifier warm-up and USER_TYPE-gated UI summaries unless your host has equivalent surfaces. Porting trap: reusing the backfilled clone as call input silently changes every file_path-bearing tool result string and invalidates recorded fixtures.
