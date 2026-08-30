<!-- capsule-v2 -->
# Approval round-trip — how do approvals issued in a previous run get collected from history, re-validated server-side, and executed exactly once?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** When a client replays message history with `tool-approval-response` parts attached, what must a porter check before executing those tools — and why do prototype-pollution lookups matter here?

## collectToolApprovals → validateApprovedToolApprovals (→ resolveToolApproval)
**Path/Symbol:** `packages/ai/src/generate-text/collect-tool-approvals.ts:collectToolApprovals` (:23–134); `validate-tool-approvals.ts:validateApprovedToolApprovals` (:23–123); `resolve-tool-approval.ts:resolveToolApproval` (:22–127).
**Signature:** `collectToolApprovals({ messages }): { approvedToolApprovals, deniedToolApprovals }` (sync); `async validateApprovedToolApprovals({ approvedToolApprovals, tools, toolApproval, messages, toolsContext, runtimeContext, toolApprovalSecret }): Promise<{ approvedToolApprovals, deniedToolApprovals }>`; `async resolveToolApproval({ tools, toolCall, toolApproval, messages, toolsContext, runtimeContext }): Promise<Exclude<ToolApprovalStatus, string|undefined>>`.
**Data Shape:** `CollectedToolApprovals = { approvalRequest, approvalResponse, toolCall, existingToolResult? }`. All three id lookup maps in the collector are `Object.create(null)` — prototype-less by intent. Status union: `{type:'user-approval'} | {type:'approved', reason?} | {type:'denied', reason?} | {type:'not-applicable'}`.

### Decisive source
```ts
// collect-tool-approvals.ts :31-38 + :42-48 comment:
const lastMessage = messages.at(-1);
if (lastMessage?.role != 'tool') return { approvedToolApprovals: [], deniedToolApprovals: [] };
// These maps are keyed by client-supplied ids (`toolCallId`, `approvalId`)
// from the message history. Using `Object.create(null)` gives them no
// prototype, so an id that matches an inherited object property (e.g.
// `toString`, `constructor`, `__proto__`) is treated as absent ...
// validate-tool-approvals.ts :51-55 + :84-96:
// Look up the tool by own property only: `toolName` comes from
// client-supplied history, so a name matching an inherited object property
// (e.g. `constructor`, `toString`) must resolve to "no such tool" rather
// than a prototype value that would silently skip input validation below.
const tool = getOwn(tools, toolCall.toolName);
if (isExecutableTool(tool) && tool.inputSchema != null) {
  const validation = await safeValidateTypes({ value: toolCall.input, schema: asSchema(tool.inputSchema) });
  if (!validation.success) throw new InvalidToolInputError({ ... });   // THROW, not deny
}
// already-resulted skip (:102-109):
if (existingToolResult != null &&
    (approvalResponse.approved || existingToolResult.output.type !== 'execution-denied')) continue;
```
Policy re-check: `resolveToolApproval` runs AGAIN on replay with precedence user-config (`function` form first, then per-tool map) > tool-defined `needsApproval`; a denial during revalidation moves the approval to `deniedToolApprovals` carrying the policy reason (:108–116).

**Flow:** generateText pre-loop: collect (last-tool-message-only scan; unknown approvalId → `InvalidToolApprovalError` throw; missing toolCall → `ToolCallNotFoundForApprovalError` throw; approved-with-existing-non-denial-result or denied-with-result → skip as already processed) → filter OUT provider-executed calls → validate each: HMAC signature verify when secret configured (missing/invalid → `InvalidToolApprovalSignatureError` throw) → input schema validation → policy re-run → execute approved + synthesize execution-denied results for resultless denials into one tool message. In-step: same `resolveToolApproval` classifies fresh calls; `not-applicable` returns BEFORE `generateId()` so approval-id sequences stay deterministic (:generate-text.ts 1152–1166).
**Invariant:** Client-supplied approval state is UNTRUSTED: signature → schema → policy must all re-pass server-side before execution, and failures throw rather than silently denying (a forged input must never become a quiet no-op). Ids and tool names are attacker-controlled strings — every lookup is own-property/prototype-less.
**Probe:** `packages/ai/src/generate-text/validate-tool-approvals.test.ts` — forged extra property (:83), policy denies replay (:110/:11222 e2e), signature missing/tampered/no-secret forward-compat (:292/:320/:369); `collect-tool-approvals.test.ts` — unknown approvalId (:347), missing tool call (:384), already-resulted skips (:113/:300).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "validateApprovedToolApprovals collectToolApprovals resolveToolApproval", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the three-gate re-validation order (HMAC → input schema → approval policy) with throw-on-forgery, prototype-less id maps, last-message-only collection, and the already-resulted skip rule. Adapt status names and error classes to host; omit HMAC signing if approvals never cross a trust boundary. Coverage caveat: best-effort index; excerpts read directly at HEAD.
