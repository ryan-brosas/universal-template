<!-- capsule-v2 -->
# Code-mode interrupt/resume ladder — how does a sandbox pause mid-program, collect a human decision, and replay without side effects?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** What is the exact protocol that turns a `run` interruption batch into one-at-a-time resumable interrupts with zero double-execution?

## Ledger-verified one-at-a-time resume
**Path/Symbol:** `packages/code-mode/src/run-code-mode.ts` — `prepareContinuation` (:402–485), `toPendingInterruptions` (:530–555), `interruptionIndex` (:557–565), `toolNameForInterruption` (:567–582), `toCodeModeInterrupt` (:584–604), `assertNoDeniedApproval` (:503–521); `packages/code-mode/src/interrupt-continuation.ts` — `assertInterruptMatchesLedger` (:140–163), `continueCodeModeInterrupt` (:47–81).
**Signature:** pending interrupt id = `` `${outerToolCallId}:tool-${requestIndex}:interrupt` ``; tool call id = `` `${outerToolCallId}:tool-${requestIndex}` ``; requestIndex parsed from run's `/^interrupt-(\d+)$/`.
**Data Shape:** signed `CodeModeContinuation {version:2, js, outerToolCallId, toolNames, token, pendingInterruptions[], resolutions[], auth}` (types.ts:96–105).

### Decisive source
```ts
const resolutionIndex = input.continuation.resolutions.length;
const pending = input.continuation.pendingInterruptions[resolutionIndex];
if (pending === undefined ||
    pending.interruptId !== input.interruptResolution.interruptId) {
  throw new CodeModeProtocolError(
    'Interrupt resolution does not match the next pending code-mode interruption.',
```

**Flow:** sandbox tool calls `context.interrupt(payload)` → `run` freezes the whole program and returns ALL interruptions → each is decoded to `{runInterruptionId, interruptId, toolName, toolCallId, input, payload}` (input taken from `arguments[1]` for the missing-tool path, else `arguments[0]`, :548–551) → continuation signed → FIRST pending returned as the public interrupt. Resume: verify signature → re-check `js` byte-equality (:424) AND sorted toolNames equality (:429) → append resolution at index `resolutions.length` → if more pendings remain, RE-SIGN and return the next one WITHOUT running anything; only when the batch is complete does `runner.run({continuation: token, resolutions})` replay — and `assertNoDeniedApproval` then throws for ANY denied approval in the batch before replay (:477). `assertInterruptMatchesLedger` (interrupt-continuation.ts:140–163) makes forged interrupts useless: outerToolCallId + the NEXT pending's id/toolName/input/payload must JSON-match the envelope or it's rejected.
**Invariant:** completed sibling work is never repeated because resolutions accumulate in the SIGNED ledger and `run` replays from its own snapshot — but no tool runs until the FULL batch resolves (test :186–189 pins both mocks uncalled after first approval). Interrupt ids are positional (`outer:tool-2:interrupt`, test :73), so id stability = sort stability. `isCodeModeInterrupt` returns FALSE (not throws) on ledger mismatch (:37–43) so callers can treat tampering as "not an interrupt".
**Probe:** deterministic (repo root): `grep -nF 'resolutions.length' packages/code-mode/src/run-code-mode.ts | head -5` → lines 440/464/473; `grep -nF 'assertNoDeniedApproval' packages/code-mode/src/run-code-mode.ts` → `477:` + `503:`; `grep -nF "toBe('outer:tool-2:interrupt')" packages/code-mode/src/approval-continuation.test.ts` → `73:`; `grep -nF 'isCodeModeApprovalInterrupt(forged)).toBe(false)' packages/code-mode/src/approval-continuation.test.ts` → `143:`; `grep -nF 'expect(first).not.toHaveBeenCalled()' packages/code-mode/src/approval-continuation.test.ts` → `188:`. Direct tests: approval-continuation.test.ts:146–204 (batch one-at-a-time), :125–144 (forged envelope rejected).
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "ai", query: "prepareContinuation assertInterruptMatchesLedger toPendingInterruptions", limit: 4 });` // verified live @9d9a73f: rank#1 assertInterruptMatchesLedger :140-163, rank#2 prepareContinuation :402-485

## Verdict
Adopt the signed-ledger positional resume and full-batch-before-replay rule verbatim; adapt id formats to your own namespace; omit nothing — allowing partial-batch replay or accepting unsigned interrupts are security holes, not simplifications.
