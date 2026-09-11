<!-- capsule-v2 -->
# Code-mode generic interrupts — requestCodeModeInterrupt and the interrupt discovery ladder over AI SDK results

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How do NON-approval interruptions (auth flows, human input) work, and how does an app find the interrupt inside arbitrary result shapes?

## Typed payload + recursive part unwrapping
**Path/Symbol:** `packages/code-mode/src/host-interrupt.ts` whole (:4–20); `packages/code-mode/src/interrupt-continuation.ts` — `isCodeModeInterrupt` (:18–45), `continueCodeModeInterrupt` (:47–81), `getCodeModeInterrupt` (:83–111), `unwrapCodeModeResult` (:113–121), `readInterruptValue` (:123–138).
**Signature:** `requestCodeModeInterrupt<T extends {kind:string}>(payload): never` — throws the runner's interrupt signal from INSIDE a tool execute; guard = object with non-empty string `kind`.
**Data Shape:** interrupt marker `{type:'code-mode-interrupt', interruptId, toolName, toolCallId, outerToolCallId, input, payload, continuation}`.

### Decisive source
```ts
// readInterruptValue: interrupts hide one level deep in common result envelopes
if (isRecord(value) && (value.type === 'json' || value.type === 'text') && 'value' in value) {
  return readInterruptValue(value.value, continuationSecurity);  // recurse
}
// getCodeModeInterrupt scans result.toolResults[] and result.content[].output
for (const key of ['toolResults', 'content'] as const) { ... }
```

**Flow:** a host tool needing e.g. connection auth calls `experimental_requestCodeModeInterrupt({kind:'connection-auth'})` → `getHostFunctionContext().interrupt(payload)` freezes the program at that bridge call → surfaces as a pending interruption whose payload round-trips verbatim (assertInterruptPayload only demands `kind:string`, run-code-mode.ts:345–357). Resume delivers `{interruptId, payload, resolution}` to the tool's execution options as `codeModeInterrupt`, so the SAME execute call observes its own resolution on replay (`if resume===undefined request else return resolution` idiom, run-compatibility.test.ts:28–59 + approval-continuation.test.ts:206–233 pin it). Discovery: `unwrapCodeModeResult` gives apps a tri-state; `getCodeModeInterrupt` checks the value directly, then `json`/`text` output parts recursively, then `toolResults[]`/`content[]` arrays.
**Invariant:** `requestCodeModeInterrupt` is typed `never` — control never returns to the tool; a porter who awaits past it or swallows the HostFunctionInterruptSignal (rethrown raw at run-code-mode.ts:337) breaks the freeze. Generic payloads are NOT signature-checked for content beyond envelope integrity — the signed continuation covers transport trust, not payload semantics; per-kind validation belongs in the consuming tool.
**Probe:** deterministic (repo root): `grep -nF 'getHostFunctionContext().interrupt' packages/code-mode/src/host-interrupt.ts` → `19:`; `grep -nF "'toolResults', 'content'" packages/code-mode/src/interrupt-continuation.ts` → `95:`; `grep -nF "value.type === 'json' || value.type === 'text'" packages/code-mode/src/interrupt-continuation.ts` → `132:`; `grep -nF 'assertInterruptMatchesLedger' packages/code-mode/src/interrupt-continuation.ts` → lines 38/67/140. Direct tests: run-compatibility.test.ts:36/:69 (request idiom), approval-continuation.test.ts:206–233 (generic kind end-to-end).
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "ai", query: "getCodeModeInterrupt unwrapCodeModeResult readInterruptValue", limit: 3 });` // verified live @9d9a73f via assertInterruptMatchesLedger :140-163 anchor family (interrupt-continuation.ts module)

## Verdict
Adopt the never-returning request helper + options-carried resolution idiom and the two-level discovery scan; adapt envelope keys to your framework's result types; omit nothing.
