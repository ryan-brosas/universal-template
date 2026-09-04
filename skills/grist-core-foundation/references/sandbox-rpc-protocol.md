<!-- capsule-v2 -->
# NSandbox FIFO RPC — how do you run request/reply over raw pipes with no message IDs?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How does the JS host call into an isolated Python process and get answers back reliably when there is no correlation ID on any message — including what must happen when the child dies mid-call?

## Call/response multiplexed by strict FIFO order over one marshalled channel
**Path/Symbol:** `app/server/lib/NSandbox.ts:NSandbox` (whole class 124–518): `pyCall` (249–264), `_pyCallWait` (372–388), `_sendData` (417–436), `_onSandboxData` (441–449), `_onSandboxMsg` (480–517), `_close` (390–397), `_onSandboxClose` (454–462), `_sandboxClosedError` (469–475), `shutdown` (217–241), `reportMemoryUsage` (273–277).
**Signature:** `pyCall(funcName: string, ...varArgs: unknown[]): Promise<any>`; `shutdown(): Promise<[code, signal]>`; constructor `(options: ISandboxOptions, spawner: SpawnFn = sandboxed)`.
**Data Shape:** wire messages are a marshalled pair `[msgCode, payload]` where `msgCode` is `CALL`(null) | `DATA`(true) | `EXC`(false) from `sandboxUtil`; pending calls live in `_pendingReads: [resolve, reject][]`; marshaller is `{ stringToBuffer: false, version: 2 }`, unmarshaller decodes with `bufferToString: true`. Optional replay recording dir per process (`RECORD_SANDBOX_BUFFERS_DIR` + ISO-timestamp subdir; `input`/`output` append-only files).

### Decisive source
```ts
public async pyCall(funcName: string, ...varArgs: unknown[]): Promise<any> {
  const startTime = Date.now();
  this._sendData(sandboxUtil.CALL, Array.from(arguments));
  const slowCallCheck = setTimeout(() => { log.rawWarn("Slow pyCall", {...}); }, 10000);
  try {
    const { data, numBytes } = await this._pyCallWait(funcName, startTime);
    ...
// _pyCallWait just queues:  this._pendingReads.push([resolve, reject]);
// reply side (_onSandboxMsg):
const resolvePair = this._pendingReads.shift();
if (resolvePair) {
  if (msgCode === sandboxUtil.EXC)      { resolvePair[1](new Error(data)); }
  else if (msgCode === sandboxUtil.DATA){ resolvePair[0]({ data, numBytes }); }
}
```

**Flow:** `pyCall` writes `[CALL, [funcName, ...args]]` → pushes its resolve pair onto the FIFO → the sandbox's answer arrives as `[DATA|EXC, value]` and is matched to whichever promise has been waiting longest (`shift()`). Calls FROM the sandbox ride the same channel: `CALL` with `[fname, args...]` resolves against `_exportedFunctions` and always replies (`DATA` result or `EXC err.toString()`); a failed reply-send itself is caught and only logged. Child `close`/`error` events are attached in the constructor before anything else can race ("especially 'error' which may lead to node exiting"); `close` while write-side still open logs "unexpectedly exited". Pipe close rejects ALL pending reads with `SandboxError("PipeFromSandbox is closed: <last stderr line>")`.
**Invariant:** ordering IS the correlation — never interleave two logical calls out of order on one NSandbox, and never add an out-of-band reply path. A dead child must surface as rejection of every queued pyCall (never a hang): the test kills the sandbox between calls and asserts first in-flight call rejects, then the NEXT call fails immediately because `_isReadClosed` short-circuits `_sendData`. Error text deliberately prefers the last raw stderr line over protocol error results ("more reliable").
**Probe:** `test/server/Sandbox.ts:114` "sandbox.pyCall" — echo/operation round-trips (:119–124) and kill-mid-call ladder :140–156 ("should not succeed"/"should not hang"/second call immediate reject).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "NSandbox pyCall shutdown pendingReads", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the FIFO + three-code envelope whenever you need sync-style RPC across a process boundary with minimal protocol machinery, plus the reject-all-pending-on-close discipline and slow-call warning timer (10s). Adapt pipe wiring: minimal 3-pipe mode uses stdin/stdout for data and logs stderr; legacy 5-pipe mode takes FDs 3/4 for data (constructor picks by `minimalPipeMode !== false`, callback-based `getData/sendData` replaces pipes entirely for in-process workers). Omit gvisor checkpoint special-casing and RECORD_SANDBOX_BUFFERS replay capture unless you are debugging the engine.
