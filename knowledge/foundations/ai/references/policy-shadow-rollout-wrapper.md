<!-- capsule-v2 -->
# Shadow policy rollout — how do you roll out a deny-policy without letting it deny anything until you trust it?

**Source:** Vercel AI SDK (inspo/ai) Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai` (MCP not connected this session — direct source read fallback). **Question:** how does a policy wrapper evaluate and audit every tool call while guaranteeing the SDK acts as approved until an explicit `enforce` flip?

## shadow — observe-then-enforce approval wrapper
**Path/Symbol:** `packages/policy-opa/src/shadow.ts:74` (`export function shadow<...>`); event type `PolicyDecisionEvent` :29–52; approval-arm dispatch `evaluateApproval` :129–170; decision normalization `normalizePolicyDecision` :172–189.

**Signature:**
```ts
function shadow<TOOLS extends Record<string, Tool>, RUNTIME_CONTEXT>(
  approval: ToolApprovalConfiguration<TOOLS & ToolSet, RUNTIME_CONTEXT>,
  opts?: { enforce?: boolean; onDecision?: (event: PolicyDecisionEvent) => void | Promise<void> },
): ToolApprovalConfiguration<TOOLS & ToolSet, RUNTIME_CONTEXT>;
```

**Data Shape:** `PolicyDecisionEvent = { toolCall: {toolName, toolCallId, input}, decision: PolicyDecision, enforced: boolean, effective: PolicyDecision, timestamp: ISO-8601 }`. `decision` is what the wrapped policy said (normalized to the object form); `effective` is what the SDK is told — identical when `enforce`, otherwise always `{type:'approved'}`.

### Decisive source
```ts
const raw = await evaluateApproval(approval, args);
const decision = normalizePolicyDecision(raw);
const effective: PolicyDecision = enforce ? decision : { type: 'approved' };
if (onDecision) {
  const event: PolicyDecisionEvent = { toolCall: {...}, decision, enforced: enforce, effective, timestamp: new Date().toISOString() };
  // Fire-and-forget so a slow or throwing logger does not block the model.
  void (async () => { try { await onDecision(event); } catch { /* enforcement must not depend on telemetry */ } })();
}
return effective;
```

**Flow:** tool call → `evaluateApproval` resolves the wrapped approval (generic function called with full args; per-tool map read through `Object.prototype.hasOwnProperty.call` so a tool named `constructor`/`toString`/`valueOf` is unconfigured, never an inherited prototype value :144–148) → `normalizePolicyDecision` maps string statuses to the object form, unknown shapes to `not-applicable` → `effective` chosen by the `enforce` latch → event emitted fire-and-forget → `effective` returned to the SDK.

**Invariant:** the return value is computed BEFORE the event fires and the event callback runs detached with a swallowing catch — a throwing, slow, or never-resolving logger can never change, delay, or abort the decision the SDK acts on. Audit completeness is separate from enforcement: approve decisions are reported too (full audit trail), and `decision !== effective` is exactly the set of calls shadow mode let through that enforce mode would have blocked or escalated.

**Probe:** `packages/policy-opa/src/shadow.test.ts` (10 cases): default shadow returns `{type:'approved'}` while the event records `{type:'denied'}` (:31–57); `enforce:true` returns the real decision (:59–78); per-tool map with an unlisted tool reports `not-applicable` (:114–136); literal `constructor`/`toString`/`valueOf` tool names all report `not-applicable` (:138–161); a throwing `onDecision` still resolves the approval (:163–183); a never-resolving `onDecision` leaves the wrapper under 50ms (:197–212).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "shadow PolicyDecisionEvent enforce onDecision", limit: 10, fields: ["signature", "name", "file"] });
```
Expected rank: shadow.ts `shadow` :74, `PolicyDecisionEvent` :29, then shadow.test.ts cases.

## Verdict
Adopt the shadow→enforce rollout ladder and the detached-logger invariant for any policy/permission rollout; adapt the event shape to your telemetry pipeline; omit the SDK-specific `ToolApprovalConfiguration` typing if your host has a different approval hook. Coverage caveat: none — the kernel is fully test-pinned (10 cases).
