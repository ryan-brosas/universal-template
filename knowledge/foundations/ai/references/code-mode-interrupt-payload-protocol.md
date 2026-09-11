<!-- capsule-v2 -->
# Code-mode interrupt payload protocol — kind-typed payloads and the approval-kind discriminator

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How are interruption payloads typed, validated, and discriminated between approvals and app-specific kinds?

## Minimal envelope + kind dispatch
**Path/Symbol:** `packages/code-mode/src/approval.ts` — kind constant :9–10, `isCodeModeApprovalInterruptPayload` (:12–16), response/resolution asserts (:18–60); `packages/code-mode/src/run-code-mode.ts` — `assertInterruptPayload` (:345–357); resume discrimination :286–306.
**Signature:** envelope contract = object, not array, with string `kind`; approval kind = `'ai-sdk-code-mode/tool-approval'`; resolution = `{approved:boolean, reason?}` normalized (undefined reason dropped).
**Data Shape:** `CodeModeInterruptPayload {kind:string, [k:string]:unknown}` — open record; only `kind` is contractual.

### Decisive source
```ts
if (context.resume !== undefined) {
  const payload = assertInterruptPayload(context.resume.payload);
  if (isCodeModeApprovalInterruptPayload(payload)) {
    const decision = normalizeApprovalResolution(context.resume.resolution);
    if (!decision.approved)
      throw new CodeModeToolApprovalDeniedError(toolName, toolInput, toolCallId, decision.reason);
    skipApproval = true;                       // approved-once never re-prompts
  } else {
    codeModeInterrupt = { interruptId: `${toolCallId}:interrupt`,
                          payload, resolution: context.resume.resolution };
  }
}
```

**Flow:** on replay each bridge call checks whether ITS pending interruption was the one resolved: approval kinds consume the decision (denied ⇒ typed throw even mid-replay; approved ⇒ skip the gate so execute proceeds without re-prompting) while generic kinds re-enter the tool as `codeModeInterrupt` execution context for the idiom `if (resume===undefined) request else return resolution`. Payload content beyond `kind` is never validated centrally — malformed app payloads are the consuming tool's problem, keeping the kernel kind-agnostic. The same assert runs when DECODING run interruptions into the signed ledger (:552), so a broken payload can't enter a continuation.
**Invariant:** exactly ONE resolution is consumed per resume step (positional ledger), so an approval decision can never leak onto a different tool's interruption. A porter who validates payload CONTENT in the kernel couples it to every consumer's schema; one who forgets `skipApproval` creates infinite prompt loops on replay.
**Probe:** deterministic (repo root): `grep -nF 'isCodeModeApprovalInterruptPayload(payload)' packages/code-mode/src/run-code-mode.ts` → `288:`; `grep -nF 'skipApproval = true' packages/code-mode/src/run-code-mode.ts` → `298:`; `grep -nF 'normalizeApprovalResolution' packages/code-mode/src/run-code-mode.ts` → lines 15(import)/289/493/511; `grep -cF "payload.kind === CODE_MODE_TOOL_APPROVAL_KIND" packages/code-mode/src/approval.ts` → `1`. Direct tests: approval-continuation.test.ts:70/:108 (`isCodeModeApprovalInterrupt(pending)===true`).
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "ai", query: "CodeModeInterruptPayload normalizeApprovalResolution", limit: 3 });` // verified family live @9d9a73f: approval.ts/types.ts resolve line-exact under project ai

## Verdict
Adopt kind-minimal envelopes with central transport validation + consumer semantic validation; adapt kind strings to your registry; omit nothing — skip-once-approved and positional consumption are correctness features.
