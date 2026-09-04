<!-- capsule-v2 -->
# Auto-approval budget windows — how do you cap runaway request/cost spend while letting the user extend it in place?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** A porter's auto-approved agent burns unlimited API budget — how does roo meter it and reset without restarting the task?

## Message-index watermark resets on approval
**Path/Symbol:** `src/core/auto-approval/AutoApprovalHandler.ts:13-155` (whole class).
**Signature:** `checkAutoApprovalLimits(state, messages, askForApproval): Promise<{shouldProceed, requiresApproval, approvalType?: "requests"|"cost", approvalCount?}>`.
**Data Shape:** Two meters computed over `messages.slice(lastResetMessageIndex)`: requests = count of `say:"api_req_started"` messages + 1 (the current request); cost = `getApiMetrics(messagesAfterReset).totalCost` compared with EPSILON 0.0001 for float safety. Limits default to Infinity.

### Decisive source
```ts
if (this.consecutiveAutoApprovedRequestsCount > maxRequests) {
	const { response } = await askForApproval("auto_approval_max_req_reached",
		JSON.stringify({ count: maxRequests, type: "requests" }));
	if (response === "yesButtonClicked") {
		this.lastResetMessageIndex = messages.length;   // future counts only include NEW messages
		return { shouldProceed: true, requiresApproval: true, ... };
	}
	return { shouldProceed: false, requiresApproval: true, ... };
}
```

**Flow:** before proceeding → check request limit FIRST, then cost limit (`checkRequestLimit` result short-circuits) → limit exceeded → blocking ask → user approves ⇒ record the current message count as the new watermark (budget window restarts from now); user rejects ⇒ shouldProceed:false. Order pinned by spec ("should check request limit before cost limit").
**Invariant:** Metering must be window-scoped, not lifetime: an approved extension starts a fresh window at the current message index, so a long task can continue in bounded increments without ever double-counting pre-approval spend.
**Probe:** `src/core/auto-approval/__tests__/AutoApprovalHandler.spec.ts` (:37 ordering, :89/:109 ask + reset-on-approve, :182 "should handle floating-point precision correctly").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "AutoApprovalHandler lastResetMessageIndex allowedMaxCost", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the watermark-window pattern for both request-count and cost budgets. Adapt metrics extraction to your message log. Omit the cost meter if you have no pricing data. Coverage caveat: none.
