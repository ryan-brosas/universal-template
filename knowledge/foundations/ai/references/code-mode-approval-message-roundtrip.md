<!-- capsule-v2 -->
# Code-mode approval message round-trip — building assistant requests and scanning tool messages for human decisions

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How does an approval interrupt become model-message parts, and how is the human's answer recovered from history?

## Synthetic assistant turn + reverse scan
**Path/Symbol:** `packages/code-mode/src/approval-continuation.ts` — `toCodeModeApprovalMessages` (:67–88), `getCodeModeApprovalResponse` (:90–115); response shape `assertCodeModeApprovalResponse` (approval.ts:18–35).
**Signature:** request part `{type:'tool-approval-request', approvalId, toolCallId}`; response part `{type:'tool-approval-response', approvalId, approved:boolean, reason?}`; `approvalId === interrupt.interruptId`.
**Data Shape:** one synthetic assistant message carrying BOTH the original `tool-call` part AND the approval request — so replayed histories stay a valid ModelMessage sequence.

### Decisive source
```ts
for (let index = messages.length - 1; index >= 0; index--) {
  const message = messages[index];
  if (message?.role !== 'tool') continue;
  for (const part of message.content) {
    if (part.type === 'tool-approval-response' &&
        part.approvalId === interrupt.interruptId &&
        typeof part.approved === 'boolean' && ...) return {...};
  }
}
return undefined;
```

**Flow:** UI receives interrupt → renders from toCodeModeApprovalMessages (assistant tool-call + approval-request pair) → human decision appended by the framework as a tool-role message containing tool-approval-response → app recovers it via getCodeModeApprovalResponse (NEWEST first) → passes to continueCodeModeApproval which asserts id match against the pending interrupt (:44–48) before routing into the generic resume ladder. Malformed responses (non-bool approved, non-string reason) throw ProtocolError at assert time, never silently coerce.
**Invariant:** recovery scans BACKWARD and returns the FIRST match — later duplicates win, matching "most recent human decision" semantics. A porter who scans forward replays stale denials after newer approvals. The undefined return (no decision yet) is a valid tri-state, not an error.
**Probe:** deterministic (repo root): `grep -nF 'approvalId !== interrupt.interruptId' packages/code-mode/src/approval-continuation.ts` → `44:`; `grep -nF 'tool-approval-request' packages/code-mode/src/approval-continuation.ts` → `81:`; `grep -nF 'messages.length - 1' packages/code-mode/src/approval-continuation.ts` → `94:`; direct-test anchor: approval-continuation.test.ts:121 (`rejects.toBeInstanceOf(CodeModeToolApprovalDeniedError)`).
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "ai", query: "continueCodeModeApproval getCodeModeApprovalResponse", limit: 3 });` // verified family live @9d9a73f via approval-continuation.test anchors (module nodes indexed)

## Verdict
Adopt newest-first recovery and strict id-matching; adapt part type strings to your message protocol (keep them stable across versions or old histories stop resolving); omit nothing.
