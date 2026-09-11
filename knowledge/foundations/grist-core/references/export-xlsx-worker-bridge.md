<!-- capsule-v2 -->
# streamXLSX worker-thread bridge — how does grist stream an Excel export from a pooled worker over a MessagePort without deadlocking the request?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the exact wiring between the HTTP request, the piscina pool, the RPC channel, and cancellation — and which lifecycle events end the download?

## Pool + MessageChannel + grain-rpc: three channels, each with exactly one job
**Path/Symbol:** `app/server/lib/ExportXLSX.ts` whole file (92L) — import-time recursion guard (:29–31), module-level `exportPool` Piscina config (:34–40), `streamXLSX` (:45–92) with `MessageChannel` port pair (:50), rpc impl/stub registration (:52–58), abort wiring (:61–71), pooled run with transferList (:73–77), dispatch `run("makeXLSXFromOptions", options)` (:81).
**Signature:** `streamXLSX(activeDoc: ActiveDoc, req: express.Request, outputStream: Writable, options: ExportParameters): Promise<void>`.
**Data Shape:** task payload `{ port: port2, testDates, args }`; `testDates = (req.hostname === "localhost")` — deterministic workbook metadata ONLY on localhost. Pool: `minThreads: 0, maxThreads: 4, maxQueue: 100, idleTimeout: 10_000`.

### Decisive source
```ts
// If this file is imported from within a worker thread, we'll create more thread pools from each
// thread, with a potential for an infinite loop of doom. Better to catch that early.
if (Piscina.isWorkerThread) {
  throw new Error("ExportXLSX must not be imported from within a worker thread");
}

const exportPool = new Piscina({
  filename: __dirname + "/workerExporter.js",
  minThreads: 0,
  maxThreads: 4,
  maxQueue: 100,          // Fail if this many tasks are already waiting for a thread.
  idleTimeout: 10_000,    // Drop unused threads after 10s of inactivity.
});
```
```ts
port1.on("close", () => {
  outputStream.end();
  req.off("close", cancelWorker);
});
addAbortHandler(req, outputStream, cancelWorker);
const run = (method: string, ...args: any[]) => exportPool.run({ port: port2, testDates, args }, {
  name: method,
  signal: abortController.signal,
  transferList: [port2],
});
```
**Invariant:** the WORKER owns termination — it closes its port when the file is done, and only THAT close event ends the HTTP response (`outputStream.end()`) and detaches the cancel listener. Client disconnects flow the other way: `addAbortHandler(req, …)` turns request-close into `abortController.abort()`, which is passed as the piscina task signal so the worker's await rejects and cleanup happens there. Error rehydration is required because thrown objects cross threads stripped to plain data: `throw (e instanceof Error) ? e : Object.assign(new Error(e.message), e)` restores `.status` etc. (workerExporter throws `{ message, ...e }` plain objects for exactly this). The `maxQueue: 100` comment is the backpressure contract: fail fast rather than queue unbounded exports.

**Flow:** guard → build ports → rpc bridges main-thread ActiveDocSource (impl) ↔ worker stub, and worker's chunk posts ↔ `outputStream.write` (`rpc.on("message", ...)`) → register abort handler → dispatch ONE method name (`makeXLSXFromOptions`) carrying the ExportParameters → finally-block closes BOTH ports even on error (double-close safe). Method selection lives in the worker (`doMakeXLSXFromOptions` branches viewSectionId/tableId/whole-doc), keeping the main thread free of export logic.

**Probe:** deterministic greps (coverage caveat: no dedicated unit file):
```bash
cd $REFERENCE_ROOT/grist-core
grep -n "Piscina.isWorkerThread" app/server/lib/ExportXLSX.ts     # 29
grep -n "transferList: \[port2\]" app/server/lib/ExportXLSX.ts    # 76
grep -n "req.off(\"close\", cancelWorker)" app/server/lib/ExportXLSX.ts  # 68
grep -n "Object.assign(new Error(e.message), e)" app/server/lib/ExportXLSX.ts  # 86
```
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "streamXLSX exportPool Piscina", limit: 5 });
// → grist-core.app.server.lib.ExportXLSX.streamXLSX Function app/server/lib/ExportXLSX.ts 45-92
```

## Verdict
Adopt for any CPU-heavy streaming response (spreadsheets, PDFs, archives): dedicated pool with bounded queue, one MessagePort per task transferred not cloned, role-named RPC service, worker-owned completion signal, client-abort plumbed as AbortSignal into the pool task, and cross-thread error rehydration at the boundary. Adapt thread counts/queue depth to your memory budget. Omit the localhost testDates knob unless you need byte-stable artifacts in tests — but if you do keep it hostname-derived like upstream so prod never sees static dates.
