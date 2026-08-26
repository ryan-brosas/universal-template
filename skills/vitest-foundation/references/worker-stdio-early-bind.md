<!-- capsule-v2 -->
# Worker stdio early-bind flush — how is worker output guaranteed delivered before the parent tears the worker down, even when tests stub process.stdout?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@c3ba16b3`); Codebase Memory `vitest`. **Question:** Why must the stdio flush protocol capture stream writers at module load, and where does the flush sit relative to completion signaling?

## Module-load-bound write references
**Path/Symbol:** `packages/vitest/src/runtime/workers/init.ts:streams` (:52–55), `flushStdio` (:65–76), call sites :197/:257 (run/collect) and :308/:315 (stop success + catch).
**Signature:** `const streams = [{ write: process.stdout.write.bind(process.stdout) }, { write: process.stderr.write.bind(process.stderr) }]`; `function flushStdio(): Promise<unknown>`.
**Data Shape:** A two-element module-level array holding BOUND plain functions — not live stream objects. `flushStdio` maps over this array; each element's `write('', cb)` resolves when the underlying backpressure queue drains; a throwing `write` resolves anyway (never rejects).

### Decisive source
```ts
const streams = [
  { write: process.stdout.write.bind(process.stdout) },
  { write: process.stderr.write.bind(process.stderr) },
]
// In worker threads stdio is proxied to the parent over a MessagePort with a
// backpressure protocol: ... An empty write's callback only fires after every
// previously buffered chunk has been acked, so awaiting it before signaling
// completion guarantees the output reached the parent.
function flushStdio(): Promise<unknown> {
  const flush = (stream: (typeof streams)[number]) =>
    new Promise((resolve) => {
      try { stream.write('', () => resolve(undefined)) }
      catch { resolve(undefined) }
    })
  return Promise.all(streams.map(stream => flush(stream)))
}
```

**Flow:** worker init captures both bound writes ONCE at module load → after each run/collect completes AND on stop (both success and error paths), `await flushStdio()` runs BEFORE `send({ type: 'testfileFinished' | 'stopped' })` → the empty-write callback fires only after every buffered chunk was acked by the parent → then the pool learns it may reuse/terminate the worker.
**Invariant:** The binding must happen at MODULE LOAD: tests can (and do — #11020) overwrite `process.stdout.write`, and an unbound late lookup would await a no-op fake that never drains real buffers. In worker_threads, stdio is MessagePort-proxied with per-chunk parent acks; `thread.terminate()` after `testfileFinished` would drop still-buffered chunks — the pre-signal await is the ONLY guarantee. The flush never rejects (catch-resolve). Forks pay a no-op cost (OS pipes). A porter who binds lazily inside flushStdio reintroduces the hang/loss bug whenever test code stubs stdout.
**Probe:** `grep -c 'process.stdout.write.bind' packages/vitest/src/runtime/workers/init.ts` = 1 (:53); `grep -c 'await flushStdio()' …` = 4 (:197 run, :257 collect, :308 stop-try, :315 stop-catch); upstream regression twin `test/unit/test/stubbed-process.test.ts` — "should not hang" calls `vi.unstubAllGlobals(); process.stdout.write = () => true` post-import and asserts termination. Verified on disk at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "flushStdio streams process.stdout.write bind testfileFinished", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt early-bound stream handles + drain-before-completion-signal for any host multiplexing child output through acked transports. Adapt the transport specifics (MessagePort vs pipes) and which lifecycle events trigger the flush. Omit nothing if your workers are threads; forks may keep it as cheap insurance.
