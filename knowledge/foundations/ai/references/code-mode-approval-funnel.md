<!-- capsule-v2 -->
# Code-mode approval funnel — how does a needsApproval tool get gated, interrupted, or denied inside a sandboxed program?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** What is the full decision path for `needsApproval` — callback mode, interrupt mode, and resume-time enforcement?

## Three-outcome gate before execute
**Path/Symbol:** `packages/code-mode/src/tool-invocation.ts` — `invokeHostTool` (:32–167), approval block :90–150, `requiresApproval` (:169–181); `packages/code-mode/src/approval.ts` — kind constant :9–16, `assertCodeModeApprovalResponse` (:18–35), `normalizeApprovalResolution` (:37–60); `packages/code-mode/src/approval-continuation.ts` — `continueCodeModeApproval` (:30–65), `toCodeModeApprovalMessages` (:67–88), `getCodeModeApprovalResponse` (:90–115).
**Signature:** payload kind `'ai-sdk-code-mode/tool-approval'` (approval.ts:10); callback returns `'approved' | 'denied' | {approved, reason?}`; interrupt payload = `{kind: CODE_MODE_TOOL_APPROVAL_KIND}`.
**Data Shape:** approval responses ride model messages as `tool-approval-request`/`tool-approval-response` parts keyed by `approvalId === interrupt.interruptId`.

### Decisive source
```ts
if (codeModeOptions.approval?.mode === 'interrupt') {
  return { type: 'interrupted', toolName, input: validation.value,
           toolCallId, payload: { kind: CODE_MODE_TOOL_APPROVAL_KIND } };
}
const approval = await raceAgainstAbort(Promise.resolve(
  codeModeOptions.approval?.onApprovalRequired?.({toolName, input, toolCallId}), ...));
if (approval === undefined)
  throw new CodeModeToolApprovalRequiredError(toolName, validation.value, toolCallId);
```

**Flow:** needsApproval (bool or async fn) evaluated → interrupt mode returns the typed payload so the WHOLE sandbox freezes (resume marks it approved and sets `skipApproval`, run-code-mode.ts:286–298) → callback mode awaits the host decision; `undefined` (no callback) = ApprovalRequired error thrown WITHOUT execute; malformed decisions/reasons = ProtocolError; denied = ApprovalDeniedError with reason. Resume-time double enforcement: even if the client approves, `assertNoDeniedApproval` re-checks EVERY batched approval on final replay and throws Denied for any false (:503–521) — denial survives replays. Message helpers let UIs round-trip: build assistant tool-call + approval-request from an interrupt; scan messages BACKWARDS (newest first) for the matching response.
**Invariant:** approval happens AFTER schema validation but BEFORE execute, and the execute mock staying uncalled is the pinned behavior in every test. A porter who treats a missing callback as "allow" instead of ApprovalRequired turns sandboxed code into an approval bypass; one who doesn't persist denial into replay lets a second continue slip a denied call through.
**Probe:** deterministic (repo root): `grep -nF "approval?.mode === 'interrupt'" packages/code-mode/src/tool-invocation.ts` → `98:`; `grep -nF 'CODE_MODE_TOOL_APPROVAL_KIND' packages/code-mode/src/tool-invocation.ts` → lines `2:`+`104:`; `grep -nF "approval === undefined" packages/code-mode/src/tool-invocation.ts` → `118:`; `grep -nF 'ai-sdk-code-mode/tool-approval' packages/code-mode/src/approval.ts packages/code-mode/src/types.ts` → approval.ts:10 + types.ts:153; `grep -cF 'it(' packages/code-mode/src/approval-continuation.test.ts` → `6`. Direct tests: exceptions.test.ts:49–65 (no execute when approval required), approval-continuation.test.ts:94–123 (denied ⇒ instance of CodeModeToolApprovalDeniedError).
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "ai", query: "invokeHostTool raceAgainstAbort needsApproval", limit: 3 });` // verified live @9d9a73f: rank#1 invokeHostTool :32-167, rank#2 raceAgainstAbort :228-255

## Verdict
Adopt validate→approve→execute ordering with undefined-callback-means-deny and replay-time denial persistence; adapt the message-part shapes to your UI protocol; omit nothing.
