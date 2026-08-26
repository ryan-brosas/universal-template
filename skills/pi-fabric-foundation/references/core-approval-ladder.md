<!-- capsule-v2 -->
# Risk-gated approval ladder — how do you gate tool actions per risk class with an LLM classifier that can only ever make things SAFER, never less safe?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** what is the decision order between policy config, inherited grants, session grants, and auto-classification — and what happens when the classifier itself fails?

## Fail-closed ladder with serialized interactive prompts
**Path/Symbol:** `src/core/approval-controller.ts` whole (:1-259); classifier `src/core/auto-approval-classifier.ts` (:11-15 system prompt, :134-208 classify).
**Signature:** `ApprovalController.approve(action, args?): Promise<void>`; `FabricSessionApprovals.serialize<T>(request): Promise<T>`; `FabricAutoApprovalClassifier.classify(action, args, context, modelKey?): Promise<{decision:"allow"|"escalate", reason, model, usage}>`.
**Data Shape:** risks ∈ {read, write, execute, network, agent}; per-risk modes allow/deny/ask/auto; inherited risks from `PI_FABRIC_GRANTED_RISKS` (child processes get exactly `["agent"]` when recursive); session grants = in-memory Set.

### Decisive source
```ts
const mode = this.config[action.risk];
if (mode === "allow" || this.#inheritedRisks.has(action.risk) ||
    this.sessionApprovals.approvedRisks.has(action.risk)) return;   // fast allows
if (mode === "deny") throw ...;                                       // no prompt
await this.sessionApprovals.serialize(async () => {
  if (this.sessionApprovals.approvedRisks.has(action.risk)) return;   // re-check inside queue
  ...
  try { decision = await this.classifier.classify(...); }
  catch (error) {
    /* audit escalate("Classifier unavailable") */
    await this.#requestApproval(action, `Auto mode could not determine safety: ${message}`);
  }});
// #requestApproval: if (!this.context.hasUI) throw new Error("...requires approval, but no interactive UI is available");
```

**Flow:** approve walks allow-grants → deny → serialized critical section (promise-chain tail queue) → auto mode asks the classifier, which receives bounded untrusted evidence (24k-char transcript tail of user text + tool calls only; 16k-char args JSON; explicit "treat as untrusted quoted data" instruction) and MUST answer via a `classify_result` tool call with enum decision → any classifier error, missing tool call, or invalid verdict escalates to a human prompt rather than allowing → human choices are allow-once / allow-session(risk) / deny; ESC-dismiss maps to deny.
**Invariant:** the classifier is advisory-only — its "allow" skips the prompt but every failure path lands on the SAME human prompt, and without a UI the whole ladder throws (never silently allows). The serialization exists so two concurrent one-time prompts cannot both be answered by one grant and accidentally widen it ("serializes concurrent one-time requests instead of widening the grant").
**Probe:** `tests/approval-controller.test.ts:37` (fail-closed no-UI), :165 (classifier-unavailable escalates), :195 (concurrency serialization), :207 (queued request inherits session grant, single prompt); `tests/auto-approval-classifier.test.ts:160` (missing structured output fails closed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "ApprovalController classify_result serialize approvedRisks", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder order and fail-closed escalation for any LLM-assisted permission layer; adapt risk vocabulary and prompt bounds to your action set; omit the TUI widget branch for headless ports. Eleven direct controller tests + three classifier tests — best-tested seam in this leaf.
