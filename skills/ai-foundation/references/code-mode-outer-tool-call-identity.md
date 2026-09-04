<!-- capsule-v2 -->
# Code-mode outer tool-call identity — invocation ids, child call ids, and context forwarding to nested tools

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How are the outer AI-SDK tool call, inner host calls, and interrupts identified so UIs and logs can correlate them?

## Three-tier id scheme
**Path/Symbol:** `packages/code-mode/src/run-code-mode.ts` — id minting :85–88 (`code-mode-${++invocationCounter}` fallback), child ids :267 (`${outerToolCallId}:tool-${context.requestIndex}`), interrupt ids `${childId}:interrupt`, context forwarding :268–282.
**Signature:** `outerToolCallId = toolExecutionOptions.toolCallId ?? continuation.outerToolCallId ?? 'code-mode-' + ++invocationCounter`; `requestIndex` comes from the runner's per-program bridge counter (matches `/^interrupt-(\d+)$/` on resume decode).
**Data Shape:** nested options = `{toolCallId: childId, messages: parent's ?? [], abortSignal: runner-scoped, context/experimental_context forwarded under both spellings}`.

### Decisive source
```ts
const forwardedContext =
  input.toolExecutionOptions?.context ??
  input.toolExecutionOptions?.experimental_context;
const forwardedExperimentalContext =
  input.toolExecutionOptions?.experimental_context ??
  input.toolExecutionOptions?.context;   // BOTH keys carry EITHER spelling
```

**Flow:** generate() executes the code_mode tool with a real toolCallId → every sandbox→host bridge call gets `outer:N` as ITS toolCallId, so a UI renders children under the right parent while approval requests/interrupts reference the same lineage (`outer:tool-2:interrupt`, test :73 pins exact format). Context forwarding is deliberately symmetric across the renamed/experimental split — tools reading either key observe the caller's value (test :117–141 pins `{requestId:'req-1'}` arrival). The module-level counter only fires for bare runCodeMode usage without execution options; continuation resumes REUSE the signed outerToolCallId instead of minting (:87), keeping ids stable across processes.
**Invariant:** child numbering is per-RUN requestIndex from the worker bridge, not a global sequence — two concurrent invocations both start at `tool-0`. A porter who regenerates the outer id on resume breaks ledger matching (assertInterruptMatchesLedger compares it). Messages default to `[]` not undefined, so nested tools can rely on array shape.
**Probe:** deterministic (repo root): `grep -nF 'code-mode-${++invocationCounter}' packages/code-mode/src/run-code-mode.ts` → `88:`; `grep -nF ':tool-' packages/code-mode/src/run-code-mode.ts | head -3` → lines 267/301/542; direct-test anchors: tool-invocation.test.ts:133 (`toolCallId: 'outer'`), :140 (`seenContexts` equality), approval-continuation.test.ts:73 (`outer:tool-2:interrupt`).
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "ai", query: "invokeCodeModeTool getHostFunctionContext requestIndex", limit: 3 });` // verified family live @9d9a73f: invokeHostTool :32-167 anchor; invokeCodeModeTool is closure-local (documented graph-invisible)

## Verdict
Adopt hierarchical ids and dual-key context mirroring; adapt prefixes to your namespace; omit nothing — id stability across resume is load-bearing for the whole capability design.
