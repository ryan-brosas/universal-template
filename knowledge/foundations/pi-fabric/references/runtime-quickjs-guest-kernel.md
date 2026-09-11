<!-- capsule-v2 -->
# QuickJS guest kernel — how do you run untrusted async JS with host tools, timers, and hard deadlines, then tear it down without leaking a single handle?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** how do host calls into a sandboxed WASM guest stay alive across awaits, extend deadlines safely, and settle deterministically at teardown?

## Host-bridge promise pumping + deadline extension + grace settlement
**Path/Symbol:** `src/runtime/quickjs-runtime.ts` — host bridge `__fabricHostCall` (:886-935), deadline extension (:865-883), resolution race (:1014-1056), teardown `finally` (:1076-1121); facts consumer `src/actors/predicate.ts`.
**Signature:** `execute(code, hostCall, options): Promise<{value?, logs, terminationReason: "completed"|"timed_out"|"aborted"|"runtime_error", error?}>`; option `minimumTimeoutMsForHostCall?(ref, args): number|undefined`.
**Data Shape:** guest receives `π` (frozen string-map of JSON facts), `print` (bounded log buffer with one-shot truncation marker), `__fabricTokenBudget`; every host call is `(reference: string, args: object) → Promise` bridged through a single global function.

### Decisive source
```ts
const promise = context.newPromise();
pendingHostPromises.add(promise);
void promise.settled.then(() => pendingHostPromises.delete(promise));
// ... host work runs on the Node side via runAbortable(hostAbortController.signal, ...)
.then(value => { if (closing || promise.alive === false) return;
  const handle = jsonHandle(context, ...value); promise.resolve(handle); handle.dispose(); })
.finally(() => { if (!closing) runtime.executePendingJobs(); });   // pump the guest
// deadline extension BEFORE an awaited blocking call:
extendExecutionTimeout(reference, args);   // only ever pushes the deadline LATER
```

**Flow:** eval wraps the program as `Promise.race([__piFabricMain(), executionGate])` → Node races guest resolution against a deadline timer and the external abort signal, classifying the loser as timed_out/aborted → each host call registers its QuickJS promise, resolves/rejects it from Node, and pumps pending jobs so guest `await`s resume → teardown settles in order: clear timers → give in-flight host tasks a 250ms grace (`settleWithin`), abort stragglers and grant ONE more grace → reject every still-pending host promise with a cleanup error → drain microtasks with `setImmediate`, dispose remaining handles with `alive !== false` guards, dispose context.
**Invariant:** deadline extensions are monotone (a shorter request never shrinks the window) and applied before the blocking call starts; every native handle is disposed exactly once with liveness guards; a guest that never finishes still terminates through the deadline race. The predicate module builds on this exact contract (100ms/16MB/deny-all-tools).
**Probe:** `tests/quickjs-runtime.test.ts:253` ("waits for host calls without spinning the Node event loop"), :268/:278 (event-driven timer pump; timeout classification), :313/:335 ("extends the active deadline before / from the call start"), :357 ("aborts sibling host calls when guest workflow code fails").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "__fabricHostCall executePendingJobs minimumTimeoutMsForHostCall settleWithin", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bridge+grace-settlement shape for any QuickJS/pyodide-style guest embedding; adapt the reference-dispatch table to your tool surface; omit token-budget plumbing unless you meter guests. Twenty-plus direct tests pin timing, classification, and teardown — no coverage caveat.
