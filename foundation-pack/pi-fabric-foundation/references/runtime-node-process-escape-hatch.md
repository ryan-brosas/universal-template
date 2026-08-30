<!-- capsule-v2 -->
# Node-process runtime — the trusted-code escape hatch: process-per-program with deadline extension, host-call settlement, and SIGKILL hygiene

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** QuickJS caps at WASM32 memory and lacks Node — how do you run the same guest contract in a real Node child without letting a hung guest or hung host call wedge the host forever?

## Connected graph-selected seam
**Path/Symbol:** `src/runtime/node-process-runtime.ts` whole file (188L): `NodeProcessRuntime.execute` (:35-187), `HOST_TASK_SETTLE_GRACE_MS = 250` (:27), `send` guard (:29-32), `finish` single-settle latch (:79-91), `scheduleDeadline`/`extendDeadline` (:92-108), abort handler (:110-118), message pump (:120-157), `child.once("error")` (:158-165), `child.once("exit")` (:166-175); consumes `settleWithin`/`runAbortable` from `src/async-settlement.ts:35-65`; child source inlined as `NODE_PROCESS_CHILD_SOURCE` (`src/runtime/node-process-child-source.ts`, 102L).
**Signature:** `execute(code, hostCall, options)` → same `FabricSandboxResult {value, logs, terminationReason: "completed"|"aborted"|"timed_out"|"runtime_error", error?}` as QuickJS — runtimes are interchangeable behind `FabricSandboxOptions` (`minimumTimeoutMsForHostCall` included).
**Data Shape:** IPC messages `{type:"execute", setup, code, strings?, tokenBudget?, maxLogChars}` → child `{type:"call", id, ref, args}` / host `{type:"response", id, ok, value|error}` → child `{type:"result", result}`.

### Decisive source
```ts
const heapLimitMb = Math.max(16, Math.floor(options.memoryLimitBytes / (1024 * 1024)));
const child = spawn(
  resolveScriptRuntimeSync({ requireNode: true }),
  [`--max-old-space-size=${heapLimitMb}`, "--input-type=module", "--eval", NODE_PROCESS_CHILD_SOURCE],
  { stdio: ["ignore", "ignore", "ignore", "ipc"] },
);
// result path: settleWithin(hostTasks, HOST_TASK_SETTLE_GRACE_MS) before finish(message.result)
```

**Flow:** pre-checks return SYNTHETIC results (pre-aborted signal ⇒ `{terminationReason:"aborted"}`; non-safe-integer memory ⇒ runtime_error) instead of throwing. One disposable child per program: heap flag derived from the SAME `memoryLimitBytes` config QuickJS uses (floor 16MB; no upper clamp here because Node accepts what WASM cannot — the 5GB test proves crossing the QuickJS ceiling works). stdio fully silenced, only fd3 ipc. Deadline timer is unref'd and RE-SCHEDULED by `extendDeadline(ref,args)` on EVERY incoming call using `options.minimumTimeoutMsForHostCall` — extension only moves the deadline LATER (never shortens). Host calls run under a SEPARATE `hostAbortController` so finishing one program's calls can't be confused with the outer signal; each task tracked in `hostTasks`. On child `result`: flip `finishing` (rejects late calls), clear deadline, abort host tasks if child failed, then `settleWithin(hostTasks, 250ms)`; if still pending after grace ⇒ abort them with `"Fabric guest execution ended before its host calls settled"` and wait ONE more grace window before delivering. On child `exit` WITHOUT result (OOM kill, crash) ⇒ runtime_error naming exit code/signal + "it may have exceeded its memory limit". External abort ⇒ aborted + child SIGKILL'd via finish(). `finish` is idempotent (settled latch), removes all listeners, disconnects, SIGKILLs live children.
**Invariant:** (1) The guest CANNOT see `process` or `require` even though it runs in Node — the child source evaluates code inside an async wrapper that shadows globals (`tests :10` pins `typeof process === "undefined"`), preserving sandbox semantics while gaining real memory/time limits. (2) Fire-and-forget host calls are BOUNDED twice: program completion waits ≤250ms×2 for issued calls, and non-cooperative siblings after a guest failure don't extend the wall-clock beyond ~2s (both timing tests pin <2000ms). (3) Deadline extension is monotonic (`if (nextDeadlineAt <= deadlineAt) return`) and driven ONLY by the host-side classifier — guest code can never negotiate its own timeout. (4) Every terminal path funnels through ONE `finish()` so exactly one result resolves and cleanup (timer/listener/kill) runs once. (5) The executor binary resolves via `resolveScriptRuntimeSync({requireNode:true})` — the same launcher logic agent transports use.
**Probe:** `tests/node-process-runtime.test.ts:10` ("runs guest code in a disposable process and bridges host calls"), `:30` "normalizes the string shorthand for tools.search", `:45` ("extends the active deadline for a long host call"), `:65` "preserves named string payloads", `:82` ("accepts a heap limit above the QuickJS WASM32 ceiling"), `:93` ("waits for issued host calls before completing"), `:108` ("does not wait for a non-cooperative sibling host call after guest failure"), `:126` "bounds non-cooperative fire-and-forget host calls", `:139` "forcibly terminates synchronous infinite loops", `:150` "surfaces unbounded recursion as a runtime error", `:161` "terminates the child process when externally aborted". Config ceiling pairing: `tests/config.test.ts:106` + `src/config.ts:241-249` (`QUICKJS_MAX_MEMORY_LIMIT_BYTES = 0xffff_ffff` vs `MAX_EXECUTOR_MEMORY_LIMIT_BYTES = min(MAX_SAFE_INTEGER, totalmem)`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "NodeProcessRuntime execute extendDeadline settleWithin HOST_TASK_SETTLE_GRACE_MS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt process-per-program with the monotonic host-call deadline extension and bounded settlement windows; adapt the launcher resolution and message schema. Porters get this wrong by trusting the child to self-terminate (OOM), waiting forever for fire-and-forget host calls, or allowing deadline SHRINKAGE mid-run.
