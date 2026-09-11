<!-- capsule-v2 -->
# Harness builtin-approval replay split — why did an approved builtin tool's real result vanish?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** After approving a provider-executed (builtin) tool, the continued stream must suppress the REPLAYED call but still emit the genuine result — how are those two tracking sets separated?

## Two settled-id sets, two replay filters
**Path/Symbol:** `packages/harness/src/agent/internal/run-prompt.ts` — `settledHostToolCallIds` (:261) vs `settledBuiltinApprovalToolCallIds` (:262); approval settle branch (:486–508); replay filter (:657–666).
**Signature:** internal Sets of toolCallIds; filter predicates keyed on displayValue.type.
**Data Shape:** Builtin set records ids at approval time; host set records ids only when a LOCAL tool outcome exists.

### Decisive source
```ts
settledBuiltinApprovalToolCallIds.add(approval.toolCallId);   // builtin branch ONLY
...
settledHostToolCallIds.add(approval.toolCallId);              // non-builtin path
if (!continuation.approvalResponse.approved) { /* synthesize denial result */ }
...
const settledBuiltinApprovalReplay =
  (displayValue.type === 'tool-call' || displayValue.type === 'tool-approval-request')
  && settledBuiltinApprovalToolCallIds.has(displayValue.toolCallId);
if (settledHostInputReplay || settledBuiltinApprovalReplay) continue;  // suppress INPUT events only
```

**Flow:** before #19160, settling ANY approval added its id to `settledHostToolCallIds`, whose replay filter also matched `tool-result`/`tool-error` display values — so the builtin's first REAL outcome arriving on the continued stream was discarded as "already settled". Now builtin approvals mark ONLY the dedicated set, whose filter matches exclusively input-event types (`tool-call`, `tool-approval-request`); genuine `tool-result`/`tool-error` pass through exactly once.
**Invariant:** Replay suppression must distinguish "input already seen" from "outcome already seen" — for builtins, approval settles the QUESTION, not the RESULT. Host tools keep the old single-set behavior because their outcomes are produced locally.
**Probe:** deterministic probes: `grep -c "settledBuiltinApprovalToolCallIds.add" packages/harness/src/agent/internal/run-prompt.ts` → `1`; `grep -c settledBuiltinApprovalReplay …ts` → `2`. Direct tests: `run-prompt.test.ts` +99-line suite ("emits the provider result after approved pending builtin tool execution").
**Retrieve:** verified live @9d9a73f — search_graph `settledBuiltinApprovalToolCallIds run-prompt harness` rank#1 `runPrompt :68-1076`.

## Verdict
Adopt the two-set separation with type-scoped filter predicates; adapt naming; companion Claude-Code usage-precedence flip in the same family: `usage: pendingStepUsage ?? harnessUsage` (#19070 — per-call usage must win over harness aggregate when both exist mid-step).
