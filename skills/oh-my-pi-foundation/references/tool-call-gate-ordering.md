<!-- capsule-v2 -->
# Tool-call gate ordering — how do you sequence interceptor hooks, policy, and approval so a hook cannot sneak a revised input past approval?

**Source:** oh-my-pi (MIT) `main@2b66ee69f249`; Codebase Memory `oh-my-pi`. **Question:** A pre-execution hook may REPLACE the tool input; where must the approval gate re-resolve so "approve one thing, run another" is impossible?

## Connected graph-selected seam
**Path/Symbol:** `packages/coding-agent/src/extensibility/extensions/wrapper.ts:ExtensionToolWrapper.execute` (:171-415), helpers `toolEventArgs`/`computerSafetyChecks` (:105-124); dedupe markers `runner.ts` :511-536.
**Signature:** `execute(toolCallId, params, signal?, onUpdate?, context?): Promise<AgentToolResult>` — wrapper implements AgentTool and forwards via applyToolProxy.
**Data Shape:** effectiveParams starts as params; hook result `{ block?, reason?, input? }`; approval resolution `{ policy: "deny"|"prompt"|..., policyKey, reason, override? }`.

### Decisive source
```ts
// Pre-resolve deny on the ORIGINAL input: an already-denied tool never emits tool_call...
const preResolved = resolveApproval(this.tool, approvalArgs(params, context), approvalMode, userPolicies);
if (preResolved.policy === "deny") throw new Error(`Tool "..." is blocked by user policy...`);
// 1. emit tool_call BEFORE the approval gate -> approval resolves against the input that
//    actually executes, closing the "approve one thing, run another" gap
if (!loopEmittedToolCall && this.runner.hasHandlers("tool_call")) { ... }
// 2. FULL gate against the possibly REVISED input:
const resolved = resolveApproval(this.tool, approvalArgs(effectiveParams, context), approvalMode, userPolicies);
// The xdev bypass only holds while the input is EXACTLY what the outer gate approved:
const xdevBypass = context?.xdevApproved === true && effectiveParams === params;
// Hook-supplied input is handler-owned raw input, not re-normalized; computer tools are exempt
// because their event input is a synthetic {actions,pendingSafetyChecks} view, not real params:
if (callResult?.input !== undefined && context?.toolCall?.providerMetadata?.type !== "computer") {
	effectiveParams = callResult.input as typeof params;
}
```
**Flow:** deny-short-circuit on original -> consume loop marker (`markToolCallEmitted` keyed `${toolCallId}:${toolName}`, bounded FIFO 512 for calls that never execute) -> emit tool_call unless already emitted by the agent loop at arg-prep -> block throws -> revision accepted -> full approval re-resolution + provider safety checks on revised input -> execute with onUpdate forwarded -> tool_result emission chain. Error path still emits tool_result(isError:true) then RE-THROWS the original error.
**Invariant:** approval prompt text, policy resolution, and safety checks all observe `effectiveParams`; any revision voids prior bypass approvals (identity check, not deep-equal). Simpler twin `hooks/tool-wrapper.ts:HookToolWrapper` (:28-124): no approval ladder, ANY hook error blocks execution (fail-safe).
**Probe:** direct-test seam: `test/extensibility/tool-proxy.test.ts` pins wrapper forwarding; anchor-greps at pin: "loopEmittedToolCall" :184, "xdevBypass = context?.xdevApproved === true && effectiveParams === params" :264.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "ExtensionToolWrapper", limit: 10 });
```

## Verdict
Adopt: three-phase order (pre-deny, revise, re-approve-on-revised) + identity-voided bypasses + emit-once markers. Adapt: your own policy resolver in place of resolveApproval; keep the computer-tool synthetic-input exemption if you have equivalent synthetic views. Omit: xd:// device-dispatch specifics.