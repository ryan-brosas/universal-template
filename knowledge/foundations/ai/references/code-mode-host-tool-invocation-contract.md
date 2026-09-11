<!-- capsule-v2 -->
# Code-mode host-tool invocation contract — validation, abort racing, and async-iterable draining at the sandbox boundary

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** What must hold for EVERY host tool call made from sandboxed code, regardless of the tool?

## Uniform invocation pipeline
**Path/Symbol:** `packages/code-mode/src/tool-invocation.ts` — `invokeHostTool` (:32–167), `validateToolInput` (:183–194), `executeHostTool` (:196–215), `isAsyncIterable` (:217–226), `raceAgainstAbort` (:228–255), `throwIfAborted` (:257–261), `abortReason` (:263–268).
**Signature:** result union `{type:'success', valueJson} | {type:'interrupted', toolName, input, toolCallId, payload}`; every await inside goes through `raceAgainstAbort(op, signal)`.
**Data Shape:** nested execution options: `toolCallId` = outer child id (`outer:tool-N`), parent's `context`/`experimental_context` forwarded under BOTH keys (run-code-mode.ts:268–273 — each falls back to the other).

### Decisive source
```ts
const output = executeHostTool(hostTool.execute.bind(hostTool), {...});
// inside executeHostTool:
if (isAsyncIterable(output)) {
  let finalOutput: unknown;
  for await (const part of output) finalOutput = part;   // drain to LAST part
  return finalOutput;
}
return await output;
```

**Flow:** pre-flight `throwIfAborted` → unknown-name / missing-execute hard errors (with availableTools list) → input JSON parsed + re-validated against `asSchema(schema).validate` when present (absent validate = pass-through) → approval gate (see approval-funnel capsule) → execute with `.bind(hostTool)` preserving `this` → async-generator tools DRAIN to the final yielded value (test :71–86 pins `{step: 2}`, not step 1) → success serialized under maxToolOutputBytes. Abort: listener added `{once:true}` + immediate re-check for already-aborted signals + listener removed in `finally`, so no leak across N bridge calls; the nested tool receives the runner-scoped signal (`context.abortSignal`) so cancellation reaches in-flight host work.
**Invariant:** validation errors and size limits fire BEFORE execute — the mocks-not-called assertions (exceptions.test.ts:46/:64/:174) are the contract, not incidental. Errors thrown by host tools are SANITIZED to generic `'Host tool failed.'` RunErrors unless they're CodeModeErrors (which ride the code-preservation channel) — sandbox code never sees host stack traces. Date.now skew test (:88–115) pins that host time is restored after async tool calls.
**Probe:** deterministic (repo root): `grep -nF 'Unknown tool:' packages/code-mode/src/tool-invocation.ts` → `59:`; `grep -nF 'does not have execute' packages/code-mode/src/tool-invocation.ts` → `65:`; `grep -cF 'raceAgainstAbort' packages/code-mode/src/tool-invocation.ts` → `6` call sites + def = 7 total lines (73/92/108/152/228); `grep -nF 'finalOutput = part' packages/code-mode/src/tool-invocation.ts` → `210:`. Direct tests: exceptions.test.ts:16/:45/:80, tool-invocation.test.ts:85 (`{step:2}`).
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "ai", query: "invokeHostTool raceAgainstAbort needsApproval", limit: 3 });` // verified live @9d9a73f (same anchor family as approval funnel): invokeHostTool :32-167 rank#1

## Verdict
Adopt validate-before-execute, last-part async-iterable semantics, and once-listener abort racing; adapt error sanitization depth to your threat model (full sanitization is the safe default); omit nothing.
