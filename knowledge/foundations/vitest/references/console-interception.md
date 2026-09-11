<!-- capsule-v2 -->
# Worker console interception — how does test-scoped `console.log` get buffered, attributed, ordered across streams, and shipped to the reporter?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@c3ba16b35847`); Codebase Memory `vitest`. **Question:** How do you capture every stdout/stderr write inside a worker, attribute it to the right task (even outside test bodies), preserve cross-stream interleaving, and deliver it as ONE rpc event per microtask burst?

## `createCustomConsole` Writable pair
**Path/Symbol:** `packages/vitest/src/runtime/console.ts:createCustomConsole` (36–221), attribution helper `getTaskIdByStack` (13–34), scheduler `schedule`/`sendBuffer`/`sendLog` (61–126).
**Signature:** `createCustomConsole(defaultState?: WorkerGlobalState): Console` (node `Console` over two custom `Writable`s).
**Data Shape:** per-task-id buffers `stdoutBuffer/stderrBuffer: Map<taskId, [data, trace?][]>`; timers map `{stdoutTime, stderrTime, cancel?}` per taskId; sentinel id `'__vitest__unknown_test__'`.

### Decisive source
```ts
function getTaskIdByStack(root: string) {
  const stack = new Error('STACK_TRACE_ERROR').stack?.split('\n')
  const index = stack.findIndex(line => line.includes('at Console.value'))
  const line = index === -1 ? null : stack[index + 2]      // skip Console + Writable frames
  const filepath = line?.match(/at\s(.*)\s?/)?.[1]
  return filepath ? relative(root, filepath) : UNKNOWN_TEST_ID
}

// group sync console.log calls with micro task
function schedule(taskId: string) {
  const timer = timers.get(taskId)!
  const { stdoutTime, stderrTime } = timer
  timer.cancel?.()                                          // replace pending flush
  timer.cancel = queueCancelableMicrotask(() => {
    if (stderrTime < stdoutTime) { sendStderr(taskId); sendStdout(taskId) }
    else                         { sendStdout(taskId); sendStderr(taskId) }
  })
}

const stdout = new Writable({
  write(data, encoding, callback) {
    const s = state()
    const id = s?.current?.id || s?.current?.suite?.id || s.current?.file.id
             || getTaskIdByStack(s.config.root)              // attribution ladder
    let timer = timers.get(id)
    if (timer) timer.stdoutTime = timer.stdoutTime || RealDate.now()   // FIRST-write wins
    else timers.set(id, { stdoutTime: RealDate.now(), stderrTime: 0 })
    ...
    if (state().config.printConsoleTrace) {
      const limit = Error.stackTraceLimit
      Error.stackTraceLimit = limit + 6
      const trace = new Error('STACK_TRACE').stack?.split('\n').slice(7).join('\n')
      Error.stackTraceLimit = limit
      buffer.push([data, trace])
    }
    else buffer.push([data, undefined])
    schedule(id); callback()
  },
})
// sendLog ships via state().rpc.onUserConsoleLog({type, content: content || '<empty line>',
//   taskId, time: time || RealDate.now(), size, origin})
```

**Flow:** any console method → node `Console` → the matching Writable.write → resolve attribution: CURRENT test id → enclosing suite id → file id → stack-derived relative path (`at Console.value` frame +2 lines; used for logs from module scope/timers) → sentinel. Record first-write wall time for that stream batch (kept if buffer already open), optionally capture a printConsoleTrace stack (limit+6, slice off 7 internal frames), append to the stream's per-task buffer, and (re)schedule a cancellable microtask flush. The flush sends whichever stream wrote FIRST first — decided by comparing recorded batch-start times — then empties both buffers and resets both timestamps to 0. stderr special case: a real `console.trace` keeps its own built-in stack and gets NO synthetic trace attached.
**Invariant:** (1) logs never hit real stdio in workers — reporters own presentation; (2) one burst of synchronous writes collapses into ≤2 rpc events (stdout+stderr), not one per line; (3) reported `time` is when the FIRST write of the batch happened, not flush time; ordering between streams within a burst is preserved at batch granularity by first-write comparison (individual lines within a stream keep write order); (4) `RealDate` captured at module load — fake timers can't corrupt log timestamps; (5) empty output still delivers as `<empty line>` so silent writes are visible.

**Probe:** `test/e2e/test/console.test.ts` — inline-snapshot pins `stdout | trace.test.ts > …` blocks with `❯ file:line:col` traces under `printConsoleTrace`, plus the console.trace exception ("shows built-in stack because we don't intercept it"). Node-side storage contract (`updateUserLog` appends to `task.logs`) at `packages/vitest/src/node/state.ts:247-255`. Caveat: e2e needs installed deps; source read byte-for-byte at pinned HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", file_pattern: "packages/vitest/src/runtime/console.ts", limit: 14 });
// observed all 12 module members incl. createCustomConsole 36-221, schedule 61-75,
// sendBuffer 84-107, getTaskIdByStack 13-34.
```

## Verdict
Adopt per-task buffering with microtask coalescing, first-write timestamping, and the four-rung attribution ladder ending in a stack-derived fallback. Adapt transport (any event bus), trace depth constants, and the sentinel id. Omit groupIndentation/colorMode wiring unless you reuse node's Console class.
