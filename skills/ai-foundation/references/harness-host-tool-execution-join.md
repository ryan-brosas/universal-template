<!-- capsule-v2 -->
# Harness host-tool execution join — when the runtime streams tool calls faster than the host executes them, where do failures and step boundaries meet?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** Host-side tools run OUTSIDE the runtime's control loop — how do you prevent unhandled rejections, keep step results complete, and normalize generator `execute` functions?

## Tracked execution set joined at every step boundary
**Path/Symbol:** `packages/harness/src/agent/internal/run-prompt.ts` — execution tracker (:275–297), `maybeExecuteHostTool` (:1114–1185), boundary joins at finishForHostInputPause :354–370 / finish-step :839–853 / terminal drain :1023.
**Signature:** `startHostToolExecution(p: Promise<void>): void`; `waitForOutstandingHostToolExecutions(): Promise<void>`; `maybeExecuteHostTool(...): Promise<{executed:false}|{executed:true,outcome}> `.
**Data Shape:** array used as a drain-on-read queue (`splice(0)`); outcome = `{ok:true,output}|{ok:false,error}`.

### Decisive source
```ts
const startHostToolExecution = (execution: Promise<void>): void => {
  outstandingHostToolExecutions.push(execution);
  // The execution is joined at the next step boundary. Attach a rejection
  // handler immediately so failures cannot become unhandled in the
  // meantime; awaiting the original promise still propagates the failure.
  void execution.catch(() => {});
};
...
const results = await Promise.allSettled(executions);
const failedExecution = results.find(result => result.status === 'rejected');
if (failedExecution != null) throw failedExecution.reason;
```

**Flow:** every non-provider-executed tool call starts an async task; each `finish-step`, each approval pause, and the final drain await the FULL set before completing the step, so no StepResult closes with an in-flight tool; the first rejection is re-thrown after all settle. Inside `maybeExecuteHostTool`, generator `execute`s are normalized through core `executeTool`: intermediate `yield`s project as consumer-only `preliminary: true` parts (workDir-stripped) while ONLY the last value is submitted to the runtime via `control.submitToolResult` — errors submit `{ error: String(err) }, isError: true` instead of throwing into the stream loop.
**Invariant:** Exactly one tool result reaches the runtime per callId (preliminary values NEVER cross the bridge); a failed execution surfaces once — at the join — never as an unhandled rejection and never twice.
**Probe:** deterministic probes: `grep -c 'Promise.allSettled' packages/harness/src/agent/internal/run-prompt.ts` → `1`; `grep -c 'submitToolResult' packages/harness/src/agent/internal/run-prompt.ts` → `6`; direct test `harness-agent.test.ts:1982` ("host-side tools are executed and the result is submitted back").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "maybeExecuteHostTool runPrompt harness", limit: 4 });
// verified live @9d9a73f — rank#2 maybeExecuteHostTool :1114-1185, rank#3 runPrompt :68-1076
```

## Verdict
Adopt the immediate-.catch + allSettled join pattern for any out-of-band async work feeding a step result; adapt preliminary-part naming to host's stream vocabulary; omit generator normalization if host execute functions are plain async.