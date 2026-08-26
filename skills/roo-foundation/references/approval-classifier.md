<!-- capsule-v2 -->
# Pure approval classifier — how do you decide approve/deny/ask/timeout for every agent action without scattering policy?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** A porter wires auto-approval ad hoc per tool — how does roo make the whole policy one testable function?

## checkAutoApproval: four-way decision incl. a timed auto-answer closure
**Path/Symbol:** `src/core/auto-approval/index.ts:47-183` (`checkAutoApproval`); result type :37-45; command sub-decision via `getCommandDecision` (`./commands`), MCP allow-lists via `isMcpToolAlwaysAllowed` (`./mcp`), read/write classification via `./tools`.
**Signature:** `checkAutoApproval({state, ask, text, isProtected?}): Promise<{decision:"approve"} | {decision:"deny"} | {decision:"ask"} | {decision:"timeout", timeout, fn}>`.
**Data Shape:** Category flags (`alwaysAllowReadOnly/Write/Mcp/ModeSwitch/Subtasks/Execute/FollowupQuestions`) with qualifiers (outside-workspace, protected files, allowed/denied command lists, per-server/per-tool MCP lists). `updateTodoList` and `skill` tools are unconditionally approved (skills only load user-installed instructions).

### Decisive source
```ts
if (ask === "followup") {
	if (state.alwaysAllowFollowupQuestions === true) {
		const suggestion = (JSON.parse(text || "{}") as FollowUpData).suggest?.[0]
		if (suggestion && typeof state.followupAutoApproveTimeoutMs === "number" && state.followupAutoApproveTimeoutMs > 0) {
			return { decision: "timeout", timeout: state.followupAutoApproveTimeoutMs,
				fn: () => ({ askResponse: "messageResponse", text: suggestion.answer }) };
		} else return { decision: "ask" };
	}
}
```
Short-circuits: non-blocking asks → approve; disabled auto-approval / no state → ask; malformed JSON payloads → ask (never throw).

**Flow:** every blocking ask passes through this ONE classifier before reaching the webview — UI, tests, and policy tuning consume the same decisions. The timeout decision is special: the human gets `followupAutoApproveTimeoutMs` to respond, then `fn()` answers with the FIRST SUGGESTED option instead of hanging forever.
**Invariant:** Approval policy must be a pure classifier over (state, ask-kind, payload) — never embedded in tool execution; parse failures degrade to "ask", never crash.
**Probe:** `src/core/auto-approval/__tests__/AutoApprovalHandler.spec.ts` (limits plane); commands matrix in `src/core/auto-approval/__tests__/commands.spec.ts`. Coverage caveat: index.ts itself has no dedicated spec at this HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "checkAutoApproval followup timeout", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pure four-way classifier + timeout-with-resume-closure. Adapt category flags to your permission model. Omit the VS Code-specific ask kinds. Coverage caveat noted above.
